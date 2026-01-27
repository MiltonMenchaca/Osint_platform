import uuid

from django.contrib.auth.models import User
from django.core.validators import MinLengthValidator
from django.db import models
from django.utils import timezone


class Investigation(models.Model):
    """
    Model representing an OSINT investigation
    """

    STATUS_CHOICES = [
        ("active", "Active"),
        ("completed", "Completed"),
        ("paused", "Paused"),
        ("archived", "Archived"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(
        max_length=255,
        validators=[MinLengthValidator(3)],
        help_text="Name of the investigation",
    )
    description = models.TextField(
        blank=True, help_text="Detailed description of the investigation"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="active",
        help_text="Current status of the investigation",
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="investigations",
        help_text="User who created this investigation",
    )
    created_at = models.DateTimeField(
        auto_now_add=True, help_text="Timestamp when investigation was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True, help_text="Timestamp when investigation was last updated"
    )
    tags = models.JSONField(
        default=list, blank=True, help_text="Tags associated with this investigation"
    )
    metadata = models.JSONField(
        default=dict, blank=True, help_text="Additional metadata for the investigation"
    )

    class Meta:
        db_table = "investigations"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["created_by"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.status})"

    def get_entity_count(self):
        """Get the number of entities in this investigation"""
        return self.entities.count()

    def get_relationship_count(self):
        """Get the number of relationships in this investigation"""
        return self.relationships.count()

    def get_transform_execution_count(self):
        """Get the number of transform executions in this investigation"""
        return self.transform_executions.count()

    def get_graph_data(self):
        """Generate graph data for visualization"""
        nodes = []
        edges = []

        # Add entities as nodes
        for entity in self.entities.all():
            nodes.append(
                {
                    "id": str(entity.id),
                    "label": entity.value,
                    "type": entity.entity_type,
                    "properties": entity.properties,
                }
            )

        # Add relationships as edges
        for relationship in self.relationships.all():
            edges.append(
                {
                    "id": str(relationship.id),
                    "source": str(relationship.source_entity.id),
                    "target": str(relationship.target_entity.id),
                    "type": relationship.relationship_type,
                    "properties": relationship.properties,
                }
            )

        return {
            "nodes": nodes,
            "edges": edges,
        }


class TransformExecution(models.Model):
    """
    Model representing the execution of a transform on an entity
    """

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("running", "Running"),
        ("completed", "Completed"),
        ("failed", "Failed"),
        ("cancelled", "Cancelled"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    investigation = models.ForeignKey(
        Investigation,
        on_delete=models.CASCADE,
        related_name="transform_executions",
        help_text="Investigation this execution belongs to",
    )
    transform_name = models.CharField(
        max_length=100, help_text="Name of the transform being executed"
    )
    input_entity = models.ForeignKey(
        "entities.Entity",
        on_delete=models.CASCADE,
        related_name="transform_executions",
        help_text="Entity that serves as input for the transform",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
        help_text="Current status of the execution",
    )
    started_at = models.DateTimeField(
        null=True, blank=True, help_text="Timestamp when execution started"
    )
    completed_at = models.DateTimeField(
        null=True, blank=True, help_text="Timestamp when execution completed"
    )
    created_at = models.DateTimeField(
        auto_now_add=True, help_text="Timestamp when execution was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True, help_text="Timestamp when execution was last updated"
    )
    parameters = models.JSONField(
        default=dict, blank=True, help_text="Parameters passed to the transform"
    )
    results = models.JSONField(
        default=dict, blank=True, help_text="Results returned by the transform"
    )
    error_message = models.TextField(
        blank=True, help_text="Error message if execution failed"
    )
    celery_task_id = models.CharField(
        max_length=255, blank=True, help_text="Celery task ID for tracking"
    )

    class Meta:
        db_table = "transform_executions"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["investigation"]),
            models.Index(fields=["transform_name"]),
            models.Index(fields=["celery_task_id"]),
        ]

    def __str__(self):
        return f"{self.transform_name} on {self.input_entity.value} ({self.status})"

    def start_execution(self):
        """Mark execution as started"""
        self.status = "running"
        self.started_at = timezone.now()
        self.save(update_fields=["status", "started_at", "updated_at"])

    def complete_execution(self, results=None):
        """Mark execution as completed with results"""
        self.status = "completed"
        self.completed_at = timezone.now()
        if results:
            self.results = results
        self.save(update_fields=["status", "completed_at", "results", "updated_at"])

    def fail_execution(self, error_message):
        """Mark execution as failed with error message"""
        self.status = "failed"
        self.completed_at = timezone.now()
        self.error_message = error_message
        self.save(
            update_fields=["status", "completed_at", "error_message", "updated_at"]
        )

    def get_duration(self):
        """Get execution duration in seconds"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    def is_running(self):
        """Check if execution is currently running"""
        return self.status == "running"

    def is_completed(self):
        """Check if execution is completed"""
        return self.status in ["completed", "failed", "cancelled"]
