import logging

from django.conf import settings
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.utils import timezone

from apps.entities.models import Entity

from .models import Investigation, TransformExecution

logger = logging.getLogger("investigations")


@receiver(post_save, sender=Investigation)
def investigation_post_save(sender, instance, created, **kwargs):
    """
    Handle post-save actions for Investigation model
    """
    if created:
        logger.info(f"New investigation created: {instance.name} (ID: {instance.id}) by {instance.created_by.username}")

        # Update investigation metadata
        if not instance.metadata:
            instance.metadata = {}

        instance.metadata.update(
            {
                "created_timestamp": timezone.now().isoformat(),
                "initial_status": instance.status,
                "version": "1.0",
            }
        )

        # Save without triggering signals again
        Investigation.objects.filter(id=instance.id).update(metadata=instance.metadata)
    else:
        # Log status changes
        if hasattr(instance, "_original_status") and instance._original_status != instance.status:
            logger.info(
                f"Investigation {instance.name} status changed from "
                f"{instance._original_status} to {instance.status}"
            )

            # Update metadata with status change
            if not instance.metadata:
                instance.metadata = {}

            status_history = instance.metadata.get("status_history", [])
            status_history.append(
                {
                    "from_status": instance._original_status,
                    "to_status": instance.status,
                    "timestamp": timezone.now().isoformat(),
                    "changed_by": getattr(instance, "_changed_by", "system"),
                }
            )

            instance.metadata["status_history"] = status_history
            instance.metadata["last_status_change"] = timezone.now().isoformat()

            # Save without triggering signals again
            Investigation.objects.filter(id=instance.id).update(metadata=instance.metadata)


@receiver(pre_delete, sender=Investigation)
def investigation_pre_delete(sender, instance, **kwargs):
    """
    Handle pre-delete actions for Investigation model
    """
    logger.warning(f"Investigation being deleted: {instance.name} (ID: {instance.id})")

    # Cancel any running transform executions
    running_executions = TransformExecution.objects.filter(investigation=instance, status="running")

    for execution in running_executions:
        try:
            if execution.celery_task_id:
                from celery import current_app

                current_app.control.revoke(execution.celery_task_id, terminate=True)
                logger.info(f"Cancelled Celery task {execution.celery_task_id} for deleted investigation")
        except Exception as e:
            logger.error(f"Failed to cancel Celery task {execution.celery_task_id}: {str(e)}")


@receiver(post_save, sender=TransformExecution)
def transform_execution_post_save(sender, instance, created, **kwargs):
    """
    Handle post-save actions for TransformExecution model
    """
    if created:
        logger.info(
            f"New transform execution created: {instance.transform_name} "
            f"on {instance.input_entity.value} (ID: {instance.id})"
        )

        # Update investigation's last activity
        Investigation.objects.filter(id=instance.investigation.id).update(updated_at=timezone.now())
    else:
        # Log status changes
        if hasattr(instance, "_original_status") and instance._original_status != instance.status:
            logger.info(
                f"Transform execution {instance.id} status changed from "
                f"{instance._original_status} to {instance.status}"
            )

            # Update investigation's last activity
            Investigation.objects.filter(id=instance.investigation.id).update(updated_at=timezone.now())

            # If execution completed successfully, check if investigation should be updated
            if instance.status == "completed":
                _check_investigation_completion(instance.investigation)
            elif instance.status == "failed":
                _handle_execution_failure(instance)


def _check_investigation_completion(investigation):
    """
    Check if investigation should be marked as completed based on execution status
    """
    try:
        # Get execution statistics
        executions = TransformExecution.objects.filter(investigation=investigation)
        total_executions = executions.count()

        if total_executions == 0:
            return

        completed_executions = executions.filter(status="completed").count()
        failed_executions = executions.filter(status="failed").count()
        running_executions = executions.filter(status__in=["pending", "running"]).count()

        # Update investigation metadata with execution stats
        if not investigation.metadata:
            investigation.metadata = {}

        investigation.metadata.update(
            {
                "execution_stats": {
                    "total": total_executions,
                    "completed": completed_executions,
                    "failed": failed_executions,
                    "running": running_executions,
                    "last_updated": timezone.now().isoformat(),
                }
            }
        )

        # Auto-complete investigation if all executions are done and investigation is active
        if running_executions == 0 and investigation.status == "active" and total_executions > 0:
            if failed_executions == 0:
                # All executions completed successfully
                investigation.status = "completed"
                logger.info(f"Investigation {investigation.name} auto-completed - all executions successful")
            elif completed_executions > 0:
                # Some executions completed, some failed
                investigation.status = "completed"
                logger.info(f"Investigation {investigation.name} completed with {failed_executions} failed executions")

        investigation.save()

    except Exception as e:
        logger.error(f"Error checking investigation completion: {str(e)}")


def _handle_execution_failure(execution):
    """
    Handle failed transform execution
    """
    try:
        investigation = execution.investigation

        # Count failed executions
        failed_count = TransformExecution.objects.filter(investigation=investigation, status="failed").count()

        # If too many failures, consider pausing the investigation
        max_failures = getattr(settings, "OSINT_MAX_EXECUTION_FAILURES", 10)

        if failed_count >= max_failures and investigation.status == "active":
            investigation.status = "paused"

            if not investigation.metadata:
                investigation.metadata = {}

            investigation.metadata["auto_paused"] = {
                "reason": "too_many_failures",
                "failed_count": failed_count,
                "timestamp": timezone.now().isoformat(),
            }

            investigation.save()

            logger.warning(
                f"Investigation {investigation.name} auto-paused due to " f"{failed_count} failed executions"
            )

    except Exception as e:
        logger.error(f"Error handling execution failure: {str(e)}")


@receiver(post_save, sender=Entity)
def entity_post_save(sender, instance, created, **kwargs):
    """
    Handle post-save actions for Entity model
    """
    if created:
        logger.info(
            f"New entity created: {instance.entity_type}:{instance.value} "
            f"in investigation {instance.investigation.name}"
        )

        # Update investigation's last activity
        Investigation.objects.filter(id=instance.investigation.id).update(updated_at=timezone.now())

        # Update investigation metadata with entity count
        investigation = instance.investigation
        entity_count = Entity.objects.filter(investigation=investigation).count()

        if not investigation.metadata:
            investigation.metadata = {}

        investigation.metadata["entity_count"] = entity_count
        investigation.metadata["last_entity_added"] = timezone.now().isoformat()

        Investigation.objects.filter(id=investigation.id).update(metadata=investigation.metadata)
