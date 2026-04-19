import sys, os
os.environ["PYTHONUTF8"] = "1"
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio
import json
import traceback
import queue
import threading

from ingestor import dual_fetch, fetch_company_profile
from simulation_engine import OracleSimulation
from graph_manager import GraphManager

app = FastAPI(title="OracleSwarm API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SimulateRequest(BaseModel):
    user_type: str
    target_company: str
    compare_against: str
    benchmarks: list[str]
    planning: list[str]
    planning_custom: str
    num_rounds: int = 4

@app.get("/api/search_company")
async def search_company(query: str):
    profile = fetch_company_profile(query)
    if not profile:
        raise HTTPException(status_code=404, detail="Company not found")
    return {"status": "success", "data": profile}

@app.post("/api/simulate")
async def simulate(req: SimulateRequest):
    """
    MiroFish-style SSE stream.
    
    Instead of running the entire simulation in one shot and returning the result, 
    we stream each debate turn as a separate SSE event so the frontend can render 
    each agent's speech bubble in real-time (like MiroFish's Step3Simulation polling).
    
    Event statuses:
      - starting     : Dual-fetch initiated
      - data_ready   : Company data loaded (includes the raw data for graph rendering)
      - graph         : Neo4j traitor scan
      - debate_turn  : Individual agent speech (speaker, round, content)
      - verdict      : CEO verdict
      - plan         : Strategist plan
      - complete     : Final summary
      - error        : Error
    """
    async def event_stream():
        try:
            # ── Phase 1: Data Ingestion ──
            
            rival = req.compare_against.strip() if req.compare_against else "TestRival"
            
            try:
                data = dual_fetch(req.target_company, rival)
            except Exception as e:
                raise Exception(f"Crustdata API Error: {str(e)}")

            # Send the raw data so frontend can build the D3 graph
            yield _sse({"status": "data_ready", "phase": "ingestion", "message": "Data loaded.", "data": data})

            # ── Phase 2: Graph / Traitor Detection ──
            traitor_detected = False
            try:
                g = GraphManager()
                g.initialize_schema()
                traitors = g.detect_boardroom_traitors()
                g.close()
                traitor_detected = len(traitors) > 0
            except Exception as e:
                print("Neo4j Error (non-fatal):", str(e))
                # Non-fatal: continue without Neo4j
                yield _sse({"status": "graph", "phase": "graph", "message": f"Neo4j skipped: {str(e)[:80]}. Continuing..."})

            # ── Phase 3: ReACT Debate (streamed per-turn) ──

            # Use a queue to stream individual turns from the synchronous simulation
            event_queue = queue.Queue()
            result_holder = {"plan": None, "error": None}

            def run_sim_streamed():
                try:
                    sim = OracleSimulation(
                        req.user_type, req.target_company, req.compare_against,
                        req.benchmarks, req.planning, req.planning_custom, data,
                        event_callback=lambda evt: event_queue.put(evt),
                        num_rounds=req.num_rounds
                    )
                    plan = sim.run()
                    result_holder["plan"] = plan
                except Exception as e:
                    result_holder["error"] = str(e)
                finally:
                    event_queue.put(None)  # Sentinel

            thread = threading.Thread(target=run_sim_streamed, daemon=True)
            thread.start()

            # Stream events from the queue as they arrive
            while True:
                try:
                    evt = await asyncio.to_thread(event_queue.get, timeout=120)
                except Exception:
                    break
                
                if evt is None:
                    break  # Simulation finished
                
                yield _sse(evt)

            # ── Phase 4: Final Result ──
            if result_holder["error"]:
                raise Exception(f"ReACT Engine Error: {result_holder['error']}")

            yield _sse({
                "status": "complete",
                "phase": "done",
                "result": {
                    "survival_plan": str(result_holder["plan"] or "").strip(),
                    "boardroom_traitor_detected": traitor_detected
                }
            })

        except Exception as e:
            print("Simulation Error:", traceback.format_exc())
            yield _sse({"status": "error", "message": str(e)})
            yield _sse({"status": "complete", "result": None})

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def _sse(data: dict) -> str:
    """Format a dict as an SSE data line."""
    return "data: " + json.dumps(data) + "\n\n"


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
