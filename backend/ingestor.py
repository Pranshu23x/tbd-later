"""
Crustdata API Integration — Search → Enrich Pipeline
=====================================================
Uses the official Crustdata API workflow:
  1. /company/search       — lightweight discovery (0.03 credits/result)
  2. /company/enrich       — full profiles by crustdata_company_id (2 credits/record)
  3. /company/identify     — FREE entity resolution for name/domain lookups
  4. /company/search/autocomplete — FREE field value discovery

Docs: https://docs.crustdata.com
"""

import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

CRUSTDATA_API_TOKEN = os.getenv("CRUSTDATA_API_TOKEN")
BASE_URL = "https://api.crustdata.com"

def get_headers():
    if not CRUSTDATA_API_TOKEN:
        raise ValueError("CRUSTDATA_API_TOKEN not found in environment variables.")
    return {
        "Authorization": f"Bearer {CRUSTDATA_API_TOKEN}",
        "x-api-version": "2025-11-01",
        "Content-Type": "application/json"
    }


# ── Company Identify (FREE) ─────────────────────────────────────────────

def identify_company(name: str) -> dict | None:
    """
    FREE entity resolution. Returns basic_info + crustdata_company_id.
    Use this to resolve a name to an ID, then enrich by ID for full data.
    """
    payload = {"names": [name]}
    try:
        r = requests.post(f"{BASE_URL}/company/identify", json=payload,
                          headers=get_headers(), verify=False)
        if r.status_code != 200:
            return None
        data = r.json()
        if not data or not isinstance(data, list):
            return None
        matches = data[0].get("matches", [])
        if not matches:
            return None
        # Return best match (highest confidence)
        best = max(matches, key=lambda m: m.get("confidence_score", 0))
        return best.get("company_data", {})
    except Exception:
        return None


# ── Company Enrich (by ID — full profile) ────────────────────────────────

def enrich_by_ids(company_ids: list[int]) -> list[dict]:
    """
    Batch enrich companies by crustdata_company_id.
    Returns full profiles: headcount, funding, revenue, hiring, people, etc.
    Cost: 2 credits per record.
    """
    if not company_ids:
        return []
    payload = {
        "crustdata_company_ids": company_ids,
        "fields": [
            "basic_info", "headcount", "funding", "revenue",
            "hiring", "people", "locations", "taxonomy",
            "followers", "competitors"
        ]
    }
    try:
        r = requests.post(f"{BASE_URL}/company/enrich", json=payload,
                          headers=get_headers(), verify=False)
        if r.status_code != 200:
            print(f"  [enrich] Error {r.status_code}: {r.text[:200]}")
            return []
        data = r.json()
        if not data or not isinstance(data, list):
            return []

        profiles = []
        for entry in data:
            matches = entry.get("matches", [])
            if not matches:
                continue
            best = max(matches, key=lambda m: m.get("confidence_score", 0))
            cd = best.get("company_data", {})
            if cd:
                profiles.append(_normalize_enriched(cd))
        return profiles
    except Exception as e:
        print(f"  [enrich] Exception: {e}")
        return []


def _normalize_enriched(cd: dict) -> dict:
    """
    Normalize the full enriched company_data into our standard format.
    """
    bi = cd.get("basic_info", {})
    hc = cd.get("headcount", {})
    fund = cd.get("funding", {})
    rev = cd.get("revenue", {}).get("estimated", {})
    hiring = cd.get("hiring", {})
    people = cd.get("people", {})

    return {
        "id": cd.get("crustdata_company_id") or bi.get("crustdata_company_id"),
        "name": bi.get("name", "Unknown"),
        "domain": bi.get("primary_domain", ""),
        "capital": {
            "funding_total": fund.get("total_investment_usd"),
            "last_round_amount": fund.get("last_round_amount_usd"),
            "last_funding_date": fund.get("last_fundraise_date"),
            "last_round_type": fund.get("last_round_type"),
            "revenue_lower": rev.get("lower_bound_usd"),
            "revenue_upper": rev.get("upper_bound_usd"),
        },
        "muscle": {
            "headcount": hc.get("total"),
            "headcount_growth_percent": hc.get("growth_percent", {}).get("6m") or hc.get("growth_percent", {}).get("yoy") if isinstance(hc.get("growth_percent"), dict) else hc.get("growth_percent"),
            "by_role": hc.get("by_role_absolute", {}),
        },
        "arsenal": {
            "industry": bi.get("industries", []),
            "year_founded": bi.get("year_founded"),
            "company_type": bi.get("company_type"),
            "hiring_openings": hiring.get("openings_count"),
            "hiring_growth": hiring.get("openings_growth_percent"),
        },
        "backing": {
            "investor_list": fund.get("investors", []),
        },
        "people": {
            "founders": people.get("founders", []),
            "cxos": people.get("cxos", []),
            "decision_makers": people.get("decision_makers", []),
        },
    }


# ── Company Search (lightweight discovery) ───────────────────────────────

