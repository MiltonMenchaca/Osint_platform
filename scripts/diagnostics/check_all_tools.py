import os
import sys
import django
from typing import Dict, Any, List
import time
import shutil

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(BASE_DIR)
os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    os.environ.get("DJANGO_SETTINGS_MODULE", "osint_platform.settings.development"),
)
django.setup()

from apps.transforms.wrappers import get_wrapper, ToolNotFoundError
from apps.transforms.wrappers.base import BaseWrapper

# Define test cases for each tool
TOOLS_TO_TEST = [
    {"name": "amass", "input": {"type": "domain", "value": "example.com"}, "args": {"passive": True, "timeout": 15}},
    {"name": "assetfinder", "input": {"type": "domain", "value": "example.com"}, "args": {"timeout": 15}},
    {"name": "dmitry", "input": {"type": "domain", "value": "example.com"}, "args": {"timeout": 15}},
    {"name": "holehe", "input": {"type": "email", "value": "test@gmail.com"}, "args": {"timeout": 15}},
    {"name": "ping", "input": {"type": "domain", "value": "example.com"}, "args": {"count": 1}},
    {"name": "traceroute", "input": {"type": "domain", "value": "example.com"}, "args": {"timeout": 10}},
    {"name": "nmap", "input": {"type": "domain", "value": "scanme.nmap.org"}, "args": {"arguments": "-sn"}},
    {"name": "nuclei", "input": {"type": "url", "value": "http://example.com"}, "args": {"timeout": 300, "templates": ["/root/nuclei-templates/http/technologies/tech-detect.yaml"]}},
    {"name": "sherlock", "input": {"type": "username", "value": "blue"}, "args": {"timeout": 60}},
    {"name": "subfinder", "input": {"type": "domain", "value": "example.com"}, "args": {"timeout": 300, "threads": 5}},
    {"name": "theharvester", "input": {"type": "domain", "value": "example.com"}, "args": {"limit": 10, "source": "bing"}},
    {"name": "wappalyzer", "input": {"type": "url", "value": "https://example.com"}, "args": {}},
    {"name": "whatweb", "input": {"type": "url", "value": "https://example.com"}, "args": {}},
    {"name": "gobuster", "input": {"type": "url", "value": "https://example.com"}, "args": {"wordlist": "/usr/share/dirb/wordlists/common.txt"}},
    {"name": "dirb", "input": {"type": "url", "value": "https://example.com"}, "args": {"timeout": 300}},
    {"name": "nikto", "input": {"type": "url", "value": "https://example.com"}, "args": {"timeout": 30}},
    {"name": "shodan", "input": {"type": "ip", "value": "8.8.8.8"}, "args": {}},
    {"name": "virustotal", "input": {"type": "domain", "value": "example.com"}, "args": {}},
    {"name": "dnstwist", "input": {"type": "domain", "value": "example.com"}, "args": {"timeout": 30}},
    {"name": "exiftool", "input": {"type": "url", "value": "https://example.com/image.jpg"}, "args": {}},
    {"name": "crtsh", "input": {"type": "domain", "value": "example.com"}, "args": {}},
]

def check_binary(tool_name: str) -> str:
    path = shutil.which(tool_name)
    return "YES" if path else "NO"

def run_tests():
    output_file = os.path.join(BASE_DIR, "docs", "reports", "tools_check.txt")
    with open(output_file, "w") as f:
        header = f"{'TOOL':<20} | {'INSTALLED':<10} | {'EXECUTION':<10} | {'NOTES':<40}"
        print(f"\n{header}")
        print("-" * 90)
        f.write(header + "\n")
        f.write("-" * 90 + "\n")

        results = []

        for tool_conf in TOOLS_TO_TEST:
            name = tool_conf["name"]
            installed = "NO"
            execution = "PENDING"
            notes = ""
            
            try:
                # 1. Check if wrapper exists in registry
                try:
                    wrapper_cls = get_wrapper(name)
                except ValueError:
                    notes = "Wrapper not registered in __init__.py"
                    results.append((name, "MISSING", "N/A", notes))
                    line = f"{name:<20} | MISSING    | N/A        | {notes:<40}"
                    print(line)
                    f.write(line + "\n")
                    continue

                # 2. Try to instantiate (checks for binary)
                try:
                    wrapper = wrapper_cls()
                    installed = "YES"
                except ToolNotFoundError:
                    # Get the tool name it was looking for
                    # We instantiate a dummy to call get_tool_name if possible, but we can't if __init__ fails
                    # So we assume it failed on binary check.
                    # Let's inspect the class to see what tool name it expects
                    try:
                        expected_binary = wrapper_cls.get_tool_name(wrapper_cls) # Hacky call to instance method
                    except:
                        expected_binary = "unknown"
                    
                    installed = "NO"
                    notes = f"Binary '{expected_binary}' not found in PATH"
                    results.append((name, installed, "FAIL", notes))
                    line = f"{name:<20} | {installed:<10} | {'FAIL':<10} | {notes:<40}"
                    print(line)
                    f.write(line + "\n")
                    continue
                except Exception as e:
                    installed = "ERR"
                    notes = f"Init failed: {str(e)}"
                    results.append((name, installed, "FAIL", notes))
                    line = f"{name:<20} | {installed:<10} | {'FAIL':<10} | {notes:<40}"
                    print(line)
                    f.write(line + "\n")
                    continue

                # 3. Try execution
                try:
                    # print(f"Testing {name}...", end="\r")
                    start_time = time.time()
                    result = wrapper.execute(tool_conf["input"], **tool_conf["args"])
                    duration = time.time() - start_time
                    
                    execution = "OK"
                    # Check for execution error (soft failure)
                    exec_info = result.get("execution_info", {})
                    if exec_info.get("error"):
                        execution = "FAIL"
                        notes = f"Error: {exec_info['error']}"
                    else:
                        # Check for entities
                        entities = result.get("entities", [])
                        if entities:
                            notes = f"Found {len(entities)} entities ({duration:.1f}s)"
                        else:
                            notes = f"No entities found ({duration:.1f}s)"
                            
                        # Special checks for some tools
                        if name == "crtsh":
                            if result.get("data"):
                                 notes = f"Found {len(result['data'])} records ({duration:.1f}s)"

                except Exception as e:
                    execution = "FAIL"
                    err_msg = str(e)
                    if "timeout" in err_msg.lower():
                        notes = "Timed out"
                    else:
                        notes = err_msg[:40]

                results.append((name, installed, execution, notes))
                line = f"{name:<20} | {installed:<10} | {execution:<10} | {notes:<40}"
                print(line)
                f.write(line + "\n")
                f.flush()

            except Exception as e:
                results.append((name, "ERR", "ERR", str(e)))
                line = f"{name:<20} | {'ERR':<10} | {'ERR':<10} | {str(e):<40}"
                print(line)
                f.write(line + "\n")


if __name__ == "__main__":
    run_tests()
