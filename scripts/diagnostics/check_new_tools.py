
import os
import django
import sys
import time
from pathlib import Path

# Setup Django environment
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(BASE_DIR)
sys.path.append("/app")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "osint_platform.settings.production")
django.setup()

from apps.investigations.models import Investigation
from apps.entities.models import Entity
from apps.transforms.models import Transform
from apps.investigations.tasks import execute_transform
from apps.transforms.wrappers import get_wrapper
from celery.result import AsyncResult

def test_dnstwist():
    print("\n--- Testing DNSTwist ---")
    
    # Check if wrapper loads
    try:
        wrapper_class = get_wrapper("dnstwist")
        wrapper = wrapper_class()
        print(f"[OK] Wrapper loaded: {wrapper.get_tool_name()}")
    except Exception as e:
        print(f"[WARN] Could not load wrapper locally (normal for backend): {e}")
        # Continue execution test


    # Create investigation and entity
    from django.contrib.auth import get_user_model
    User = get_user_model()
    admin_user, _ = User.objects.get_or_create(username="admin")

    # Ensure Transform exists
    try:
        from apps.transforms.models import Transform
        Transform.objects.get_or_create(
            name="recon-ng",
            defaults={
                "description": "Recon-ng OSINT Framework",
                "tool_name": "recon-ng",
                "input_type": "domain",
                "timeout": 300,
                "is_enabled": True
            }
        )
    except Exception as e:
        print(f"[WARN] Could not create Transform 'recon-ng': {e}")

    investigation, _ = Investigation.objects.get_or_create(
        name="Tool Verification",
        defaults={"created_by": admin_user}
    )
    entity, _ = Entity.objects.get_or_create(
        investigation=investigation,
        entity_type="domain",
        value="example.com",
        defaults={"source": "test"}
    )
    print(f"[OK] Created/Retrieved entity: {entity}")

    # Trigger transform
    try:
        transform = Transform.objects.get(name="dnstwist")
        # We need a TransformExecution record
        from apps.investigations.models import TransformExecution
        execution = TransformExecution.objects.create(
            investigation=investigation,
            transform_name="dnstwist",
            input_entity=entity,
            status="pending"
        )
        
        task = execute_transform.delay(
            execution_id=str(execution.id),
            transform_name="dnstwist",
            input_value=entity.value,
            parameters={"format": "json"}
        )
        print(f"[OK] Task submitted. Task ID: {task.id}")
        
        # Wait for result
        for _ in range(30):  # Wait up to 30 seconds (dnstwist can be slow, but let's see if it starts)
            state = task.state
            print(f"Status: {state}", end="\r")
            if state in ["SUCCESS", "FAILURE", "REVOKED"]:
                break
            time.sleep(2)
        print()
        
        if task.state == "SUCCESS":
            result = task.result
            print("[OK] Execution completed successfully!")
            # print(f"Results: {result}") # Verbose
            if result.get("entities_created", 0) > 0:
                 print(f"[OK] Entities created: {result['entities_created']}")
            else:
                 print("[WARN] No entities created (this might be normal for example.com if cached or limited)")
        else:
            print(f"[FAIL] Task finished with state: {task.state}")
            if task.result:
                print(f"Error: {task.result}")

    except Exception as e:
        print(f"[FAIL] Error triggering dnstwist: {e}")

