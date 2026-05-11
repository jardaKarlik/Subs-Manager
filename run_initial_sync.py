import requests
import json
import time

API_URL = "http://localhost:8000/api/parse-emails"

def run_initial_sync():
    print("Starting initial 1-year sync...")
    payload = {
        "max_results": 2000,
        "since_days": 365
    }
    
    try:
        start_time = time.time()
        response = requests.post(API_URL, json=payload, timeout=600) # Long timeout for backfill
        response.raise_for_status()
        
        duration = time.time() - start_time
        result = response.json()
        
        print(f"\nSync complete in {duration:.2f} seconds!")
        print(f"Message: {result.get('message')}")
        print(f"Results summary:")
        print(json.dumps(result.get('results', {}), indent=2))
        
    except requests.exceptions.RequestException as e:
        print(f"\nError triggering sync: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"Response: {e.response.text}")

if __name__ == "__main__":
    # Note: Ensure the FastAPI server is running before executing this
    run_initial_sync()
