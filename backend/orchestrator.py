"""
Reflex Orchestrator — AI-Driven Deal Intelligence Pipeline
============================================================
Takes a raw natural-language prompt from the user, uses DeepSeek to extract
the investment thesis, autonomously calls Crustdata APIs to gather data,
then kicks off the Bull vs Bear ReACT debate with live tool access.

Pipeline:
  1. Parse intent from natural language (DeepSeek)
  2. Search Crustdata for ALL matching companies
  3. Enrich EVERY match with full profiles (funding, headcount, investors)
  4. Build a rich deal pipeline dossier
  5. Feed everything to Bull vs Bear agents who debate with live web search
"""

import os
import json
import re
from openai import OpenAI
from dotenv import load_dotenv
from ingestor import fetch_company_profile, search_by_thesis, enrich_by_ids

load_dotenv()

# Map common region names to ISO3 codes for Crustdata
REGION_MAP = {
    "eu": ["DEU", "FRA", "GBR", "NLD", "ESP", "ITA", "SWE", "IRL"],
    "europe": ["DEU", "FRA", "GBR", "NLD", "ESP", "ITA", "SWE", "IRL"],
    "us": ["USA"], "usa": ["USA"], "united states": ["USA"],
    "india": ["IND"], "in": ["IND"],
    "uk": ["GBR"], "united kingdom": ["GBR"],
    "germany": ["DEU"], "france": ["FRA"],
    "southeast asia": ["SGP", "IDN", "THA", "VNM", "PHL"],
    "sea": ["SGP", "IDN", "THA", "VNM"],
    "latam": ["BRA", "MEX", "ARG", "COL"],
    "middle east": ["ARE", "SAU", "ISR"],
    "israel": ["ISR"],
}

INTENT_SYSTEM = """\
You are an AI assistant for a Venture Capital firm called Reflex.
Your job is to parse a natural-language investment prompt and extract structured parameters.

You MUST respond with ONLY a valid JSON object. No explanation. No markdown. No backticks.

CRITICAL RULES:
- search_industry must NEVER be null. If the user says "startups" or is vague, infer the best industry.
  Map common terms: "AI" → "Technology, Information and Internet", "fintech" → "Financial Services",
  "healthtech" → "Hospitals and Health Care", "SaaS" or "software" → "Software Development",
  "biotech" → "Biotechnology Research", "startups" (generic) → "Technology, Information and Internet".
- For broad prompts like "find best startups", default to "Technology, Information and Internet".
- If the user mentions "startups", set max_headcount to 500 unless they specify otherwise.

The JSON must have these fields:
{
  "target_company": "string or null — specific company name if one is mentioned",
  "search_industry": "string — REQUIRED, never null. Crustdata industry label.",
  "search_location": "string or null — region keyword like 'USA', 'EU', 'India', 'UK', 'Southeast Asia'.",
  "min_headcount": "integer or null — minimum employee count",
  "max_headcount": "integer or null — maximum employee count (500 if 'startups' mentioned)",
  "min_growth_percent": "integer or null — minimum headcount growth percentage if mentioned",
  "compare_against": "string or null — rival company if mentioned",
  "benchmarks": ["list of key metrics. Pick from: 'Headcount Growth', 'Funding Amount', 'Burn Multiple', 'ARR Growth', 'Investor Quality', 'Market Size'"],
  "investment_goal": "string — what the user wants",
  "user_role": "string — inferred role: 'Managing Partner', 'Analyst', 'Scout', 'LP'"
}
"""


