from django.db import migrations


def add_recon_transforms(apps, schema_editor):
    Transform = apps.get_model("transforms", "Transform")

    Transform.objects.get_or_create(
        name="subfinder",
        defaults={
            "display_name": "Subfinder - Passive Subdomain Enumeration",
            "description": "Discover subdomains for a domain using ProjectDiscovery Subfinder",
            "category": "dns",
            "input_type": "domain",
            "output_types": ["domain"],
            "tool_name": "subfinder",
            "command_template": "subfinder -d {input} -silent",
            "parameters": {"silent": True, "timeout": 120},
            "timeout": 120,
            "is_enabled": True,
            "requires_api_key": False,
            "api_key_name": "",
        },
    )

    Transform.objects.get_or_create(
        name="theharvester",
        defaults={
            "display_name": "theHarvester - Emails & Hosts Discovery",
            "description": "Collect emails, hosts and IPs from public sources using theHarvester",
            "category": "search",
            "input_type": "domain",
            "output_types": ["email", "domain", "ip"],
            "tool_name": "theHarvester",
            "command_template": "theHarvester -d {input} -b all -l 500",
            "parameters": {"source": "all", "limit": 500, "timeout": 180},
            "timeout": 180,
            "is_enabled": True,
            "requires_api_key": False,
            "api_key_name": "",
        },
    )

    Transform.objects.get_or_create(
        name="sherlock",
        defaults={
            "display_name": "Sherlock - Username Enumeration",
            "description": "Find usernames across social networks and websites using Sherlock",
            "category": "social",
            "input_type": "social_media",
            "output_types": ["social_media", "url"],
            "tool_name": "sherlock",
            "command_template": "sherlock --print-found --no-color {input}",
            "parameters": {"timeout": 90},
            "timeout": 300,
            "is_enabled": True,
            "requires_api_key": False,
            "api_key_name": "",
        },
    )


def remove_recon_transforms(apps, schema_editor):
    Transform = apps.get_model("transforms", "Transform")
    Transform.objects.filter(name__in=["subfinder", "theharvester", "sherlock"]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("transforms", "0002_add_holehe_transform"),
    ]

    operations = [
        migrations.RunPython(add_recon_transforms, remove_recon_transforms),
    ]
