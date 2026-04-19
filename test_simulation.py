"""
Reflex VC Intelligence — Backend Workflow Test
Usage: python test_simulation.py [company_name]
Example: python test_simulation.py "Retool"
"""
import os
import sys
import json
from dotenv import load_dotenv

# Load from .env file
load_dotenv()

# Set working directory to backend so imports work
sys.path.insert(0, os.path.abspath('backend'))

from simulation_engine import OracleSimulation
from ingestor import fetch_company_profile, search_by_thesis

# Get target company from CLI args or default
target_name = sys.argv[1] if len(sys.argv) > 1 else "Retool"

print(f"{'='*60}")
print(f"  REFLEX VC INTELLIGENCE — Deal Review Pipeline")
print(f"  Target: {target_name}")
print(f"{'='*60}")

# 1. Fetch Target Company
print(f"\n[1/3] Ingesting Target Company Data from Crustdata...")
target_data = fetch_company_profile(target_name)
if not target_data:
    print(f"  WARN: Could not fetch enriched data for '{target_name}'. Using minimal stub.")
    target_data = {"name": target_name, "id": None}
else:
    print(f"  ✓ Ingested {target_data.get('name')}")
    print(f"    Headcount: {target_data.get('muscle', {}).get('headcount')}")
    print(f"    Funding: ${target_data.get('capital', {}).get('funding_total', 'N/A')}")

# 2. Build Data Dict (format the simulation expects)
print(f"\n[2/3] Preparing Market Context...")
data = {
    "target": {
        "company": target_data,
        "employees": []
    },
    "rival": {
        "company": {},
        "employees": []
    }
}
print(f"  ✓ Market context ready")

# 3. Run the Simulation
print(f"\n[3/3] Running Bull vs Bear ReACT Debate Loop...")
print(f"{'='*60}\n")

try:
    sim = OracleSimulation(
        user_type="Managing Partner",
        target_company=target_name,
        compare_against="Industry Average",
        benchmarks=["ARR Growth", "Burn Multiple", "Headcount Growth"],
        planning=["Investment Memo"],
        planning_custom=f"Evaluate if we should lead {target_name}'s next funding round.",
        data=data,
        num_rounds=2  # Keep short for testing
    )

    result = sim.run()

    print(f"\n{'='*60}")
    print(f"  INVESTMENT MEMO — FINAL OUTPUT")
    print(f"{'='*60}\n")
    print(result)

except Exception as e:
    print(f"\nSIMULATION FAILED: {e}")
    import traceback
    traceback.print_exc()
