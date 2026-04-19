"""
OracleSwarm Simulation Engine — MiroFish ReACT Architecture
============================================================
Replaces the static CrewAI task chain with a MiroFish-style
Reasoning + Acting loop where each agent can query real data
on-demand during their debate turn before committing to an answer.

Flow:
  Round 0 : CEO opens with data-backed brief
  Round 1 : Agent 2 reacts | Agent 3 counters (both with tool access)
  Round 2 : Agent 2 rebuts | Agent 3 defends (both with tool access)
  Round 3 : Agent 2 final  | Agent 3 final  (lightweight, 1 tool min)
  Verdict : Chair makes binding decision (with tool access)
  Plan    : Strategist writes Investment Memo (3 tool min)
"""

import sys
if sys.stdout and sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import os
import re
import json
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from openai import OpenAI
from dotenv import load_dotenv
from schemas import MarketContext
from tools import OracleTools
from prompts import (
    TOOL_SCHEMA, REACT_RULES,
    TOOL_REJECT_MSG, TOOL_LIMIT_MSG, TOOL_FORCE_PUSH,
    CEO_BRIEF_SYSTEM, CEO_BRIEF_PROMPT,
    R1_REACT_PROMPT, R1_COUNTER_PROMPT,
    R2_REBUTTAL_PROMPT, R2_DEFENSE_PROMPT,
    R3_ESCALATE_PROMPT, R3_FINAL_PROMPT,
    CEO_VERDICT_SYSTEM, CEO_VERDICT_PROMPT,
    STRATEGIST_SYSTEM, STRATEGIST_PROMPT,
)

load_dotenv()


# ── Data structures ───────────────────────────────────────────────────────

@dataclass
class DebateAgent:
    name: str
    title: str
    dept: str
    company: str
    system_prompt: str          # fully-rendered, ready for LLM
    signals: Dict[str, Any] = field(default_factory=dict)
    career: List[Dict] = field(default_factory=list)


# ── Helpers ───────────────────────────────────────────────────────────────

def _build_company_dossier(company: dict, label: str) -> str:
    """Render a dense, line-by-line data sheet for one company."""
    cap = company.get("capital", {})
    muscle = company.get("muscle", {})
    arsenal = company.get("arsenal", {})
    budget = company.get("budget", {})
    backing = company.get("backing", {})

    burn = cap.get("monthly_burn_usd", 0)
    burn_str = f"${burn / 1e6:.1f}M/month" if burn else "unknown"

    dept_spend = budget.get("by_department", {})
    dept_str = " | ".join(f"{k}: ${v // 1000}k/mo" for k, v in dept_spend.items())

    cuttable = budget.get("cuttable_line_items", [])
    cuts_str = "\n".join(
        f"  [{c.get('status','?').upper()}] {c['item']}: ${c['monthly_cost_usd'] // 1000}k/mo"
        for c in cuttable
    ) or "  None identified"

    open_r = arsenal.get("open_roles_by_function", {})
    new_h  = arsenal.get("recent_hires_30d_by_function", {})
    hc_fn  = arsenal.get("employee_count_by_function", {})

    return (
        f"=== {label}: {company.get('name', '?')} ===\n"
        f"CAPITAL   : raised {cap.get('funding_total')} | burn {burn_str} "
        f"| runway {cap.get('runway_months', '?')} months "
        f"| last round {cap.get('last_funding_date', '?')}\n"
        f"HEADCOUNT : {muscle.get('headcount')} total "
        f"| {muscle.get('open_roles_total', '?')} open roles "
        f"| attrition last 90d: {muscle.get('attrition_last_90d', '?')} "
        f"({muscle.get('senior_attrition_last_90d', '?')} senior)\n"
        f"BY DEPT   : {hc_fn}\n"
        f"OPEN ROLES BY DEPT: {open_r}\n"
        f"NEW HIRES LAST 30d: {new_h}\n"
        f"INVESTORS : {', '.join(backing.get('investor_list', []))}\n"
        f"DEPT SPEND: {dept_str}\n"
        f"CUTTABLE LINE ITEMS:\n{cuts_str}"
    )


