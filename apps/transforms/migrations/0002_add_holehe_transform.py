# Generated migration for adding Holehe transform

from django.db import migrations


def add_holehe_transform(apps, schema_editor):
    """Add Holehe transform to the database"""
    Transform = apps.get_model("transforms", "Transform")

    # Create Holehe transform
    Transform.objects.get_or_create(
        name="holehe_email_accounts",
        defaults={
            "display_name": "Holehe - Email Account Finder",
            "description": "Find accounts associated with an email address across multiple platforms using Holehe",
            "category": "social",
            "input_type": "email",
            "output_types": ["social_media", "person", "organization"],
            "tool_name": "holehe",
            "command_template": "holehe --output json --only-used {input}",
            "parameters": {"timeout": 180, "only_used": True, "output_format": "json"},
            "timeout": 180,
            "is_enabled": True,
            "requires_api_key": False,
            "api_key_name": "",
        },
    )


def remove_holehe_transform(apps, schema_editor):
    """Remove Holehe transform from the database"""
    Transform = apps.get_model("transforms", "Transform")

    try:
        transform = Transform.objects.get(name="holehe_email_accounts")
        transform.delete()
    except Transform.DoesNotExist:
        pass


class Migration(migrations.Migration):
    dependencies = [
        ("transforms", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(add_holehe_transform, remove_holehe_transform),
    ]
