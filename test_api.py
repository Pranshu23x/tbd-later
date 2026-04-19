import os
import json
from dotenv import load_dotenv

# Load from .env file
load_dotenv()

# Set working directory to backend so imports work
import sys
sys.path.insert(0, os.path.abspath('backend'))

from ingestor import search_by_thesis, fetch_company_profile

print("Testing Crustdata API Connection...")
try:
    print("\n--- Testing search_by_thesis ---")
    results = search_by_thesis(industry="Software Development", min_growth=20.0, location="USA")
    print(f"Successfully found {len(results)} companies matching the thesis!")
    if results:
        print("First result:")
        print(json.dumps(results[0], indent=2))
        
        # Test fetching details for the first company
        first_company = results[0].get("basic_info", {}).get("name", "")
        if first_company:
            print(f"\n--- Testing fetch_company_profile for {first_company} ---")
            profile = fetch_company_profile(first_company)
            print("Successfully fetched profile!")
            print(f"Company: {profile.get('name')}")
            print(f"Headcount: {profile.get('muscle', {}).get('headcount')}")
            
except Exception as e:
    print(f"TEST FAILED: {e}")
