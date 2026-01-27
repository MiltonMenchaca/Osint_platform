from django.contrib.auth.models import User
from rest_framework import serializers

from apps.entities.serializers import EntitySerializer, RelationshipSerializer
from apps.transforms.models import Transform

from .models import Investigation, TransformExecution


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model"""

    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "date_joined"]
        read_only_fields = ["id", "date_joined"]


class InvestigationListSerializer(serializers.ModelSerializer):
    """Serializer for Investigation list view"""

    created_by = UserSerializer(read_only=True)
    entities_count = serializers.IntegerField(read_only=True)
    relationships_count = serializers.IntegerField(read_only=True)
    executions_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Investigation
        fields = [
            "id",
            "name",
            "description",
            "status",
            "created_by",
            "created_at",
            "updated_at",
            "entities_count",
            "relationships_count",
            "executions_count",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class InvestigationDetailSerializer(serializers.ModelSerializer):
    """Serializer for Investigation detail view"""

    created_by = UserSerializer(read_only=True)
    entities = EntitySerializer(many=True, read_only=True)
    relationships = RelationshipSerializer(many=True, read_only=True)
    executions = serializers.SerializerMethodField()
    metadata = serializers.JSONField(required=False)

    class Meta:
        model = Investigation
        fields = [
            "id",
            "name",
            "description",
            "status",
            "created_by",
            "created_at",
            "updated_at",
            "metadata",
            "entities",
            "relationships",
            "executions",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_executions(self, obj):
        """Get recent executions for the investigation"""
        executions = obj.executions.select_related("transform", "created_by").order_by(
            "-created_at"
        )[:10]
        return TransformExecutionListSerializer(executions, many=True).data

    def validate_status(self, value):
        """Validate investigation status"""
        valid_statuses = ["active", "completed", "paused", "archived"]
        if value not in valid_statuses:
            raise serializers.ValidationError(
                f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
            )
        return value

    def validate_metadata(self, value):
        """Validate metadata structure"""
        if value is None:
            return {}

        if not isinstance(value, dict):
            raise serializers.ValidationError("Metadata must be a JSON object")

        # Validate specific metadata fields if needed
        allowed_keys = ["tags", "priority", "source", "notes", "custom_fields"]
        for key in value.keys():
            if key not in allowed_keys:
                raise serializers.ValidationError(
                    f"Invalid metadata key '{key}'. Allowed keys: {', '.join(allowed_keys)}"
                )

        return value


class InvestigationCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating investigations"""

    class Meta:
        model = Investigation
        fields = ["name", "description", "metadata"]

    def validate_name(self, value):
        """Validate investigation name"""
        if len(value.strip()) < 3:
            raise serializers.ValidationError(
                "Investigation name must be at least 3 characters long"
            )

        # Check for duplicate names for the same user
        user = self.context["request"].user
        if Investigation.objects.filter(name=value, created_by=user).exists():
            raise serializers.ValidationError(
                "You already have an investigation with this name"
            )

        return value.strip()

    def create(self, validated_data):
        """Create investigation with current user as creator"""
        validated_data["created_by"] = self.context["request"].user
        return super().create(validated_data)


class TransformExecutionListSerializer(serializers.ModelSerializer):
    """Serializer for TransformExecution list view"""

    transform = serializers.StringRelatedField()
    created_by = UserSerializer(read_only=True)
    investigation_name = serializers.CharField(
        source="investigation.name", read_only=True
    )

    class Meta:
        model = TransformExecution
        fields = [
            "id",
            "transform",
            "status",
            "created_by",
            "investigation_name",
            "created_at",
            "started_at",
            "completed_at",
            "celery_task_id",
        ]
        read_only_fields = ["id", "created_at", "started_at", "completed_at"]


class TransformExecutionDetailSerializer(serializers.ModelSerializer):
    """Serializer for TransformExecution detail view"""

    transform = serializers.StringRelatedField()
    created_by = UserSerializer(read_only=True)
    investigation = InvestigationListSerializer(read_only=True)
    input_data = serializers.JSONField()
    output_data = serializers.JSONField(read_only=True)
    error_message = serializers.CharField(read_only=True)

    class Meta:
        model = TransformExecution
        fields = [
            "id",
            "investigation",
            "transform",
            "status",
            "created_by",
            "input_data",
            "output_data",
            "error_message",
            "created_at",
            "started_at",
            "completed_at",
            "celery_task_id",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "started_at",
            "completed_at",
            "output_data",
            "error_message",
            "celery_task_id",
        ]


class TransformExecutionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating transform executions"""

    transform_id = serializers.IntegerField(write_only=True)
    investigation_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = TransformExecution
        fields = ["transform_id", "investigation_id", "input_data"]

    def validate_transform_id(self, value):
        """Validate transform exists and is enabled"""
        try:
            transform = Transform.objects.get(id=value)
            if not transform.is_enabled:
                raise serializers.ValidationError("Transform is not enabled")
            return value
        except Transform.DoesNotExist:
            raise serializers.ValidationError("Transform not found")

    def validate_investigation_id(self, value):
        """Validate investigation exists and user has access"""
        user = self.context["request"].user
        try:
            investigation = Investigation.objects.get(id=value, created_by=user)
            if investigation.status == "archived":
                raise serializers.ValidationError(
                    "Cannot execute transforms on archived investigations"
                )
            return value
        except Investigation.DoesNotExist:
            raise serializers.ValidationError(
                "Investigation not found or you don't have access"
            )

    def validate_input_data(self, value):
        """Validate input data structure"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Input data must be a JSON object")

        # Basic validation - specific validation will be done by the transform
        required_fields = ["target"]
        for field in required_fields:
            if field not in value:
                raise serializers.ValidationError(f"Missing required field: {field}")

        return value

    def create(self, validated_data):
        """Create transform execution"""
        transform_id = validated_data.pop("transform_id")
        investigation_id = validated_data.pop("investigation_id")

        validated_data["transform"] = Transform.objects.get(id=transform_id)
        validated_data["investigation"] = Investigation.objects.get(id=investigation_id)
        validated_data["created_by"] = self.context["request"].user

        return super().create(validated_data)


class InvestigationStatsSerializer(serializers.Serializer):
    """Serializer for investigation statistics"""

    total_investigations = serializers.IntegerField()
    active_investigations = serializers.IntegerField()
    completed_investigations = serializers.IntegerField()
    total_entities = serializers.IntegerField()
    total_relationships = serializers.IntegerField()
    total_executions = serializers.IntegerField()
    recent_executions = TransformExecutionListSerializer(many=True)

    class Meta:
        fields = [
            "total_investigations",
            "active_investigations",
            "completed_investigations",
            "total_entities",
            "total_relationships",
            "total_executions",
            "recent_executions",
        ]


class BulkExecutionSerializer(serializers.Serializer):
    """Serializer for bulk transform execution"""

    investigation_id = serializers.IntegerField()
    transform_ids = serializers.ListField(
        child=serializers.IntegerField(), min_length=1, max_length=10
    )
    input_data = serializers.JSONField()

    def validate_investigation_id(self, value):
        """Validate investigation exists and user has access"""
        user = self.context["request"].user
        try:
            investigation = Investigation.objects.get(id=value, created_by=user)
            if investigation.status == "archived":
                raise serializers.ValidationError(
                    "Cannot execute transforms on archived investigations"
                )
            return value
        except Investigation.DoesNotExist:
            raise serializers.ValidationError(
                "Investigation not found or you don't have access"
            )

    def validate_transform_ids(self, value):
        """Validate all transforms exist and are enabled"""
        transforms = Transform.objects.filter(id__in=value, is_enabled=True)
        if len(transforms) != len(value):
            raise serializers.ValidationError(
                "One or more transforms not found or not enabled"
            )
        return value

    def validate_input_data(self, value):
        """Validate input data structure"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Input data must be a JSON object")

        required_fields = ["target"]
        for field in required_fields:
            if field not in value:
                raise serializers.ValidationError(f"Missing required field: {field}")

        return value


class ExecutionControlSerializer(serializers.Serializer):
    """Serializer for execution control actions"""

    action = serializers.ChoiceField(choices=["cancel", "retry", "pause", "resume"])
    execution_ids = serializers.ListField(
        child=serializers.IntegerField(), min_length=1, max_length=50
    )

    def validate_execution_ids(self, value):
        """Validate executions exist and user has access"""
        user = self.context["request"].user
        executions = TransformExecution.objects.filter(
            id__in=value, investigation__created_by=user
        )

        if len(executions) != len(value):
            raise serializers.ValidationError(
                "One or more executions not found or you don't have access"
            )

        return value
