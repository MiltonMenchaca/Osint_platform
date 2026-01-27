import json
import logging
from datetime import timedelta

from django.core.cache import cache
from django.db.models import Avg, Count, Max, Min, Q
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
        queryset = Transform.objects.all()

        # Search functionality
        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(description__icontains=search)
                | Q(category__icontains=search)
                | Q(author__icontains=search)
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
            queryset = queryset.filter(is_available=is_available)

        # Filter by input entity types
        input_types = self.request.query_params.get("input_types")
        if input_types:
            input_type_list = [t.strip() for t in input_types.split(",")]
            for input_type in input_type_list:
                queryset = queryset.filter(input_entity_types__contains=[input_type])

        # Filter by output entity types
        output_types = self.request.query_params.get("output_types")
        if output_types:
            output_type_list = [t.strip() for t in output_types.split(",")]
            for output_type in output_type_list:
                queryset = queryset.filter(output_entity_types__contains=[output_type])

        # Filter by author
        author = self.request.query_params.get("author")
        if author:
            queryset = queryset.filter(author__icontains=author)

        # Filter by timeout range
        min_timeout = self.request.query_params.get("min_timeout")
        max_timeout = self.request.query_params.get("max_timeout")

        if min_timeout:
            try:
                min_time = int(min_timeout)
                queryset = queryset.filter(timeout_seconds__gte=min_time)
            except ValueError:
                pass

        if max_timeout:
            try:
                max_time = int(max_timeout)
                queryset = queryset.filter(timeout_seconds__lte=max_time)
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
            "author",
            "-author",
            "timeout_seconds",
            "-timeout_seconds",
            "created_at",
            "-created_at",
            "updated_at",
            "-updated_at",
            "usage_count",
            "-usage_count",
        ]

        if ordering in valid_orderings:
            queryset = queryset.order_by(ordering)
        else:
            queryset = queryset.order_by("-created_at")

        return queryset

    def perform_create(self, serializer):
        """Log transform creation"""
        transform = serializer.save()

        logger.info(
            f"Transform '{transform.name}' created by {self.request.user.username}"
        )

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

        logger.info(
            f"Transform '{transform.name}' updated by {self.request.user.username}"
        )

        # Clear caches
        cache.delete(f"transform_{transform.id}")
        cache.delete("transforms_list")
        cache.delete("transforms_stats")

    def perform_destroy(self, instance):
        """Log transform deletion"""
        logger.info(
            f"Transform '{instance.name}' deleted by {self.request.user.username}"
        )

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

    stats = {
        "transforms": {
            "total": transforms.count(),
            "enabled": transforms.filter(is_enabled=True).count(),
            "disabled": transforms.filter(is_enabled=False).count(),
            "available": transforms.filter(is_available=True).count(),
            "unavailable": transforms.filter(is_available=False).count(),
            "by_category": dict(
                transforms.values("category")
                .annotate(count=Count("id"))
                .values_list("category", "count")
            ),
            "timeout_stats": transforms.aggregate(
                avg_timeout=Avg("timeout_seconds"),
                max_timeout=Max("timeout_seconds"),
                min_timeout=Min("timeout_seconds"),
            ),
            "recent": transforms.filter(
                created_at__gte=timezone.now() - timedelta(days=7)
            ).count(),
        },
        "executions": {
            "total": executions.count(),
            "successful": executions.filter(status="completed").count(),
            "failed": executions.filter(status="failed").count(),
            "running": executions.filter(status="running").count(),
            "pending": executions.filter(status="pending").count(),
            "by_status": dict(
                executions.values("status")
                .annotate(count=Count("id"))
                .values_list("status", "count")
            ),
            "recent": executions.filter(
                created_at__gte=timezone.now() - timedelta(days=7)
            ).count(),
            "avg_duration": executions.filter(
                status="completed", ended_at__isnull=False
            )
            .extra(select={"duration": "EXTRACT(EPOCH FROM (ended_at - started_at))"})
            .aggregate(avg_duration=Avg("duration"))["avg_duration"]
            or 0,
        },
        "usage": {
            "most_used_transforms": list(
                transforms.annotate(execution_count=Count("transformexecution"))
                .order_by("-execution_count")[:10]
                .values("id", "name", "category", "execution_count")
            ),
            "success_rates": list(
                transforms.annotate(
                    total_executions=Count("transformexecution"),
                    successful_executions=Count(
                        "transformexecution",
                        filter=Q(transformexecution__status="completed"),
                    ),
                )
                .filter(total_executions__gt=0)
                .extra(
                    select={
                        "success_rate": (
                            "CASE WHEN total_executions > 0 THEN "
                            "(successful_executions::float / total_executions::float) * 100 "
                            "ELSE 0 END"
                        )
                    }
                )
                .order_by("-success_rate")[:10]
                .values(
                    "id",
                    "name",
                    "total_executions",
                    "successful_executions",
                    "success_rate",
                )
            ),
        },
    }

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

    # Validate input against transform's input schema
    if transform.input_schema:
        try:
            import jsonschema

            jsonschema.validate(test_input, transform.input_schema)
        except jsonschema.ValidationError as e:
            return Response(
                {"error": "Input validation failed", "details": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                {"error": "Schema validation error", "details": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    # Check if transform is available
    if not transform.is_available:
        return Response(
            {
                "error": "Transform is not available",
                "details": "Transform dependencies may not be installed",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Check if transform is enabled
    if not transform.is_enabled:
        return Response(
            {
                "error": "Transform is disabled",
                "details": "Transform has been disabled by administrator",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        # Import and execute transform wrapper
        from apps.osint_tools.wrappers import get_transform_wrapper

        wrapper = get_transform_wrapper(transform.name)
        if not wrapper:
            return Response(
                {
                    "error": "Transform wrapper not found",
                    "details": f"No wrapper found for transform {transform.name}",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Execute test
        result = wrapper.execute(test_input, dry_run=True)

        # Validate output against transform's output schema
        if transform.output_schema and result.get("data"):
            try:
                import jsonschema

                jsonschema.validate(result["data"], transform.output_schema)
            except jsonschema.ValidationError as e:
                logger.warning(
                    f"Transform {transform.name} output validation failed: {e}"
                )
                result["warnings"] = result.get("warnings", []) + [
                    f"Output validation warning: {str(e)}"
                ]

        logger.info(
            f"Transform '{transform.name}' tested successfully by {request.user.username}"
        )

        return Response(
            {
                "success": True,
                "transform": TransformDetailSerializer(transform).data,
                "test_result": result,
                "execution_time": result.get("execution_time", 0),
            }
        )

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
            required_placeholders = ["{{input}}"]
            for placeholder in required_placeholders:
                if placeholder not in transform.command_template:
                    validation_results["warnings"].append(
                        f"Missing recommended placeholder: {placeholder}"
                    )

        validation_results["checks"]["command_template"] = {
            "status": "pass" if transform.command_template else "fail",
            "message": "Command template is valid"
            if transform.command_template
            else "Command template is missing",
        }

        # Check input/output entity types
        if not transform.input_entity_types:
            validation_results["errors"].append("Input entity types are required")
            validation_results["is_valid"] = False

        if not transform.output_entity_types:
            validation_results["errors"].append("Output entity types are required")
            validation_results["is_valid"] = False

        validation_results["checks"]["entity_types"] = {
            "status": "pass"
            if (transform.input_entity_types and transform.output_entity_types)
            else "fail",
            "message": "Entity types are configured"
            if (transform.input_entity_types and transform.output_entity_types)
            else "Entity types are missing",
        }

        # Check schemas if provided
        if transform.input_schema:
            try:
                import jsonschema

                jsonschema.Draft7Validator.check_schema(transform.input_schema)
                validation_results["checks"]["input_schema"] = {
                    "status": "pass",
                    "message": "Input schema is valid JSON Schema",
                }
            except Exception as e:
                validation_results["errors"].append(f"Invalid input schema: {str(e)}")
                validation_results["is_valid"] = False
                validation_results["checks"]["input_schema"] = {
                    "status": "fail",
                    "message": f"Input schema validation failed: {str(e)}",
                }

        if transform.output_schema:
            try:
                import jsonschema

                jsonschema.Draft7Validator.check_schema(transform.output_schema)
                validation_results["checks"]["output_schema"] = {
                    "status": "pass",
                    "message": "Output schema is valid JSON Schema",
                }
            except Exception as e:
                validation_results["errors"].append(f"Invalid output schema: {str(e)}")
                validation_results["is_valid"] = False
                validation_results["checks"]["output_schema"] = {
                    "status": "fail",
                    "message": f"Output schema validation failed: {str(e)}",
                }

        # Check configuration
        if transform.configuration:
            try:
                if isinstance(transform.configuration, str):
                    json.loads(transform.configuration)
                validation_results["checks"]["configuration"] = {
                    "status": "pass",
                    "message": "Configuration is valid JSON",
                }
            except json.JSONDecodeError as e:
                validation_results["errors"].append(
                    f"Invalid configuration JSON: {str(e)}"
                )
                validation_results["is_valid"] = False
                validation_results["checks"]["configuration"] = {
                    "status": "fail",
                    "message": f"Configuration JSON validation failed: {str(e)}",
                }

        # Check timeout
        if transform.timeout_seconds <= 0:
            validation_results["errors"].append("Timeout must be greater than 0")
            validation_results["is_valid"] = False
        elif transform.timeout_seconds > 3600:  # 1 hour
            validation_results["warnings"].append("Timeout is very high (>1 hour)")

        validation_results["checks"]["timeout"] = {
            "status": "pass" if transform.timeout_seconds > 0 else "fail",
            "message": f"Timeout is set to {transform.timeout_seconds} seconds",
        }

        # Check availability (if full validation)
        if validation_type == "full":
            try:
                from apps.osint_tools.wrappers import get_transform_wrapper

                wrapper = get_transform_wrapper(transform.name)

                if wrapper:
                    availability_check = wrapper.check_availability()
                    validation_results["checks"]["availability"] = {
                        "status": "pass" if availability_check["available"] else "fail",
                        "message": availability_check.get(
                            "message", "Availability check completed"
                        ),
                    }

                    if not availability_check["available"]:
                        validation_results["errors"].append(
                            f"Transform is not available: {availability_check.get('message', 'Unknown reason')}"
                        )
                        validation_results["is_valid"] = False
                else:
                    validation_results["errors"].append("Transform wrapper not found")
                    validation_results["is_valid"] = False
                    validation_results["checks"]["availability"] = {
                        "status": "fail",
                        "message": "Transform wrapper not found",
                    }

            except Exception as e:
                validation_results["warnings"].append(
                    f"Could not check availability: {str(e)}"
                )
                validation_results["checks"]["availability"] = {
                    "status": "warning",
                    "message": f"Availability check failed: {str(e)}",
                }

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
            from apps.osint_tools.wrappers import get_transform_wrapper

            for transform in transforms:
                try:
                    wrapper = get_transform_wrapper(transform.name)
                    if wrapper:
                        availability = wrapper.check_availability()
                        transform.is_available = availability["available"]
                        transform.save()

                        results.append(
                            {
                                "transform_id": transform.id,
                                "name": transform.name,
                                "available": availability["available"],
                                "message": availability.get("message", ""),
                            }
                        )
                    else:
                        transform.is_available = False
                        transform.save()

                        results.append(
                            {
                                "transform_id": transform.id,
                                "name": transform.name,
                                "available": False,
                                "message": "Wrapper not found",
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
            # This would update command templates based on current wrapper configurations
            updated_count = 0

            for transform in transforms:
                try:
                    from apps.osint_tools.wrappers import get_transform_wrapper

                    wrapper = get_transform_wrapper(transform.name)

                    if wrapper and hasattr(wrapper, "get_default_command_template"):
                        new_template = wrapper.get_default_command_template()
                        if new_template and new_template != transform.command_template:
                            transform.command_template = new_template
                            transform.save()
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
                    else:
                        results.append(
                            {
                                "transform_id": transform.id,
                                "name": transform.name,
                                "updated": False,
                                "message": "Wrapper not found or no template method",
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

        logger.info(
            f"Bulk action '{action}' performed on {len(transform_ids)} transforms by {request.user.username}"
        )

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
    overwrite = serializer.validated_data.get("overwrite", False)

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

                    logger.info(
                        f"Transform '{name}' updated during import by {request.user.username}"
                    )
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
            "message": f"Import completed. {results['imported']} imported, {results['updated']} updated, {results['skipped']} skipped.",
            "results": results,
        }
    )


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated, HasAPIAccess])
def export_transforms(request):
    """Export transforms to JSON format"""
    transform_ids = request.query_params.get("ids")

    if transform_ids:
        # Export specific transforms
        ids = [
            int(id.strip()) for id in transform_ids.split(",") if id.strip().isdigit()
        ]
        transforms = Transform.objects.filter(id__in=ids)
    else:
        # Export all transforms
        transforms = Transform.objects.all()

    # Serialize transforms
    export_data = []
    for transform in transforms:
        transform_data = {
            "name": transform.name,
            "description": transform.description,
            "category": transform.category,
            "author": transform.author,
            "version": transform.version,
            "command_template": transform.command_template,
            "input_entity_types": transform.input_entity_types,
            "output_entity_types": transform.output_entity_types,
            "input_schema": transform.input_schema,
            "output_schema": transform.output_schema,
            "configuration": transform.configuration,
            "timeout_seconds": transform.timeout_seconds,
            "is_enabled": transform.is_enabled,
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
    categories = (
        Transform.objects.values_list("category", flat=True)
        .distinct()
        .order_by("category")
    )

    category_stats = []
    for category in categories:
        if category:  # Skip empty categories
            count = Transform.objects.filter(category=category).count()
            enabled_count = Transform.objects.filter(
                category=category, is_enabled=True
            ).count()

            category_stats.append(
                {
                    "name": category,
                    "total_transforms": count,
                    "enabled_transforms": enabled_count,
                    "disabled_transforms": count - enabled_count,
                }
            )

    return Response(
        {"categories": category_stats, "total_categories": len(category_stats)}
    )


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated, HasAPIAccess])
def transform_usage_stats(request, pk):
    """Get usage statistics for a specific transform"""
    transform = get_object_or_404(Transform, pk=pk)

    # Get execution statistics
    executions = TransformExecution.objects.filter(transform=transform)

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
            "by_status": dict(
                executions.values("status")
                .annotate(count=Count("id"))
                .values_list("status", "count")
            ),
            "success_rate": (
                executions.filter(status="completed").count()
                / max(executions.count(), 1)
            )
            * 100,
            "avg_duration": executions.filter(
                status="completed", ended_at__isnull=False
            )
            .extra(select={"duration": "EXTRACT(EPOCH FROM (ended_at - started_at))"})
            .aggregate(avg_duration=Avg("duration"))["avg_duration"]
            or 0,
            "last_execution": executions.order_by("-created_at").first().created_at
            if executions.exists()
            else None,
        },
        "users": {
            "unique_users": executions.values("investigation__created_by")
            .distinct()
            .count(),
            "top_users": list(
                executions.values("investigation__created_by__username")
                .annotate(execution_count=Count("id"))
                .order_by("-execution_count")[:5]
            ),
        },
    }

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
        return Response(
            {"error": "Email is required"}, status=status.HTTP_400_BAD_REQUEST
        )

    # Validate email format
    import re

    email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if not re.match(email_pattern, email):
        return Response(
            {"error": "Invalid email format"}, status=status.HTTP_400_BAD_REQUEST
        )

    # Get optional parameters
    investigation_id = request.data.get("investigation_id")
    timeout = request.data.get("timeout", 300)  # Default 5 minutes
    only_used = request.data.get("only_used", True)  # Only show accounts that exist

    try:
        # Get or create investigation if provided
        investigation = None
        if investigation_id:
            investigation = get_object_or_404(
                Investigation, id=investigation_id, created_by=request.user
            )

        # Get Holehe transform
        holehe_transform = Transform.objects.filter(name="holehe").first()
        if not holehe_transform:
            return Response(
                {
                    "error": "Holehe transform not found. Please ensure it is properly configured."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # Check if transform is enabled and available
        if not holehe_transform.is_enabled:
            return Response(
                {"error": "Holehe transform is disabled"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not holehe_transform.is_available:
            return Response(
                {"error": "Holehe is not available. Please check if it is installed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Create execution record if investigation is provided
        execution = None
        if investigation:
            execution = TransformExecution.objects.create(
                investigation=investigation,
                transform=holehe_transform,
                input_data={"email": email, "only_used": only_used},
                created_by=request.user,
                status="running",
            )

        # Execute Holehe
        wrapper = HoleheWrapper()

        # Prepare input data in the format expected by the wrapper
        input_data = {"type": "email", "value": email}

        # Execute the transform with additional parameters
        result = wrapper.execute(input_data, timeout=timeout, only_used=only_used)

        # Update execution record if created
        if execution:
            if result.get("success", False):
                execution.status = "completed"
                execution.output_data = result
                execution.completed_at = timezone.now()
            else:
                execution.status = "failed"
                execution.error_message = result.get("error", "Unknown error")
                execution.completed_at = timezone.now()

            execution.save()

        # Get results from wrapper output
        results = result.get("results", [])
        execution_info = result.get("execution_info", {})

        logger.info(
            f"Holehe executed for email '{email}' by {request.user.username}. "
            f"Found {len(results)} accounts."
        )

        response_data = {
            "success": result.get("success", False),
            "email": email,
            "accounts_found": len(results),
            "execution_time": execution_info.get("execution_time", 0),
            "total_platforms_checked": execution_info.get("total_platforms_checked", 0),
            "results": results,
            "execution_info": execution_info,
        }

        if execution:
            response_data["execution_id"] = execution.id

        return Response(response_data)

    except Exception as e:
        logger.error(f"Holehe execution failed for email '{email}': {str(e)}")

        # Update execution record if created
        if execution:
            execution.status = "failed"
            execution.error_message = str(e)
            execution.completed_at = timezone.now()
            execution.save()

        return Response(
            {"error": "Holehe execution failed", "details": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
