import logging
from datetime import timedelta

from django.core.cache import cache
from django.db.models import Avg, Count, Max, Min, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, permissions, serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from apps.authentication.permissions import HasAPIAccess, IsOwnerOrReadOnly
from apps.entities.models import Entity, Relationship
from apps.transforms.models import Transform

from .models import Investigation, TransformExecution
from .serializers import (
    InvestigationCreateSerializer,
    InvestigationDetailSerializer,
    InvestigationListSerializer,
    TransformExecutionCreateSerializer,
    TransformExecutionDetailSerializer,
    TransformExecutionListSerializer,
)


# Create temporary serializers for missing ones
class BulkExecutionSerializer(serializers.Serializer):
    transform_ids = serializers.ListField(child=serializers.IntegerField())
    input_data = serializers.JSONField()


class ExecutionControlSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["cancel", "retry"])


# Mock task functions for now
def execute_transform_task(execution_id):
    pass


def bulk_execute_transforms_task(execution_ids):
    pass


logger = logging.getLogger(__name__)


class StandardResultsSetPagination(PageNumberPagination):
    """Standard pagination for API views"""

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class InvestigationListCreateView(generics.ListCreateAPIView):
    """List all investigations or create a new investigation"""

    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_serializer_class(self):
        if self.request.method == "POST":
            return InvestigationCreateSerializer
        return InvestigationListSerializer

    def get_queryset(self):
        """Filter investigations by user and search parameters"""
        # Temporarily allow all investigations for development
        queryset = Investigation.objects.all()
        # queryset = Investigation.objects.filter(created_by=self.request.user)

        # Search functionality
        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(description__icontains=search)
                | Q(target__icontains=search)
            )

        # Filter by status
        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # Filter by priority - temporarily disabled (field not in model)
        # priority_filter = self.request.query_params.get('priority')
        # if priority_filter:
        #     queryset = queryset.filter(priority=priority_filter)

        # Date range filtering
        date_from = self.request.query_params.get("date_from")
        date_to = self.request.query_params.get("date_to")

        if date_from:
            try:
                from datetime import datetime

                date_from = datetime.fromisoformat(date_from.replace("Z", "+00:00"))
                queryset = queryset.filter(created_at__gte=date_from)
            except ValueError:
                pass

        if date_to:
            try:
                from datetime import datetime

                date_to = datetime.fromisoformat(date_to.replace("Z", "+00:00"))
                queryset = queryset.filter(created_at__lte=date_to)
            except ValueError:
                pass

        # Ordering
        ordering = self.request.query_params.get("ordering", "-created_at")
        valid_orderings = [
            "name",
            "-name",
            "status",
            "-status",
            "created_at",
            "-created_at",
            "updated_at",
            "-updated_at",
        ]

        if ordering in valid_orderings:
            queryset = queryset.order_by(ordering)
        else:
            queryset = queryset.order_by("-created_at")

        return queryset.select_related("created_by").prefetch_related(
            "entities", "relationships", "transform_executions"
        )

    def perform_create(self, serializer):
        """Set the investigation creator"""
        # Temporarily create without user for development
        from django.contrib.auth import get_user_model

        User = get_user_model()
        default_user, created = User.objects.get_or_create(
            username="admin", defaults={"email": "admin@osint.com", "is_staff": True}
        )
        investigation = serializer.save(created_by=default_user)

        logger.info(f"Investigation '{investigation.name}' created")

        # Clear user's investigation cache
        cache_key = f"user_investigations_{default_user.id}"
        cache.delete(cache_key)


class InvestigationDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update or delete an investigation"""

    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method in ["PUT", "PATCH"]:
            return InvestigationDetailSerializer  # Using DetailSerializer temporarily
        return InvestigationDetailSerializer

    def get_queryset(self):
        # Temporarily allow all investigations for development
        return (
            Investigation.objects.all()
            .select_related("created_by")
            .prefetch_related(
                "entities",
                "relationships",
                "transform_executions__transform",
                "transform_executions__created_by",
            )
        )

    def perform_update(self, serializer):
        """Log investigation updates"""
        investigation = serializer.save()

        logger.info(
            f"Investigation '{investigation.name}' updated by user {self.request.user.username}"
        )

        # Clear caches
        cache_key = f"investigation_{investigation.id}"
        cache.delete(cache_key)
        cache_key = f"user_investigations_{self.request.user.id}"
        cache.delete(cache_key)

    def perform_destroy(self, instance):
        """Log investigation deletion"""
        logger.info(
            f"Investigation '{instance.name}' deleted by user {self.request.user.username}"
        )

        # Clear caches
        cache_key = f"investigation_{instance.id}"
        cache.delete(cache_key)
        cache_key = f"user_investigations_{self.request.user.id}"
        cache.delete(cache_key)

        instance.delete()


class TransformExecutionListCreateView(generics.ListCreateAPIView):
    """List transform executions or create a new execution"""

    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_serializer_class(self):
        if self.request.method == "POST":
            return TransformExecutionCreateSerializer
        return TransformExecutionListSerializer

    def get_queryset(self):
        """Filter executions by investigation and user"""
        investigation_id = self.kwargs.get("investigation_id")

        # Verify user owns the investigation
        investigation = get_object_or_404(
            Investigation, id=investigation_id, created_by=self.request.user
        )

        queryset = TransformExecution.objects.filter(investigation=investigation)

        # Filter by status
        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # Filter by transform
        transform_filter = self.request.query_params.get("transform")
        if transform_filter:
            queryset = queryset.filter(transform_id=transform_filter)

        # Date range filtering
        date_from = self.request.query_params.get("date_from")
        date_to = self.request.query_params.get("date_to")

        if date_from:
            try:
                from datetime import datetime

                date_from = datetime.fromisoformat(date_from.replace("Z", "+00:00"))
                queryset = queryset.filter(created_at__gte=date_from)
            except ValueError:
                pass

        if date_to:
            try:
                from datetime import datetime

                date_to = datetime.fromisoformat(date_to.replace("Z", "+00:00"))
                queryset = queryset.filter(created_at__lte=date_to)
            except ValueError:
                pass

        # Ordering
        ordering = self.request.query_params.get("ordering", "-created_at")
        valid_orderings = [
            "status",
            "-status",
            "created_at",
            "-created_at",
            "started_at",
            "-started_at",
            "completed_at",
            "-completed_at",
        ]

        if ordering in valid_orderings:
            queryset = queryset.order_by(ordering)
        else:
            queryset = queryset.order_by("-created_at")

        return queryset.select_related("investigation", "transform", "created_by")

    def perform_create(self, serializer):
        """Create and execute transform"""
        investigation_id = self.kwargs.get("investigation_id")

        # Verify user owns the investigation
        investigation = get_object_or_404(
            Investigation, id=investigation_id, created_by=self.request.user
        )

        execution = serializer.save(
            investigation=investigation, created_by=self.request.user
        )

        # Execute transform asynchronously
        execute_transform_task.delay(execution.id)

        logger.info(
            f"Transform execution {execution.id} created and queued for investigation {investigation.name}"
        )


class TransformExecutionDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update or delete a transform execution"""

    permission_classes = [permissions.IsAuthenticated, HasAPIAccess, IsOwnerOrReadOnly]
    serializer_class = TransformExecutionDetailSerializer

    def get_queryset(self):
        investigation_id = self.kwargs.get("investigation_id")

        # Verify user owns the investigation
        investigation = get_object_or_404(
            Investigation, id=investigation_id, created_by=self.request.user
        )

        return TransformExecution.objects.filter(
            investigation=investigation
        ).select_related("investigation", "transform", "created_by")

    def update(self, request, *args, **kwargs):
        """Only allow status updates"""
        instance = self.get_object()

        # Only allow certain status transitions
        new_status = request.data.get("status")
        if new_status and new_status != instance.status:
            if instance.status == "completed" and new_status != "completed":
                return Response(
                    {"error": "Cannot change status of completed execution"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if instance.status == "failed" and new_status not in [
                "pending",
                "cancelled",
            ]:
                return Response(
                    {
                        "error": "Failed executions can only be reset to pending or cancelled"
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        return super().update(request, *args, **kwargs)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated, HasAPIAccess])
def investigation_stats(request, investigation_id):
    """Get investigation statistics"""
    # Verify user owns the investigation
    investigation = get_object_or_404(
        Investigation, id=investigation_id, created_by=request.user
    )

    # Check cache first
    cache_key = f"investigation_stats_{investigation_id}"
    cached_stats = cache.get(cache_key)
    if cached_stats:
        return Response(cached_stats)

    # Calculate statistics
    executions = TransformExecution.objects.filter(investigation=investigation)
    entities = Entity.objects.filter(investigation=investigation)
    relationships = Relationship.objects.filter(investigation=investigation)

    stats = {
        "investigation": {
            "id": investigation.id,
            "name": investigation.name,
            "status": investigation.status,
            "created_at": investigation.created_at,
            "updated_at": investigation.updated_at,
        },
        "executions": {
            "total": executions.count(),
            "by_status": dict(
                executions.values("status")
                .annotate(count=Count("id"))
                .values_list("status", "count")
            ),
            "recent": executions.filter(
                created_at__gte=timezone.now() - timedelta(days=7)
            ).count(),
            "avg_duration": executions.filter(
                status="completed", started_at__isnull=False, completed_at__isnull=False
            ).aggregate(avg_duration=Avg("completed_at") - Avg("started_at"))[
                "avg_duration"
            ],
        },
        "entities": {
            "total": entities.count(),
            "by_type": dict(
                entities.values("entity_type")
                .annotate(count=Count("id"))
                .values_list("entity_type", "count")
            ),
            "confidence_stats": entities.aggregate(
                avg_confidence=Avg("confidence_score"),
                max_confidence=Max("confidence_score"),
                min_confidence=Min("confidence_score"),
            ),
        },
        "relationships": {
            "total": relationships.count(),
            "by_type": dict(
                relationships.values("relationship_type")
                .annotate(count=Count("id"))
                .values_list("relationship_type", "count")
            ),
            "confidence_stats": relationships.aggregate(
                avg_confidence=Avg("confidence_score"),
                max_confidence=Max("confidence_score"),
                min_confidence=Min("confidence_score"),
            ),
        },
    }

    # Cache for 5 minutes
    cache.set(cache_key, stats, 300)

    return Response(stats)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated, HasAPIAccess])
