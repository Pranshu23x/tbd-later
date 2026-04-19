"""
OracleTools — Data query layer for agent ReACT turns.
Mirrors MiroFish's ZepToolsService pattern: agents call tools during debate,
system executes them and injects observations back into the conversation.
"""
import json
import re
import requests
from typing import Dict, Any, List, Optional
from ingestor import get_headers, BASE_URL


class OracleTools:
    """
    Five tools available to every debate agent during their ReACT loop.
    All methods return plain text strings ready to be injected as Observations.
    """

    AVAILABLE_TOOLS = {
        "query_company_data": {
            "description": "Look up a specific data field for a company using dot-notation path",
            "params": {
                "company": "Company name: 'OpenAI' (our company) or 'Anthropic' (rival)",
                "field_path": "Dot-notation path. Examples: 'capital.monthly_burn_usd', "
                              "'muscle.attrition_last_90d', 'arsenal.open_roles_by_function', "
                              "'capital.runway_months', 'muscle.headcount', 'budget.total_monthly_spend_usd'"
            }
        },
        "query_employee_signals": {
            "description": "Get the full signals profile and career history of a specific named person",
            "params": {
                "name": "Full name. Examples: 'Brad Lightcap', 'Mira Murati', "
                        "'Neel Nanda', 'Sandy Banerjee', 'Sam Altman'"
            }
        },
        "compare_field": {
            "description": "Compare a specific metric side by side — our company vs rival — with delta/gap",
            "params": {
                "field_path": "Dot-notation path. Examples: 'muscle.attrition_last_90d', "
                              "'capital.runway_months', 'muscle.open_roles_total', "
                              "'arsenal.open_roles_by_function'"
            }
        },
        "list_cuttable_items": {
            "description": "List all cuttable budget line items with exact monthly costs and status",
            "params": {
                "company": "Company name: 'OpenAI' or 'Anthropic'"
            }
        },
        "get_dept_budget": {
            "description": "Get the full monthly budget breakdown by department for a company",
            "params": {
                "company": "Company name: 'OpenAI' or 'Anthropic'"
            }
        },
        "web_search_live": {
            "description": "Perform a live web search to find recent news, public posts, or sentiment about a company or person. Use this to verify traction or find red flags.",
            "params": {
                "query": "The search query (e.g., 'OpenAI recent news', 'Anthropic funding rumor')"
            }
        },
        "calculate_traction_score": {
            "description": "Calculate a 0-100 Traction Score based on a company's headcount growth, funding, and web traffic signals.",
            "params": {
                "company": "Company name: 'OpenAI' or 'Anthropic'"
            }
        }
    }

    def __init__(self, data: dict):
        self.target = data.get("target", {})
        self.rival = data.get("rival", {})
        self.target_company = self.target.get("company", {})
        self.rival_company = self.rival.get("company", {})
        self.target_employees = self.target.get("employees", [])
        self.rival_employees = self.rival.get("employees", [])

    def _resolve_company(self, name: str):
        """Return (company_dict, label) for a given name."""
        nl = name.lower()
        my_name = self.target_company.get("name", "").lower()
        rival_name = self.rival_company.get("name", "").lower()
        if nl in (my_name, "target", "us", "ours", "openai"):
            return self.target_company, self.target_company.get("name", "Our Company")
        elif nl in (rival_name, "rival", "anthropic"):
            return self.rival_company, self.rival_company.get("name", "Rival")
        return self.target_company, self.target_company.get("name", "Our Company")

    def _get_nested(self, d: dict, path: str):
        """Navigate a dot-notation path in a nested dict."""
        for k in path.split("."):
            if isinstance(d, dict):
                d = d.get(k)
            else:
                return None
            if d is None:
                return None
        return d

    def execute(self, tool_name: str, params: Dict[str, Any]) -> str:
        """Route and execute a tool call, return result as string."""
        try:
            if tool_name == "query_company_data":
                return self.query_company_data(
                    params.get("company", "OpenAI"),
                    params.get("field_path", "")
                )
            elif tool_name == "query_employee_signals":
                return self.query_employee_signals(params.get("name", ""))
            elif tool_name == "compare_field":
                return self.compare_field(params.get("field_path", ""))
            elif tool_name == "list_cuttable_items":
                return self.list_cuttable_items(params.get("company", "OpenAI"))
            elif tool_name == "get_dept_budget":
                return self.get_dept_budget(params.get("company", "OpenAI"))
            elif tool_name == "web_search_live":
                return self.web_search_live(params.get("query", ""))
            elif tool_name == "calculate_traction_score":
                return self.calculate_traction_score(params.get("company", "OpenAI"))
            else:
                return (f"Unknown tool: '{tool_name}'. "
                        f"Available tools: {', '.join(self.AVAILABLE_TOOLS.keys())}")
        except Exception as e:
            return f"Tool execution error ({tool_name}): {str(e)}"

    # ── Tool implementations ───────────────────────────────────────────────

    def query_company_data(self, company: str, field_path: str) -> str:
        company_dict, label = self._resolve_company(company)
        value = self._get_nested(company_dict, field_path)

        if value is None:
            top_keys = list(company_dict.keys())
            return (f"Field '{field_path}' not found in {label} data.\n"
                    f"Available top-level keys: {top_keys}\n"
                    f"Tip: Try a sub-path like 'capital.monthly_burn_usd' or "
                    f"'arsenal.open_roles_by_function'")

        if isinstance(value, dict):
            lines = "\n".join(f"  {k}: {v}" for k, v in value.items())
            return f"RESULT — {label} | {field_path}:\n{lines}"
        elif isinstance(value, list):
            lines = "\n".join(f"  - {item}" for item in value)
            return f"RESULT — {label} | {field_path}:\n{lines}"
        else:
            return f"RESULT — {label} | {field_path}: {value}"

    def query_employee_signals(self, name: str) -> str:
        name_lower = name.lower()
        all_employees = (
            [(emp, self.target_company.get("name", "Our Company"))
             for emp in self.target_employees] +
            [(emp, self.rival_company.get("name", "Rival"))
             for emp in self.rival_employees]
        )

        for emp, company_label in all_employees:
            ident = emp.get("professional_identity", {})
            full_name = ident.get("full_name", "")
            if name_lower in full_name.lower():
                signals = emp.get("signals_and_vibe", {})
                history = emp.get("deep_work_history", [])
                dept = ident.get("department", "")
                title = ident.get("current_title", "")
                academic = emp.get("academic_background", [])

                lines = [
                    f"PERSON: {full_name}",
                    f"ROLE: {title} | Department: {dept} | Company: {company_label}",
                    f"SIGNALS (hard numbers): {json.dumps(signals, indent=2)}",
                    f"CAREER HISTORY: {json.dumps(history, indent=2)}",
                    f"ACADEMIC: {json.dumps(academic, indent=2)}"
                ]
                return "\n".join(lines)

        available = [
            emp.get("professional_identity", {}).get("full_name", "?")
            for emp, _ in all_employees
        ]
        return (f"Person '{name}' not found.\n"
                f"Available people: {', '.join(available)}")

    def compare_field(self, field_path: str) -> str:
        my_val = self._get_nested(self.target_company, field_path)
        rival_val = self._get_nested(self.rival_company, field_path)
        my_label = self.target_company.get("name", "Ours")
        rival_label = self.rival_company.get("name", "Rival")

        def fmt(val):
            if val is None:
                return "  N/A"
            if isinstance(val, dict):
                return "\n" + "\n".join(f"    {k}: {v}" for k, v in val.items())
            return f"  {val}"

        result = f"COMPARISON — {field_path}:\n"
        result += f"  {my_label}:{fmt(my_val)}\n"
        result += f"  {rival_label}:{fmt(rival_val)}\n"

        # Delta analysis for numeric values
        if isinstance(my_val, (int, float)) and isinstance(rival_val, (int, float)):
            delta = my_val - rival_val
            pct = abs(delta / rival_val * 100) if rival_val != 0 else 0
            if delta > 0:
                result += f"  DELTA: We LEAD by {abs(delta):,} ({pct:.0f}% advantage)"
            elif delta < 0:
                result += f"  DELTA: We TRAIL by {abs(delta):,} ({pct:.0f}% disadvantage)"
            else:
                result += f"  DELTA: Tied"

        return result

    def list_cuttable_items(self, company: str = "OpenAI") -> str:
        company_dict, label = self._resolve_company(company)
        items = company_dict.get("budget", {}).get("cuttable_line_items", [])
        if not items:
            return f"No cuttable line items found for {label}."

        total = sum(item.get("monthly_cost_usd", 0) for item in items)
        lines = [
            f"CUTTABLE LINE ITEMS — {label}",
            f"Total recoverable per month: ${total:,} (${total//1000}k/month)\n"
        ]
        for i, item in enumerate(items, 1):
            cost = item.get("monthly_cost_usd", 0)
            status = item.get("status", "unknown").upper()
            lines.append(
                f"  {i}. [{status}] {item['item']}\n"
                f"     Cost: ${cost:,}/month (${cost//1000}k/month)"
            )
        return "\n".join(lines)

    def get_dept_budget(self, company: str = "OpenAI") -> str:
        company_dict, label = self._resolve_company(company)
        by_dept = company_dict.get("budget", {}).get("by_department", {})
        total = company_dict.get("budget", {}).get("total_monthly_spend_usd", 0)
        if not by_dept:
            return f"No department budget data found for {label}."

        lines = [
            f"DEPT BUDGET — {label}",
            f"Total monthly burn: ${total:,} (${total//1000000:.1f}M/month)\n"
        ]
        for dept, amt in sorted(by_dept.items(), key=lambda x: x[1], reverse=True):
            pct = amt / total * 100 if total else 0
            lines.append(
                f"  {dept}: ${amt:,}/month ({pct:.0f}% of total burn)"
            )
        return "\n".join(lines)

    def web_search_live(self, query: str) -> str:
        """Calls Crustdata's live web search API."""
        if not query:
            return "Error: Empty query."
        payload = {"queries": [query]}
        try:
            resp = requests.post(f"{BASE_URL}/v1/web/search/live", json=payload, headers=get_headers())
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("data", [])
                if not results:
                    return f"No live search results found for '{query}'."
                
                formatted = []
                for idx, r in enumerate(results[:3], 1):
                    formatted.append(f"Result {idx}: {r.get('title', 'No Title')} - {r.get('snippet', 'No Snippet')} ({r.get('url', '')})")
                return "\n".join(formatted)
            return f"Web search failed: {resp.text}"
        except Exception as e:
            return f"Web search exception: {str(e)}"

    def calculate_traction_score(self, company: str) -> str:
        """Calculates a deterministic traction score based on metrics."""
        company_dict, label = self._resolve_company(company)
        growth = company_dict.get("muscle", {}).get("headcount_growth_percentage", 0)
        
        if growth is None: 
            growth = 0
            
        score = 50 + (growth * 2)
        score = max(0, min(100, score))
        grade = "A" if score > 80 else "B" if score > 60 else "C" if score > 40 else "D"
        
        return f"TRACTION SCORE for {label}: {score:.1f}/100 (Grade: {grade})\nGrowth factor: {growth}%"
