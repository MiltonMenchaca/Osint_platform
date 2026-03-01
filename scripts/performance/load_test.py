import os
import sys
import time
import django
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "osint_platform.settings.production")
django.setup()

from apps.investigations.models import Investigation
from apps.entities.models import Entity
from apps.investigations.tasks import execute_transform

def run_investigation_load(idx, domain):
    print(f"[{idx}] Starting investigation for {domain}")
    
    from django.contrib.auth.models import User
    
    # Get a user (admin or first available)
    user = User.objects.filter(is_superuser=True).first()
    if not user:
        user = User.objects.first()
    if not user:
        # Create a temp admin if no user exists
        print("Creating temporary admin user for tests...")
        user = User.objects.create_superuser('admin_test', 'admin@example.com', 'admin123')

    # Create investigation
    inv = Investigation.objects.create(
        name=f"Load Test {idx} - {domain}",
        description="Automated load test",
        created_by=user
    )
    
    # Create input entity
    entity = Entity.objects.create(
        investigation=inv,
        entity_type="domain",
        value=domain,
        source="user"
    )
    
    tools = ["crtsh", "dnstwist", "spiderfoot"]
    tasks = []
    
    for tool in tools:
        print(f"[{idx}] Triggering {tool} for {domain}")
        # Use execute_transform task
        # We need a unique execution ID (UUID)
        import uuid
        execution_id = str(uuid.uuid4())
        
        # Note: In real app, we create TransformExecution record here.
        # But execute_transform handles it if we pass execution_id? 
        # Actually execute_transform expects an existing TransformExecution ID usually, 
        # OR it creates one? 
        # Looking at tasks.py: 
        # def execute_transform(execution_id, ...):
        #     execution = TransformExecution.objects.get(id=execution_id)
        
        # So we MUST create TransformExecution first.
        from apps.investigations.models import TransformExecution
            
        execution = TransformExecution.objects.create(
            id=execution_id,
            investigation=inv,
            transform_name=tool,
            input_entity=entity,
            status="pending"
        )
        
        # Dispatch task
        params = {"modules": "sfp_whois"} if tool == "spiderfoot" else {}
        async_result = execute_transform.delay(
            execution_id=execution_id,
            transform_name=tool,
            input_value=domain,
            parameters=params
        )
        tasks.append((tool, async_result, execution))
        
    # Wait for results (polling DB or AsyncResult)
    results = {}
    for tool, res, execution in tasks:
        # Simple polling for 60s
        start = time.time()
        status = "TIMEOUT"
        while time.time() - start < 120:
            execution.refresh_from_db()
            if execution.status in ["completed", "failed"]:
                status = execution.status
                break
            time.sleep(2)
        results[tool] = status
        print(f"[{idx}] {tool} finished with {status}")
        
    return results

def main():
    domains = ["example.com", "google.com", "microsoft.com"]
    start_total = time.time()
    
    print(f"Starting load test with {len(domains)} domains, 3 tools each...")
    
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(run_investigation_load, i, d): d for i, d in enumerate(domains)}
        
        for future in as_completed(futures):
            d = futures[future]
            try:
                res = future.result()
                print(f"Domain {d} results: {res}")
            except Exception as e:
                print(f"Domain {d} failed: {e}")
                
    print(f"Total time: {time.time() - start_total:.2f}s")

if __name__ == "__main__":
    main()