def bulk_execute_transforms(request, investigation_id):
    """Execute multiple transforms in bulk"""
    # Verify user owns the investigation
    investigation = get_object_or_404(
        Investigation, id=investigation_id, created_by=request.user
    )

    serializer = BulkExecutionSerializer(data=request.data)
    if serializer.is_valid():
        transform_ids = serializer.validated_data["transform_ids"]
        input_data = serializer.validated_data["input_data"]

        # Create execution records
        executions = []
        for transform_id in transform_ids:
            transform = get_object_or_404(Transform, id=transform_id, is_enabled=True)

            execution = TransformExecution.objects.create(
                investigation=investigation,
                transform=transform,
                input_data=input_data,
                created_by=request.user,
            )
            executions.append(execution)

        # Execute transforms asynchronously
        execution_ids = [e.id for e in executions]
        bulk_execute_transforms_task.delay(execution_ids)

        logger.info(
            f"Bulk execution of {len(executions)} transforms queued for investigation {investigation.name}"
        )

        return Response(
            {
                "message": f"{len(executions)} transforms queued for execution",
                "execution_ids": execution_ids,
            },
            status=status.HTTP_201_CREATED,
        )

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated, HasAPIAccess])
def control_execution(request, investigation_id, execution_id):
    """Control transform execution (pause, resume, cancel)"""
    # Verify user owns the investigation
    investigation = get_object_or_404(
        Investigation, id=investigation_id, created_by=request.user
    )

    execution = get_object_or_404(
        TransformExecution, id=execution_id, investigation=investigation
    )

    serializer = ExecutionControlSerializer(data=request.data)
    if serializer.is_valid():
        action = serializer.validated_data["action"]

        if action == "cancel":
            if execution.status in ["pending", "running"]:
                execution.status = "cancelled"
                execution.error_message = "Cancelled by user"
                execution.completed_at = timezone.now()
                execution.save()

                # TODO: Cancel the actual task if it's running

                logger.info(
                    f"Execution {execution_id} cancelled by user {request.user.username}"
                )

                return Response({"message": "Execution cancelled"})
            else:
                return Response(
                    {"error": "Cannot cancel execution in current status"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        elif action == "retry":
            if execution.status in ["failed", "cancelled"]:
                execution.status = "pending"
                execution.error_message = None
                execution.started_at = None
                execution.completed_at = None
                execution.output_data = None
                execution.save()

                # Re-queue the task
                execute_transform_task.delay(execution.id)

                logger.info(
                    f"Execution {execution_id} retried by user {request.user.username}"
                )

                return Response({"message": "Execution queued for retry"})
            else:
                return Response(
                    {"error": "Cannot retry execution in current status"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        else:
            return Response(
                {"error": "Invalid action"}, status=status.HTTP_400_BAD_REQUEST
            )

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated, HasAPIAccess])
def user_investigations_stats(request):
    """Get user's investigation statistics"""
    # Check cache first
    cache_key = f"user_investigations_stats_{request.user.id}"
    cached_stats = cache.get(cache_key)
    if cached_stats:
        return Response(cached_stats)

    investigations = Investigation.objects.filter(created_by=request.user)
    executions = TransformExecution.objects.filter(
        investigation__created_by=request.user
    )
    entities = Entity.objects.filter(investigation__created_by=request.user)
    relationships = Relationship.objects.filter(investigation__created_by=request.user)

    stats = {
        "investigations": {
            "total": investigations.count(),
            "by_status": dict(
                investigations.values("status")
                .annotate(count=Count("id"))
                .values_list("status", "count")
            ),
            "recent": investigations.filter(
                created_at__gte=timezone.now() - timedelta(days=30)
            ).count(),
        },
        "executions": {
            "total": executions.count(),
            "by_status": dict(
                executions.values("status")
                .annotate(count=Count("id"))
                .values_list("status", "count")
            ),
            "recent": executions.filter(
                created_at__gte=timezone.now() - timedelta(days=7)
            ).count(),
            "success_rate": (
                executions.filter(status="completed").count()
                / max(executions.count(), 1)
            )
            * 100,
        },
        "entities": {
            "total": entities.count(),
            "by_type": dict(
                entities.values("entity_type")
                .annotate(count=Count("id"))
                .values_list("entity_type", "count")
            ),
            "avg_confidence": entities.aggregate(
                avg_confidence=Avg("confidence_score")
            )["avg_confidence"],
        },
        "relationships": {
            "total": relationships.count(),
            "by_type": dict(
                relationships.values("relationship_type")
                .annotate(count=Count("id"))
                .values_list("relationship_type", "count")
            ),
            "avg_confidence": relationships.aggregate(
                avg_confidence=Avg("confidence_score")
            )["avg_confidence"],
        },
    }

    # Cache for 10 minutes
    cache.set(cache_key, stats, 600)

    return Response(stats)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated, HasAPIAccess])
