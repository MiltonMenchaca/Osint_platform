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
    priority = serializers.SerializerMethodField()
    target = serializers.SerializerMethodField()
    jurisdiction = serializers.SerializerMethodField()
    estimated_loss = serializers.SerializerMethodField()
    victim_count = serializers.SerializerMethodField()
    case_number = serializers.SerializerMethodField()

    class Meta:
        model = Investigation
        fields = [
            "id",
            "name",
            "description",
            "status",
            "priority",
            "target",
            "jurisdiction",
            "estimated_loss",
            "victim_count",
            "case_number",
            "created_by",
            "created_at",
            "updated_at",
            "entities_count",
            "relationships_count",
            "executions_count",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_priority(self, obj):
        return (obj.metadata or {}).get("priority")

    def get_target(self, obj):
        return (obj.metadata or {}).get("target")

    def get_jurisdiction(self, obj):
        return (obj.metadata or {}).get("jurisdiction")

    def get_estimated_loss(self, obj):
        return (obj.metadata or {}).get("estimated_loss")

    def get_victim_count(self, obj):
        return (obj.metadata or {}).get("victim_count")

    def get_case_number(self, obj):
        return (obj.metadata or {}).get("case_number")


class InvestigationDetailSerializer(serializers.ModelSerializer):
    """Serializer for Investigation detail view"""

    created_by = UserSerializer(read_only=True)
    entities = EntitySerializer(many=True, read_only=True)
    relationships = RelationshipSerializer(many=True, read_only=True)
    executions = serializers.SerializerMethodField()
    metadata = serializers.JSONField(required=False)
    priority = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    target = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    jurisdiction = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    estimated_loss = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    victim_count = serializers.IntegerField(required=False, allow_null=True)
    case_number = serializers.CharField(required=False, allow_blank=True, allow_null=True)

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
            "priority",
            "target",
            "jurisdiction",
            "estimated_loss",
            "victim_count",
            "case_number",
            "metadata",
            "entities",
            "relationships",
            "executions",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_executions(self, obj):
        """Get recent executions for the investigation"""
        executions = obj.transform_executions.select_related("input_entity").order_by("-created_at")[:10]
        return TransformExecutionListSerializer(executions, many=True).data

    def validate_status(self, value):
        """Validate investigation status"""
        valid_statuses = ["active", "completed", "paused", "archived"]
        if value not in valid_statuses:
            raise serializers.ValidationError(f"Invalid status. Must be one of: {', '.join(valid_statuses)}")
        return value

    def validate_metadata(self, value):
        """Validate metadata structure"""
        if value is None:
            return {}

        if not isinstance(value, dict):
            raise serializers.ValidationError("Metadata must be a JSON object")

        # Validate specific metadata fields if needed
        allowed_keys = [
            "tags",
            "priority",
            "target",
            "jurisdiction",
            "estimated_loss",
            "victim_count",
            "case_number",
            "source",
            "notes",
            "custom_fields",
            "auto_recon",
            "auto_recon_updated_at",
        ]
        for key in value.keys():
            if key not in allowed_keys:
                raise serializers.ValidationError(
                    f"Invalid metadata key '{key}'. Allowed keys: {', '.join(allowed_keys)}"
                )

        return value

    def to_representation(self, instance):
        data = super().to_representation(instance)
        metadata = instance.metadata or {}
        data.setdefault("priority", metadata.get("priority"))
        data.setdefault("target", metadata.get("target"))
        data.setdefault("jurisdiction", metadata.get("jurisdiction"))
        data.setdefault("estimated_loss", metadata.get("estimated_loss"))
        data.setdefault("victim_count", metadata.get("victim_count"))
        data.setdefault("case_number", metadata.get("case_number"))
        return data

    def update(self, instance, validated_data):
        metadata = validated_data.get("metadata") or instance.metadata or {}
        for key in [
            "priority",
            "target",
            "jurisdiction",
            "estimated_loss",
            "victim_count",
            "case_number",
        ]:
            if key in validated_data:
                value = validated_data.get(key)
                if value in ("", None):
                    metadata.pop(key, None)
                else:
                    metadata[key] = value
        validated_data["metadata"] = metadata
        return super().update(instance, validated_data)


class InvestigationCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating investigations"""

    priority = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    target = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    jurisdiction = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    estimated_loss = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    victim_count = serializers.IntegerField(required=False, allow_null=True)
    case_number = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = Investigation
        fields = [
            "id",
            "name",
            "description",
            "metadata",
            "priority",
            "target",
            "jurisdiction",
            "estimated_loss",
            "victim_count",
            "case_number",
        ]

    def validate_name(self, value):
        """Validate investigation name"""
        if len(value.strip()) < 3:
            raise serializers.ValidationError("Investigation name must be at least 3 characters long")

        # Check for duplicate names for the same user
        user = self.context["request"].user
        if Investigation.objects.filter(name=value, created_by=user).exists():
            raise serializers.ValidationError("You already have an investigation with this name")

        return value.strip()

    def create(self, validated_data):
        """Create investigation with current user as creator"""
        metadata = validated_data.get("metadata") or {}
        for key in [
            "priority",
            "target",
            "jurisdiction",
            "estimated_loss",
            "victim_count",
            "case_number",
        ]:
            value = validated_data.pop(key, None)
            if value not in ("", None):
                metadata[key] = value
        validated_data["metadata"] = metadata
        validated_data["created_by"] = self.context["request"].user
        return super().create(validated_data)


class TransformExecutionListSerializer(serializers.ModelSerializer):
    """Serializer for TransformExecution list view"""

    investigation_id = serializers.UUIDField(source="investigation.id", read_only=True)
    input_entity = serializers.SerializerMethodField()

    class Meta:
        model = TransformExecution
        fields = [
            "id",
            "investigation_id",
            "transform_name",
            "input_entity",
            "status",
            "created_at",
            "started_at",
            "completed_at",
            "celery_task_id",
        ]
        read_only_fields = ["id", "created_at", "started_at", "completed_at"]

    def get_input_entity(self, obj):
        entity = getattr(obj, "input_entity", None)
        if not entity:
            return None
        return {"id": str(entity.id), "type": entity.entity_type, "value": entity.value}


class TransformExecutionDetailSerializer(serializers.ModelSerializer):
    """Serializer for TransformExecution detail view"""

    investigation_id = serializers.UUIDField(source="investigation.id", read_only=True)
    input_entity = serializers.SerializerMethodField()

    class Meta:
        model = TransformExecution
        fields = [
            "id",
            "investigation_id",
            "transform_name",
            "status",
            "error_message",
            "parameters",
            "results",
            "input_entity",
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
            "error_message",
            "celery_task_id",
        ]

    def get_input_entity(self, obj):
        entity = getattr(obj, "input_entity", None)
        if not entity:
            return None
        return {"id": str(entity.id), "type": entity.entity_type, "value": entity.value}


class TransformExecutionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating transform executions"""

    input_entity = serializers.SerializerMethodField(read_only=True)
    input_entity_id = serializers.UUIDField(write_only=True, required=False)
    input = serializers.DictField(write_only=True, required=False)
    parameters = serializers.JSONField(required=False)

    class Meta:
        model = TransformExecution
        fields = [
            "id",
            "transform_name",
            "status",
            "input_entity",
            "input_entity_id",
            "input",
            "parameters",
            "results",
            "error_message",
            "created_at",
            "started_at",
            "completed_at",
            "celery_task_id",
        ]
        read_only_fields = [
            "id",
            "status",
            "input_entity",
            "results",
            "error_message",
            "created_at",
            "started_at",
            "completed_at",
            "celery_task_id",
        ]

    def validate_transform_name(self, value):
        transform_name = value.strip()
        if not transform_name:
            raise serializers.ValidationError("transform_name is required")
        if not Transform.objects.filter(name=transform_name, is_enabled=True).exists():
            raise serializers.ValidationError("Transform not found or disabled")
        return transform_name

    def validate(self, attrs):
        from apps.entities.models import Entity

        view = self.context.get("view")
        request = self.context.get("request")
        if not view or not request:
            raise serializers.ValidationError("Invalid request context")

        investigation_id = view.kwargs.get("investigation_id")
        investigation = Investigation.objects.filter(id=investigation_id, created_by=request.user).first()
        if not investigation:
            raise serializers.ValidationError("Investigation not found")

        if investigation.status == "archived":
            raise serializers.ValidationError("Cannot execute transforms on archived investigations")

        input_entity = None
        input_entity_id = attrs.pop("input_entity_id", None)
        input_payload = attrs.pop("input", None)

        if input_entity_id:
            input_entity = Entity.objects.filter(id=input_entity_id, investigation=investigation).first()
            if not input_entity:
                raise serializers.ValidationError("Input entity not found")
        elif input_payload:
            entity_type = input_payload.get("entity_type")
            value = input_payload.get("value")
            if not entity_type or not value:
                raise serializers.ValidationError("input must include entity_type and value")
            input_entity, _ = Entity.objects.get_or_create(
                investigation=investigation,
                entity_type=entity_type,
                value=value,
                defaults={"source": "execution", "confidence_score": 1.0},
            )
        else:
            raise serializers.ValidationError("input_entity_id or input is required")

        attrs["investigation"] = investigation
        attrs["input_entity"] = input_entity
        attrs["parameters"] = attrs.get("parameters") or {}

        return attrs

    def get_input_entity(self, obj):
        entity = getattr(obj, "input_entity", None)
        if not entity:
            return None
        return {"id": str(entity.id), "type": entity.entity_type, "value": entity.value}


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
    transform_ids = serializers.ListField(child=serializers.IntegerField(), min_length=1, max_length=10)
    input_data = serializers.JSONField()

    def validate_investigation_id(self, value):
        """Validate investigation exists and user has access"""
        user = self.context["request"].user
        try:
            investigation = Investigation.objects.get(id=value, created_by=user)
            if investigation.status == "archived":
                raise serializers.ValidationError("Cannot execute transforms on archived investigations")
            return value
        except Investigation.DoesNotExist:
            raise serializers.ValidationError("Investigation not found or you don't have access")

    def validate_transform_ids(self, value):
        """Validate all transforms exist and are enabled"""
        transforms = Transform.objects.filter(id__in=value, is_enabled=True)
        if len(transforms) != len(value):
            raise serializers.ValidationError("One or more transforms not found or not enabled")
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
    execution_ids = serializers.ListField(child=serializers.IntegerField(), min_length=1, max_length=50)

    def validate_execution_ids(self, value):
        """Validate executions exist and user has access"""
        user = self.context["request"].user
        executions = TransformExecution.objects.filter(id__in=value, investigation__created_by=user)

        if len(executions) != len(value):
            raise serializers.ValidationError("One or more executions not found or you don't have access")

        return value
