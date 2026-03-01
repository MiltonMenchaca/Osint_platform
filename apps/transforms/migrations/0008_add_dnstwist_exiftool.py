from django.db import migrations


def add_new_tools(apps, schema_editor):
    Transform = apps.get_model("transforms", "Transform")

    transforms = [
        {
            "name": "dnstwist",
            "display_name": "DNSTwist - Domain Permutation",
            "description": "Generate domain permutations for typo-squatting detection",
            "category": "dns",
            "input_type": "domain",
            "output_types": ["domain", "other"],
            "tool_name": "dnstwist",
            "command_template": "dnstwist {input}",
            "parameters": {"format": "json"},
            "timeout": 300,
            "is_enabled": True,
            "requires_api_key": False,
            "api_key_name": "",
        },
        {
            "name": "exiftool",
            "display_name": "ExifTool - Metadata Analysis",
            "description": "Extract metadata from files and images",
            "category": "file",
            "input_type": "file",
            "output_types": ["other"],
            "tool_name": "exiftool",
            "command_template": "exiftool {input}",
            "parameters": {},
            "timeout": 60,
            "is_enabled": True,
            "requires_api_key": False,
            "api_key_name": "",
        },
    ]

    for t in transforms:
        name = t.pop("name")
        Transform.objects.get_or_create(name=name, defaults=t)


def remove_new_tools(apps, schema_editor):
    Transform = apps.get_model("transforms", "Transform")
    Transform.objects.filter(name__in=["dnstwist", "exiftool"]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("transforms", "0007_add_core_cli_transforms"),
    ]

    operations = [
        migrations.RunPython(add_new_tools, remove_new_tools),
    ]