def _parse_tool_calls(response: str) -> List[Dict[str, Any]]:
    """
    Parse <tool_call>...</tool_call> blocks from LLM response.
    Supports both JSON payload and XML inner payload.
    Falls back to bare JSON if no XML tags found.
    """
    calls = []

    # Primary: XML-style tags with JSON payload
    for match in re.finditer(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", response, re.DOTALL):
        try:
            calls.append(json.loads(match.group(1)))
        except json.JSONDecodeError:
            pass

    # Secondary: XML-style tags with XML payload (name and parameters)
    if not calls:
        for match in re.finditer(r"<tool_call>(.*?)</tool_call>", response, re.DOTALL):
            inner = match.group(1)
            name_match = re.search(r"<name>(.*?)</name>", inner, re.DOTALL)
            params_match = re.search(r"<parameters>(.*?)</parameters>", inner, re.DOTALL)
            
            if name_match:
                name = name_match.group(1).strip()
                params = {}
                if params_match:
                    params_text = params_match.group(1)
                    try:
                        params = json.loads(params_text)
                    except json.JSONDecodeError:
                        for param_match in re.finditer(r"<([^>]+)>(.*?)</\1>", params_text, re.DOTALL):
                            params[param_match.group(1)] = param_match.group(2).strip()
                calls.append({"name": name, "parameters": params})

    if calls:
        return calls

    # Fallback: bare JSON object as entire response
    stripped = response.strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        try:
            obj = json.loads(stripped)
            if "name" in obj and "parameters" in obj:
                calls.append(obj)
        except json.JSONDecodeError:
            pass

    return calls


# ── Persona Factory ───────────────────────────────────────────────────────

class PersonaFactory:
    """
    Builds DebateAgent objects with rich behavioral models.
    Each agent gets: full dual-company dossier, rival exec intel,
    personal signals/budget, career history, and tool schema.
    Mirrors MiroFish's OasisProfileGenerator philosophy.
    """

    @staticmethod
    def build_agents(
        market_context: MarketContext,
        target_employees: List[dict],
        rival_employees: List[dict],
        memory_context: str = "",
        user_context: str = ""
    ):
        my    = market_context.my_company_stats
        rival = market_context.rival_company_stats

        # Dual-company dossiers
        my_dossier    = _build_company_dossier(my,    "OUR COMPANY")
        rival_dossier = _build_company_dossier(rival, "RIVAL")

        # Rival executive intel sheet
        rival_intel_lines = []
        for emp in rival_employees:
            ident   = emp.get("professional_identity", {})
            signals = emp.get("signals_and_vibe", {})
            history = emp.get("deep_work_history", [])
            prev    = history[0] if history else {}
            rival_intel_lines.append(
                f"  {ident.get('full_name')} | {ident.get('current_title')} "
                f"| dept: {ident.get('department')} "
                f"| prev: {prev.get('company_name','?')} ({prev.get('job_title','?')}) "
                f"| signals: {json.dumps(signals)}"
            )
        rival_exec_intel = "\n".join(rival_intel_lines)

        # Shared investors (boardroom traitors)
        traitors = market_context.hidden_alliances
        traitor_str = (
            "BOARDROOM TRAITORS (shared investors — dual loyalties): "
            + ", ".join(t["investor"] for t in traitors)
            if traitors
            else "No shared investors detected."
        )

        # Shared intelligence block — every agent sees this
        shared_intelligence = (
            f"{user_context}\n"
            f"{my_dossier}\n\n"
            f"{rival_dossier}\n\n"
            f"RIVAL EXECUTIVE INTEL:\n{rival_exec_intel}\n\n"
            f"{traitor_str}\n"
            f"{memory_context}"
        )

        agents = []
        
        vc_roles = [
            {"name": "Committee Chair", "title": "Partner", "mandate": "You must listen to both sides and evaluate the deal objectively."},
            {"name": "Bull Analyst", "title": "Associate", "mandate": "You are arguing TO INVEST. Focus on the upside, growth metrics, and market opportunity. Defend the startup's valuation."},
            {"name": "Bear Analyst", "title": "Principal", "mandate": "You are arguing TO PASS. Focus on the downside, high burn rate, weak team signals, and market risks. Be ruthless about the numbers."}
        ]

        for role in vc_roles:
            name = role["name"]
            title = role["title"]
            dept = "Venture Intelligence"
            company_name = "Reflex VC"
            
            personal_block = (
                f"YOUR ROLE:\n"
                f"  Name: {name} | Title: {title}\n"
                f"  Mandate: {role['mandate']}\n"
                f"\nBEHAVIORAL MANDATE:\n"
                f"  - Fight for your position, but only with numbers.\n"
                f"  - 'Significant', 'large', 'major' are not arguments. The number is the argument.\n"
                f"  - Call tools to verify before claiming a number you are unsure of.\n"
            )

            system_prompt = (
                f"You are {name}, {title} at {company_name}.\n\n"
                f"{shared_intelligence}\n\n"
                f"{personal_block}\n\n"
                f"{TOOL_SCHEMA}\n\n"
                f"{REACT_RULES.replace('MIN_TOOLS_REQUIRED', '2')}"
            )

            agents.append(DebateAgent(
                name=name,
                title=title,
                dept=dept,
                company=company_name,
                system_prompt=system_prompt,
                signals={},
                career=[],
            ))

        return agents, shared_intelligence


# ── OracleSimulation ──────────────────────────────────────────────────────

class OracleSimulation:
    """
    Orchestrates the full 3-round debate + CEO verdict + Strategist plan.
    Replaces CrewAI's Crew/Task system with a pure Python ReACT loop
    identical in principle to MiroFish's ReportAgent._generate_section_with_react().
    """

    MODEL       = "deepseek-chat"
    TEMPERATURE = 0.4

    # Minimum tool calls per turn — agents must call at least this many tools
    MIN_CEO_BRIEF    = 2
    MIN_EXEC         = 2   # Bull/Bear must verify with live data
    MIN_ESCALATE     = 1   # Quick-fire rounds
    MIN_FINAL_STMT   = 1
    MIN_CEO_VERDICT  = 2   # Chair must pull live data before deciding
    MIN_STRATEGIST   = 2

    MAX_TOOLS = 5   # Higher cap = more live data calls per turn

    def __init__(self, user_type: str, target_company: str, compare_against: str, benchmarks: list, planning: list, planning_custom: str, data: dict, event_callback=None, num_rounds: int = 4):
        self.event_callback = event_callback or (lambda evt: None)
        self.num_rounds = max(2, min(num_rounds, 6))  # Clamp 2-6
        self.user_type = user_type
        self.target_company = target_company
        self.compare_against = compare_against
        self.benchmarks = benchmarks
        self.planning = planning
        self.planning_custom = planning_custom
        self.scenario = f"User is {user_type}. Goal: {', '.join(planning) if planning else 'General Plan'} - {planning_custom}"
        self.move = f"Benchmark {target_company} against {compare_against} explicitly on metrics: {', '.join(benchmarks) if benchmarks else 'General Metrics'}"
        self.data     = data

        self.client = OpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url="https://api.deepseek.com",
        )
        self.oracle_tools = OracleTools(data)

        # Supermemory (optional, non-fatal)
        self.memory_context    = ""
        self.supermemory_client = None
        supermemory_key = os.getenv("SUPERMEMORY_API_KEY")
        if supermemory_key:
            try:
                from supermemory import Supermemory
                self.supermemory_client = Supermemory(api_key=supermemory_key)
                company_name = data.get("target", {}).get("company", {}).get("name", "Unknown")
                # Sanitize company name for container_tags (only alphanumeric, hyphens, underscores, colons)
                safe_tag = re.sub(r'[^a-zA-Z0-9_:-]', '-', f"company-{company_name}")
                results = self.supermemory_client.search.documents(
                    q=self.scenario, container_tags=[safe_tag]
                )
                if results:
                    self.memory_context = "\nHISTORICAL CONTEXT: Similar scenario found in memory."
            except Exception as e:
                print(f"[Supermemory] Skipped: {e}")

        # Extract employees from data
        target_emps = data.get("target", {}).get("employees", [])
        rival_emps  = data.get("rival",  {}).get("employees", [])

        # Boardroom traitor detection
        t_inv = set(data.get("target", {}).get("company", {}).get("backing", {}).get("investor_list", []))
        r_inv = set(data.get("rival",  {}).get("company", {}).get("backing", {}).get("investor_list", []))
        shared = [{"investor": inv} for inv in t_inv & r_inv]

        # Build MarketContext
        self.market_context = MarketContext(
            my_company_stats=data.get("target", {}).get("company", {}),
            rival_company_stats=data.get("rival", {}).get("company", {}),
            hidden_alliances=shared
        )

        # Shared intelligence block — every agent sees this
        user_context_parts = [
            f"=== MISSION PERSPECTIVE ===",
            f"The user requesting this debate is a(n): {self.user_type}",
            f"Subject Company: {self.target_company}",
            f"Comparing Against: {self.compare_against}",
            f"Requested Benchmarks to focus on: {', '.join(self.benchmarks) if self.benchmarks else 'None specified'}",
            f"User's Core Goal/Planning: {', '.join(self.planning) if self.planning else 'Research'} - {self.planning_custom}\n"
        ]
        user_context_str = "\n".join(user_context_parts)

        self.debate_agents, self.shared_intelligence = PersonaFactory.build_agents(
            self.market_context, target_emps, rival_emps, self.memory_context, user_context_str
        )

        if len(self.debate_agents) < 3:
            raise ValueError(f"Need 3 debate agents, got {len(self.debate_agents)}")

        # Strategist gets full intelligence + tool access
        my = self.market_context.my_company_stats
        company_name = my.get("name", "Company")
        self.strategist_system = (
            STRATEGIST_SYSTEM
            .replace("{dossier}",      self.shared_intelligence)
            .replace("{tool_schema}",  TOOL_SCHEMA)
            .replace("{react_rules}",  REACT_RULES.replace("MIN_TOOLS_REQUIRED", str(self.MIN_STRATEGIST)))
        )

    # ── Core ReACT loop ───────────────────────────────────────────────────

    def _call_llm(self, messages: List[Dict]) -> str:
        import time
        for attempt in range(3):
            try:
                resp = self.client.chat.completions.create(
                    model=self.MODEL,
                    messages=messages,
                    temperature=self.TEMPERATURE,
                )
                return resp.choices[0].message.content
            except Exception as e:
                if attempt < 2:
                    wait = 2 ** attempt
                    print(f"    [LLM] Connection error, retrying in {wait}s... ({e.__class__.__name__})")
                    time.sleep(wait)
                else:
                    raise

    def _call_llm_stream(self, messages: List[Dict], speaker: str, title: str, label: str, round_num: int) -> str:
        """Stream tokens to frontend via event_callback, return full text."""
        resp = self.client.chat.completions.create(
            model=self.MODEL,
            messages=messages,
            temperature=self.TEMPERATURE,
            stream=True,
        )
        full_text = ""
        # Send stream_start so frontend creates the bubble
        self.event_callback({"status": "stream_start", "phase": "debate", "round": round_num, "speaker": speaker, "title": title, "label": label})
        for chunk in resp:
            delta = chunk.choices[0].delta.content or ""
            if delta:
                full_text += delta
                self.event_callback({"status": "stream_token", "token": delta})
        self.event_callback({"status": "stream_end"})
        return full_text

    def _emit_as_stream(self, text: str, meta: dict):
        """Emit already-received text as word-by-word stream events (simulated typing)."""
        if not meta:
            return
        self.event_callback({
            "status": "stream_start", "phase": "debate",
            "round": meta.get("round_num", 0),
            "speaker": meta.get("speaker", ""),
            "title": meta.get("title", ""),
            "label": meta.get("label", ""),
        })
        # Send word-by-word for typing effect
        words = text.split(' ')
        for i, word in enumerate(words):
            token = word + (' ' if i < len(words) - 1 else '')
            self.event_callback({"status": "stream_token", "token": token})
        self.event_callback({"status": "stream_end"})

    def _run_react_turn(
        self,
        system_prompt: str,
        turn_prompt:   str,
        min_tools:     int,
        max_tools:     int = None,
        label:         str = "Agent",
        stream_meta:   dict = None,
    ) -> str:
        """
        MiroFish-style ReACT loop.

        1. Call LLM.
        2. If <tool_call> detected → execute tool → inject Observation → repeat.
        3. If "Final Answer:" detected before min_tools → reject + re-prompt.
        4. If max_tools hit → force Final Answer.
        5. If neither tool nor Final Answer → push agent back to tool call.
        """
        if max_tools is None:
            max_tools = self.MAX_TOOLS

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": turn_prompt},
        ]

        tool_count  = 0
        used_tools  = []
        all_tools   = list(self.oracle_tools.AVAILABLE_TOOLS.keys())
        loop_limit = 5
        attempts = 0

        print(f"    [{label}] ReACT loop starting (min={min_tools}, max={max_tools})")

        while attempts < loop_limit:
            attempts += 1
            response = self._call_llm(messages)

            # ── Tool call path ────────────────────────────────────────────
            tool_calls = _parse_tool_calls(response)
            if tool_calls and tool_count < max_tools:
                call      = tool_calls[0]
                tool_name = call.get("name", "")
                params    = call.get("parameters", {})
                result    = self.oracle_tools.execute(tool_name, params)
                tool_count += 1
                used_tools.append(tool_name)

                unused      = [t for t in all_tools if t not in used_tools]
                unused_hint = (
                    f"\n(You haven't used yet: {', '.join(unused[:3])} — consider them.)"
                    if unused else ""
                )
                can_answer = tool_count >= min_tools

                observation = (
                    f"Observation ({tool_name} — call {tool_count}/{max_tools}):\n"
                    f"{result}\n\n"
                    f"{'You may now write Final Answer: or call another tool.' if can_answer else f'You must call at least {min_tools - tool_count} more tool(s) before answering.'}"
                    f"{unused_hint}"
                )

                print(f"    [{label}] Tool {tool_count}: {tool_name}")
                messages.append({"role": "assistant", "content": response})
                messages.append({"role": "user",      "content": observation})
                continue

            # ── Final Answer path ─────────────────────────────────────────
            if "Final Answer:" in response:
                if tool_count < min_tools and attempts < loop_limit - 1:
                    rejection = TOOL_REJECT_MSG.format(n=tool_count, min_tools=min_tools)
                    print(f"    [{label}] Final Answer rejected ({tool_count}/{min_tools} tools)")
                    messages.append({"role": "assistant", "content": response})
                    messages.append({"role": "user",      "content": rejection})
                    continue

                idx = response.index("Final Answer:")
                answer = response[idx + len("Final Answer:"):].strip()
                print(f"    [{label}] Final Answer accepted ({tool_count} tools used, {len(answer)} chars)")
                self._emit_as_stream(answer, stream_meta)
                return answer

            # ── Max tools reached — force answer ──────────────────────────
            if tool_count >= max_tools or attempts >= loop_limit - 1:
                force_msg = TOOL_LIMIT_MSG.format(max_tools=max_tools) if tool_count >= max_tools else "Please provide your Final Answer now."
                print(f"    [{label}] Forcing Final Answer (attempts={attempts})")
                messages.append({"role": "assistant", "content": response})
                messages.append({"role": "user",      "content": force_msg})
                
                if stream_meta:
                    forced = self._call_llm_stream(messages, **stream_meta)
                else:
                    forced = self._call_llm(messages)
                    
                if "Final Answer:" in forced:
                    idx = forced.index("Final Answer:")
                    answer = forced[idx + len("Final Answer:"):].strip()
                    return answer
                return forced

            # ── Neither tool nor Final Answer ──────────────────────────────
            if tool_count >= min_tools:
                print(f"    [{label}] Accepted (no tag, {tool_count} tools used)")
                self._emit_as_stream(response, stream_meta)
                return response
            else:
                # Agent didn't use tools and hasn't met minimum — push ONCE then accept
                if attempts >= loop_limit - 2:
                    # Accept whatever we got — don't keep pushing
                    print(f"    [{label}] Accepting response (push limit, {tool_count}/{min_tools} tools)")
                    self._emit_as_stream(response, stream_meta)
                    return response
                push = TOOL_FORCE_PUSH.format(n=tool_count, min_tools=min_tools)
                print(f"    [{label}] Pushing ({tool_count}/{min_tools})")
                messages.append({"role": "assistant", "content": response})
                messages.append({"role": "user",      "content": push})
        
        return "Simulation error: Agent failed to provide a valid response after multiple attempts."

    # ── Transcript helpers ────────────────────────────────────────────────

    def _fmt_transcript(self, transcript: List[Dict]) -> str:
        parts = [f"[{t['speaker']}]:\n{t['content']}" for t in transcript]
        return "\n\n" + ("─" * 60 + "\n\n").join(parts)

    def _append(self, transcript: List[Dict], speaker: str, content: str):
        transcript.append({"speaker": speaker, "content": content})
        print(f"\n{'-'*60}\n🗣️  [{speaker.upper()} SPEAKS]:\n{content}\n{'-'*60}\n")
        print(f"  -> Appended to central transcript ({len(content)} chars)")

    # ── Main orchestrator ─────────────────────────────────────────────────

    def run(self) -> str:
        lead   = self.debate_agents[0]
        agent2 = self.debate_agents[1]
        agent3 = self.debate_agents[2]
        my     = self.market_context.my_company_stats
        company_name = my.get("name", "Company")

        transcript: List[Dict] = []

        # ── Round 0: Chair Opens ────────────────────────────────────────────
        print(f"\n{'='*60}")
        print(f"ROUND 0 — {lead.name} ({lead.title}) opens the session")
        print("="*60)

        ceo_system = (
            CEO_BRIEF_SYSTEM
            .replace("{name}",         lead.name)
            .replace("{title}",        lead.title)
            .replace("{company}",      company_name)
            .replace("{dossier}",      self.shared_intelligence)
            .replace("{tool_schema}",  TOOL_SCHEMA)
            .replace("{react_rules}",  REACT_RULES.replace("MIN_TOOLS_REQUIRED", str(self.MIN_CEO_BRIEF)))
        )
        ceo_prompt = (
            CEO_BRIEF_PROMPT
            .replace("{scenario}", self.scenario)
            .replace("{move}",     self.move)
        )
        brief = self._run_react_turn(ceo_system, ceo_prompt, self.MIN_CEO_BRIEF,
                                     label=f"{lead.name} (Brief)",
                                     stream_meta={"speaker": lead.name, "title": lead.title, "label": "OPENING BRIEF", "round_num": 0})
        self._append(transcript, f"{lead.name} ({lead.title}) — OPENING BRIEF", brief)

        # ── Round 1: First Reactions (runs if num_rounds >= 2) ─────────────
        if self.num_rounds >= 2:
            print(f"\n{'='*60}")
            print(f"ROUND 1 — {agent2.name} reacts")
            print("="*60)

            r1_p2 = R1_REACT_PROMPT.replace("{transcript}", self._fmt_transcript(transcript)) \
                                    .replace("{name}",      agent2.name) \
                                    .replace("{dept}",      agent2.dept)
            r1_reply2 = self._run_react_turn(
                agent2.system_prompt, r1_p2, self.MIN_EXEC, label=f"{agent2.name} (R1)",
                stream_meta={"speaker": agent2.name, "title": agent2.title, "label": "REACTION", "round_num": 1}
            )
            self._append(transcript, f"{agent2.name} ({agent2.title}) — ROUND 1", r1_reply2)

            print(f"\n{'='*60}")
            print(f"ROUND 1 — {agent3.name} counters")
            print("="*60)

            r1_p3 = R1_COUNTER_PROMPT.replace("{transcript}",   self._fmt_transcript(transcript)) \
                                      .replace("{name}",         agent3.name) \
                                      .replace("{dept}",         agent3.dept) \
                                      .replace("{prev_speaker}", agent2.name)
            r1_reply3 = self._run_react_turn(
                agent3.system_prompt, r1_p3, self.MIN_EXEC, label=f"{agent3.name} (R1)",
                stream_meta={"speaker": agent3.name, "title": agent3.title, "label": "COUNTER", "round_num": 1}
            )
            self._append(transcript, f"{agent3.name} ({agent3.title}) — ROUND 1", r1_reply3)

        # ── Round 2: Rebuttals (runs if num_rounds >= 3) ──────────────────
        if self.num_rounds >= 3:
            print(f"\n{'='*60}")
            print(f"ROUND 2 — {agent2.name} rebuts")
            print("="*60)

            r2_p2 = R2_REBUTTAL_PROMPT.replace("{transcript}",   self._fmt_transcript(transcript)) \
                                       .replace("{name}",         agent2.name) \
                                       .replace("{dept}",         agent2.dept) \
                                       .replace("{prev_speaker}", agent3.name)
            r2_reply2 = self._run_react_turn(
                agent2.system_prompt, r2_p2, self.MIN_EXEC, label=f"{agent2.name} (R2)",
                stream_meta={"speaker": agent2.name, "title": agent2.title, "label": "REBUTTAL", "round_num": 2}
            )
            self._append(transcript, f"{agent2.name} ({agent2.title}) — ROUND 2 REBUTTAL", r2_reply2)

            print(f"\n{'='*60}")
            print(f"ROUND 2 — {agent3.name} defends")
            print("="*60)

            r2_p3 = R2_DEFENSE_PROMPT.replace("{transcript}",   self._fmt_transcript(transcript)) \
                                      .replace("{name}",         agent3.name) \
                                      .replace("{dept}",         agent3.dept) \
                                      .replace("{prev_speaker}", agent2.name)
            r2_reply3 = self._run_react_turn(
                agent3.system_prompt, r2_p3, self.MIN_EXEC, label=f"{agent3.name} (R2)",
                stream_meta={"speaker": agent3.name, "title": agent3.title, "label": "DEFENSE", "round_num": 2}
            )
            self._append(transcript, f"{agent3.name} ({agent3.title}) — ROUND 2 DEFENSE", r2_reply3)

        # ── Round 3: Escalation (runs if num_rounds >= 4) ─────────────────
        if self.num_rounds >= 4:
            print(f"\n{'='*60}")
            print(f"ROUND 3 — {agent2.name} escalates")
            print("="*60)

            r3e_p2 = R3_ESCALATE_PROMPT.replace("{transcript}", self._fmt_transcript(transcript)) \
                                        .replace("{name}",      agent2.name) \
                                        .replace("{dept}",      agent2.dept)
            r3e_reply2 = self._run_react_turn(
                agent2.system_prompt, r3e_p2, self.MIN_ESCALATE, label=f"{agent2.name} (R3-Esc)",
                stream_meta={"speaker": agent2.name, "title": agent2.title, "label": "ESCALATION", "round_num": 3}
            )
            self._append(transcript, f"{agent2.name} ({agent2.title}) — ROUND 3 ESCALATION", r3e_reply2)

            print(f"\n{'='*60}")
            print(f"ROUND 3 — {agent3.name} fires back")
            print("="*60)

            r3e_p3 = R3_ESCALATE_PROMPT.replace("{transcript}", self._fmt_transcript(transcript)) \
                                        .replace("{name}",      agent3.name) \
                                        .replace("{dept}",      agent3.dept)
            r3e_reply3 = self._run_react_turn(
                agent3.system_prompt, r3e_p3, self.MIN_ESCALATE, label=f"{agent3.name} (R3-Esc)",
                stream_meta={"speaker": agent3.name, "title": agent3.title, "label": "ESCALATION", "round_num": 3}
            )
            self._append(transcript, f"{agent3.name} ({agent3.title}) — ROUND 3 ESCALATION", r3e_reply3)

        # ── Round 4: Final Positions (runs if num_rounds >= 5) ────────────
        if self.num_rounds >= 5:
            print(f"\n{'='*60}")
            print(f"ROUND 4 — {agent2.name} final position")
            print("="*60)

            r3_p2 = R3_FINAL_PROMPT.replace("{transcript}", self._fmt_transcript(transcript)) \
                                    .replace("{name}",      agent2.name) \
                                    .replace("{dept}",      agent2.dept)
            r3_reply2 = self._run_react_turn(
                agent2.system_prompt, r3_p2, self.MIN_FINAL_STMT, label=f"{agent2.name} (R4)",
                stream_meta={"speaker": agent2.name, "title": agent2.title, "label": "FINAL", "round_num": 4}
            )
            self._append(transcript, f"{agent2.name} ({agent2.title}) — ROUND 4 FINAL", r3_reply2)

            print(f"\n{'='*60}")
            print(f"ROUND 4 — {agent3.name} final position")
            print("="*60)

            r3_p3 = R3_FINAL_PROMPT.replace("{transcript}", self._fmt_transcript(transcript)) \
                                    .replace("{name}",      agent3.name) \
                                    .replace("{dept}",      agent3.dept)
            r3_reply3 = self._run_react_turn(
                agent3.system_prompt, r3_p3, self.MIN_FINAL_STMT, label=f"{agent3.name} (R4)",
                stream_meta={"speaker": agent3.name, "title": agent3.title, "label": "FINAL", "round_num": 4}
            )
            self._append(transcript, f"{agent3.name} ({agent3.title}) — ROUND 4 FINAL", r3_reply3)

        # ── Committee Verdict ─────────────────────────────────────────────
        print(f"\n{'='*60}")
        print(f"COMMITTEE VERDICT — {lead.name} makes the binding call")
        print("="*60)

        verdict_system = (
            CEO_VERDICT_SYSTEM
            .replace("{name}",         lead.name)
            .replace("{title}",        lead.title)
            .replace("{company}",      company_name)
            .replace("{dossier}",      self.shared_intelligence)
            .replace("{tool_schema}",  TOOL_SCHEMA)
            .replace("{react_rules}",  REACT_RULES.replace("MIN_TOOLS_REQUIRED", str(self.MIN_CEO_VERDICT)))
        )
        verdict_prompt = (
            CEO_VERDICT_PROMPT
            .replace("{transcript}",   self._fmt_transcript(transcript))
            .replace("{name}",         lead.name)
            .replace("{agent2_name}",  agent2.name)
            .replace("{agent3_name}",  agent3.name)
        )
        verdict = self._run_react_turn(verdict_system, verdict_prompt, self.MIN_CEO_VERDICT,
                                       label=f"{lead.name} (Verdict)",
                                       stream_meta={"speaker": lead.name, "title": lead.title, "label": "COMMITTEE VERDICT", "round_num": 5})
        self._append(transcript, f"{lead.name} ({lead.title}) — COMMITTEE VERDICT", verdict)

        # ── Strategist: Investment Memo ───────────────────────────────────
        print(f"\n{'='*60}")
        print("STRATEGIST — Synthesizing Investment Memo")
        print("="*60)

        strat_prompt = STRATEGIST_PROMPT.replace("{transcript}", self._fmt_transcript(transcript))
        survival_plan = self._run_react_turn(
            self.strategist_system, strat_prompt, self.MIN_STRATEGIST,
            label="Strategist",
            stream_meta={"speaker": "Strategist", "title": "Chief Strategist", "label": "INVESTMENT MEMO", "round_num": 6}
        )

        # Save to Supermemory
        if self.supermemory_client:
            try:
                cn = self.data.get("target", {}).get("company", {}).get("name", "Unknown")
                safe_tag = re.sub(r'[^a-zA-Z0-9_:-]', '-', f"company-{cn}")
                self.supermemory_client.add(
                    content=f"Scenario: {self.scenario}. Move: {self.move}. Plan: {survival_plan}",
                    container_tags=[safe_tag, "investment-memo"],
                )
                print("[Supermemory] Plan saved.")
            except Exception as e:
                print(f"[Supermemory] Save failed: {e}")

        return survival_plan


# ── CLI entry point ───────────────────────────────────────────────────────

if __name__ == "__main__":
    from ingestor import dual_fetch

    data  = dual_fetch("OpenAI", "Anthropic")
    event = "Anthropic is scaling"
    move  = "Launch enterprise tier"

    sim = OracleSimulation("Founder", "OpenAI", "Anthropic", ["Revenue"], ["Pitching"], "Some thoughts", data)
    print("\nStarting MiroFish ReACT debate simulation...")
    result = sim.run()

    print("\n" + "=" * 70)
    print("                    INVESTMENT MEMO")
    print("=" * 70 + "\n")
    print(result)
