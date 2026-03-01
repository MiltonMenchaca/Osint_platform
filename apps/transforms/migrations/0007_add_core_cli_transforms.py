from django.db import migrations


def add_core_cli_transforms(apps, schema_editor):
    Transform = apps.get_model("transforms", "Transform")

    transforms = [
        {
            "name": "assetfinder",
            "display_name": "Assetfinder - Subdomain Enumeration",
            "description": "Find subdomains for a domain using assetfinder",
            "category": "dns",
            "input_type": "domain",
            "output_types": ["domain"],
            "tool_name": "assetfinder",
            "command_template": "assetfinder --subs-only {input}",
            "parameters": {"timeout": 120, "subs_only": True},
            "timeout": 120,
            "is_enabled": True,
            "requires_api_key": False,
            "api_key_name": "",
        },
        {
            "name": "amass",
            "display_name": "Amass - Subdomain Enumeration",
            "description": "Enumerate subdomains and related data using OWASP Amass",
            "category": "dns",
            "input_type": "domain",
            "output_types": ["domain", "ip", "other"],
            "tool_name": "amass",
            "command_template": "amass enum -d {input} -nocolor",
            "parameters": {"timeout": 600, "mode": "enum", "passive": False},
            "timeout": 600,
            "is_enabled": True,
            "requires_api_key": False,
            "api_key_name": "",
        },
        {
            "name": "nmap",
            "display_name": "Nmap - Network Scan",
            "description": "Scan open ports and services using nmap",
            "category": "network",
            "input_type": "ip",
            "output_types": ["ip", "other"],
            "tool_name": "nmap",
            "command_template": "nmap -sV -O {input}",
            "parameters": {"timeout": 300},
            "timeout": 300,
            "is_enabled": True,
            "requires_api_key": False,
            "api_key_name": "",
        },
        {
            "name": "shodan",
            "display_name": "Shodan - Host Intelligence",
            "description": "Query Shodan for host intelligence (requires SHODAN_API_KEY for most features)",
            "category": "threat_intel",
            "input_type": "any",
            "output_types": ["ip", "other"],
            "tool_name": "shodan",
            "command_template": "shodan host {input}",
            "parameters": {"timeout": 180, "search_type": "host", "limit": 100},
            "timeout": 180,
            "is_enabled": True,
            "requires_api_key": False,
            "api_key_name": "",
        },
    ]

    for t in transforms:
        name = t.pop("name")
        Transform.objects.get_or_create(name=name, defaults=t)


def remove_core_cli_transforms(apps, schema_editor):
    Transform = apps.get_model("transforms", "Transform")
    Transform.objects.filter(name__in=["assetfinder", "amass", "nmap", "shodan"]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("transforms", "0006_add_orchestrator_transforms"),
    ]

    operations = [
        migrations.RunPython(add_core_cli_transforms, remove_core_cli_transforms),
    ]

