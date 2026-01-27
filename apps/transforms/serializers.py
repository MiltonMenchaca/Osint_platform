import re

from rest_framework import serializers

from .models import Transform


class TransformListSerializer(serializers.ModelSerializer):
    """Serializer for Transform list view"""

    usage_count = serializers.IntegerField(read_only=True)
    last_used = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Transform
        fields = [
            "id",
            "name",
            "description",
            "category",
            "tool_name",
            "is_enabled",
            "usage_count",
            "last_used",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class TransformDetailSerializer(serializers.ModelSerializer):
    """Serializer for Transform detail view"""

    command_template = serializers.CharField()
    input_schema = serializers.JSONField()
    output_schema = serializers.JSONField()
    configuration = serializers.JSONField(required=False)

    class Meta:
        model = Transform
        fields = [
            "id",
            "name",
            "description",
            "category",
            "tool_name",
            "command_template",
            "input_schema",
            "output_schema",
            "configuration",
            "is_enabled",
            "timeout_seconds",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class TransformCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating transforms"""

    class Meta:
        model = Transform
        fields = [
            "name",
            "description",
            "category",
            "tool_name",
            "command_template",
            "input_schema",
            "output_schema",
            "configuration",
            "timeout_seconds",
        ]

    def validate_name(self, value):
        """Validate transform name"""
        if len(value.strip()) < 3:
            raise serializers.ValidationError(
                "Transform name must be at least 3 characters long"
            )

        # Check for duplicate names
        if Transform.objects.filter(name=value).exists():
            raise serializers.ValidationError(
                "A transform with this name already exists"
            )

        return value.strip()

    def validate_category(self, value):
        """Validate transform category"""
        valid_categories = [
            "reconnaissance",
            "enumeration",
            "vulnerability_scanning",
            "network_analysis",
            "dns_analysis",
            "web_analysis",
            "email_analysis",
            "social_media",
            "threat_intelligence",
            "forensics",
            "malware_analysis",
            "data_collection",
        ]

        if value not in valid_categories:
            raise serializers.ValidationError(
                f"Invalid category. Must be one of: {', '.join(valid_categories)}"
            )

        return value

    def validate_tool_name(self, value):
        """Validate tool name"""
        valid_tools = [
            "assetfinder",
            "amass",
            "nmap",
            "shodan",
            "subfinder",
            "httpx",
            "nuclei",
            "gobuster",
            "ffuf",
            "masscan",
            "whatweb",
            "wafw00f",
            "nikto",
            "dirb",
            "dirsearch",
            "sqlmap",
            "xsstrike",
            "commix",
            "custom",
        ]

        if value not in valid_tools:
            raise serializers.ValidationError(
                f"Invalid tool name. Must be one of: {', '.join(valid_tools)}"
            )

        return value

    def validate_command_template(self, value):
        """Validate command template"""
        if not value.strip():
            raise serializers.ValidationError("Command template cannot be empty")

        # Check for required placeholders
        required_placeholders = ["{target}"]
        for placeholder in required_placeholders:
            if placeholder not in value:
                raise serializers.ValidationError(
                    f"Command template must contain '{placeholder}' placeholder"
                )

        # Validate placeholder format
        placeholder_pattern = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")
        placeholder_pattern.findall(value)

        # Check for invalid characters in command
        dangerous_patterns = [
            r";\s*rm\s+",
            r";\s*del\s+",
            r"&&\s*rm\s+",
            r"&&\s*del\s+",
            r"\|\s*rm\s+",
            r"\|\s*del\s+",
            r"`rm\s+",
            r"`del\s+",
            r"\$\(rm\s+",
            r"\$\(del\s+",
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                raise serializers.ValidationError(
                    "Command template contains potentially dangerous operations"
                )

        return value.strip()

    def validate_input_schema(self, value):
        """Validate input schema"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Input schema must be a JSON object")

        # Validate JSON Schema structure
        required_fields = ["type", "properties"]
        for field in required_fields:
            if field not in value:
                raise serializers.ValidationError(
                    f"Input schema must contain '{field}' field"
                )

        if value["type"] != "object":
            raise serializers.ValidationError("Input schema type must be 'object'")

        if not isinstance(value["properties"], dict):
            raise serializers.ValidationError(
                "Input schema properties must be an object"
            )

        # Ensure 'target' property exists
        if "target" not in value["properties"]:
            raise serializers.ValidationError(
                "Input schema must contain 'target' property"
            )

        return value

    def validate_output_schema(self, value):
        """Validate output schema"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Output schema must be a JSON object")

        # Validate JSON Schema structure
        required_fields = ["type"]
        for field in required_fields:
            if field not in value:
                raise serializers.ValidationError(
                    f"Output schema must contain '{field}' field"
                )

        return value

    def validate_configuration(self, value):
        """Validate configuration"""
        if value is None:
            return {}

        if not isinstance(value, dict):
            raise serializers.ValidationError("Configuration must be a JSON object")

        # Validate specific configuration fields
        allowed_keys = [
            "max_retries",
            "retry_delay",
            "rate_limit",
            "concurrent_limit",
            "output_format",
            "custom_flags",
            "environment_vars",
            "working_dir",
        ]

        for key in value.keys():
            if key not in allowed_keys:
                raise serializers.ValidationError(
                    f"Invalid configuration key '{key}'. Allowed keys: {', '.join(allowed_keys)}"
                )

        # Validate specific values
        if "max_retries" in value:
            if not isinstance(value["max_retries"], int) or value["max_retries"] < 0:
                raise serializers.ValidationError(
                    "max_retries must be a non-negative integer"
                )

        if "retry_delay" in value:
            if (
                not isinstance(value["retry_delay"], (int, float))
                or value["retry_delay"] < 0
            ):
                raise serializers.ValidationError(
                    "retry_delay must be a non-negative number"
                )

        if "rate_limit" in value:
            if not isinstance(value["rate_limit"], int) or value["rate_limit"] <= 0:
                raise serializers.ValidationError(
                    "rate_limit must be a positive integer"
                )

        return value

    def validate_timeout_seconds(self, value):
        """Validate timeout"""
        if value <= 0:
            raise serializers.ValidationError("Timeout must be a positive integer")

        if value > 3600:  # 1 hour max
            raise serializers.ValidationError(
                "Timeout cannot exceed 3600 seconds (1 hour)"
            )

        return value


class TransformUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating transforms"""

    class Meta:
        model = Transform
        fields = [
            "name",
            "description",
            "category",
            "command_template",
            "input_schema",
            "output_schema",
            "configuration",
            "is_enabled",
            "timeout_seconds",
        ]

    def validate_name(self, value):
        """Validate transform name for updates"""
        if len(value.strip()) < 3:
            raise serializers.ValidationError(
                "Transform name must be at least 3 characters long"
            )

        # Check for duplicate names (excluding current instance)
        instance = getattr(self, "instance", None)
        if instance:
            if Transform.objects.filter(name=value).exclude(id=instance.id).exists():
                raise serializers.ValidationError(
                    "A transform with this name already exists"
                )

        return value.strip()

    # Reuse validation methods from create serializer
    validate_category = TransformCreateSerializer.validate_category
    validate_command_template = TransformCreateSerializer.validate_command_template
    validate_input_schema = TransformCreateSerializer.validate_input_schema
    validate_output_schema = TransformCreateSerializer.validate_output_schema
    validate_configuration = TransformCreateSerializer.validate_configuration
    validate_timeout_seconds = TransformCreateSerializer.validate_timeout_seconds


class TransformSerializer(serializers.ModelSerializer):
    """Basic Transform serializer for nested use"""

    class Meta:
        model = Transform
        fields = ["id", "name", "description", "category", "tool_name", "is_enabled"]
        read_only_fields = ["id"]


class TransformStatsSerializer(serializers.Serializer):
    """Serializer for transform statistics"""

    total_transforms = serializers.IntegerField()
    enabled_transforms = serializers.IntegerField()
    transforms_by_category = serializers.DictField()
    transforms_by_tool = serializers.DictField()
    most_used_transforms = TransformListSerializer(many=True)
    recent_executions = serializers.IntegerField()

    class Meta:
        fields = [
            "total_transforms",
            "enabled_transforms",
            "transforms_by_category",
            "transforms_by_tool",
            "most_used_transforms",
            "recent_executions",
        ]


class TransformTestSerializer(serializers.Serializer):
    """Serializer for testing transforms"""

    transform_id = serializers.IntegerField()
    test_input = serializers.JSONField()

    def validate_transform_id(self, value):
        """Validate transform exists"""
        try:
            transform = Transform.objects.get(id=value)
            if not transform.is_enabled:
                raise serializers.ValidationError("Transform is not enabled")
            return value
        except Transform.DoesNotExist:
            raise serializers.ValidationError("Transform not found")

    def validate_test_input(self, value):
        """Validate test input"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Test input must be a JSON object")

        # Basic validation - specific validation will be done by the transform
        if "target" not in value:
            raise serializers.ValidationError("Test input must contain 'target' field")

        return value


class TransformValidationSerializer(serializers.Serializer):
    """Serializer for transform validation"""

    command_template = serializers.CharField()
    input_schema = serializers.JSONField()
    test_input = serializers.JSONField()

    def validate_command_template(self, value):
        """Validate command template"""
        return TransformCreateSerializer().validate_command_template(value)

    def validate_input_schema(self, value):
        """Validate input schema"""
        return TransformCreateSerializer().validate_input_schema(value)

    def validate_test_input(self, value):
        """Validate test input against schema"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Test input must be a JSON object")

        return value

    def validate(self, attrs):
        """Cross-field validation"""
        # Validate test input against input schema
        input_schema = attrs["input_schema"]
        test_input = attrs["test_input"]

        # Check required properties
        required_props = input_schema.get("required", [])
        for prop in required_props:
            if prop not in test_input:
                raise serializers.ValidationError(
                    f"Test input missing required property: {prop}"
                )

        # Validate property types
        properties = input_schema.get("properties", {})
        for prop, value in test_input.items():
            if prop in properties:
                prop_schema = properties[prop]
                expected_type = prop_schema.get("type")

                if expected_type == "string" and not isinstance(value, str):
                    raise serializers.ValidationError(
                        f"Property '{prop}' must be a string"
                    )
                elif expected_type == "integer" and not isinstance(value, int):
                    raise serializers.ValidationError(
                        f"Property '{prop}' must be an integer"
                    )
                elif expected_type == "number" and not isinstance(value, (int, float)):
                    raise serializers.ValidationError(
                        f"Property '{prop}' must be a number"
                    )
                elif expected_type == "boolean" and not isinstance(value, bool):
                    raise serializers.ValidationError(
                        f"Property '{prop}' must be a boolean"
                    )
                elif expected_type == "array" and not isinstance(value, list):
                    raise serializers.ValidationError(
                        f"Property '{prop}' must be an array"
                    )

        return attrs


