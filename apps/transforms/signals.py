import json
import logging

from django.core.cache import cache
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.utils import timezone

from .models import Transform

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Transform)
def transform_post_save(sender, instance, created, **kwargs):
    """
    Handle post-save operations for Transform model
    """
    try:
        # Clear transform cache when a transform is modified
        cache_key = f"transform_{instance.name}"
        cache.delete(cache_key)

        # Clear category cache
        category_cache_key = f"transforms_category_{instance.category}"
        cache.delete(category_cache_key)

        # Clear all transforms cache
        cache.delete("all_transforms")
        cache.delete("enabled_transforms")

        if created:
            logger.info(
                f"New transform created: {instance.name} "
                f"(Category: {instance.category}, Tool: {instance.tool_name})"
            )

            # Validate the new transform
            _validate_transform_configuration(instance)

            # Check tool availability
            is_available, message = instance.check_availability()
            if not is_available:
                logger.warning(
                    f"Transform '{instance.name}' tool '{instance.tool_name}' "
                    f"is not available: {message}"
                )
        else:
            logger.info(f"Transform updated: {instance.name}")

            # Re-validate configuration after update
            _validate_transform_configuration(instance)

        # Update transform metadata
        _update_transform_metadata(instance)

    except Exception as e:
        logger.error(
            f"Error in transform post_save signal for {instance.name}: {str(e)}"
        )


@receiver(pre_delete, sender=Transform)
def transform_pre_delete(sender, instance, **kwargs):
    """
    Handle pre-delete operations for Transform model
    """
    try:
        # Check if transform has active executions
        from apps.investigations.models import TransformExecution

        active_executions = TransformExecution.objects.filter(
            transform_name=instance.name, status__in=["pending", "running"]
        ).count()

        if active_executions > 0:
            logger.warning(
                f"Deleting transform '{instance.name}' with {active_executions} "
                f"active executions"
            )

        # Clear caches
        cache_key = f"transform_{instance.name}"
        cache.delete(cache_key)

        category_cache_key = f"transforms_category_{instance.category}"
        cache.delete(category_cache_key)

        cache.delete("all_transforms")
        cache.delete("enabled_transforms")

        logger.info(
            f"Transform deleted: {instance.name} "
            f"(Category: {instance.category}, Tool: {instance.tool_name})"
        )

    except Exception as e:
        logger.error(
            f"Error in transform pre_delete signal for {instance.name}: {str(e)}"
        )


def _validate_transform_configuration(transform):
    """
    Validate transform configuration
    """
    try:
        # Validate command template
        if not transform.command_template:
            logger.error(f"Transform '{transform.name}' has empty command template")
            return False

        if not any(placeholder in transform.command_template
                   for placeholder in ["{input_value}", "{target}", "{input}", "{{input}}"]):
            logger.warning(
                f"Transform '{transform.name}' command template missing input placeholder"
                f" ({{input_value}} or {{target}})"
            )

        # Validate parameters JSON
        if transform.parameters and isinstance(transform.parameters, str):
            try:
                json.loads(transform.parameters)
            except json.JSONDecodeError as e:
                logger.error(
                    f"Transform '{transform.name}' has invalid JSON parameters: {str(e)}"
                )
                return False

        # Validate timeout
        if transform.timeout and transform.timeout <= 0:
            logger.error(
                f"Transform '{transform.name}' has invalid timeout: {transform.timeout}"
            )
            return False

        # Validate input/output types
        valid_types = [
            "domain",
            "ip",
            "url",
            "email",
            "phone",
            "person",
            "organization",
            "location",
            "hash",
            "file",
            "text",
            "username",
            "social_media",
            "cryptocurrency",
            "technology",
            "vulnerability",
            "port",
            "service",
            "os",
            "subdomain",
            "account",
            "other",
            "mixed",
            "any"
        ]

        if transform.input_type not in valid_types:
            logger.warning(
                f"Transform '{transform.name}' has unknown input type: {transform.input_type}"
            )

        if hasattr(transform, 'output_types') and isinstance(transform.output_types, list):
            for output_type in transform.output_types:
                if output_type not in valid_types:
                    logger.warning(
                        f"Transform '{transform.name}' has unknown output type: {output_type}"
                    )
        elif hasattr(transform, 'output_type'):  # Legacy check
            if transform.output_type not in valid_types:
                logger.warning(
                    f"Transform '{transform.name}' has unknown output type: {transform.output_type}"
                )

        logger.debug(
            f"Transform '{transform.name}' configuration validated successfully"
        )
        return True

    except Exception as e:
        logger.error(
            f"Error validating transform '{transform.name}' configuration: {str(e)}"
        )
        return False


