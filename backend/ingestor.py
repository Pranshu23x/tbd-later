import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

CRUSTDATA_API_TOKEN = os.getenv("CRUSTDATA_API_TOKEN")
BASE_URL = "https://api.crustdata.com"

def mock_dual_fetch():
    mock_path = os.path.join(os.path.dirname(__file__), "..", "data", "sample.json")
    try:
        with open(mock_path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print("Mock file not found at", mock_path)
        return {}

def get_headers():
    if not CRUSTDATA_API_TOKEN:
        raise ValueError("CRUSTDATA_API_TOKEN not found in environment variables.")
    return {
        "Authorization": f"Bearer {CRUSTDATA_API_TOKEN}",
        "x-api-version": "2025-11-01",
        "Content-Type": "application/json"
    }

def fetch_company_profile(company_name: str):
    """
    Fetch a company's profile using Crustdata API.
    Returns capital, muscle, arsenal, and backing metrics.
    """
    search_payload = {
        "filters": [
            {"filter_type": "company_name", "type": "eq", "value": company_name}
        ],
        "limit": 1
    }
    company_search_url = f"{BASE_URL}/v1/company/search"
    response = requests.post(company_search_url, json=search_payload, headers=get_headers())
    
    if response.status_code != 200:
        print(f"Error fetching company {company_name}: {response.text}")
        return None
        
    companies = response.json().get("data", [])

    if not companies:
        return None
        
    c = companies[0]
    
    return {
        "id": c.get("id"),
        "name": c.get("name"),
        "capital": {
            "funding_total": c.get("funding_total"),
            "last_funding_date": c.get("last_funding_date")
        },
        "muscle": {
            "headcount": c.get("headcount"),
            "headcount_growth_percentage": c.get("headcount_growth_percentage")
        },
        "arsenal": {
            "employee_count_by_function": c.get("employee_count_by_function", {})
        },
        "backing": {
            "investor_list": c.get("investor_list", [])
        }
    }

def fetch_employee_data(company_id: str):
    """
    Deep Employee Extraction mapping to the detailed schema.
    """
    people_search_payload = {
        "filters": [
            {"filter_type": "company_id", "type": "eq", "value": company_id}
        ],
        "limit": 10 # Limit for prototyping
    }
    
    people_url = f"{BASE_URL}/v1/person/search"
    response = requests.post(people_url, json=people_search_payload, headers=get_headers())
    
    if response.status_code != 200:
        print(f"Error fetching people for company {company_id}: {response.text}")
        return []
        
    people_data = response.json().get("data", [])
    
    mapped_employees = []
    for p in people_data:
        mapped_employees.append({
            "professional_identity": {
                "full_name": p.get("name"),
                "current_title": p.get("title"),
                "seniority_level": p.get("seniority_level"),
                "department": p.get("department"),
                "location": p.get("location")
            },
            "deep_work_history": p.get("work_history", []), # Assumes structured history
            "academic_background": p.get("education_history", []),
            "signals_and_vibe": {
                "social_posts": p.get("recent_posts", []),
                "engagement_metrics": p.get("engagement_metrics", {}),
                "recent_job_changes": p.get("job_changes_last_year", 0)
            }
        })
    return mapped_employees

def dual_fetch(my_company_name: str, rival_company_name: str):
    """
    The Dual-Fetch pattern to get both protagonist and antagonist.
    """
    if not CRUSTDATA_API_TOKEN or CRUSTDATA_API_TOKEN == "your_crustdata_token_here":
        print("Using sample.json mockup since CRUSTDATA_API_TOKEN is missing...")
        return mock_dual_fetch()
        
    my_company = fetch_company_profile(my_company_name)
    rival_company = fetch_company_profile(rival_company_name)
    
    my_employees = fetch_employee_data(my_company["id"]) if my_company else []
    rival_employees = fetch_employee_data(rival_company["id"]) if rival_company else []
    
    return {
        "target": {
            "company": my_company,
            "employees": my_employees
        },
        "rival": {
            "company": rival_company,
            "employees": rival_employees
        }
    }

def search_by_thesis(industry: str = None, min_growth: float = None, location: str = None, limit: int = 5):
    """
    Search for companies matching a specific investment thesis.
    Example: 'B2B SaaS', '20% growth', 'India'
    """
    filters = []
    if industry:
        filters.append({"filter_type": "industry", "type": "eq", "value": industry})
    if min_growth:
        filters.append({"filter_type": "headcount_growth_percentage", "type": "gte", "value": min_growth})
    if location:
        filters.append({"filter_type": "location", "type": "contains", "value": location})

    payload = {
        "filters": filters,
        "limit": limit
    }
    
    response = requests.post(f"{BASE_URL}/v1/company/search", json=payload, headers=get_headers())
    
    if response.status_code != 200:
        print(f"Error searching by thesis: {response.text}")
        return []
        
    return response.json().get("data", [])

if __name__ == "__main__":
    # Example Dual Fetch
    data = dual_fetch("Zepto", "Blinkit")
    with open("../data/dual_fetch_mock.json", "w") as f:
        json.dump(data, f, indent=4)
    print("Dual fetch test complete.")
