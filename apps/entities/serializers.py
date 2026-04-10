import ipaddress
import re
from urllib.parse import urlparse

from rest_framework import serializers

from .models import Entity, Relationship


class EntityListSerializer(serializers.ModelSerializer):
    """Serializer for Entity list view"""

    investigation_id = serializers.UUIDField(source="investigation.id", read_only=True)
    investigation_name = serializers.CharField(source="investigation.name", read_only=True)
    relationships_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Entity
        fields = [
            "id",
            "investigation_id",
            "entity_type",
            "value",
            "confidence_score",
            "investigation_name",
            "created_at",
            "updated_at",
            "relationships_count",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class EntityDetailSerializer(serializers.ModelSerializer):
    """Serializer for Entity detail view"""

    investigation_id = serializers.UUIDField(source="investigation.id", read_only=True)
    investigation = serializers.StringRelatedField(read_only=True)
    source_relationships = serializers.SerializerMethodField()
    target_relationships = serializers.SerializerMethodField()

    class Meta:
        model = Entity
        fields = [
            "id",
            "investigation_id",
            "investigation",
            "entity_type",
            "display_name",
            "value",
            "description",
            "confidence_score",
            "properties",
            "source",
            "tags",
            "is_seed",
            "created_at",
            "updated_at",
            "source_relationships",
            "target_relationships",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_source_relationships(self, obj):
        """Get relationships where this entity is the source"""
        relationships = obj.source_relationships.select_related("target_entity")
        return RelationshipListSerializer(relationships, many=True).data

    def get_target_relationships(self, obj):
        """Get relationships where this entity is the target"""
        relationships = obj.target_relationships.select_related("source_entity")
        return RelationshipListSerializer(relationships, many=True).data


class EntityCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating entities"""

    class Meta:
        model = Entity
        fields = [
            "id",
            "entity_type",
            "display_name",
            "value",
            "description",
            "confidence_score",
            "properties",
            "source",
            "tags",
            "is_seed",
        ]

    def validate_entity_type(self, value):
        """Validate entity type"""
        valid_types = {choice[0] for choice in Entity.ENTITY_TYPE_CHOICES}
        if value not in valid_types:
            raise serializers.ValidationError(f"Invalid entity type. Must be one of: {', '.join(sorted(valid_types))}")

        return value

    def validate_value(self, value):
        """Validate entity value based on type"""
        entity_type = self.initial_data.get("entity_type")

        if not entity_type:
            return value

        # Validate based on entity type
        if entity_type in ["domain", "subdomain"]:
            if not self._is_valid_domain(value):
                raise serializers.ValidationError("Invalid domain format")

        elif entity_type == "ip":
            if not self._is_valid_ip(value):
                raise serializers.ValidationError("Invalid IP address format")

        elif entity_type == "email":
            if not self._is_valid_email(value):
                raise serializers.ValidationError("Invalid email format")

        elif entity_type == "url":
            if not self._is_valid_url(value):
                raise serializers.ValidationError("Invalid URL format")

        elif entity_type == "phone":
            if not self._is_valid_phone(value):
                raise serializers.ValidationError("Invalid phone number format")

        elif entity_type == "hash":
            if not self._is_valid_hash(value):
                raise serializers.ValidationError("Invalid hash format")

        return value.strip()

    def validate_confidence_score(self, value):
        """Validate confidence score"""
        if value is None:
            return value
        if not 0.0 <= float(value) <= 1.0:
            raise serializers.ValidationError("Confidence score must be between 0.0 and 1.0")
        return value

    def validate_properties(self, value):
        if value is None:
            return {}
        if not isinstance(value, dict):
            raise serializers.ValidationError("Properties must be a JSON object")
        return value

    def _is_valid_domain(self, value):
        """Validate domain format"""
        domain_pattern = re.compile(
            r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+"  # Domain parts
            r"[a-zA-Z]{2,}$"  # TLD
        )
        return bool(domain_pattern.match(value))

    def _is_valid_ip(self, value):
        """Validate IP address format"""
        try:
            ipaddress.ip_address(value)
            return True
        except ValueError:
            return False

    def _is_valid_email(self, value):
        """Validate email format"""
        email_pattern = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
        return bool(email_pattern.match(value))

    def _is_valid_url(self, value):
        """Validate URL format"""
        try:
            result = urlparse(value)
            return all([result.scheme, result.netloc])
        except Exception:
            return False

    def _is_valid_phone(self, value):
        """Validate phone number format"""
        phone_pattern = re.compile(r"^\+?[1-9]\d{1,14}$")  # E.164 format
        return bool(phone_pattern.match(value.replace(" ", "").replace("-", "")))

    def _is_valid_hash(self, value):
        """Validate hash format (MD5, SHA1, SHA256, etc.)"""
        hash_patterns = {
            32: re.compile(r"^[a-fA-F0-9]{32}$"),  # MD5
            40: re.compile(r"^[a-fA-F0-9]{40}$"),  # SHA1
            64: re.compile(r"^[a-fA-F0-9]{64}$"),  # SHA256
            128: re.compile(r"^[a-fA-F0-9]{128}$"),  # SHA512
        }

        length = len(value)
        if length in hash_patterns:
            return bool(hash_patterns[length].match(value))

        return False


class EntitySerializer(serializers.ModelSerializer):
    """Basic Entity serializer for nested use"""

    class Meta:
        model = Entity
        fields = ["id", "entity_type", "value", "confidence_score"]
        read_only_fields = ["id"]


class RelationshipListSerializer(serializers.ModelSerializer):
    """Serializer for Relationship list view"""

    source_entity = EntitySerializer(read_only=True)
    target_entity = EntitySerializer(read_only=True)
    investigation_name = serializers.CharField(source="investigation.name", read_only=True)

    class Meta:
        model = Relationship
        fields = [
            "id",
            "source_entity",
            "target_entity",
            "relationship_type",
            "confidence_score",
            "investigation_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class RelationshipDetailSerializer(serializers.ModelSerializer):
    """Serializer for Relationship detail view"""

    source_entity = EntityDetailSerializer(read_only=True)
    target_entity = EntityDetailSerializer(read_only=True)
    investigation = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Relationship
        fields = [
            "id",
            "investigation",
            "source_entity",
            "target_entity",
            "relationship_type",
            "description",
            "confidence_score",
            "properties",
            "source",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class RelationshipCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating relationships"""

    source_entity_id = serializers.UUIDField(write_only=True)
    target_entity_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = Relationship
        fields = [
            "source_entity_id",
            "target_entity_id",
            "relationship_type",
            "confidence_score",
            "description",
            "properties",
            "source",
        ]

    def validate_source_entity_id(self, value):
        """Validate source entity exists"""
        try:
            Entity.objects.get(id=value)
            return value
        except Entity.DoesNotExist:
            raise serializers.ValidationError("Source entity not found")

    def validate_target_entity_id(self, value):
        """Validate target entity exists"""
        try:
            Entity.objects.get(id=value)
            return value
        except Entity.DoesNotExist:
            raise serializers.ValidationError("Target entity not found")

    def validate_relationship_type(self, value):
        """Validate relationship type"""
        valid_types = {choice[0] for choice in Relationship.RELATIONSHIP_TYPE_CHOICES}
        if value not in valid_types:
            raise serializers.ValidationError(
                f"Invalid relationship type. Must be one of: {', '.join(sorted(valid_types))}"
            )

        return value

    def validate_confidence_score(self, value):
        """Validate confidence score"""
        if value is None:
            return value
        if not 0.0 <= float(value) <= 1.0:
            raise serializers.ValidationError("Confidence score must be between 0.0 and 1.0")
        return value

    def validate_properties(self, value):
        if value is None:
            return {}
        if not isinstance(value, dict):
            raise serializers.ValidationError("Properties must be a JSON object")
        return value

    def validate(self, attrs):
        """Cross-field validation"""
        source_entity_id = attrs["source_entity_id"]
        target_entity_id = attrs["target_entity_id"]

        # Check for self-relationships
        if source_entity_id == target_entity_id:
            raise serializers.ValidationError("Source and target entities cannot be the same")

        # Check for duplicate relationships
        investigation_id = self.context.get("view", None)
        investigation_id = getattr(investigation_id, "kwargs", {}).get("investigation_id")
        if investigation_id:
            if Relationship.objects.filter(
                investigation_id=investigation_id,
                source_entity_id=source_entity_id,
                target_entity_id=target_entity_id,
                relationship_type=attrs["relationship_type"],
            ).exists():
                raise serializers.ValidationError("This relationship already exists")

        return attrs

    def create(self, validated_data):
        """Create relationship with entities and investigation"""
        source_entity_id = validated_data.pop("source_entity_id")
        target_entity_id = validated_data.pop("target_entity_id")

        validated_data["source_entity"] = Entity.objects.get(id=source_entity_id)
        validated_data["target_entity"] = Entity.objects.get(id=target_entity_id)

        return super().create(validated_data)


class RelationshipSerializer(serializers.ModelSerializer):
    """Basic Relationship serializer for nested use"""

    source_entity = EntitySerializer(read_only=True)
    target_entity = EntitySerializer(read_only=True)

    class Meta:
        model = Relationship
        fields = [
            "id",
            "source_entity",
            "target_entity",
            "relationship_type",
            "confidence_score",
        ]
        read_only_fields = ["id"]


class EntityStatsSerializer(serializers.Serializer):
    """Serializer for entity statistics"""

    total_entities = serializers.IntegerField()
    entities_by_type = serializers.DictField()
    total_relationships = serializers.IntegerField()
    relationships_by_type = serializers.DictField()
    average_confidence = serializers.FloatField()
    recent_entities = EntityListSerializer(many=True)

    class Meta:
        fields = [
            "total_entities",
            "entities_by_type",
            "total_relationships",
            "relationships_by_type",
            "average_confidence",
            "recent_entities",
        ]


class BulkEntityCreateSerializer(serializers.Serializer):
    """Serializer for bulk entity creation"""

    entities = serializers.ListField(child=serializers.DictField(), min_length=1, max_length=100)

    def validate_entities(self, value):
        """Validate entity data"""
        required_fields = ["entity_type", "value"]

        valid_types = {choice[0] for choice in Entity.ENTITY_TYPE_CHOICES}
        for i, entity_data in enumerate(value):
            for field in required_fields:
                if field not in entity_data:
                    raise serializers.ValidationError(f"Entity {i+1}: Missing required field '{field}'")

            # Validate entity type
            entity_type = entity_data.get("entity_type")
            if entity_type not in valid_types:
                raise serializers.ValidationError(f"Entity {i+1}: Invalid entity type '{entity_type}'")

            # Set default confidence score if not provided
            if "confidence_score" not in entity_data:
                entity_data["confidence_score"] = 1.0

            # Validate confidence score
            confidence = entity_data.get("confidence_score", 1.0)
            try:
                confidence_value = float(confidence)
            except (TypeError, ValueError):
                raise serializers.ValidationError(f"Entity {i+1}: Confidence score must be a number")
            if not 0.0 <= confidence_value <= 1.0:
                raise serializers.ValidationError(f"Entity {i+1}: Confidence score must be between 0.0 and 1.0")
            entity_data["confidence_score"] = confidence_value

        return value
