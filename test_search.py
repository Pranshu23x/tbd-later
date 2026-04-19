"""Full combined test matching the exact query the orchestrator sends."""
import requests

API_KEY = "9cfe46e68772efc3a32bea818a9e188a8f0efd47"
headers = {
    "Authorization": f"Bearer {API_KEY}",
    "x-api-version": "2025-11-01",
    "Content-Type": "application/json"
}

payload = {
    "filters": {
        "op": "and",
        "conditions": [
            {"field": "taxonomy.professional_network_industry", "type": "=", "value": "Technology, Information and Internet"},
            {"field": "headcount.total", "type": ">", "value": 10},
            {"field": "headcount.total", "type": "=<", "value": 100},
            {"field": "locations.country", "type": "in", "value": ["DEU", "FRA", "GBR", "NLD", "ESP", "ITA", "SWE", "IRL"]}
        ]
    },
    "sorts": [{"column": "headcount.total", "order": "desc"}],
    "limit": 10,
    "fields": [
        "crustdata_company_id", "basic_info.name", "basic_info.primary_domain",
        "basic_info.year_founded", "headcount.total", "locations.hq_country",
        "funding.total_investment_usd", "funding.investors",
        "revenue.estimated.lower_bound_usd", "taxonomy.professional_network_industry"
    ]
}

r = requests.post("https://api.crustdata.com/company/search", headers=headers, json=payload)
print(f"Status: {r.status_code}")
data = r.json()
companies = data.get("companies", [])
print(f"Found: {len(companies)} companies\n")

for c in companies:
    bi = c.get("basic_info", {})
    hc = c.get("headcount", {}).get("total", "?")
    loc = c.get("locations", {}).get("hq_country", "?")
    fund = c.get("funding", {}).get("total_investment_usd")
    fund_str = f"${fund:,.0f}" if fund else "N/A"
    print(f"  {bi.get('name'):30s} | HC: {hc:>4} | {loc} | Funding: {fund_str}")
