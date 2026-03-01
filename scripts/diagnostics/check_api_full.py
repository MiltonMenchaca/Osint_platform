import requests
import json
import time
import sys
import os

# Configuration
BASE_URL = os.environ.get("BASE_URL", "http://localhost:8000/api")
USERNAME = os.environ.get("USERNAME", "admin")
PASSWORD = os.environ.get("PASSWORD", "admin_password")

# Colors for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"

def log(msg, status="INFO"):
    if status == "SUCCESS":
        print(f"{GREEN}[SUCCESS] {msg}{RESET}")
    elif status == "FAIL":
        print(f"{RED}[FAIL] {msg}{RESET}")
    elif status == "WARN":
        print(f"{YELLOW}[WARN] {msg}{RESET}")
    else:
        print(f"[INFO] {msg}")

def check_response(response, expected_code=200, context=""):
    if response.status_code == expected_code:
        return True
    else:
        log(f"{context} Failed. Status: {response.status_code}", "FAIL")
        try:
            print(json.dumps(response.json(), indent=2))
        except:
            print(response.text)
        return False

def main():
    log("Starting Full API Integration Test...")
    
    # 1. Authentication
    log("1. Authenticating...")
    auth_url = f"{BASE_URL}/auth/token/"
    try:
        response = requests.post(auth_url, data={"username": USERNAME, "password": PASSWORD})
    except requests.exceptions.ConnectionError:
        log("Could not connect to API. Is the server running on port 8000?", "FAIL")
        sys.exit(1)

    if not check_response(response, 200, "Authentication"):
        sys.exit(1)
    
    tokens = response.json()
    access_token = tokens.get("access")
    if not access_token:
        log("No access token received", "FAIL")
        sys.exit(1)
    
    headers = {"Authorization": f"Bearer {access_token}"}
    log("Authentication Successful", "SUCCESS")

    # 2. Create Investigation
    log("2. Creating Investigation...")
    inv_data = {
        "name": f"API Test {int(time.time())}",
        "description": "Automated API test investigation",
        "status": "active"
    }
    response = requests.post(f"{BASE_URL}/investigations/", headers=headers, json=inv_data)
    if not check_response(response, 201, "Create Investigation"):
        sys.exit(1)
    
    investigation = response.json()
    log(f"Investigation Response: {json.dumps(investigation)}", "INFO")
    inv_id = investigation["id"]
    log(f"Investigation created: {inv_id}", "SUCCESS")

    # 3. Create Entity (Target)
    log("3. Creating Target Entity...")
    entity_data = {
        "entity_type": "domain",
        "value": "example.com",
        "source": "manual",
        "confidence_score": 1.0
    }
    # Note: URL pattern is /investigations/{id}/entities/
    response = requests.post(f"{BASE_URL}/investigations/{inv_id}/entities/", headers=headers, json=entity_data)
    if not check_response(response, 201, "Create Entity"):
        sys.exit(1)
    
    entity = response.json()
    entity_id = entity["id"]
    log(f"Entity created: {entity_id} ({entity['value']})", "SUCCESS")

    # 4. Trigger Transform (Ping)
    log("4. Triggering Ping Transform...")
    exec_data = {
        "transform_name": "ping",
        "input_entity_id": entity_id,
        "parameters": {
            "count": 2,
            "timeout": 10
        }
    }
    response = requests.post(f"{BASE_URL}/investigations/{inv_id}/executions/", headers=headers, json=exec_data)
    if not check_response(response, 201, "Trigger Transform"):
        sys.exit(1)
    
    execution = response.json()
    exec_id = execution["id"]
    log(f"Transform triggered: {exec_id}", "SUCCESS")

    # 5. Poll Execution Status
    log("5. Polling Execution Status...")
    status = "pending"
    max_retries = 150 # 300 seconds
    for i in range(max_retries):
        response = requests.get(f"{BASE_URL}/investigations/{inv_id}/executions/{exec_id}/", headers=headers)
        if response.status_code == 200:
            data = response.json()
            status = data["status"]
            log(f"Status: {status}", "INFO")
            
            if status == "completed":
                log("Execution Completed", "SUCCESS")
                break
            elif status == "failed":
                log(f"Execution Failed: {data.get('error_message')}", "FAIL")
                break
        else:
            log(f"Error polling status: {response.status_code}", "WARN")
        
        time.sleep(2)
    else:
        log("Timeout waiting for execution", "FAIL")
        sys.exit(1)

    # 6. Verify Results (Entities Created)
    log("6. Verifying Results...")
    # List entities in investigation
    response = requests.get(f"{BASE_URL}/investigations/{inv_id}/entities/", headers=headers)
    if check_response(response, 200, "List Entities"):
        entities = response.json()
        count = len(entities)
        log(f"Total entities in investigation: {count}", "INFO")
        
        # We expect more than 1 (the initial one + results)
        if count > 1:
            log(f"Verification Passed: {count} entities found (New entities created)", "SUCCESS")
        else:
            log("Verification Warning: No new entities created (Only initial entity found)", "WARN")
            # Print execution logs if available
            log("Checking execution logs...", "INFO")
            log_response = requests.get(f"{BASE_URL}/investigations/{inv_id}/executions/{exec_id}/logs/", headers=headers)
            if log_response.status_code == 200:
                print(json.dumps(log_response.json(), indent=2))

    log("Full API Integration Test Completed", "SUCCESS")

if __name__ == "__main__":
    main()
