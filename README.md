# Reflex

**Reflex** is an AI-native market simulation engine designed to support faster, more structured investment decision-making. It combines live company intelligence, adversarial multi-agent reasoning, and graph-based relationship analysis to help users evaluate market opportunities with greater clarity.

Built for **ContextCon** by **Crustdata x Y Combinator**.

## Overview

Traditional market research tools surface data. Reflex is built to turn that data into a decision workflow.

Given a market thesis or target company, Reflex:

- parses the investment prompt into structured search intent
- retrieves live company intelligence through Crustdata-powered workflows
- runs a Bull vs Bear multi-agent simulation
- incorporates graph-based relationship analysis through Neo4j
- produces a decision-oriented investment memo with rationale and next steps

The result is a more rigorous, debate-driven layer for sourcing, evaluating, and comparing opportunities.

## Core Capabilities

- **Natural-language thesis parsing** to translate broad prompts into structured search parameters
- **Live market intelligence enrichment** across company, funding, growth, and investor signals
- **Adversarial multi-agent reasoning** with Bull, Bear, and committee-style debate flows
- **Graph-based intelligence** to identify cross-company relationships and potential signal conflicts
- **Streaming simulation output** for real-time debate rendering in the interface
- **Decision memo generation** with a verdict, supporting evidence, and action plan

## How It Works

### 1. Thesis Input

Users begin with a natural-language thesis such as:

```text
B2B SaaS companies in Europe with strong headcount growth and no U.S. VC funding
```

Reflex converts that input into structured parameters including industry, region, company size, benchmarks, and investment goal.

### 2. Intelligence Gathering

The backend searches and enriches matching companies using external market intelligence sources, with Crustdata serving as the primary live data layer.

Signals used in the workflow include:

- company identity and profile data
- headcount and hiring indicators
- funding history
- investor information
- revenue and growth context

### 3. Multi-Agent Simulation

Reflex runs a structured adversarial reasoning loop:

- **Bull Analyst** argues for upside and opportunity
- **Bear Analyst** surfaces risks and weaknesses
- **Committee / CEO layer** synthesizes the arguments into a final verdict

This creates a more defensible decision process than a single-pass LLM response.

### 4. Graph Intelligence

Neo4j is used to model entity relationships and detect patterns that matter during evaluation, including overlapping investor relationships and other hidden strategic signals.

### 5. Decision Output

The final output is an investment-style memo that can include:

- an invest / pass style verdict
- key opportunities
- major risks
- structured supporting reasoning
- follow-up actions
- reversal triggers or monitoring signals

## Product Walkthrough

### Landing Page

![Landing Page](https://github.com/user-attachments/assets/113d191e-6918-4177-adb2-c6d447319f07)

### Simulation Input

![Simulation Input](https://github.com/user-attachments/assets/1be2d8ba-3cf3-4baa-b273-b3c0cea2b4a4)

### Multi-Agent Debate

![Multi-Agent Debate](https://github.com/user-attachments/assets/a6d828ce-8663-442b-b290-e95a6cc03d5f)

### Graph Intelligence View

![Graph Intelligence View](https://github.com/user-attachments/assets/ba6eaa3c-f11a-4038-a2f4-e4d06a2ad3cf)

### Investment Memo Output

![Investment Memo Output](https://github.com/user-attachments/assets/046db80c-390d-4a3c-b1d0-f2554043160f)

Example outcome:

```text
Decision: PASS on Huwise | CONSIDER Hypatos

Why:
- Huwise: low growth and weak hiring momentum
- Hypatos: stronger scaling signals and healthier expansion

Next Steps:
- validate burn profile
- monitor hiring velocity

Reversal Triggers:
- growth drops below threshold
- runway falls below acceptable range
```

## Architecture

Reflex is split into a Python backend and a React frontend.

### Backend

The backend is built with **FastAPI** and is responsible for:

- thesis parsing
- data ingestion and enrichment
- simulation orchestration
- SSE-based streaming of debate events
- graph analysis via Neo4j

Key backend modules:

- `backend/server.py` - FastAPI server and streaming API endpoints
- `backend/orchestrator.py` - end-to-end Reflex pipeline orchestration
- `backend/ingestor.py` - data search and enrichment workflows
- `backend/simulation_engine.py` - multi-agent simulation logic
- `backend/graph_manager.py` - Neo4j schema and graph analysis
- `backend/prompts.py` - agent prompt definitions
- `backend/tools.py` - tool integrations used by the agents

### Frontend

The frontend is built with **React + Vite** and provides:

- landing and onboarding views
- simulation setup flows
- real-time simulation rendering
- memo and graph-oriented result views

Key frontend areas:

- `frontend/src/pages/Landing.jsx`
- `frontend/src/pages/RunSimulation.jsx`
- `frontend/src/pages/Simulation.jsx`

## Tech Stack

### Frontend

- React 19
- Vite
- React Router
- GSAP
- D3
- React Markdown

### Backend

- Python
- FastAPI
- Uvicorn
- Pydantic
- Pandas
- Neo4j
- CrewAI
- LangChain OpenAI

### Data and Intelligence Layer

- Crustdata
- DeepSeek / OpenAI-compatible orchestration
- Neo4j knowledge graph

## API Surface

The current backend exposes endpoints for:

- `GET /api/search_company`
- `POST /api/search_thesis`
- `POST /api/simulate`

The simulation endpoint streams server-sent events so the frontend can render debate turns in real time.

## Local Setup

### Backend

Install Python dependencies:

```bash
pip install -r requirements.txt
```

Run the API server:

```bash
cd backend
python server.py
```

The backend runs on `http://localhost:8000`.

### Frontend

Install frontend dependencies:

```bash
cd frontend
npm install
```

Start the Vite development server:

```bash
npm run dev
```

The frontend runs on the default Vite port unless changed in configuration.

## Environment Variables

The repository expects environment configuration for external services. Based on the current codebase, this includes values such as:

```env
DEEPSEEK_API_KEY=

NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=
```

Additional API credentials may be required depending on the data and tool integrations configured in the backend.

## Positioning

Reflex is best understood as a decision layer for capital allocation workflows:

- Crustdata provides live market intelligence
- Reflex structures that intelligence into an interactive simulation and recommendation system

It is designed for use cases such as:

- early-stage company screening
- thematic sourcing
- market mapping
- comparative diligence
- internal investment memo generation

## Disclaimer

Reflex is a decision-support product. It is not financial advice and should not be treated as a substitute for legal, financial, or investment due diligence.

## Contact

- [LinkedIn](https://www.linkedin.com/in/pranshukumar23/)
- [X](https://x.com/Pranshu23x)
