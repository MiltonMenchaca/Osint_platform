
import sys
import os
import django
from typing import Dict, Any

# Add app to path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(BASE_DIR)
sys.path.append("/app")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "osint_platform.settings.production")
django.setup()

from apps.transforms.wrappers.web_enum import CrtShWrapper

try:
    print("Initializing CrtShWrapper...")
    wrapper = CrtShWrapper()
    print(f"Wrapper initialized: {wrapper}")
    
    input_data = {"type": "domain", "value": "example.com"}
    print(f"Executing with input: {input_data}")
    
    result = wrapper.execute(input_data)
    print("Execution result:")
    print(result)
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
