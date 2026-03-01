from django.db import migrations


def add_threat_intel_transforms(apps, schema_editor):
    Transform = apps.get_model("transforms", "Transform")

    transforms = [
        {
            "name": "virustotal",
            "display_name": "VirusTotal - Reputation & Relationships",
            "description": "Query VirusTotal v3 API for domains, IPs and URLs",
            "category": "threat_intel",
            "input_type": "any",
            "output_types": ["domain", "ip", "url", "other"],
            "tool_name": "virustotal",
            "command_template": "api:virustotal {input}",
            "parameters": {"timeout": 30, "include_resolutions": True, "resolutions_limit": 20},
            "timeout": 60,
            "is_enabled": True,
            "requires_api_key": True,
            "api_key_name": "VIRUSTOTAL_API_KEY",
        },
        {
            "name": "securitytrails",
            "display_name": "SecurityTrails - Domain Intelligence",
            "description": "Query SecurityTrails API for domain data and subdomains",
            "category": "threat_intel",
            "input_type": "domain",
            "output_types": ["domain", "ip", "other"],
            "tool_name": "securitytrails",
            "command_template": "api:securitytrails {input}",
            "parameters": {"timeout": 30, "include_subdomains": True, "subdomains_limit": 200},
            "timeout": 60,
            "is_enabled": True,
            "requires_api_key": True,
            "api_key_name": "SECURITYTRAILS_API_KEY",
        },
        {
            "name": "censys",
            "display_name": "Censys - Host Intelligence",
            "description": "Query Censys Search API for host details by IP",
            "category": "threat_intel",
            "input_type": "ip",
            "output_types": ["ip", "domain", "url", "other"],
            "tool_name": "censys",
            "command_template": "api:censys {input}",
            "parameters": {"timeout": 30},
            "timeout": 60,
            "is_enabled": True,
            "requires_api_key": True,
            "api_key_name": "CENSYS_API_ID,CENSYS_API_SECRET",
        },
        {
            "name": "hibp",
            "display_name": "HIBP - Breach Check",
            "description": "Query HaveIBeenPwned API for breached accounts",
            "category": "threat_intel",
            "input_type": "email",
            "output_types": ["email", "other"],
            "tool_name": "hibp",
            "command_template": "api:hibp {input}",
            "parameters": {"timeout": 30, "truncate": True},
            "timeout": 60,
            "is_enabled": True,
            "requires_api_key": True,
            "api_key_name": "HIBP_API_KEY",
        },
        {
            "name": "dehashed",
            "display_name": "DeHashed - Breach Search",
            "description": "Query DeHashed API for leaked credentials related to an email or domain",
            "category": "threat_intel",
            "input_type": "any",
            "output_types": ["email", "domain", "other"],
            "tool_name": "dehashed",
            "command_template": "api:dehashed {input}",
            "parameters": {"timeout": 30, "size": 50, "page": 1},
            "timeout": 60,
            "is_enabled": True,
            "requires_api_key": True,
            "api_key_name": "DEHASHED_EMAIL,DEHASHED_API_KEY",
        },
    ]

    for t in transforms:
        name = t.pop("name")
        Transform.objects.get_or_create(name=name, defaults=t)


def remove_threat_intel_transforms(apps, schema_editor):
    Transform = apps.get_model("transforms", "Transform")
    Transform.objects.filter(
        name__in=["virustotal", "securitytrails", "censys", "hibp", "dehashed"]
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("transforms", "0004_add_additional_transforms"),
    ]

    operations = [
        migrations.RunPython(add_threat_intel_transforms, remove_threat_intel_transforms),
    ]
