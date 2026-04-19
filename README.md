# Reflex: AI-Native Venture Intelligence

**Powered by Crustdata | Built for YC Spring 2026 RFS**

Reflex is an autonomous venture research platform that identifies high-growth startups and subjects them to rigorous, data-backed "Bull vs. Bear" agentic debates to generate high-conviction investment memos.

## 🚀 The Vision
In the future, VC firms won't just use AI to search for deals; they'll use AI to **stress-test** them. Reflex automates the entire "Due Diligence" loop:
1.  **Thesis-Driven Sourcing**: Identifies companies matching complex growth, industry, and geographic criteria using Crustdata's 40M+ company database.
2.  **Autonomous Research**: Agents call Crustdata's Person, Company, and Web APIs in real-time to find "Hidden Signals" (e.g., specific hiring spikes, founder history, recent media sentiment).
3.  **Conflict-Based Reasoning**: A "Bull Analyst" and a "Bear Analyst" debate the deal. The Bear is incentivized to find "deal breakers" (burn rate, churn signals), while the Bull focuses on "alpha" (hiring velocity, market capture).
4.  **Investment Memo**: A final verdict is delivered by an Investment Committee Chair agent, synthesizing the debate into a 100-Day Strategic Plan.

## 🛠️ Technology Stack
- **Data Backbone**: [Crustdata](https://crustdata.com/) (Company Search, Person Enrich, Web Search Live).
- **Reasoning Engine**: ReACT-based Multi-Agent Debate Loop (DeepSeek-V3).
- **Knowledge Graph**: Neo4j (Relationship mapping between founders and previous exits).
- **Frontend**: React (Venture Intelligence Dashboard).

## 🎯 Use Case Alignment: AI-Native Hedge Funds (RFS 03)
Reflex directly addresses the YC Spring 2026 Request for Startups for **Investment Infrastructure**. It transforms the repetitive work of VC analysts into an autonomous research loop that never sleeps.

---

### How to Run
1. Install dependencies: `pip install -r requirements.txt`
2. Set your environment variables in `.env` (CRUSTDATA_API_TOKEN, DEEPSEEK_API_KEY).
3. Start the backend: `python backend/server.py`
4. Start the frontend: `npm run dev` (in /frontend)
