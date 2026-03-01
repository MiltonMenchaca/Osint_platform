import os
import django
import sys
from pathlib import Path

# Add project root to sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
sys.path.append("/app")

# Setup Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "osint_platform.settings.development")
django.setup()

from apps.transforms.models import Transform
from apps.transforms.wrappers import WRAPPER_REGISTRY

def register_transforms():
    print("Registering transforms...")
    
    transforms_data = [
        {
            "name": "spiderfoot",
            "display_name": "SpiderFoot",
            "description": "Automated OSINT collection",
            "category": "other",
            "input_type": "any",
            "output_types": ["mixed"],
            "tool_name": "spiderfoot",
            "command_template": "sf.py -s {target}",
            "timeout": 1200
        },
        {
            "name": "recon-ng",
            "display_name": "Recon-ng",
            "description": "Web Reconnaissance framework",
            "category": "web",
            "input_type": "domain",
            "output_types": ["mixed"],
            "tool_name": "recon-ng",
            "command_template": "recon-ng -r {resource}",
            "timeout": 600
        },
        {
            "name": "ping",
            "display_name": "Ping",
            "description": "Send ICMP ECHO_REQUEST to network hosts",
            "category": "network",
            "input_type": "domain",
            "output_types": ["ip"],
            "tool_name": "ping",
            "command_template": "ping -c 4 {target}",
            "timeout": 30
        },
        {
            "name": "dnstwist",
            "display_name": "DNSTwist",
            "description": "Domain name permutation engine",
            "category": "dns",
            "input_type": "domain",
            "output_types": ["domain"],
            "tool_name": "dnstwist",
            "command_template": "dnstwist {target}",
            "timeout": 300
        },
        {
            "name": "crtsh",
            "display_name": "crt.sh",
            "description": "Certificate Transparency search",
            "category": "dns",
            "input_type": "domain",
            "output_types": ["domain"],
            "tool_name": "crtsh",
            "command_template": "crt.sh query",
            "timeout": 60
        },
        {
            "name": "exiftool",
            "display_name": "ExifTool",
            "description": "Read, Write and Edit Meta Information",
            "category": "file_analysis",
            "input_type": "file",
            "output_types": ["other"],
            "tool_name": "exiftool",
            "command_template": "exiftool {target}",
            "timeout": 60
        },
        {
            "name": "wappalyzer",
            "display_name": "Wappalyzer",
            "description": "Identify technologies on websites",
            "category": "web",
            "input_type": "url",
            "output_types": ["technology"],
            "tool_name": "wappalyzer",
            "command_template": "wappalyzer {target}",
            "timeout": 120
        },
        {
            "name": "urlscan",
            "display_name": "UrlScan.io",
            "description": "Website scanner for suspicious URLs",
            "category": "web",
            "input_type": "url",
            "output_types": ["url", "ip"],
            "tool_name": "urlscan",
            "command_template": "api call",
            "timeout": 300
        },
        {
            "name": "whatweb",
            "display_name": "WhatWeb",
            "description": "Next generation web scanner",
            "category": "web",
            "input_type": "url",
            "output_types": ["other"],
            "tool_name": "whatweb",
            "command_template": "whatweb {target}",
            "timeout": 300
        },
        {
            "name": "dirb",
            "display_name": "Dirb",
            "description": "Web Content Scanner",
            "category": "web",
            "input_type": "url",
            "output_types": ["url"],
            "tool_name": "dirb",
            "command_template": "dirb {target}",
            "timeout": 600
        },
        {
            "name": "nikto",
            "display_name": "Nikto",
            "description": "Web Server Scanner",
            "category": "web",
            "input_type": "url",
            "output_types": ["other"],
            "tool_name": "nikto",
            "command_template": "nikto -h {target}",
            "timeout": 900
        },
        {
            "name": "holehe",
            "display_name": "Holehe",
            "description": "Email to Social Media Account OSINT",
            "category": "social",
            "input_type": "email",
            "output_types": ["account"],
            "tool_name": "holehe",
            "command_template": "holehe {target} --only-used --no-password-recovery",
            "timeout": 300
        },
        {
            "name": "sherlock",
            "display_name": "Sherlock",
            "description": "Find usernames across social networks",
            "category": "social",
            "input_type": "username",
            "output_types": ["account"],
            "tool_name": "sherlock",
            "command_template": "sherlock {target} --print-found",
            "timeout": 300
        },
        {
            "name": "subfinder",
            "display_name": "Subfinder",
            "description": "Subdomain discovery tool",
            "category": "dns",
            "input_type": "domain",
            "output_types": ["domain"],
            "tool_name": "subfinder",
            "command_template": "subfinder -d {target} -silent",
            "timeout": 300
        },
        {
            "name": "assetfinder",
            "display_name": "Assetfinder",
            "description": "Find domains and subdomains",
            "category": "dns",
            "input_type": "domain",
            "output_types": ["domain"],
            "tool_name": "assetfinder",
            "command_template": "assetfinder --subs-only {target}",
            "timeout": 300
        },
        {
            "name": "waybackurls",
            "display_name": "WaybackUrls",
            "description": "Fetch known URLs from Wayback Machine",
            "category": "web",
            "input_type": "domain",
            "output_types": ["url"],
            "tool_name": "waybackurls",
            "command_template": "echo {target} | waybackurls",
            "timeout": 600
        },
        {
            "name": "httpx",
            "display_name": "HTTPX",
            "description": "Fast and multi-purpose HTTP toolkit",
            "category": "web",
            "input_type": "domain",
            "output_types": ["url", "ip"],
            "tool_name": "httpx",
            "command_template": "httpx -l {target} -silent -json",
            "timeout": 300
        },
        {
            "name": "nmap",
            "display_name": "Nmap",
            "description": "Network Mapper",
            "category": "network",
            "input_type": "ip",
            "output_types": ["port", "service", "os"],
            "tool_name": "nmap",
            "command_template": "nmap -T4 -F {target}",
            "timeout": 600
        },
        {
            "name": "nuclei",
            "display_name": "Nuclei",
            "description": "Vulnerability Scanner",
            "category": "vulnerability",
            "input_type": "url",
            "output_types": ["vulnerability"],
            "tool_name": "nuclei",
            "command_template": "nuclei -u {target} -json",
            "timeout": 1200
        },
        {
            "name": "dmitry",
            "display_name": "Dmitry",
            "description": "Deepmagic Information Gathering Tool",
            "category": "passive",
            "input_type": "domain",
            "output_types": ["subdomain", "email", "port"],
            "tool_name": "dmitry",
            "command_template": "dmitry -winse {target}",
            "timeout": 300
        },
        {
            "name": "amass",
            "display_name": "Amass",
            "description": "In-depth Attack Surface Mapping and Asset Discovery",
            "category": "dns",
            "input_type": "domain",
            "output_types": ["subdomain", "ip"],
            "tool_name": "amass",
            "command_template": "amass enum -d {target} -json",
            "timeout": 1800
        },
        {
            "name": "theharvester",
            "display_name": "TheHarvester",
            "description": "E-mail, subdomain and people names harvester",
            "category": "passive",
            "input_type": "domain",
            "output_types": ["email", "subdomain"],
            "tool_name": "theharvester",
            "command_template": "theHarvester -d {target} -b all",
            "timeout": 600
        },
    ]

    for data in transforms_data:
        transform, created = Transform.objects.update_or_create(
            name=data["name"],
            defaults=data
        )
        if created:
            print(f"Created transform: {transform.name}")
        else:
            print(f"Updated transform: {transform.name}")

if __name__ == "__main__":
    register_transforms()