def search_by_thesis(industry: str = None, min_headcount: int = None,
                     max_headcount: int = None, location=None, limit: int = 10) -> list[dict]:
    """
    Search for companies matching an investment thesis.
    Uses /company/search with proper filter structure.

    Args:
        industry: Crustdata industry label (use autocomplete to discover exact values)
        min_headcount: Minimum employee count
        max_headcount: Maximum employee count (use for startup searches)
        min_growth_percent: Minimum headcount growth percent (usually 6m or yoy)
        location: ISO3 code string ("USA") or list (["DEU","FRA"])
        limit: Max results (1-1000)
    """
    conditions = []

    if industry:
        conditions.append({
            "field": "taxonomy.professional_network_industry",
            "type": "=",
            "value": industry
        })

    if min_headcount:
        conditions.append({
            "field": "headcount.total",
            "type": ">",
            "value": min_headcount
        })

    if max_headcount:
        conditions.append({
            "field": "headcount.total",
            "type": "=<",
            "value": max_headcount
        })

    if min_growth_percent:
        # Prefer 6m growth if specified, otherwise fallback to yoy
        conditions.append({
            "field": "headcount.growth_percent.6m",
            "type": ">",
            "value": min_growth_percent
        })

    if location:
        if isinstance(location, list):
            conditions.append({
                "field": "locations.country",
                "type": "in",
                "value": location
            })
        else:
            conditions.append({
                "field": "locations.country",
                "type": "=",
                "value": location
            })

    payload = {
        "limit": limit,
        "sorts": [{"column": "headcount.growth_percent.6m", "order": "desc"}],
        "fields": [
            "crustdata_company_id",
            "basic_info.name",
            "basic_info.primary_domain",
            "headcount.total",
            "headcount.growth_percent.6m",
            "headcount.growth_percent.yoy",
            "locations.country",
            "funding.total_investment_usd",
            "funding.investors",
            "revenue.estimated.lower_bound_usd",
            "taxonomy.professional_network_industry"
        ]
    }

    if len(conditions) > 1:
        payload["filters"] = {"op": "and", "conditions": conditions}
    elif len(conditions) == 1:
        payload["filters"] = conditions[0]

    try:
        r = requests.post(f"{BASE_URL}/company/search", json=payload,
                          headers=get_headers(), verify=False)
        if r.status_code != 200:
            print(f"  [search] Error {r.status_code}: {r.text[:200]}")
            return []
        return r.json().get("companies", [])
    except Exception as e:
        print(f"  [search] Exception: {e}")
        return []


# ── Fetch Company Profile (Identify → Enrich) ───────────────────────────

def fetch_company_profile(company_name: str) -> dict | None:
    """
    High-level: resolve a company name to full profile.
    Step 1: Identify (FREE) to get crustdata_company_id
    Step 2: Enrich by ID for full data
    """
    # Step 1: Identify
    identified = identify_company(company_name)
    if not identified:
        return None

    bi = identified.get("basic_info", {})
    cid = identified.get("crustdata_company_id") or bi.get("crustdata_company_id")

    if not cid:
        # Return basic info only
        return {
            "id": None,
            "name": bi.get("name", company_name),
            "domain": bi.get("primary_domain", ""),
            "capital": {}, "muscle": {}, "arsenal": {}, "backing": {}, "people": {}
        }

    # Step 2: Enrich by ID
    enriched = enrich_by_ids([cid])
    if enriched:
        return enriched[0]

    # Fallback to basic info
    return {
        "id": cid,
        "name": bi.get("name", company_name),
        "domain": bi.get("primary_domain", ""),
        "capital": {}, "muscle": {}, "arsenal": {}, "backing": {}, "people": {}
    }


# ── Search + Enrich Pipeline ────────────────────────────────────────────

def search_and_enrich(industry: str = None, min_headcount: int = None,
                      location=None, limit: int = 10) -> list[dict]:
    """
    Full pipeline: Search → collect IDs → batch Enrich.
    Returns fully enriched company profiles.
    """
    # Step 1: Search
    results = search_by_thesis(industry, min_headcount, location, limit)
    if not results:
        return []

    # Step 2: Collect IDs
    ids = [c.get("crustdata_company_id") for c in results if c.get("crustdata_company_id")]
    if not ids:
        return results  # Return search results as-is

    # Step 3: Batch enrich
    enriched = enrich_by_ids(ids)
    return enriched if enriched else results


# ── Autocomplete (FREE) ─────────────────────────────────────────────────

def autocomplete_field(field: str, query: str = "", limit: int = 10) -> list[str]:
    """
    Discover valid field values for search filters. FREE.
    Example: autocomplete_field("taxonomy.professional_network_industry", "soft")
    """
    payload = {"field": field, "query": query, "limit": limit}
    try:
        r = requests.post(f"{BASE_URL}/company/search/autocomplete", json=payload,
                          headers=get_headers(), verify=False)
        if r.status_code != 200:
            return []
        suggestions = r.json().get("suggestions", [])
        return [s.get("value") for s in suggestions]
    except Exception:
        return []


# ── Legacy dual_fetch (compatibility) ────────────────────────────────────

def dual_fetch(target_name: str, rival_name: str = None):
    target_profile = fetch_company_profile(target_name)
    rival_profile = fetch_company_profile(rival_name) if rival_name else None
    return {
        "target": {"company": target_profile or {"name": target_name}, "employees": []},
        "rival": {"company": rival_profile or {"name": rival_name or "Industry Average"}, "employees": []}
    }
