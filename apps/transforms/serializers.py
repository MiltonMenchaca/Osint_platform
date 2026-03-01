import re

from rest_framework import serializers

from .models import Transform


class TransformListSerializer(serializers.ModelSerializer):
    """Serializer for Transform list view"""

    usage_count = serializers.IntegerField(read_only=True)
    last_used = serializers.DateTimeField(read_only=True)
    is_available = serializers.SerializerMethodField()
    availability_message = serializers.SerializerMethodField()

    class Meta:
        model = Transform
        fields = [
            "id",
            "name",
            "display_name",
            "description",
            "category",
            "tool_name",
            "input_type",
            "output_types",
            "is_enabled",
            "requires_api_key",
            "api_key_name",
            "timeout",
            "parameters",
            "is_available",
            "availability_message",
            "usage_count",
            "last_used",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_is_available(self, obj):
        is_available, _ = obj.check_availability()
        return bool(is_available)

    def get_availability_message(self, obj):
        _, message = obj.check_availability()
        return message


class TransformDetailSerializer(serializers.ModelSerializer):
    """Serializer for Transform detail view"""

    is_available = serializers.SerializerMethodField()
    availability_message = serializers.SerializerMethodField()

    class Meta:
        model = Transform
        fields = [
            "id",
            "name",
            "display_name",
            "description",
            "category",
            "tool_name",
            "command_template",
            "input_type",
            "output_types",
            "parameters",
            "is_enabled",
            "timeout",
            "requires_api_key",
            "api_key_name",
            "is_available",
            "availability_message",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_is_available(self, obj):
        is_available, _ = obj.check_availability()
        return bool(is_available)

    def get_availability_message(self, obj):
        _, message = obj.check_availability()
        return message


class TransformCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating transforms"""

    class Meta:
        model = Transform
        fields = [
            "name",
            "display_name",
            "description",
            "category",
            "tool_name",
            "command_template",
            "input_type",
            "output_types",
            "parameters",
            "timeout",
            "is_enabled",
            "requires_api_key",
            "api_key_name",
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
        valid_categories = {c[0] for c in Transform.CATEGORY_CHOICES}
        if value not in valid_categories:
            raise serializers.ValidationError(
                f"Invalid category. Must be one of: {', '.join(sorted(valid_categories))}"
            )

        return value

    def validate_tool_name(self, value):
        """Validate tool name"""
        value = (value or "").strip()
        if not value:
            raise serializers.ValidationError("Tool name cannot be empty")
        return value

    def validate_command_template(self, value):
        """Validate command template"""
        if not value.strip():
            raise serializers.ValidationError("Command template cannot be empty")

        # Check for required placeholders
        allowed_placeholders = ["{input}", "{input_value}", "{target}"]
        if not any(p in value for p in allowed_placeholders):
            raise serializers.ValidationError(
                f"Command template must contain one of: {', '.join(allowed_placeholders)}"
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

    def validate_input_type(self, value):
        valid_input_types = {c[0] for c in Transform.INPUT_TYPE_CHOICES}
        if value not in valid_input_types:
            raise serializers.ValidationError(
                f"Invalid input_type. Must be one of: {', '.join(sorted(valid_input_types))}"
            )
        return value

    def validate_output_types(self, value):
        if value is None:
            return []
        if not isinstance(value, list):
            raise serializers.ValidationError("output_types must be a list")
        valid_output_types = {c[0] for c in Transform.OUTPUT_TYPE_CHOICES}
        for item in value:
            if item not in valid_output_types:
                raise serializers.ValidationError(
                    f"Invalid output_type '{item}'. Must be one of: {', '.join(sorted(valid_output_types))}"
                )
        return value

    def validate_timeout(self, value):
        if value <= 0:
            raise serializers.ValidationError("Timeout must be a positive integer")
        if value > 3600:
            raise serializers.ValidationError("Timeout cannot exceed 3600 seconds (1 hour)")
        return value


class TransformUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating transforms"""

    class Meta:
        model = Transform
        fields = [
            "name",
            "display_name",
            "description",
            "category",
            "tool_name",
            "command_template",
            "is_enabled",
            "input_type",
            "output_types",
            "parameters",
            "timeout",
            "requires_api_key",
            "api_key_name",
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
    validate_tool_name = TransformCreateSerializer.validate_tool_name
    validate_command_template = TransformCreateSerializer.validate_command_template
    validate_input_type = TransformCreateSerializer.validate_input_type
    validate_output_types = TransformCreateSerializer.validate_output_types
    validate_timeout = TransformCreateSerializer.validate_timeout


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

    test_input = serializers.JSONField()
    execute = serializers.BooleanField(required=False, default=False)

    def validate_test_input(self, value):
        """Validate test input"""
        if isinstance(value, str):
            if not value.strip():
                raise serializers.ValidationError("Test input cannot be empty")
            return value.strip()

        if isinstance(value, dict):
            for key in ("target", "input", "input_value", "value"):
                if key in value and isinstance(value[key], str) and value[key].strip():
                    return value
            raise serializers.ValidationError(
                "Test input must contain one of: target, input, input_value, value"
            )

        raise serializers.ValidationError("Test input must be a string or a JSON object")


class TransformValidationSerializer(serializers.Serializer):
    """Serializer for transform validation"""

    validation_type = serializers.ChoiceField(
        choices=["basic", "full"], required=False, default="full"
    )


class BulkTransformActionSerializer(serializers.Serializer):
    """Serializer for bulk transform actions"""

    action = serializers.ChoiceField(
        choices=[
            "enable",
            "disable",
            "delete",
            "check_availability",
            "update_command_templates",
        ]
    )
    transform_ids = serializers.ListField(
        child=serializers.UUIDField(), min_length=1, max_length=50
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
            "display_name",
            "description",
            "category",
            "tool_name",
            "command_template",
            "input_type",
            "output_types",
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
