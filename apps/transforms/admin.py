from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .models import Transform


@admin.register(Transform)
class TransformAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "category",
        "tool_name",
        "input_type",
        "output_types",
        "is_enabled",
        "requires_api_key",
        "timeout",
        "usage_count"
    ]
    list_filter = [
        "category",
        "tool_name",
        "input_type",
        "is_enabled",
        "requires_api_key",
        "created_at"
    ]
    search_fields = ["name", "description", "tool_name", "command_template"]
    readonly_fields = ["id", "created_at", "updated_at", "usage_count"]

    fieldsets = (
        (
            "Basic Information",
            {"fields": ("id", "name", "display_name", "description", "category", "is_enabled")},
        ),
        (
            "Tool Configuration",
            {
                "fields": (
                    "tool_name",
                    "command_template",
                    "timeout",
                    "requires_api_key",
                    "api_key_name",
                )
            },
        ),
        (
            "Input/Output Types",
            {
                "fields": ("input_type", "output_types")
            },
        ),
        ("Parameters", {"fields": ("parameters",), "classes": ("collapse",)}),
        ("Usage Statistics", {"fields": ("usage_count",), "classes": ("collapse",)}),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def usage_count(self, obj):
        """Display usage count from transform executions"""
        from apps.investigations.models import TransformExecution

        count = TransformExecution.objects.filter(transform_name=obj.name).count()
        if count > 0:
            return format_html(
                '<span style="color: #0066cc; font-weight: bold;">{}</span>', count
            )
        return "0"

    usage_count.short_description = "Usage Count"

    actions = [
        "enable_transforms",
        "disable_transforms",
        "test_transforms",
        "update_command_templates",
    ]

    def enable_transforms(self, request, queryset):
        """Enable selected transforms"""
        updated = queryset.update(is_enabled=True)
        self.message_user(request, f"Successfully enabled {updated} transforms.")

    enable_transforms.short_description = "Enable selected transforms"

    def disable_transforms(self, request, queryset):
        """Disable selected transforms"""
        updated = queryset.update(is_enabled=False)
        self.message_user(request, f"Successfully disabled {updated} transforms.")

    disable_transforms.short_description = "Disable selected transforms"

    def test_transforms(self, request, queryset):
        """Test selected transforms availability"""
        results = []

        for transform in queryset:
            is_available, message = transform.check_availability()
            status = "✓" if is_available else "✗"
            results.append(f"{status} {transform.name}: {message}")

        result_html = "<br>".join(results)
        self.message_user(
            request, mark_safe(f"Transform availability test results:<br>{result_html}")
        )

    test_transforms.short_description = "Test transform availability"

    def update_command_templates(self, request, queryset):
        """Update command templates with latest versions"""
        updated_count = 0

        # Default command templates for common tools
        default_templates = {
            "assetfinder": "assetfinder {input}",
            "amass": "amass enum -d {input} -o /tmp/amass_output.txt && cat /tmp/amass_output.txt",
            "nmap": "nmap -sS -O -A {input}",
            "shodan": "shodan host {input}",
            "whois": "whois {input}",
            "dig": "dig {input} ANY",
            "nslookup": "nslookup {input}",
        }

        for transform in queryset:
            if transform.tool_name in default_templates:
                old_template = transform.command_template
                new_template = default_templates[transform.tool_name]

                if old_template != new_template:
                    transform.command_template = new_template
                    transform.save()
                    updated_count += 1

        if updated_count > 0:
            self.message_user(
                request, f"Updated command templates for {updated_count} transforms."
            )
        else:
            self.message_user(request, "No transforms required template updates.")

    update_command_templates.short_description = "Update command templates"

    def get_form(self, request, obj=None, **kwargs):
        """Customize the form"""
        form = super().get_form(request, obj, **kwargs)

        # Add help text for command template
        if "command_template" in form.base_fields:
            form.base_fields["command_template"].help_text = (
                "Use {input} as placeholder for the input entity value. "
                "Additional parameters can be referenced as {param_name}."
            )

        # Add help text for parameters
        if "parameters" in form.base_fields:
            form.base_fields["parameters"].help_text = (
                "JSON object defining additional parameters. "
                'Example: {"timeout": 30, "format": "json"}'
            )

        return form

    def save_model(self, request, obj, form, change):
        """Custom save logic"""
        # Validate command template
        if (
            "{input}" not in obj.command_template
            and "{input_value}" not in obj.command_template
            and "{target}" not in obj.command_template
        ):
            self.message_user(
                request,
                "Warning: Command template should contain {input} placeholder.",
                level="WARNING",
            )

        # Set default timeout if not specified
        if not obj.timeout:
            default_timeouts = {
                "assetfinder": 60,
                "amass": 300,  # 5 minutes
                "nmap": 600,  # 10 minutes
                "shodan": 30,
                "whois": 30,
                "dig": 30,
                "nslookup": 30,
            }
            obj.timeout = default_timeouts.get(obj.tool_name, 120)

        super().save_model(request, obj, form, change)

    def changelist_view(self, request, extra_context=None):
        """Add extra context to changelist view"""
        extra_context = extra_context or {}

        # Add statistics
        total_transforms = Transform.objects.count()
        enabled_transforms = Transform.objects.filter(is_enabled=True).count()

        from apps.investigations.models import TransformExecution

        total_executions = TransformExecution.objects.count()
        successful_executions = TransformExecution.objects.filter(
            status="completed"
        ).count()

        extra_context.update(
            {
                "total_transforms": total_transforms,
                "enabled_transforms": enabled_transforms,
                "total_executions": total_executions,
                "successful_executions": successful_executions,
                "success_rate": (
                    (successful_executions / total_executions * 100)
                    if total_executions > 0
                    else 0
                ),
            }
        )

        return super().changelist_view(request, extra_context=extra_context)


# Custom admin site configuration
class TransformAdminSite(admin.AdminSite):
    site_header = "OSINT Platform - Transform Management"
    site_title = "Transform Admin"
    index_title = "Transform Administration"

    def index(self, request, extra_context=None):
        """Custom admin index with transform statistics"""
        extra_context = extra_context or {}

        # Transform statistics
        from apps.investigations.models import TransformExecution

        transform_stats = {
            "total_transforms": Transform.objects.count(),
            "enabled_transforms": Transform.objects.filter(is_enabled=True).count(),
            "total_executions": TransformExecution.objects.count(),
            "running_executions": TransformExecution.objects.filter(
                status="running"
            ).count(),
            "failed_executions": TransformExecution.objects.filter(
                status="failed"
            ).count(),
        }

        # Most used transforms
        from django.db.models import Count

        popular_transforms = (
            TransformExecution.objects.values("transform_name")
            .annotate(usage_count=Count("id"))
            .order_by("-usage_count")[:5]
        )

        extra_context.update(
            {
                "transform_stats": transform_stats,
                "popular_transforms": popular_transforms,
            }
        )

        return super().index(request, extra_context=extra_context)
