from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from .models import Investigation, TransformExecution


@admin.register(Investigation)
class InvestigationAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "status",
        "entities_count",
        "created_at",
        "updated_at"
        # Temporarily commented out fields that don't exist yet
        # 'user', 'priority'
    ]
    list_filter = ["status", "created_at"]
    # Temporarily commented out fields that don't exist yet
    # 'priority', 'user'
    search_fields = ["name", "description"]
    # Temporarily commented out: 'user__username'
    readonly_fields = ["id", "created_at", "updated_at", "entities_count"]

    fieldsets = (
        (
            "Basic Information",
            {
                "fields": ("id", "name", "description")
                # Temporarily commented out: 'user'
            },
        ),
        (
            "Status & Priority",
            {
                "fields": ("status",)
                # Temporarily commented out: 'priority'
            },
        ),
        ("Metadata", {"fields": ("tags", "metadata")}),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def entities_count(self, obj):
        """Display count of entities in this investigation"""
        count = obj.entities.count()
        if count > 0:
            url = reverse("admin:entities_entity_changelist")
            return format_html(
                '<a href="{}?investigation__id__exact={}">{} entities</a>',
                url,
                obj.id,
                count,
            )
        return "0 entities"

    entities_count.short_description = "Entities"

    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        return super().get_queryset(request)
        # Temporarily commented out: .select_related('user')


@admin.register(TransformExecution)
class TransformExecutionAdmin(admin.ModelAdmin):
    list_display = [
        "investigation",
        "transform_name",
        "input_entity_value",
        "status",
        "created_at",
        "execution_time",
        "celery_task_link",
    ]
    list_filter = ["status", "transform_name", "created_at", "investigation__status"]
    search_fields = [
        "investigation__name",
        "transform_name",
        "input_entity__value",
        "celery_task_id",
    ]
    readonly_fields = [
        "id",
        "celery_task_id",
        "started_at",
        "completed_at",
        "created_at",
        "updated_at",
        "execution_time",
    ]

    fieldsets = (
        (
            "Execution Info",
            {
                "fields": (
                    "id",
                    "investigation",
                    "transform_name",
                    "input_entity",
                    "parameters",
                )
            },
        ),
        (
            "Status & Timing",
            {"fields": ("status", "started_at", "completed_at", "execution_time")},
        ),
        ("Celery Task", {"fields": ("celery_task_id",), "classes": ("collapse",)}),
        ("Results", {"fields": ("results", "error_message"), "classes": ("collapse",)}),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def input_entity_value(self, obj):
        """Display input entity value"""
        if obj.input_entity:
            return f"{obj.input_entity.entity_type}: {obj.input_entity.value}"
        return "-"

    input_entity_value.short_description = "Input Entity"

    def execution_time(self, obj):
        """Display execution time if available"""
        if obj.started_at and obj.completed_at:
            duration = obj.completed_at - obj.started_at
            return f"{duration.total_seconds():.2f}s"
        return "-"

    execution_time.short_description = "Duration"

    def celery_task_link(self, obj):
        """Display Celery task ID as link if available"""
        if obj.celery_task_id:
            return format_html(
                '<code style="background: #f0f0f0; padding: 2px 4px; border-radius: 3px;">{}</code>',
                obj.celery_task_id[:8] + "..."
                if len(obj.celery_task_id) > 8
                else obj.celery_task_id,
            )
        return "-"

    celery_task_link.short_description = "Task ID"

    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        return (
            super()
            .get_queryset(request)
            .select_related("investigation", "input_entity")
        )

    actions = ["retry_failed_executions", "cancel_running_executions"]

    def retry_failed_executions(self, request, queryset):
        """Retry failed transform executions"""
        failed_executions = queryset.filter(status="failed")
        count = 0

        for execution in failed_executions:
            try:
                # Reset execution status
                execution.status = "pending"
                execution.error_message = ""
                execution.celery_task_id = ""
                execution.save()

                # Re-queue the task
                from .tasks import execute_transform

                task = execute_transform.delay(
                    str(execution.id),
                    execution.transform_name,
                    execution.input_entity.value,
                    execution.parameters,
                )

                execution.celery_task_id = task.id
                execution.save()
                count += 1

            except Exception as e:
                self.message_user(
                    request,
                    f"Failed to retry execution {execution.id}: {str(e)}",
                    level="ERROR",
                )

        if count > 0:
            self.message_user(
                request, f"Successfully retried {count} failed executions."
            )

    retry_failed_executions.short_description = "Retry selected failed executions"

    def cancel_running_executions(self, request, queryset):
        """Cancel running transform executions"""
        running_executions = queryset.filter(status="running")
        count = 0

        for execution in running_executions:
            try:
                if execution.celery_task_id:
                    # Revoke the Celery task
                    from celery import current_app

                    current_app.control.revoke(execution.celery_task_id, terminate=True)

                # Update execution status
                execution.status = "cancelled"
                execution.error_message = "Cancelled by administrator"
                execution.save()
                count += 1

            except Exception as e:
                self.message_user(
                    request,
                    f"Failed to cancel execution {execution.id}: {str(e)}",
                    level="ERROR",
                )

        if count > 0:
            self.message_user(
                request, f"Successfully cancelled {count} running executions."
            )

    cancel_running_executions.short_description = "Cancel selected running executions"
