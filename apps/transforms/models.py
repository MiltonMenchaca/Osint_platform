import uuid

from django.core.validators import MinLengthValidator
from django.db import models


class Transform(models.Model):
    """
    Model representing a transform that can be executed on entities
    """

    CATEGORY_CHOICES = [
        ("dns", "DNS"),
        ("network", "Network"),
        ("web", "Web"),
        ("social", "Social Media"),
        ("search", "Search Engine"),
        ("threat_intel", "Threat Intelligence"),
        ("geolocation", "Geolocation"),
        ("cryptocurrency", "Cryptocurrency"),
        ("file_analysis", "File Analysis"),
        ("other", "Other"),
    ]

    INPUT_TYPE_CHOICES = [
        ("domain", "Domain"),
        ("ip", "IP Address"),
        ("email", "Email Address"),
        ("person", "Person"),
        ("organization", "Organization"),
        ("phone", "Phone Number"),
        ("url", "URL"),
        ("hash", "Hash"),
        ("file", "File"),
        ("cryptocurrency", "Cryptocurrency Address"),
        ("social_media", "Social Media Account"),
        ("geolocation", "Geolocation"),
        ("any", "Any Type"),
    ]

    OUTPUT_TYPE_CHOICES = [
        ("domain", "Domain"),
        ("ip", "IP Address"),
        ("email", "Email Address"),
        ("person", "Person"),
        ("organization", "Organization"),
        ("phone", "Phone Number"),
        ("url", "URL"),
        ("hash", "Hash"),
        ("file", "File"),
        ("cryptocurrency", "Cryptocurrency Address"),
        ("social_media", "Social Media Account"),
        ("geolocation", "Geolocation"),
        ("mixed", "Mixed Types"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(
        max_length=100,
        unique=True,
        validators=[MinLengthValidator(3)],
        help_text="Unique name of the transform",
    )
    display_name = models.CharField(
        max_length=255, help_text="Human-readable display name"
    )
    description = models.TextField(help_text="Description of what the transform does")
    category = models.CharField(
        max_length=50, choices=CATEGORY_CHOICES, help_text="Category of the transform"
    )
    input_type = models.CharField(
        max_length=50,
        choices=INPUT_TYPE_CHOICES,
        help_text="Type of entity this transform accepts as input",
    )
    output_types = models.JSONField(
        default=list, help_text="List of entity types this transform can output"
    )
    tool_name = models.CharField(
        max_length=100, help_text="Name of the underlying OSINT tool"
    )
    command_template = models.TextField(
        help_text="Command template for executing the tool"
    )
    parameters = models.JSONField(
        default=dict, blank=True, help_text="Default parameters for the transform"
    )
    timeout = models.IntegerField(
        default=300, help_text="Timeout in seconds for transform execution"
    )
    is_enabled = models.BooleanField(
        default=True, help_text="Whether this transform is enabled"
    )
    requires_api_key = models.BooleanField(
        default=False, help_text="Whether this transform requires an API key"
    )
    api_key_name = models.CharField(
        max_length=100,
        blank=True,
        help_text="Name of the environment variable for API key",
    )
    created_at = models.DateTimeField(
        auto_now_add=True, help_text="Timestamp when transform was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True, help_text="Timestamp when transform was last updated"
    )

    class Meta:
        db_table = "transforms"
        ordering = ["category", "name"]
        indexes = [
            models.Index(fields=["category"]),
            models.Index(fields=["input_type"]),
            models.Index(fields=["is_enabled"]),
            models.Index(fields=["tool_name"]),
        ]

    def __str__(self):
        return f"{self.display_name} ({self.name})"

    def can_process_entity_type(self, entity_type):
        """Check if this transform can process the given entity type"""
        return self.input_type == "any" or self.input_type == entity_type

    def get_expected_output_types(self):
        """Get list of expected output entity types"""
        return self.output_types if self.output_types else []

    def is_available(self):
        """Check if transform is available for execution"""
        if not self.is_enabled:
            return False

        if self.requires_api_key and self.api_key_name:
            import os

            required_keys = [
                key.strip() for key in self.api_key_name.split(",") if key.strip()
            ]
            return all(os.environ.get(key) for key in required_keys)

        return True

    def check_availability(self):
        import shutil

        if not self.is_enabled:
            return False, "Transform is disabled"

        if self.requires_api_key and self.api_key_name:
            import os

            required_keys = [
                key.strip() for key in self.api_key_name.split(",") if key.strip()
            ]
            missing = [key for key in required_keys if not os.environ.get(key)]
            if missing:
                return (
                    False,
                    f"Missing API key environment variable(s): {', '.join(missing)}",
                )

        if self.tool_name and self.tool_name not in {"custom"}:
            wrapper_exists = False
            try:
                from apps.transforms.wrappers import get_wrapper

                get_wrapper(self.tool_name)
                wrapper_exists = True
            except Exception:
                wrapper_exists = False

            if not wrapper_exists and shutil.which(self.tool_name) is None:
                return False, f"Tool '{self.tool_name}' not found in PATH"

        return True, "Available"

    def get_command(self, input_value, **kwargs):
        """Generate command for execution with given input"""
        # Replace placeholders in command template
        command = self.command_template
        command = command.replace("{{input}}", str(input_value))
        command = command.replace("{input}", str(input_value))
        command = command.replace("{input_value}", str(input_value))
        command = command.replace("{target}", str(input_value))

        # Replace parameter placeholders
        for key, value in kwargs.items():
            command = command.replace(f"{{{key}}}", str(value))

        # Replace default parameters
        for key, value in self.parameters.items():
            if f"{{{key}}}" in command:
                command = command.replace(f"{{{key}}}", str(value))

        return command

    def validate_input(self, entity):
        """Validate if the entity can be processed by this transform"""
        if not self.is_available():
            return False, "Transform is not available"

        if not self.can_process_entity_type(entity.entity_type):
            return False, f"Transform cannot process {entity.entity_type} entities"

        return True, "Valid input"
