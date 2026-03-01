from django.db import migrations


def add_orchestrator_transforms(apps, schema_editor):
    Transform = apps.get_model("transforms", "Transform")

    transforms = [
        {
            "name": "crtsh",
            "display_name": "crt.sh - Certificate Transparency",
            "description": "Query crt.sh and extract subdomains from certificate logs",
            "category": "dns",
            "input_type": "domain",
            "output_types": ["domain", "other"],
            "tool_name": "crtsh",
            "command_template": "api:crt.sh {input}",
            "parameters": {"timeout": 20, "limit": 200},
            "timeout": 60,
            "is_enabled": True,
            "requires_api_key": False,
            "api_key_name": "",
        },
        {
            "name": "recon_ng",
            "display_name": "Recon-ng - Modular Recon (Lite)",
            "description": "Run a lightweight recon module (hackertarget hostsearch supported)",
            "category": "search",
            "input_type": "any",
            "output_types": ["domain", "ip", "url", "other"],
            "tool_name": "recon-ng",
            "command_template": "api:recon-ng {input}",
            "parameters": {"timeout": 30, "module": "hackertarget"},
            "timeout": 120,
            "is_enabled": True,
            "requires_api_key": False,
            "api_key_name": "",
        },
        {
            "name": "spiderfoot",
            "display_name": "SpiderFoot - Automated OSINT (Orchestrator)",
            "description": "Run a curated set of OSINT transforms against a target",
            "category": "other",
            "input_type": "any",
            "output_types": ["domain", "ip", "url", "email", "other"],
            "tool_name": "spiderfoot",
            "command_template": "orchestrator:spiderfoot {input}",
            "parameters": {"modules": "passive", "timeout": 300},
            "timeout": 600,
            "is_enabled": True,
            "requires_api_key": False,
            "api_key_name": "",
        },
        {
            "name": "maltego",
            "display_name": "Maltego - Link Analysis (Orchestrator)",
            "description": "Run a transform set and merge results as Maltego-like expansion",
            "category": "other",
            "input_type": "any",
            "output_types": ["domain", "ip", "url", "email", "other"],
            "tool_name": "maltego",
            "command_template": "orchestrator:maltego {input}",
            "parameters": {"transform_set": "standard", "timeout": 600},
            "timeout": 900,
            "is_enabled": True,
            "requires_api_key": False,
            "api_key_name": "",
        },
    ]

    for t in transforms:
        name = t.pop("name")
        Transform.objects.get_or_create(name=name, defaults=t)


def remove_orchestrator_transforms(apps, schema_editor):
    Transform = apps.get_model("transforms", "Transform")
    Transform.objects.filter(name__in=["crtsh", "recon_ng", "spiderfoot", "maltego"]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("transforms", "0005_add_threat_intel_transforms"),
    ]

    operations = [
        migrations.RunPython(add_orchestrator_transforms, remove_orchestrator_transforms),
    ]
