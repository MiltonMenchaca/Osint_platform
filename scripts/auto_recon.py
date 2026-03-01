import os
import sys
import django
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Setup Django environment
if __name__ == "__main__":
    # Add project root to path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    sys.path.append(project_root)
    
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "osint_platform.settings.development")
    django.setup()

from apps.investigations.services import AutoReconService

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python auto_recon.py <target_url>")
        sys.exit(1)
    
    target_arg = sys.argv[1]
    
    print(f"[*] Initializing Auto Recon for: {target_arg}")
    service = AutoReconService()
    results = service.run_scan(target_arg)
    
    print(json.dumps(results, indent=2, default=str))