def test_exiftool():
    print("\n--- Testing ExifTool ---")
    try:
        from apps.transforms.wrappers.metadata import ExifToolWrapper
        from apps.transforms.models import Transform
        
        # Update Transform to accept 'any' input type (since file detection defaults to 'other')
        Transform.objects.filter(name="exiftool").update(input_type="any")
        
        wrapper = ExifToolWrapper()
        try:
            wrapper.check_availability()
        except Exception as e:
            print(f"[WARN] Could not load wrapper locally (normal for backend): {e}")

    except Exception as e:
        print(f"[WARN] Exiftool setup warning: {e}")

    # Create a dummy file entity
    dummy_file_path = "/app/test_image.jpg"
    with open(dummy_file_path, "wb") as f:
        f.write(b"\xFF\xD8\xFF\xE0\x00\x10\x4A\x46\x49\x46\x00\x01\x01\x01\x00\x48\x00\x48\x00\x00\xFF\xDB\x00\x43\x00\xFF\xFF") # Partial JPEG header
    
    print(f"[OK] Created dummy file: {dummy_file_path}")

    from django.contrib.auth import get_user_model
    User = get_user_model()
    admin_user, _ = User.objects.get_or_create(username="admin")

    investigation, _ = Investigation.objects.get_or_create(
        name="Tool Verification",
        defaults={"created_by": admin_user}
    )
    entity, _ = Entity.objects.get_or_create(
        investigation=investigation,
        entity_type="other",
        value=dummy_file_path,
        defaults={"source": "test"}
    )
    print(f"[OK] Created/Retrieved entity: {entity}")

    # Trigger transform
    try:
        transform = Transform.objects.get(name="exiftool")
        from apps.investigations.models import TransformExecution
        execution = TransformExecution.objects.create(
            investigation=investigation,
            transform_name="exiftool",
            input_entity=entity,
            status="pending"
        )

        task = execute_transform.delay(
            execution_id=str(execution.id),
            transform_name="exiftool",
            input_value=entity.value,
            parameters={}
        )
        print(f"[OK] Task submitted. Task ID: {task.id}")
        
        # Wait for result
        for _ in range(10):
            state = task.state
            print(f"Status: {state}", end="\r")
            if state in ["SUCCESS", "FAILURE", "REVOKED"]:
                break
            time.sleep(1)
        print()
        
        if task.state == "SUCCESS":
            print("[OK] Execution completed successfully!")
            # print(f"Results: {task.result}")
            # We expect 'other' entity with metadata
        else:
            print(f"[FAIL] Task finished with state: {task.state}")

    except Exception as e:
        print(f"[FAIL] Error triggering exiftool: {e}")

def test_crtsh():
    print("\n--- Testing Crt.sh ---")
    try:
        from apps.transforms.wrappers.web_enum import CrtShWrapper
        from apps.transforms.models import Transform
        
        # Create investigation and entity
        from django.contrib.auth import get_user_model
        User = get_user_model()
        admin_user, _ = User.objects.get_or_create(username="admin")

        investigation, _ = Investigation.objects.get_or_create(
            name="Tool Verification",
            defaults={"created_by": admin_user}
        )
        entity, _ = Entity.objects.get_or_create(
            investigation=investigation,
            entity_type="domain",
            value="scanme.nmap.org",
            defaults={"source": "test"}
        )

        # Trigger transform
        try:
            transform = Transform.objects.get(name="crtsh")
            from apps.investigations.models import TransformExecution
            execution = TransformExecution.objects.create(
                investigation=investigation,
                transform_name="crtsh",
                input_entity=entity,
                status="pending"
            )
            
            task = execute_transform.delay(
                execution_id=str(execution.id),
                transform_name="crtsh",
                input_value=entity.value,
                parameters={}
            )
            print(f"[OK] Task submitted. Task ID: {task.id}")
            
            # Wait for result
            for _ in range(60):
                state = task.state
                print(f"Status: {state}", end="\r")
                if state in ["SUCCESS", "FAILURE", "REVOKED"]:
                    break
                time.sleep(1)
            print()
            
            if task.state == "SUCCESS":
                result = task.result
                print("[OK] Execution completed successfully!")
                if result.get("entities_created", 0) > 0:
                     print(f"[OK] Entities created: {result['entities_created']}")
                else:
                     print("[WARN] No entities created (crt.sh might return nothing for example.com or API limit)")
            else:
                print(f"[FAIL] Task finished with state: {task.state}")

        except Exception as e:
            print(f"[FAIL] Error triggering crtsh: {e}")

    except Exception as e:
        print(f"[FAIL] Error setup crtsh: {e}")

