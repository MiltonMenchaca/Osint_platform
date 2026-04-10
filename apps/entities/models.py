import uuid

from django.core.validators import MinLengthValidator
from django.db import models


class Entity(models.Model):
    """
    Model representing an entity in an OSINT investigation
    """

    ENTITY_TYPE_CHOICES = [
        ("domain", "Domain"),
        ("ip", "IP Address"),
        ("email", "Email Address"),
        ("person", "Person"),
        ("organization", "Organization"),
        ("phone", "Phone Number"),
        ("url", "URL"),
        ("port", "Port"),
        ("service", "Service"),
        ("hash", "Hash"),
        ("file", "File"),
        ("cryptocurrency", "Cryptocurrency Address"),
        ("social_media", "Social Media Account"),
        ("geolocation", "Geolocation"),
        ("other", "Other"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    investigation = models.ForeignKey(
        "investigations.Investigation",
        on_delete=models.CASCADE,
        related_name="entities",
        help_text="Investigation this entity belongs to",
    )
    entity_type = models.CharField(max_length=50, choices=ENTITY_TYPE_CHOICES, help_text="Type of the entity")
    value = models.CharField(
        max_length=500,
        validators=[MinLengthValidator(1)],
        help_text="Primary value of the entity",
    )
    display_name = models.CharField(max_length=255, blank=True, help_text="Human-readable display name")
    description = models.TextField(blank=True, help_text="Description of the entity")
    properties = models.JSONField(default=dict, blank=True, help_text="Additional properties of the entity")
    confidence_score = models.FloatField(default=1.0, help_text="Confidence score (0.0 to 1.0)")
    source = models.CharField(max_length=255, blank=True, help_text="Source where this entity was discovered")
    created_at = models.DateTimeField(auto_now_add=True, help_text="Timestamp when entity was created")
    updated_at = models.DateTimeField(auto_now=True, help_text="Timestamp when entity was last updated")
    tags = models.JSONField(default=list, blank=True, help_text="Tags associated with this entity")
    is_seed = models.BooleanField(default=False, help_text="Whether this entity is a seed entity (starting point)")

    class Meta:
        db_table = "entities"
        ordering = ["-created_at"]
        unique_together = ["investigation", "entity_type", "value"]
        indexes = [
            models.Index(fields=["entity_type"]),
            models.Index(fields=["investigation"]),
            models.Index(fields=["value"]),
            models.Index(fields=["is_seed"]),
            models.Index(fields=["confidence_score"]),
        ]

    def __str__(self):
        return f"{self.entity_type}: {self.value}"

    def save(self, *args, **kwargs):
        # Set display_name if not provided
        if not self.display_name:
            self.display_name = self.value
        super().save(*args, **kwargs)

    def get_relationships_as_source(self):
        """Get relationships where this entity is the source"""
        return self.source_relationships.all()

    def get_relationships_as_target(self):
        """Get relationships where this entity is the target"""
        return self.target_relationships.all()

    def get_all_relationships(self):
        """Get all relationships involving this entity"""
        from django.db.models import Q

        return Relationship.objects.filter(Q(source_entity=self) | Q(target_entity=self))

    def get_connected_entities(self):
        """Get all entities connected to this entity"""
        relationships = self.get_all_relationships()
        connected_entities = set()

        for rel in relationships:
            if rel.source_entity != self:
                connected_entities.add(rel.source_entity)
            if rel.target_entity != self:
                connected_entities.add(rel.target_entity)

        return list(connected_entities)

    def add_property(self, key, value):
        """Add a property to the entity"""
        if not self.properties:
            self.properties = {}
        self.properties[key] = value
        self.save(update_fields=["properties", "updated_at"])

    def get_property(self, key, default=None):
        """Get a property value"""
        return self.properties.get(key, default) if self.properties else default

    def add_tag(self, tag):
        """Add a tag to the entity"""
        if not self.tags:
            self.tags = []
        if tag not in self.tags:
            self.tags.append(tag)
            self.save(update_fields=["tags", "updated_at"])

    def remove_tag(self, tag):
        """Remove a tag from the entity"""
        if self.tags and tag in self.tags:
            self.tags.remove(tag)
            self.save(update_fields=["tags", "updated_at"])


class Relationship(models.Model):
    """
    Model representing a relationship between two entities
    """

    RELATIONSHIP_TYPE_CHOICES = [
        ("resolves_to", "Resolves To"),
        ("subdomain_of", "Subdomain Of"),
        ("hosted_on", "Hosted On"),
        ("owns", "Owns"),
        ("associated_with", "Associated With"),
        ("communicates_with", "Communicates With"),
        ("located_at", "Located At"),
        ("member_of", "Member Of"),
        ("works_for", "Works For"),
        ("similar_to", "Similar To"),
        ("linked_to", "Linked To"),
        ("contains", "Contains"),
        ("part_of", "Part Of"),
        ("references", "References"),
        ("other", "Other"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    investigation = models.ForeignKey(
        "investigations.Investigation",
        on_delete=models.CASCADE,
        related_name="relationships",
        help_text="Investigation this relationship belongs to",
    )
    source_entity = models.ForeignKey(
        Entity,
        on_delete=models.CASCADE,
        related_name="source_relationships",
        help_text="Source entity of the relationship",
    )
    target_entity = models.ForeignKey(
        Entity,
        on_delete=models.CASCADE,
        related_name="target_relationships",
        help_text="Target entity of the relationship",
    )
    relationship_type = models.CharField(
        max_length=50,
        choices=RELATIONSHIP_TYPE_CHOICES,
        help_text="Type of the relationship",
    )
    description = models.TextField(blank=True, help_text="Description of the relationship")
    properties = models.JSONField(default=dict, blank=True, help_text="Additional properties of the relationship")
    confidence_score = models.FloatField(default=1.0, help_text="Confidence score (0.0 to 1.0)")
    source = models.CharField(
        max_length=255,
        blank=True,
        help_text="Source where this relationship was discovered",
    )
    created_at = models.DateTimeField(auto_now_add=True, help_text="Timestamp when relationship was created")
    updated_at = models.DateTimeField(auto_now=True, help_text="Timestamp when relationship was last updated")

    class Meta:
        db_table = "relationships"
        ordering = ["-created_at"]
        unique_together = [
            "investigation",
            "source_entity",
            "target_entity",
            "relationship_type",
        ]
        indexes = [
            models.Index(fields=["relationship_type"]),
            models.Index(fields=["investigation"]),
            models.Index(fields=["source_entity"]),
            models.Index(fields=["target_entity"]),
            models.Index(fields=["confidence_score"]),
        ]

    def __str__(self):
        return f"{self.source_entity.value} {self.relationship_type} {self.target_entity.value}"

    def clean(self):
        """Validate that source and target entities are different"""
        from django.core.exceptions import ValidationError

        if self.source_entity == self.target_entity:
            raise ValidationError("Source and target entities cannot be the same.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def add_property(self, key, value):
        """Add a property to the relationship"""
        if not self.properties:
            self.properties = {}
        self.properties[key] = value
        self.save(update_fields=["properties", "updated_at"])

    def get_property(self, key, default=None):
        """Get a property value"""
        return self.properties.get(key, default) if self.properties else default

    def reverse_relationship(self):
        """Get the reverse relationship type if applicable"""
        reverse_mapping = {
            "resolves_to": "resolved_by",
            "subdomain_of": "has_subdomain",
            "hosted_on": "hosts",
            "owns": "owned_by",
            "member_of": "has_member",
            "works_for": "employs",
            "contains": "part_of",
            "part_of": "contains",
        }
        return reverse_mapping.get(self.relationship_type, "related_to")
