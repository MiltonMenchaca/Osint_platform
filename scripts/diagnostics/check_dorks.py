import requests
import time
import sys
import json

BASE_URL = "http://localhost:8000/api"
USERNAME = "admin"
PASSWORD = "admin_password"  # Replace with actual admin password if different, or use a known user

def login():
    url = f"{BASE_URL}/auth/token/"
    try:
        response = requests.post(url, json={"username": USERNAME, "password": PASSWORD})
        if response.status_code == 200:
            return response.json()["access"]
        else:
            print(f"Login failed: {response.status_code} {response.text}")
            return None
    except Exception as e:
        print(f"Connection failed: {e}")
        return None

def create_investigation(token):
    timestamp = int(time.time())
    url = f"{BASE_URL}/investigations/"
    headers = {"Authorization": f"Bearer {token}"}
    data = {
        "name": f"Dork Test Investigation {timestamp}",
        "description": "Testing Google Dorks execution",
        "status": "active"
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 201:
        return response.json()["id"]
    else:
        print(f"Create investigation failed: {response.text}")
        return None

def execute_dorks(token, investigation_id, dork_query):
    url = f"{BASE_URL}/investigations/{investigation_id}/execute-dorks/"
    headers = {"Authorization": f"Bearer {token}"}
    data = {
        "dorks": [dork_query],
        "target_domain": "example.com"
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 202:
        return response.json()["execution_ids"][0]
    else:
        print(f"Execute dorks failed: {response.text}")
        return None

def get_execution_status(token, investigation_id, execution_id):
    url = f"{BASE_URL}/investigations/{investigation_id}/executions/{execution_id}/"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Get status failed: {response.text}")
        return None

def get_entities(token, investigation_id):
    url = f"{BASE_URL}/investigations/{investigation_id}/"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json().get("entities", [])
    else:
        print(f"Get entities failed: {response.text}")
        return []

def main():
    print("1. Logging in...")
    token = login()
    if not token:
        # Try to register if login fails? Or assume admin exists.
        # For now, let's assume the user might need to be created or we can't proceed.
        # But wait, I can probably use the django shell to create a user if needed.
        # Let's try to proceed.
        print("Login failed. Please ensure the server is running and user exists.")
        return

    print("2. Creating investigation...")
    inv_id = create_investigation(token)
    if not inv_id:
        return
    print(f"Investigation created: {inv_id}")

    print("3. Executing Google Dork...")
    dork = "site:stackoverflow.com python"
    exec_id = execute_dorks(token, inv_id, dork)
    if not exec_id:
        return
    print(f"Execution started: {exec_id}")

    print("4. Waiting for results...")
    for i in range(10):
        status_data = get_execution_status(token, inv_id, exec_id)
        if not status_data:
            break
            
        status = status_data.get("status")
        print(f"Status: {status}")
        
        if status in ["completed", "failed"]:
            # Fetch logs
            logs_url = f"{BASE_URL}/investigations/{inv_id}/executions/{exec_id}/logs/"
            headers = {"Authorization": f"Bearer {token}"}
            logs_resp = requests.get(logs_url, headers=headers)
            if logs_resp.status_code == 200:
                logs = logs_resp.json()
                print(f"Results: {json.dumps(logs.get('results'), indent=2)}")
                print(f"Error: {logs.get('error_message')}")
            else:
                print(f"Failed to fetch logs: {logs_resp.status_code}")
            break
        time.sleep(5)

    if status == "completed":
        print("5. Verifying entities...")
        entities = get_entities(token, inv_id)
        url_entities = [e for e in entities if e["entity_type"] == "url"]
        print(f"Found {len(url_entities)} URL entities.")
        for e in url_entities:
            print(f" - {e['value']}")
    else:
        print("Execution did not complete successfully.")

if __name__ == "__main__":
    main()