def investigation_export(request, investigation_id):
    """Export investigation data"""
    # Verify user owns the investigation
    investigation = get_object_or_404(
        Investigation, id=investigation_id, created_by=request.user
    )

    # Get all related data
    executions = TransformExecution.objects.filter(
        investigation=investigation
    ).select_related("transform", "created_by")

    entities = Entity.objects.filter(investigation=investigation)

    relationships = Relationship.objects.filter(
        investigation=investigation
    ).select_related("source_entity", "target_entity")

    # Serialize data
    investigation_data = InvestigationDetailSerializer(investigation).data
    execution_data = TransformExecutionDetailSerializer(executions, many=True).data

    from apps.entities.serializers import (
        EntityDetailSerializer,
        RelationshipDetailSerializer,
    )

    entity_data = EntityDetailSerializer(entities, many=True).data
    relationship_data = RelationshipDetailSerializer(relationships, many=True).data

    export_data = {
        "investigation": investigation_data,
        "executions": execution_data,
        "entities": entity_data,
        "relationships": relationship_data,
        "exported_at": timezone.now().isoformat(),
        "exported_by": request.user.username,
    }

    logger.info(
        f"Investigation {investigation.name} exported by user {request.user.username}"
    )

    return Response(export_data)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated, HasAPIAccess])
def execution_logs(request, investigation_id, execution_id):
    """Get execution logs and output"""
    # Verify user owns the investigation
    investigation = get_object_or_404(
        Investigation, id=investigation_id, created_by=request.user
    )

    execution = get_object_or_404(
        TransformExecution, id=execution_id, investigation=investigation
    )

    logs_data = {
        "execution_id": execution.id,
        "status": execution.status,
        "input_data": execution.input_data,
        "output_data": execution.output_data,
        "error_message": execution.error_message,
        "created_at": execution.created_at,
        "started_at": execution.started_at,
        "completed_at": execution.completed_at,
        "duration": None,
    }

    # Calculate duration if available
    if execution.started_at and execution.completed_at:
        duration = execution.completed_at - execution.started_at
        logs_data["duration"] = duration.total_seconds()

    return Response(logs_data)
