import logging
from datetime import timedelta

from django.core.cache import cache
from django.db.models import (
    Avg,
    Count,
    DateTimeField,
    DurationField,
    ExpressionWrapper,
    F,
    IntegerField,
    Max,
    Min,
    OuterRef,
    Q,
    Subquery,
)
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from apps.authentication.permissions import HasAPIAccess
from apps.investigations.models import TransformExecution

from .models import Transform
from .serializers import (
    BulkTransformActionSerializer,
    TransformCreateSerializer,
    TransformDetailSerializer,
    TransformImportSerializer,
    TransformListSerializer,
    TransformTestSerializer,
    TransformUpdateSerializer,
    TransformValidationSerializer,
)

logger = logging.getLogger(__name__)


class StandardResultsSetPagination(PageNumberPagination):
    """Standard pagination for API views"""

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class TransformListCreateView(generics.ListCreateAPIView):
    """List all transforms or create a new transform"""

    permission_classes = [permissions.IsAuthenticated, HasAPIAccess]
    pagination_class = StandardResultsSetPagination

    def get_serializer_class(self):
        if self.request.method == "POST":
            return TransformCreateSerializer
        return TransformListSerializer

    def get_queryset(self):
        """Filter transforms with search and filtering"""
        execution_count_subquery = (
            TransformExecution.objects.filter(transform_name=OuterRef("name"))
            .values("transform_name")
            .annotate(c=Count("id"))
            .values("c")
        )
        last_used_subquery = (
            TransformExecution.objects.filter(transform_name=OuterRef("name"))
            .values("transform_name")
            .annotate(m=Max("created_at"))
            .values("m")
        )

        queryset = Transform.objects.all().annotate(
            usage_count=Coalesce(Subquery(execution_count_subquery, output_field=IntegerField()), 0),
            last_used=Subquery(last_used_subquery, output_field=DateTimeField()),
        )

        # Search functionality
        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(description__icontains=search)
                | Q(category__icontains=search)
                | Q(tool_name__icontains=search)
                | Q(display_name__icontains=search)
            )

        # Filter by category
        category = self.request.query_params.get("category")
        if category:
            queryset = queryset.filter(category=category)

        # Filter by enabled status
        enabled = self.request.query_params.get("enabled")
        if enabled is not None:
            is_enabled = enabled.lower() in ["true", "1", "yes"]
            queryset = queryset.filter(is_enabled=is_enabled)

        # Filter by availability
        available = self.request.query_params.get("available")
        if available is not None:
            is_available = available.lower() in ["true", "1", "yes"]
            candidate_transforms = list(queryset)
            available_ids = [
                transform.id for transform in candidate_transforms if transform.check_availability()[0] == is_available
            ]
            queryset = queryset.filter(id__in=available_ids)

        # Filter by input entity types
        input_types = self.request.query_params.get("input_types")
        if input_types:
            input_type_list = [t.strip() for t in input_types.split(",")]
            queryset = queryset.filter(Q(input_type__in=input_type_list) | Q(input_type="any"))

        # Filter by output entity types
        output_types = self.request.query_params.get("output_types")
        if output_types:
            output_type_list = [t.strip() for t in output_types.split(",")]
            for output_type in output_type_list:
                queryset = queryset.filter(output_types__contains=[output_type])

        # Filter by timeout range
        min_timeout = self.request.query_params.get("min_timeout")
        max_timeout = self.request.query_params.get("max_timeout")

        if min_timeout:
            try:
                min_time = int(min_timeout)
                queryset = queryset.filter(timeout__gte=min_time)
            except ValueError:
                pass

        if max_timeout:
            try:
                max_time = int(max_timeout)
                queryset = queryset.filter(timeout__lte=max_time)
            except ValueError:
                pass

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
            "category",
            "-category",
            "tool_name",
            "-tool_name",
            "timeout",
            "-timeout",
            "created_at",
            "-created_at",
            "updated_at",
            "-updated_at",
            "usage_count",
            "-usage_count",
            "last_used",
            "-last_used",
        ]

        if ordering in valid_orderings:
            queryset = queryset.order_by(ordering)
        else:
            queryset = queryset.order_by("-created_at")

        return queryset

    def perform_create(self, serializer):
        """Log transform creation"""
        transform = serializer.save()

        logger.info(f"Transform '{transform.name}' created by {self.request.user.username}")

        # Clear transforms cache
        cache.delete("transforms_list")
        cache.delete("transforms_stats")


class TransformDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update or delete a transform"""

    queryset = Transform.objects.all()
    permission_classes = [permissions.IsAuthenticated, HasAPIAccess]

    def get_serializer_class(self):
        if self.request.method in ["PUT", "PATCH"]:
            return TransformUpdateSerializer
        return TransformDetailSerializer

    def perform_update(self, serializer):
        """Log transform updates"""
        transform = serializer.save()

        logger.info(f"Transform '{transform.name}' updated by {self.request.user.username}")

        # Clear caches
        cache.delete(f"transform_{transform.id}")
        cache.delete("transforms_list")
        cache.delete("transforms_stats")

    def perform_destroy(self, instance):
        """Log transform deletion"""
        logger.info(f"Transform '{instance.name}' deleted by {self.request.user.username}")

        # Clear caches
        cache.delete(f"transform_{instance.id}")
        cache.delete("transforms_list")
        cache.delete("transforms_stats")

        instance.delete()


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated, HasAPIAccess])
def transform_stats(request):
    """Get transform statistics"""
    # Check cache first
    cache_key = "transforms_stats"
    cached_stats = cache.get(cache_key)
    if cached_stats:
        return Response(cached_stats)

    transforms = Transform.objects.all()
    executions = TransformExecution.objects.all()

    enabled_transforms = list(transforms.filter(is_enabled=True))
    available_count = 0
    for t in enabled_transforms:
        is_available, _ = t.check_availability()
        if is_available:
            available_count += 1

    stats = {
        "transforms": {
            "total": transforms.count(),
            "enabled": transforms.filter(is_enabled=True).count(),
            "disabled": transforms.filter(is_enabled=False).count(),
            "available": available_count,
            "unavailable": max(len(enabled_transforms) - available_count, 0),
            "by_category": dict(
                transforms.values("category").annotate(count=Count("id")).values_list("category", "count")
            ),
            "timeout_stats": transforms.aggregate(
                avg_timeout=Avg("timeout"),
                max_timeout=Max("timeout"),
                min_timeout=Min("timeout"),
            ),
            "recent": transforms.filter(created_at__gte=timezone.now() - timedelta(days=7)).count(),
        },
        "executions": {
            "total": executions.count(),
            "successful": executions.filter(status="completed").count(),
            "failed": executions.filter(status="failed").count(),
            "running": executions.filter(status="running").count(),
            "pending": executions.filter(status="pending").count(),
            "by_status": dict(executions.values("status").annotate(count=Count("id")).values_list("status", "count")),
            "recent": executions.filter(created_at__gte=timezone.now() - timedelta(days=7)).count(),
            "avg_duration": 0,
        },
        "usage": {
            "most_used_transforms": [],
            "success_rates": [],
        },
    }

    duration_expr = ExpressionWrapper(F("completed_at") - F("started_at"), output_field=DurationField())
    avg_duration = (
        executions.filter(
            status="completed",
            started_at__isnull=False,
            completed_at__isnull=False,
        )
        .aggregate(avg=Avg(duration_expr))
        .get("avg")
    )
    stats["executions"]["avg_duration"] = avg_duration.total_seconds() if avg_duration else 0

    total_exec_subquery = (
        TransformExecution.objects.filter(transform_name=OuterRef("name"))
        .values("transform_name")
        .annotate(c=Count("id"))
        .values("c")
    )
    success_exec_subquery = (
        TransformExecution.objects.filter(transform_name=OuterRef("name"), status="completed")
        .values("transform_name")
        .annotate(c=Count("id"))
        .values("c")
    )

    transforms_with_usage = transforms.annotate(
        execution_count=Coalesce(Subquery(total_exec_subquery, output_field=IntegerField()), 0),
        successful_executions=Coalesce(Subquery(success_exec_subquery, output_field=IntegerField()), 0),
    )

    stats["usage"]["most_used_transforms"] = list(
        transforms_with_usage.order_by("-execution_count")[:10].values("id", "name", "category", "execution_count")
    )

    success_rates = []
    for t in transforms_with_usage:
        total = int(getattr(t, "execution_count", 0) or 0)
        if total <= 0:
            continue
        successful = int(getattr(t, "successful_executions", 0) or 0)
        success_rates.append(
            {
                "id": str(t.id),
                "name": t.name,
                "total_executions": total,
                "successful_executions": successful,
                "success_rate": (successful / total) * 100,
            }
        )

    success_rates.sort(key=lambda x: x["success_rate"], reverse=True)
    stats["usage"]["success_rates"] = success_rates[:10]

    # Cache for 5 minutes
    cache.set(cache_key, stats, 300)

    return Response(stats)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated, HasAPIAccess])
def test_transform(request, pk):
    """Test a transform with sample data"""
    transform = get_object_or_404(Transform, pk=pk)

    serializer = TransformTestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    test_input = serializer.validated_data["test_input"]
    execute = serializer.validated_data.get("execute", False)

    if isinstance(test_input, str):
        target_value = test_input
    else:
        target_value = (
            test_input.get("target")
            or test_input.get("input")
            or test_input.get("input_value")
            or test_input.get("value")
            or ""
        )
        target_value = str(target_value).strip()

    if not target_value:
        return Response(
            {"error": "Invalid test_input", "details": "Missing target/input value"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    is_available, availability_message = transform.check_availability()
    if not is_available:
        return Response(
            {"error": "Transform is not available", "details": availability_message},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        response_data = {
            "success": True,
            "transform": TransformDetailSerializer(transform).data,
            "test_input_value": target_value,
            "generated_command": transform.get_command(target_value),
            "execute": execute,
        }

        if execute:
            from apps.transforms.wrappers import OSINTToolError, ToolNotFoundError, get_wrapper

            wrapper_result = None
            try:
                wrapper_cls = get_wrapper(transform.tool_name)
                wrapper = wrapper_cls()
                input_type = transform.input_type if transform.input_type != "any" else "domain"
                wrapper_result = wrapper.execute({"type": input_type, "value": target_value}, timeout=transform.timeout)
            except (ValueError, ToolNotFoundError) as e:
                return Response(
                    {
                        "error": "Transform wrapper not found or tool missing",
                        "details": str(e),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            except OSINTToolError as e:
                return Response(
                    {"error": "Transform execution failed", "details": str(e)},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            response_data["test_result"] = wrapper_result

        logger.info(f"Transform '{transform.name}' tested by {request.user.username}. Execute={execute}")

        return Response(response_data)

    except Exception as e:
        logger.error(f"Transform test failed for '{transform.name}': {str(e)}")

        return Response(
            {"error": "Transform test failed", "details": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated, HasAPIAccess])
def validate_transform(request, pk):
    """Validate a transform configuration"""
    transform = get_object_or_404(Transform, pk=pk)

    serializer = TransformValidationSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    validation_type = serializer.validated_data.get("validation_type", "full")

    validation_results = {"is_valid": True, "errors": [], "warnings": [], "checks": {}}

    try:
        # Check command template
        if not transform.command_template:
            validation_results["errors"].append("Command template is required")
            validation_results["is_valid"] = False
        else:
            # Check for required placeholders
            required_placeholders = ["{input}", "{input_value}", "{target}", "{{input}}"]
            if not any(p in transform.command_template for p in required_placeholders):
                validation_results["warnings"].append(
                    f"Command template should contain one of: {', '.join(required_placeholders)}"
                )

        validation_results["checks"]["command_template"] = {
            "status": "pass" if transform.command_template else "fail",
            "message": "Command template is valid" if transform.command_template else "Command template is missing",
        }

        # Check input/output entity types
        if not transform.input_type:
            validation_results["errors"].append("Input type is required")
            validation_results["is_valid"] = False

        validation_results["checks"]["entity_types"] = {
            "status": "pass" if transform.input_type else "fail",
            "message": "Entity types are configured" if transform.input_type else "Entity types are missing",
        }

        # Check timeout
        if transform.timeout <= 0:
            validation_results["errors"].append("Timeout must be greater than 0")
            validation_results["is_valid"] = False
        elif transform.timeout > 3600:  # 1 hour
            validation_results["warnings"].append("Timeout is very high (>1 hour)")

        validation_results["checks"]["timeout"] = {
            "status": "pass" if transform.timeout > 0 else "fail",
            "message": f"Timeout is set to {transform.timeout} seconds",
        }

        # Check availability (if full validation)
        if validation_type == "full":
            is_available, message = transform.check_availability()
            validation_results["checks"]["availability"] = {
                "status": "pass" if is_available else "fail",
                "message": message,
            }
            if not is_available:
                validation_results["errors"].append(f"Transform is not available: {message}")
                validation_results["is_valid"] = False
            else:
                try:
                    from apps.transforms.wrappers import list_available_tools

                    available_tools = set(list_available_tools())
                    if transform.tool_name not in available_tools and transform.tool_name not in {"custom"}:
                        validation_results["warnings"].append(f"No wrapper registered for tool '{transform.tool_name}'")
                except Exception:
                    pass

        logger.info(
            f"Transform '{transform.name}' validated by {request.user.username}. "
            f"Valid: {validation_results['is_valid']}"
        )

        return Response(
            {
                "transform": TransformDetailSerializer(transform).data,
                "validation": validation_results,
            }
        )

    except Exception as e:
        logger.error(f"Transform validation failed for '{transform.name}': {str(e)}")

        return Response(
            {"error": "Validation failed", "details": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated, HasAPIAccess])
def bulk_transform_actions(request):
    """Perform bulk actions on transforms"""
    serializer = BulkTransformActionSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    transform_ids = serializer.validated_data["transform_ids"]
    action = serializer.validated_data["action"]

    # Verify transforms exist
    transforms = Transform.objects.filter(id__in=transform_ids)
    if len(transforms) != len(transform_ids):
        return Response(
            {"error": "One or more transforms not found"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    results = []

    try:
        if action == "enable":
            updated_count = transforms.update(is_enabled=True)
            message = f"Enabled {updated_count} transforms"

        elif action == "disable":
            updated_count = transforms.update(is_enabled=False)
            message = f"Disabled {updated_count} transforms"

        elif action == "delete":
            deleted_count = transforms.count()
            transforms.delete()
            message = f"Deleted {deleted_count} transforms"

        elif action == "check_availability":
            for transform in transforms:
                try:
                    available, message = transform.check_availability()
                    results.append(
                        {
                            "transform_id": transform.id,
                            "name": transform.name,
                            "available": bool(available),
                            "message": message,
                        }
                    )

                except Exception as e:
                    results.append(
                        {
                            "transform_id": transform.id,
                            "name": transform.name,
                            "available": False,
                            "message": f"Check failed: {str(e)}",
                        }
                    )

            available_count = sum(1 for r in results if r["available"])
            message = f"Checked {len(results)} transforms. {available_count} available."

        elif action == "update_command_templates":
            updated_count = 0

            default_templates = {
                "assetfinder": "assetfinder {input}",
                "amass": "amass enum -d {input} -o /tmp/amass_output.txt && cat /tmp/amass_output.txt",
                "nmap": "nmap -sS -O -A {input}",
                "shodan": "shodan host {input}",
                "whois": "whois {input}",
                "dig": "dig {input} ANY",
                "nslookup": "nslookup {input}",
                "holehe": "holehe --output json --only-used {input}",
            }

            for transform in transforms:
                try:
                    new_template = default_templates.get(transform.tool_name)
                    if not new_template:
                        results.append(
                            {
                                "transform_id": transform.id,
                                "name": transform.name,
                                "updated": False,
                                "message": "No default template for tool",
                            }
                        )
                        continue

                    if transform.command_template != new_template:
                        transform.command_template = new_template
                        transform.save(update_fields=["command_template", "updated_at"])
                        updated_count += 1
                        results.append(
                            {
                                "transform_id": transform.id,
                                "name": transform.name,
                                "updated": True,
                                "new_template": new_template,
                            }
                        )
                    else:
                        results.append(
                            {
                                "transform_id": transform.id,
                                "name": transform.name,
                                "updated": False,
                                "message": "No update needed",
                            }
                        )

                except Exception as e:
                    results.append(
                        {
                            "transform_id": transform.id,
                            "name": transform.name,
                            "updated": False,
                            "message": f"Update failed: {str(e)}",
                        }
                    )

            message = f"Updated {updated_count} command templates"

        else:
            return Response(
                {"error": f"Unknown action: {action}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        logger.info(f"Bulk action '{action}' performed on {len(transform_ids)} transforms by {request.user.username}")

        # Clear caches
        cache.delete("transforms_list")
        cache.delete("transforms_stats")

        response_data = {"message": message, "affected_transforms": len(transform_ids)}

        if results:
            response_data["results"] = results

        return Response(response_data)

    except Exception as e:
        logger.error(f"Bulk action '{action}' failed: {str(e)}")

        return Response(
            {"error": "Bulk action failed", "details": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated, HasAPIAccess])
def import_transforms(request):
    """Import transforms from JSON data"""
    serializer = TransformImportSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    transforms_data = serializer.validated_data["transforms"]
    overwrite = serializer.validated_data.get("overwrite_existing", False)

    results = {"imported": 0, "updated": 0, "skipped": 0, "errors": []}

    for transform_data in transforms_data:
        try:
            name = transform_data.get("name")
            if not name:
                results["errors"].append("Transform name is required")
                continue

            # Check if transform exists
            existing_transform = Transform.objects.filter(name=name).first()

            if existing_transform:
                if overwrite:
                    # Update existing transform
                    for field, value in transform_data.items():
                        if hasattr(existing_transform, field):
                            setattr(existing_transform, field, value)

                    existing_transform.save()
                    results["updated"] += 1

                    logger.info(f"Transform '{name}' updated during import by {request.user.username}")
                else:
                    results["skipped"] += 1
                    continue
            else:
                # Create new transform
                Transform.objects.create(**transform_data)
                results["imported"] += 1

                logger.info(f"Transform '{name}' imported by {request.user.username}")

        except Exception as e:
            error_msg = f"Failed to import transform '{transform_data.get('name', 'unknown')}': {str(e)}"
            results["errors"].append(error_msg)
            logger.error(error_msg)

    # Clear caches
    cache.delete("transforms_list")
    cache.delete("transforms_stats")

    return Response(
        {
            "message": (
                f"Import completed. {results['imported']} imported,"
                f" {results['updated']} updated, {results['skipped']} skipped."
            ),
            "results": results,
        }
    )


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated, HasAPIAccess])
def export_transforms(request):
    """Export transforms to JSON format"""
    transform_ids = request.query_params.get("ids")

    if transform_ids:
        ids = [s.strip() for s in transform_ids.split(",") if s.strip()]
        transforms = Transform.objects.filter(id__in=ids)
    else:
        # Export all transforms
        transforms = Transform.objects.all()

    # Serialize transforms
    export_data = []
    for transform in transforms:
        transform_data = {
            "id": str(transform.id),
            "name": transform.name,
            "display_name": transform.display_name,
            "description": transform.description,
            "category": transform.category,
            "tool_name": transform.tool_name,
            "command_template": transform.command_template,
            "input_type": transform.input_type,
            "output_types": transform.output_types,
            "parameters": transform.parameters,
            "timeout": transform.timeout,
            "is_enabled": transform.is_enabled,
            "requires_api_key": transform.requires_api_key,
            "api_key_name": transform.api_key_name,
            "created_at": transform.created_at.isoformat() if transform.created_at else None,
            "updated_at": transform.updated_at.isoformat() if transform.updated_at else None,
        }
        export_data.append(transform_data)

    logger.info(f"Exported {len(export_data)} transforms by {request.user.username}")

    return Response(
        {
            "transforms": export_data,
            "export_info": {
                "count": len(export_data),
                "exported_at": timezone.now().isoformat(),
                "exported_by": request.user.username,
            },
        }
    )


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated, HasAPIAccess])
def transform_categories(request):
    """Get list of available transform categories"""
    categories = Transform.objects.values_list("category", flat=True).distinct().order_by("category")

    category_stats = []
    for category in categories:
        if category:  # Skip empty categories
            count = Transform.objects.filter(category=category).count()
            enabled_count = Transform.objects.filter(category=category, is_enabled=True).count()

            category_stats.append(
                {
                    "name": category,
                    "total_transforms": count,
                    "enabled_transforms": enabled_count,
                    "disabled_transforms": count - enabled_count,
                }
            )

    return Response({"categories": category_stats, "total_categories": len(category_stats)})


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated, HasAPIAccess])
def transform_usage_stats(request, pk):
    """Get usage statistics for a specific transform"""
    transform = get_object_or_404(Transform, pk=pk)

    # Get execution statistics
    executions = TransformExecution.objects.filter(transform_name=transform.name)

    # Time-based statistics
    now = timezone.now()
    last_24h = executions.filter(created_at__gte=now - timedelta(hours=24))
    last_7d = executions.filter(created_at__gte=now - timedelta(days=7))
    last_30d = executions.filter(created_at__gte=now - timedelta(days=30))

    stats = {
        "transform": TransformDetailSerializer(transform).data,
        "usage": {
            "total_executions": executions.count(),
            "last_24h": last_24h.count(),
            "last_7d": last_7d.count(),
            "last_30d": last_30d.count(),
            "by_status": dict(executions.values("status").annotate(count=Count("id")).values_list("status", "count")),
            "success_rate": (executions.filter(status="completed").count() / max(executions.count(), 1)) * 100,
            "avg_duration": 0,
            "last_execution": executions.order_by("-created_at").first().created_at if executions.exists() else None,
        },
        "users": {
            "unique_users": executions.values("investigation__created_by").distinct().count(),
            "top_users": list(
                executions.values("investigation__created_by__username")
                .annotate(execution_count=Count("id"))
                .order_by("-execution_count")[:5]
            ),
        },
    }

    duration_expr = ExpressionWrapper(F("completed_at") - F("started_at"), output_field=DurationField())
    avg_duration = (
        executions.filter(
            status="completed",
            started_at__isnull=False,
            completed_at__isnull=False,
        )
        .aggregate(avg=Avg(duration_expr))
        .get("avg")
    )
    stats["usage"]["avg_duration"] = avg_duration.total_seconds() if avg_duration else 0

    return Response(stats)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated, HasAPIAccess])
def execute_holehe(request):
    """Execute Holehe transform for email account enumeration"""
    from apps.investigations.models import Investigation, TransformExecution
    from apps.transforms.wrappers.holehe import HoleheWrapper

    # Validate input data
    email = request.data.get("email")
    if not email:
        return Response({"error": "Email is required"}, status=status.HTTP_400_BAD_REQUEST)

    # Validate email format
    import re

    email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if not re.match(email_pattern, email):
        return Response({"error": "Invalid email format"}, status=status.HTTP_400_BAD_REQUEST)

    # Get optional parameters
    investigation_id = request.data.get("investigation_id")
    timeout = request.data.get("timeout", 300)  # Default 5 minutes
    only_used = request.data.get("only_used", True)  # Only show accounts that exist
    execution = None

    try:
        # Get or create investigation if provided
        investigation = None
        if investigation_id:
            investigation = get_object_or_404(Investigation, id=investigation_id, created_by=request.user)

        holehe_transform = Transform.objects.filter(tool_name="holehe", is_enabled=True).first()
        if not holehe_transform:
            return Response(
                {"error": "Holehe transform not found. Please ensure it is properly configured."},
                status=status.HTTP_404_NOT_FOUND,
            )

        is_available, availability_message = holehe_transform.check_availability()
        if not is_available:
            return Response(
                {"error": "Holehe is not available", "details": availability_message},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Create execution record if investigation is provided
        if investigation:
            from apps.entities.models import Entity

            input_entity, _ = Entity.objects.get_or_create(
                investigation=investigation, entity_type="email", value=email
            )
            execution = TransformExecution.objects.create(
                investigation=investigation,
                transform_name=holehe_transform.name,
                input_entity=input_entity,
                status="pending",
                parameters={"only_used": only_used},
            )
            execution.start_execution()

        # Execute Holehe
        wrapper = HoleheWrapper()

        # Prepare input data in the format expected by the wrapper
        input_data = {"type": "email", "value": email}

        # Execute the transform with additional parameters
        result = wrapper.execute(input_data, timeout=timeout, only_used=only_used)

        # Update execution record if created
        if execution:
            execution.complete_execution(results={"wrapper_output": result})

        # Get results from wrapper output
        results = result.get("results", [])
        metadata = result.get("metadata", {})

        logger.info(
            f"Holehe executed for email '{email}' by {request.user.username}. " f"Found {len(results)} accounts."
        )

        response_data = {
            "success": True,
            "email": email,
            "tool": result.get("tool"),
            "input_type": result.get("input_type"),
            "input_value": result.get("input_value"),
            "results": results,
            "metadata": metadata,
            "accounts_found": metadata.get("accounts_found", len(results)),
            "execution_time": metadata.get("execution_time", 0) or 0,
            "total_platforms_checked": metadata.get("total_platforms_checked", 0) or 0,
        }

        if execution:
            response_data["execution_id"] = execution.id

        return Response(response_data)

    except Exception as e:
        logger.error(f"Holehe execution failed for email '{email}': {str(e)}")

        # Update execution record if created
        if execution:
            execution.fail_execution(str(e))

        return Response(
            {"error": "Holehe execution failed", "details": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