class ReflexOrchestrator:
    """
    Full autonomous pipeline:
    1. Parse natural language → structured intent
    2. Search Crustdata → find ALL matching companies
    3. Batch Enrich by ID → full profiles (funding, revenue, headcount, hiring, people)
    4. Build deal pipeline dossier
    5. Run Bull vs Bear debate with live web search + Crustdata tools
    """

    def __init__(self, event_callback=None):
        self.client = OpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url="https://api.deepseek.com",
        )
        self.event_callback = event_callback or (lambda evt: None)

    def _emit(self, event: dict):
        self.event_callback(event)
        phase = event.get("phase", "")
        detail = event.get("detail", "")
        if detail:
            print(f"  [{phase}] {detail}")

    def _build_profiles_from_search(self, search_results, existing_ids, enriched_profiles):
        """Convert lightweight search results into our standard profile format."""
        for c in search_results:
            cid = c.get("crustdata_company_id")
            if cid in existing_ids:
                continue
            existing_ids.add(cid)
            enriched_profiles.append({
                "id": cid,
                "name": c.get("basic_info", {}).get("name", "Unknown"),
                "domain": c.get("basic_info", {}).get("primary_domain", ""),
                "capital": {
                    "funding_total": c.get("funding", {}).get("total_investment_usd"),
                    "revenue_lower": c.get("revenue", {}).get("estimated", {}).get("lower_bound_usd"),
                },
                "muscle": {
                    "headcount": c.get("headcount", {}).get("total"),
                },
                "arsenal": {"industry": c.get("taxonomy", {}).get("professional_network_industry")},
                "backing": {"investor_list": c.get("funding", {}).get("investors", [])},
                "people": {}
            })

    # ── Step 1: Parse Intent ─────────────────────────────────────────────

    def parse_intent(self, user_prompt: str) -> dict:
        print(f"\n{'='*60}")
        print(f"  STEP 1: PARSING INVESTMENT THESIS")
        print(f"  Prompt: \"{user_prompt[:100]}...\"" if len(user_prompt) > 100 else f"  Prompt: \"{user_prompt}\"")
        print(f"{'='*60}")

        resp = self.client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": INTENT_SYSTEM},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,
        )

        raw = resp.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)

        try:
            intent = json.loads(raw)
        except json.JSONDecodeError:
            print(f"  WARN: Could not parse intent. Using defaults.")
            intent = {
                "target_company": None, "search_industry": "Technology, Information and Internet",
                "search_location": "USA", "min_headcount": None, "max_headcount": 500,
                "compare_against": None, "benchmarks": ["Headcount Growth", "Funding Amount"],
                "investment_goal": user_prompt, "user_role": "Analyst"
            }

        print(f"\n  Extracted Intent:")
        for k, v in intent.items():
            print(f"    {k}: {v}")

        self._emit({"phase": "intent_parsed", "detail": json.dumps(intent), "intent": intent})
        return intent

    # ── Step 2: Gather Intelligence (Search → Batch Enrich by ID) ────────

    def gather_intelligence(self, intent: dict) -> tuple:
        print(f"\n{'='*60}")
        print(f"  STEP 2: GATHERING LIVE INTELLIGENCE (Crustdata)")
        print(f"{'='*60}")

        enriched_profiles = []
        target_name = intent.get("target_company")

        # --- Direct company lookup (Identify → Enrich) ---
        if target_name:
            self._emit({"phase": "ingestion", "detail": f"Direct lookup: {target_name}"})
            profile = fetch_company_profile(target_name)
            if profile:
                enriched_profiles.append(profile)
                hc = profile.get('muscle', {}).get('headcount', 'N/A')
                fund = profile.get('capital', {}).get('funding_total')
                rev = profile.get('capital', {}).get('revenue_lower')
                fin = f"${fund:,.0f}" if fund and fund > 0 else (f"Rev ~${rev:,.0f}" if rev else "N/A")
                print(f"  ✓ {profile.get('name')}: HC={hc}, {fin}")

        # --- Thesis-driven search ---
        industry = intent.get("search_industry") or "Software Development"
        location_raw = (intent.get("search_location") or "").lower().strip()
        iso_codes = REGION_MAP.get(location_raw, [location_raw.upper()] if location_raw else [])

        max_hc = intent.get("max_headcount")
        min_hc = intent.get("min_headcount")

        # Progressive broadening: try strict first, then relax filters
        search_attempts = [
            {"industry": industry, "location": iso_codes, "min_hc": min_hc, "max_hc": max_hc, "label": "strict"},
            {"industry": "Technology, Information and Internet", "location": iso_codes, "min_hc": min_hc, "max_hc": max_hc, "label": "broader industry"},
            {"industry": industry, "location": None, "min_hc": min_hc, "max_hc": max_hc, "label": "no location"},
            {"industry": None, "location": iso_codes, "min_hc": None, "max_hc": max_hc, "label": "location only"},
        ]

        search_results = []
        for attempt in search_attempts:
            label = attempt["label"]
            loc = attempt["location"]
            ind = attempt["industry"]
            self._emit({"phase": "search", "detail": f"Searching ({label}): {ind or 'any'} in {loc or 'global'}" + (f" (HC <= {attempt['max_hc']})" if attempt["max_hc"] else "")})
            
            search_results = search_by_thesis(
                industry=ind,
                location=loc if loc else None,
                min_headcount=attempt["min_hc"],
                max_headcount=attempt["max_hc"],
                limit=10
            )

            if search_results:
                print(f"  ✓ Found {len(search_results)} companies matching thesis")

                # Collect IDs for batch enrichment (skip already-enriched)
                existing_ids = {p.get("id") for p in enriched_profiles if p.get("id")}
                ids_to_enrich = [
                    c.get("crustdata_company_id")
                    for c in search_results
                    if c.get("crustdata_company_id") and c.get("crustdata_company_id") not in existing_ids
                ]

                if ids_to_enrich:
                    self._emit({"phase": "enrich", "detail": f"Batch enriching {len(ids_to_enrich)} companies by ID..."})
                    batch_enriched = enrich_by_ids(ids_to_enrich)
                    if batch_enriched:
                        enriched_profiles.extend(batch_enriched)
                        print(f"  ✓ Enriched {len(batch_enriched)} companies with full profiles")
                    else:
                        # Fallback: use search result data directly
                        print(f"  ~ Batch enrichment returned no data, using search results directly")
                        self._build_profiles_from_search(search_results, existing_ids, enriched_profiles)
                else:
                    # All IDs already enriched or no IDs returned — use search data
                    print(f"  ~ No new IDs to enrich, using search results directly")
                    self._build_profiles_from_search(search_results, existing_ids, enriched_profiles)
                break  # Found results, stop broadening
            else:
                print(f"  ✗ No results for {label}, trying broader search...")
        # --- Print deal pipeline ---
        print(f"\n  ═══ DEAL PIPELINE: {len(enriched_profiles)} companies enriched ═══")
        for i, p in enumerate(enriched_profiles, 1):
            hc = p.get('muscle', {}).get('headcount', 'N/A')
            fund_val = p.get('capital', {}).get('funding_total')
            rev_val = p.get('capital', {}).get('revenue_lower')
            investors = p.get('backing', {}).get('investor_list', [])

            if fund_val and fund_val > 0:
                fin = f"Funded: ${fund_val:,.0f}"
            elif rev_val and rev_val > 0:
                fin = f"Revenue: ~${rev_val:,.0f}"
            else:
                fin = "Pre-revenue/Bootstrapped"

            inv_str = f" | Investors: {', '.join(investors[:3])}" if investors else ""
            print(f"    {i}. {p.get('name', '?')} | HC: {hc} | {fin}{inv_str}")

        # Package for simulation engine
        if not enriched_profiles:
            self._emit({"status": "data_ready", "phase": "data_ready", "detail": "No companies found", "data": {"pipeline": []}})
            return None, None

        primary = enriched_profiles[0]
        target_name = primary.get("name", "Unknown")
        rival = enriched_profiles[1] if len(enriched_profiles) > 1 else {}

        data = {
            "target": {"company": primary, "employees": []},
            "rival": {"company": rival, "employees": []},
            "pipeline": enriched_profiles,
        }

        self._emit({"status": "data_ready", "phase": "data_ready", "detail": f"Pipeline ready: {len(enriched_profiles)} companies", "data": data})
        return data, target_name

    # ── Step 3: Run the Debate ───────────────────────────────────────────

    def run(self, user_prompt: str, num_rounds: int = 4) -> str:
        from simulation_engine import OracleSimulation

        # Step 1
        intent = self.parse_intent(user_prompt)

        # Step 2
        data, target_name = self.gather_intelligence(intent)
        
        if not data or not data.get("pipeline"):
            msg = "No companies matching your investment thesis were found in our live data feeds. Try broadening your criteria (e.g., removing headcount growth or location constraints)."
            self._emit({"phase": "error", "status": "error", "message": msg})
            return msg

        # Step 3
        print(f"\n{'='*60}")
        print(f"  STEP 3: BULL vs BEAR DEBATE (LIVE)")
        print(f"  Primary Target: {target_name}")
        print(f"  Pipeline: {len(data.get('pipeline', []))} companies")
        print(f"{'='*60}\n")

        rival_name = intent.get("compare_against") or (data["rival"].get("company", {}).get("name") or "Industry Average")
        benchmarks = intent.get("benchmarks") or ["Headcount Growth", "Funding Amount", "Burn Multiple"]
        goal = intent.get("investment_goal", "Evaluate investment potential")
        role = intent.get("user_role", "Managing Partner")

        # Build a pipeline summary for the agents
        pipeline_summary = "\n=== FULL DEAL PIPELINE (Use these companies for your debate) ===\n"
        for i, p in enumerate(data.get("pipeline", []), 1):
            pipeline_summary += (
                f"  {i}. {p.get('name', '?')} | "
                f"HC: {p.get('muscle', {}).get('headcount', 'N/A')} | "
                f"Funding: ${p.get('capital', {}).get('funding_total', 'N/A')} | "
                f"Investors: {', '.join(p.get('backing', {}).get('investor_list', []) or ['N/A'])}\n"
            )

        # Inject pipeline into data so simulation_engine can pick it up explicitly
        data["pipeline_summary"] = pipeline_summary

        # Inject pipeline into planning_custom so all agents see it
        full_goal = f"{goal}\n\n{pipeline_summary}"

        sim = OracleSimulation(
            user_type=role,
            target_company=target_name,
            compare_against=rival_name,
            benchmarks=benchmarks,
            planning=["Investment Memo"],
            planning_custom=full_goal,
            data=data,
            event_callback=self.event_callback,
            num_rounds=num_rounds
        )

        result = sim.run()
        return result


# ── CLI Entry Point ──────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:])
    else:
        prompt = input("\n🔍 Enter your investment prompt: ")

    orchestrator = ReflexOrchestrator()
    memo = orchestrator.run(prompt, num_rounds=4)

    print(f"\n{'='*60}")
    print(f"  INVESTMENT MEMO — FINAL OUTPUT")
    print(f"{'='*60}\n")
    print(memo)