class BulkTransformActionSerializer(serializers.Serializer):
    """Serializer for bulk transform actions"""

    action = serializers.ChoiceField(choices=["enable", "disable", "delete", "test"])
    transform_ids = serializers.ListField(
        child=serializers.IntegerField(), min_length=1, max_length=50
    )

    def validate_transform_ids(self, value):
        """Validate transforms exist"""
        transforms = Transform.objects.filter(id__in=value)
        if len(transforms) != len(value):
            raise serializers.ValidationError("One or more transforms not found")
        return value


class TransformImportSerializer(serializers.Serializer):
    """Serializer for importing transforms"""

    transforms = serializers.ListField(
        child=serializers.DictField(), min_length=1, max_length=100
    )
    overwrite_existing = serializers.BooleanField(default=False)

    def validate_transforms(self, value):
        """Validate transform data for import"""
        required_fields = [
            "name",
            "category",
            "tool_name",
            "command_template",
            "input_schema",
        ]

        for i, transform_data in enumerate(value):
            for field in required_fields:
                if field not in transform_data:
                    raise serializers.ValidationError(
                        f"Transform {i+1}: Missing required field '{field}'"
                    )

            # Validate individual fields using existing validators
            try:
                # Create a temporary serializer instance for validation
                temp_serializer = TransformCreateSerializer(data=transform_data)
                if not temp_serializer.is_valid():
                    raise serializers.ValidationError(
                        f"Transform {i+1}: {temp_serializer.errors}"
                    )
            except Exception as e:
                raise serializers.ValidationError(
                    f"Transform {i+1}: Validation error - {str(e)}"
                )

        return value