def _update_transform_metadata(transform):
    """
    Update transform metadata and statistics
    """
    try:
        # Update last_modified timestamp
        transform.updated_at = timezone.now()

        # Calculate usage statistics
        from apps.investigations.models import TransformExecution

        total_executions = TransformExecution.objects.filter(
            transform_name=transform.name
        ).count()

        successful_executions = TransformExecution.objects.filter(
            transform_name=transform.name, status="completed"
        ).count()

        failed_executions = TransformExecution.objects.filter(
            transform_name=transform.name, status="failed"
        ).count()

        # Calculate success rate
        success_rate = (
            (successful_executions / total_executions * 100)
            if total_executions > 0
            else 0
        )

        # Store metadata in cache for quick access
        metadata = {
            "total_executions": total_executions,
            "successful_executions": successful_executions,
            "failed_executions": failed_executions,
            "success_rate": success_rate,
            "last_updated": timezone.now().isoformat(),
        }

        cache_key = f"transform_metadata_{transform.name}"
        cache.set(cache_key, metadata, timeout=3600)  # Cache for 1 hour

        logger.debug(
            f"Updated metadata for transform '{transform.name}': "
            f"{total_executions} total, {success_rate:.1f}% success rate"
        )

    except Exception as e:
        logger.error(
            f"Error updating metadata for transform '{transform.name}': {str(e)}"
        )


def get_transform_statistics():
    """
    Get comprehensive transform statistics
    """
    try:
        from django.db.models import Count, Q

        from apps.investigations.models import TransformExecution

        # Overall statistics
        total_transforms = Transform.objects.count()
        enabled_transforms = Transform.objects.filter(is_enabled=True).count()

        # Execution statistics
        total_executions = TransformExecution.objects.count()

        execution_stats = TransformExecution.objects.aggregate(
            completed=Count("id", filter=Q(status="completed")),
            failed=Count("id", filter=Q(status="failed")),
            running=Count("id", filter=Q(status="running")),
            pending=Count("id", filter=Q(status="pending")),
        )

        # Category statistics
        category_stats = (
            Transform.objects.values("category")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        # Tool statistics
        tool_stats = (
            Transform.objects.values("tool_name")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        # Most used transforms
        popular_transforms = (
            TransformExecution.objects.values("transform_name")
            .annotate(usage_count=Count("id"))
            .order_by("-usage_count")[:10]
        )

        statistics = {
            "total_transforms": total_transforms,
            "enabled_transforms": enabled_transforms,
            "total_executions": total_executions,
            "execution_stats": execution_stats,
            "category_stats": list(category_stats),
            "tool_stats": list(tool_stats),
            "popular_transforms": list(popular_transforms),
            "success_rate": (
                (execution_stats["completed"] / total_executions * 100)
                if total_executions > 0
                else 0
            ),
        }

        # Cache statistics
        cache.set("transform_statistics", statistics, timeout=1800)  # 30 minutes

        return statistics

    except Exception as e:
        logger.error(f"Error getting transform statistics: {str(e)}")
        return {}


def refresh_transform_cache():
    """
    Refresh all transform-related caches
    """
    try:
        # Clear all transform caches
        cache.delete_many(
            ["all_transforms", "enabled_transforms", "transform_statistics"]
        )

        # Clear individual transform caches
        for transform in Transform.objects.all():
            cache.delete(f"transform_{transform.name}")
            cache.delete(f"transform_metadata_{transform.name}")

        # Clear category caches
        categories = Transform.objects.values_list("category", flat=True).distinct()
        for category in categories:
            cache.delete(f"transforms_category_{category}")

        logger.info("Transform cache refreshed successfully")

    except Exception as e:
        logger.error(f"Error refreshing transform cache: {str(e)}")


def check_all_transforms_availability():
    """
    Check availability of all transforms and update their status
    """
    try:
        results = []

        for transform in Transform.objects.filter(is_enabled=True):
            is_available, message = transform.check_availability()

            results.append(
                {
                    "name": transform.name,
                    "tool_name": transform.tool_name,
                    "available": is_available,
                    "message": message,
                }
            )

            if not is_available:
                logger.warning(
                    f"Transform '{transform.name}' tool '{transform.tool_name}' "
                    f"is not available: {message}"
                )

        # Cache results
        cache.set("transform_availability_check", results, timeout=3600)

        logger.info(f"Checked availability of {len(results)} transforms")
        return results

    except Exception as e:
        logger.error(f"Error checking transform availability: {str(e)}")
        return []