def test_spiderfoot():
    print("\n--- Testing SpiderFoot ---")
    try:
        from apps.transforms.wrappers.web_enum import SpiderFootWrapper
        from apps.transforms.models import Transform
        
        # Ensure Transform exists
        # We might need to create it if it doesn't exist, but usually it should be in fixtures/initial data
        # If not, let's create a dummy one for test
        Transform.objects.get_or_create(
            name="spiderfoot",
            defaults={
                "description": "SpiderFoot OSINT",
                "tool_name": "spiderfoot",
                "input_type": "domain",
                "timeout": 300
            }
        )

        # Create investigation and entity
        from django.contrib.auth import get_user_model
        User = get_user_model()
        admin_user, _ = User.objects.get_or_create(username="admin")

        investigation, _ = Investigation.objects.get_or_create(
            name="Tool Verification",
            defaults={"created_by": admin_user}
        )
        entity, _ = Entity.objects.get_or_create(
            investigation=investigation,
            entity_type="domain",
            value="scanme.nmap.org",
            defaults={"source": "test"}
        )

        # Trigger transform
        try:
            from apps.investigations.models import TransformExecution
            execution = TransformExecution.objects.create(
                investigation=investigation,
                transform_name="spiderfoot",
                input_entity=entity,
                status="pending"
            )
            
            # Use specific module to be fast
            print("[INFO] Triggering SpiderFoot with module sfp_dnsresolve for speed...")
            task = execute_transform.delay(
                execution_id=str(execution.id),
                transform_name="spiderfoot",
                input_value=entity.value,
                parameters={"modules": "sfp_dnsresolve", "timeout": 300} 
            )
            print(f"[OK] Task submitted. Task ID: {task.id}")
            
            # Wait for result
            for _ in range(350): # Wait up to 350s
                state = task.state
                print(f"Status: {state}", end="\r")
                if state in ["SUCCESS", "FAILURE", "REVOKED"]:
                    break
                time.sleep(1)
            print()
            
            if task.state == "SUCCESS":
                print("[OK] Execution completed successfully!")
                # print(f"Results: {task.result}")
            else:
                print(f"[FAIL] Task finished with state: {task.state}")

        except Exception as e:
            print(f"[FAIL] Error triggering spiderfoot: {e}")

    except Exception as e:
        print(f"[FAIL] Error setting up spiderfoot test: {e}")

def test_recon_ng():
    print("\n--- Testing Recon-ng ---")
    
    # Check if wrapper loads
    try:
        wrapper_class = get_wrapper("recon-ng")
        wrapper = wrapper_class()
        print(f"[OK] Wrapper loaded: {wrapper.get_tool_name()}")
    except Exception as e:
        print(f"[WARN] Could not load wrapper locally: {e}")

    # Create investigation and entity
    from django.contrib.auth import get_user_model
    User = get_user_model()
    admin_user, _ = User.objects.get_or_create(username="admin")

    # Ensure Transform exists
    try:
        from apps.transforms.models import Transform
        Transform.objects.get_or_create(
            name="recon-ng",
            defaults={
                "description": "Recon-ng OSINT Framework",
                "tool_name": "recon-ng",
                "input_type": "domain",
                "timeout": 300,
                "is_enabled": True
            }
        )
    except Exception as e:
        print(f"[WARN] Could not create Transform 'recon-ng': {e}")

    investigation, _ = Investigation.objects.get_or_create(
        name="Tool Verification Recon-ng",
        defaults={"created_by": admin_user}
    )
    entity, _ = Entity.objects.get_or_create(
        investigation=investigation,
        entity_type="domain",
        value="scanme.nmap.org",
        defaults={"source": "test"}
    )
    print(f"[OK] Created/Retrieved entity: {entity}")

    # Trigger transform
    try:
        # Create execution record
        from apps.investigations.models import TransformExecution
        execution = TransformExecution.objects.create(
            investigation=investigation,
            transform_name="recon-ng",
            input_entity=entity,
            status="pending"
        )
        
        task = execute_transform.delay(
            execution_id=str(execution.id),
            transform_name="recon-ng",
            input_value=entity.value,
            parameters={}
        )
        print(f"[OK] Task submitted. Task ID: {task.id}")
        
        # Wait for result
        for _ in range(60):  # Wait up to 60 seconds (recon-ng is slower)
            state = task.state
            print(f"Status: {state}", end="\r")
            if state in ["SUCCESS", "FAILURE", "REVOKED"]:
                break
            time.sleep(2)
        print()
        
        if task.state == "SUCCESS":
            result = task.result
            print("[OK] Execution completed successfully!")
            if result.get("entities_created", 0) > 0:
                 print(f"[OK] Entities created: {result['entities_created']}")
                 print(f"Results preview: {result['data'][:2] if 'data' in result else 'No data'}")
            else:
                 print("[WARN] No entities created (check if modules found data)")
                 # Print raw output if available for debugging
                 if 'execution_info' in result and 'raw_output' in result['execution_info']:
                     print(f"Raw output: {result['execution_info']['raw_output'][:200]}...")
        else:
            print(f"[FAIL] Task finished with state: {task.state}")
            if task.result:
                print(f"Error: {task.result}")

    except Exception as e:
        print(f"[FAIL] Error triggering recon-ng: {e}")

