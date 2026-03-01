
import os
import django
import sys
import time
import json
from pathlib import Path

# Setup Django environment
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(BASE_DIR)
sys.path.append("/app")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "osint_platform.settings.production")
django.setup()

from apps.investigations.models import Investigation, TransformExecution
from apps.entities.models import Entity
from apps.transforms.models import Transform
from apps.investigations.tasks import execute_transform
from apps.transforms.wrappers import get_wrapper
from django.contrib.auth import get_user_model

def print_header(title):
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")

def check_wrapper_availability(tool_name):
    print(f"[*] Checking wrapper for {tool_name}...")
    try:
        wrapper_class = get_wrapper(tool_name)
        wrapper = wrapper_class()
        # wrappers usually have check_availability or similar, but instantiation is a good first step
        print(f"[OK] Wrapper {tool_name} loaded successfully.")
        return True
    except Exception as e:
        print(f"[FAIL] Failed to load wrapper {tool_name}: {e}")
        return False

def run_transform_test(investigation, tool_name, input_entity, params=None, timeout=60):
    print(f"\n[-] Testing Transform: {tool_name}")
    print(f"    Input: {input_entity.value} ({input_entity.entity_type})")
    
    # Ensure Transform exists in DB
    try:
        Transform.objects.get(name=tool_name)
    except Transform.DoesNotExist:
        print(f"[WARN] Transform {tool_name} not found in DB. Registering it temporary/checking scripts...")
        # In a real scenario, we expect them to be registered via register_transforms.py
        # We will assume they are or fail.
        print(f"[FAIL] Transform {tool_name} does not exist in database. Run register_transforms.py first.")
        return False

    # Create Execution
    execution = TransformExecution.objects.create(
        investigation=investigation,
        transform_name=tool_name,
        input_entity=input_entity,
        status="pending"
    )

    # Dispatch Task
    task = execute_transform.delay(
        execution_id=str(execution.id),
        transform_name=tool_name,
        input_value=input_entity.value,
        parameters=params or {}
    )
    print(f"    Task ID: {task.id}")

    # Poll for result
    start_time = time.time()
    while time.time() - start_time < timeout:
        if task.ready():
            break
        print(f"    Waiting... ({int(time.time() - start_time)}s)", end="\r")
        time.sleep(2)
    print()

    if task.successful():
        result = task.result
        print(f"[OK] Task {tool_name} completed successfully.")
        
        entities_count = result.get("entities_created", 0)
        print(f"    Entities created: {entities_count}")
        
        # Optional: Print first few entities
        if entities_count > 0:
            # We can't easily get the specific entities created from the result dict without querying DB
            # But we can check the investigation's entities
            pass
            
        return True
    else:
        print(f"[FAIL] Task {tool_name} failed or timed out.")
        if task.failed():
             print(f"    Error: {task.result}")
        return False

def main():
    print_header("PHISHING CAMPAIGN FLOW VALIDATION")
    
    # 1. Setup User and Investigation
    User = get_user_model()
    admin_user, _ = User.objects.get_or_create(username="admin")
    
    investigation, _ = Investigation.objects.get_or_create(
        name="Phishing Simulation Test",
        defaults={
            "created_by": admin_user,
            "description": "Automated validation of phishing detection tools"
        }
    )
    print(f"[*] Investigation: {investigation.name} (ID: {investigation.id})")

    # 2. Check Wrappers Availability
    tools_to_test = [
        "nmap", "nuclei", "amass", "theharvester", 
        "sherlock", "holehe", "waybackurls", "httpx"
    ]
    
    print_header("WRAPPER AVAILABILITY CHECK")
    all_wrappers_ok = True
    for tool in tools_to_test:
        if not check_wrapper_availability(tool):
            all_wrappers_ok = False
    
    if not all_wrappers_ok:
        print("\n[WARN] Some wrappers failed to load. Validation might fail.")
    
    # 3. Execute Transforms (Mocked/Safe Targets)
    print_header("EXECUTION TESTS")
    
    # Create Seed Entities
    domain_entity, _ = Entity.objects.get_or_create(
        investigation=investigation,
        entity_type="domain",
        value="scanme.nmap.org",
        defaults={"source": "seed"}
    )
    
    ip_entity, _ = Entity.objects.get_or_create(
        investigation=investigation,
        entity_type="ip",
        value="45.33.32.156", # scanme.nmap.org
        defaults={"source": "seed"}
    )
    
    url_entity, _ = Entity.objects.get_or_create(
        investigation=investigation,
        entity_type="url",
        value="http://scanme.nmap.org",
        defaults={"source": "seed"}
    )

    # Test Nmap (Fast scan)
    run_transform_test(investigation, "nmap", ip_entity, params={"scan_type": "tcp_connect", "ports": "80,443", "timing": 4}, timeout=60)

    # Test Dmitry (Passive) - DISABLED
    # run_transform_test(investigation, "dmitry", domain_entity, params={}, timeout=60)
    
    # Test Nuclei (Version/Info check - might need a real target to return something, but we check execution success)
    run_transform_test(investigation, "nuclei", url_entity, params={"timeout": 60}, timeout=120)

    # Test TheHarvester
    run_transform_test(investigation, "theharvester", domain_entity, params={"limit": 10}, timeout=120)

    print("\n" + "="*60)
    print(" VALIDATION COMPLETE")
    print("="*60)

if __name__ == "__main__":
    main()
