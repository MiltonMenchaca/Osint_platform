import os
import sys
import django
import time
import uuid

# Setup Django environment
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(BASE_DIR)
sys.path.append('/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'osint_platform.settings.development')
django.setup()

from apps.investigations.models import Investigation, TransformExecution
from apps.transforms.models import Transform
from apps.entities.models import Entity
from apps.investigations.tasks import execute_transform
from apps.transforms.wrappers import get_wrapper

from django.contrib.auth import get_user_model

def run_verification():
    print("Starting deployment verification...")
    
    # 0. Get or create user
    User = get_user_model()
    user, created = User.objects.get_or_create(username="admin", defaults={"email": "admin@example.com", "is_staff": True, "is_superuser": True})
    if created:
        user.set_password("admin")
        user.save()
        print(f"[OK] Created admin user")
    
    # 1. Create test investigation
    inv_name = f"Verification Test {uuid.uuid4().hex[:8]}"
    investigation = Investigation.objects.create(
        name=inv_name,
        description="Automated verification test",
        created_by=user
    )
    print(f"[OK] Created investigation: {investigation.name} ({investigation.id})")
    
    # 2. Verify wrapper availability (SpiderFoot)
    try:
        wrapper_cls = get_wrapper("spiderfoot")
        # Try to instantiate to check local availability, but don't fail if missing (might be on worker)
        try:
            sf_wrapper = wrapper_cls()
            print(f"[OK] SpiderFoot wrapper loaded locally: {sf_wrapper.get_tool_name()}")
        except Exception as e:
            print(f"[WARN] SpiderFoot wrapper could not be loaded locally (normal for backend): {e}")
            print("[INFO] Proceeding to test execution on worker...")
    except Exception as e:
        print(f"[FAIL] Could not get SpiderFoot wrapper class: {e}")
        return

    # 3. Create a scope entity
    target_value = "scanme.nmap.org"
    domain_entity, _ = Entity.objects.get_or_create(
        entity_type="domain",
        value=target_value,
        investigation=investigation
    )
    print(f"[OK] Created scope entity: {domain_entity.value}")

    # 4. Trigger transform execution via Celery
    tool_name = "spiderfoot"
    # Use sfp_dnsresolve for speed
    params = {"modules": "sfp_dnsresolve", "timeout": 300}
    
    print(f"Triggering {tool_name} on {domain_entity.value}...")
    
    # Create execution record first
    execution_record = TransformExecution.objects.create(
        investigation=investigation,
        transform_name=tool_name,
        input_entity=domain_entity,
        status="pending"
    )
    
    # Launch task
    task = execute_transform.delay(
        execution_id=str(execution_record.id),
        transform_name=tool_name,
        input_value=domain_entity.value,
        parameters=params
    )
    print(f"[OK] Task submitted. Task ID: {task.id}")
    
    # 5. Poll for completion
    print("Waiting for task completion...")
    max_retries = 200 # 400s max
    for i in range(max_retries):
        execution_record.refresh_from_db()
        
        if execution_record.status == "completed":
            print(f"[OK] Execution completed successfully!")
            results = execution_record.results
            
            # Basic validation of results
            entities_count = results.get("entities_created", 0)
            print(f"Results: {entities_count} entities created.")
            
            if entities_count > 0:
                print("[SUCCESS] Verification PASSED: Entities were created.")
            else:
                print("[WARN] Verification WARNING: No entities created (check tool output).")
                print(f"Raw Output Snippet: {str(results.get('raw_output', ''))[:200]}")
            
            break
        elif execution_record.status == "failed":
            print(f"[FAIL] Execution failed: {execution_record.error_message}")
            break
            
        print(f"Status: {execution_record.status}. Waiting...", end="\r")
        time.sleep(2)
    else:
        print("\n[FAIL] Timeout waiting for execution completion")

if __name__ == "__main__":
    try:
        run_verification()
    except Exception as e:
        print(f"\n[FATAL] Verification script crashed: {e}")
        import traceback
        traceback.print_exc()