def test_dirb():
    print("\n--- Testing Dirb ---")
    try:
        from apps.transforms.models import Transform
        Transform.objects.get_or_create(
            name="dirb",
            defaults={
                "description": "Dirb Web Content Scanner",
                "tool_name": "dirb",
                "input_type": "url",
                "timeout": 600,
                "is_enabled": True
            }
        )
        
        # Create investigation and entity
        from django.contrib.auth import get_user_model
        User = get_user_model()
        admin_user, _ = User.objects.get_or_create(username="admin")

        investigation, _ = Investigation.objects.get_or_create(
            name="Tool Verification Dirb",
            defaults={"created_by": admin_user}
        )
        entity, _ = Entity.objects.get_or_create(
            investigation=investigation,
            entity_type="url",
            value="http://scanme.nmap.org", # Use a safe target
            defaults={"source": "test"}
        )
        print(f"[OK] Created/Retrieved entity: {entity}")
        
        # Trigger transform
        from apps.investigations.models import TransformExecution
        execution = TransformExecution.objects.create(
            investigation=investigation,
            transform_name="dirb",
            input_entity=entity,
            status="pending"
        )
        
        task = execute_transform.delay(
            execution_id=str(execution.id),
            transform_name="dirb",
            input_value=entity.value,
            parameters={"timeout": 300} # Increased timeout for test
        )
        print(f"[OK] Task submitted. Task ID: {task.id}")
        
        # Wait for result
        for _ in range(150): # Wait longer
            state = task.state
            print(f"Status: {state}", end="\r")
            if state in ["SUCCESS", "FAILURE", "REVOKED"]:
                break
            time.sleep(2)
        print()
        
        if task.state == "SUCCESS":
            print("[OK] Execution completed successfully!")
            result = task.result
            if result.get("entities_created", 0) > 0:
                 print(f"[OK] Entities created: {result['entities_created']}")
        else:
            print(f"[FAIL] Task finished with state: {task.state}")

    except Exception as e:
        print(f"[FAIL] Error triggering dirb: {e}")

def test_nikto():
    print("\n--- Testing Nikto ---")
    try:
        from apps.transforms.models import Transform
        Transform.objects.get_or_create(
            name="nikto",
            defaults={
                "description": "Nikto Web Vulnerability Scanner",
                "tool_name": "nikto",
                "input_type": "url",
                "timeout": 1200,
                "is_enabled": True
            }
        )
        
        # Create investigation and entity
        from django.contrib.auth import get_user_model
        User = get_user_model()
        admin_user, _ = User.objects.get_or_create(username="admin")

        investigation, _ = Investigation.objects.get_or_create(
            name="Tool Verification Nikto",
            defaults={"created_by": admin_user}
        )
        entity, _ = Entity.objects.get_or_create(
            investigation=investigation,
            entity_type="url",
            value="http://scanme.nmap.org",
            defaults={"source": "test"}
        )
        print(f"[OK] Created/Retrieved entity: {entity}")
        
        # Trigger transform
        from apps.investigations.models import TransformExecution
        execution = TransformExecution.objects.create(
            investigation=investigation,
            transform_name="nikto",
            input_entity=entity,
            status="pending"
        )
        
        task = execute_transform.delay(
            execution_id=str(execution.id),
            transform_name="nikto",
            input_value=entity.value,
            parameters={"timeout": 600} # Increased timeout
        )
        print(f"[OK] Task submitted. Task ID: {task.id}")
        
        # Wait for result
        for _ in range(300): # Wait longer
            state = task.state
            print(f"Status: {state}", end="\r")
            if state in ["SUCCESS", "FAILURE", "REVOKED"]:
                break
            time.sleep(2)
        print()
        
        if task.state == "SUCCESS":
            print("[OK] Execution completed successfully!")
            result = task.result
            if result.get("entities_created", 0) > 0:
                 print(f"[OK] Entities created: {result['entities_created']}")
        else:
            print(f"[FAIL] Task finished with state: {task.state}")

    except Exception as e:
        print(f"[FAIL] Error triggering nikto: {e}")

def test_whatweb():
    print("\n--- Testing WhatWeb ---")
    try:
        from apps.transforms.models import Transform
        Transform.objects.get_or_create(
            name="whatweb",
            defaults={
                "description": "WhatWeb Tech Identifier",
                "tool_name": "whatweb",
                "input_type": "url",
                "timeout": 120,
                "is_enabled": True
            }
        )
        
        # Create investigation and entity
        from django.contrib.auth import get_user_model
        User = get_user_model()
        admin_user, _ = User.objects.get_or_create(username="admin")

        investigation, _ = Investigation.objects.get_or_create(
            name="Tool Verification WhatWeb",
            defaults={"created_by": admin_user}
        )
        entity, _ = Entity.objects.get_or_create(
            investigation=investigation,
            entity_type="url",
            value="http://scanme.nmap.org",
            defaults={"source": "test"}
        )
        print(f"[OK] Created/Retrieved entity: {entity}")
        
        # Trigger transform
        from apps.investigations.models import TransformExecution
        execution = TransformExecution.objects.create(
            investigation=investigation,
            transform_name="whatweb",
            input_entity=entity,
            status="pending"
        )
        
        task = execute_transform.delay(
            execution_id=str(execution.id),
            transform_name="whatweb",
            input_value=entity.value,
            parameters={}
        )
        print(f"[OK] Task submitted. Task ID: {task.id}")
        
        # Wait for result
        for _ in range(30):
            state = task.state
            print(f"Status: {state}", end="\r")
            if state in ["SUCCESS", "FAILURE", "REVOKED"]:
                break
            time.sleep(1)
        print()
        
        if task.state == "SUCCESS":
            print("[OK] Execution completed successfully!")
            result = task.result
            if result.get("entities_created", 0) > 0:
                 print(f"[OK] Entities created: {result['entities_created']}")
        else:
            print(f"[FAIL] Task finished with state: {task.state}")

    except Exception as e:
        print(f"[FAIL] Error triggering whatweb: {e}")

if __name__ == "__main__":
    # Already verified / Fast tests
    test_dnstwist()
    test_exiftool()
    test_crtsh()
    test_whatweb()
    
    # Target tests for this iteration
    test_spiderfoot() 
    test_recon_ng()
    
    # Slow tests (Verified previously, skipping for speed)
    # test_dirb()
    # test_nikto()
