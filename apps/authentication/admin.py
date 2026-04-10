from datetime import timedelta

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .models import APIToken, UserProfile


# Inline for UserProfile in User admin
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = "Profile"
    fields = (
        "role",
        "organization",
        # Temporarily commented out fields that don't exist yet
        # 'phone_number', 'timezone', 'language', 'theme',
        # 'notifications_enabled', 'email_notifications', 'api_access_enabled'
    )
    extra = 0


# Extended User Admin
class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "get_role",
        "get_organization",
        "is_active",
        "date_joined",
        "last_login",
    )
    list_filter = [
        "is_active",
        "is_staff",
        "is_superuser",
        "date_joined",
        "last_login",
        # Temporarily commented out fields that don't exist yet
        # 'userprofile__role', 'userprofile__organization'
    ]
    search_fields = (
        "username",
        "first_name",
        "last_name",
        "email",
        "userprofile__organization",
        "userprofile__phone_number",
    )

    def get_role(self, obj):
        """Get user role from profile"""
        try:
            profile = obj.userprofile
            role_colors = {
                "admin": "#dc3545",
                "analyst": "#007bff",
                "investigator": "#28a745",
                "viewer": "#6c757d",
            }
            color = role_colors.get(profile.role, "#6c757d")
            return format_html(
                '<span style="color: {}; font-weight: bold;">{}</span>',
                color,
                profile.get_role_display(),
            )
        except UserProfile.DoesNotExist:
            return format_html('<span style="color: #dc3545;">No Profile</span>')

    get_role.short_description = "Role"
    get_role.admin_order_field = "userprofile__role"

    def get_organization(self, obj):
        """Get user organization from profile"""
        try:
            return obj.userprofile.organization or "-"
        except UserProfile.DoesNotExist:
            return "-"

    get_organization.short_description = "Organization"
    get_organization.admin_order_field = "userprofile__organization"

    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        return super().get_queryset(request).select_related("userprofile")


# Unregister the default User admin and register our custom one
admin.site.unregister(User)
admin.site.register(User, UserAdmin)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = [
        "user",
        "role",
        "organization",
        "created_at",
        # Temporarily commented out fields that don't exist yet
        # 'phone_number', 'timezone', 'language', 'api_access_enabled',
        # 'notifications_enabled'
    ]
    list_filter = [
        "role",
        "organization",
        "created_at",
        # Temporarily commented out fields that don't exist yet
        # 'timezone', 'language', 'api_access_enabled', 'notifications_enabled',
        # 'email_notifications', 'theme'
    ]
    search_fields = [
        "user__username",
        "user__email",
        "user__first_name",
        "user__last_name",
        "organization",
        "phone_number",
    ]
    readonly_fields = ["id", "created_at", "updated_at"]

    fieldsets = (
        ("User Information", {"fields": ("id", "user")}),
        ("Role & Organization", {"fields": ("role", "organization", "phone_number")}),
        # Temporarily commented out until fields exist
        # ('Preferences', {
        #     'fields': (
        #         'timezone', 'language', 'theme',
        #         'notifications_enabled', 'email_notifications'
        #     )
        # }),
        # ('API Access', {
        #     'fields': ('api_access_enabled',)
        # }),
        (
            "Timestamps",
            {
                "fields": ("created_at",),
                "classes": ("collapse",),
                # Temporarily commented out field that doesn't exist yet
                # 'updated_at'
            },
        ),
    )

    def get_queryset(self, request):
        """Optimize queryset"""
        return super().get_queryset(request).select_related("user")

    # Temporarily commented out actions that reference non-existent fields
    # actions = [
    #     'enable_api_access', 'disable_api_access',
    #     'enable_notifications', 'disable_notifications'
    # ]

    def enable_api_access(self, request, queryset):
        """Enable API access for selected profiles"""
        updated = queryset.update(api_access_enabled=True)
        self.message_user(request, f"API access enabled for {updated} user profiles.")

    enable_api_access.short_description = "Enable API access"

    def disable_api_access(self, request, queryset):
        """Disable API access for selected profiles"""
        updated = queryset.update(api_access_enabled=False)
        self.message_user(request, f"API access disabled for {updated} user profiles.")

    disable_api_access.short_description = "Disable API access"

    def enable_notifications(self, request, queryset):
        """Enable notifications for selected profiles"""
        updated = queryset.update(notifications_enabled=True, email_notifications=True)
        self.message_user(request, f"Notifications enabled for {updated} user profiles.")

    enable_notifications.short_description = "Enable notifications"

    def disable_notifications(self, request, queryset):
        """Disable notifications for selected profiles"""
        updated = queryset.update(notifications_enabled=False, email_notifications=False)
        self.message_user(request, f"Notifications disabled for {updated} user profiles.")

    disable_notifications.short_description = "Disable notifications"


@admin.register(APIToken)
class APITokenAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "user",
        "token_preview",
        "scopes_display",
        "is_active",
        "expires_at",
        "last_used_at",
        "created_at",
    ]
    list_filter = [
        "is_active",
        "created_at",
        "expires_at",
        "last_used_at",
        # Temporarily commented out fields that don't exist yet
        # 'scopes', 'user__userprofile__role'
    ]
    search_fields = [
        "name",
        "user__username",
        "user__email",
        "user__first_name",
        "user__last_name",
    ]
    readonly_fields = [
        "id",
        "token",
        "created_at",
        # Temporarily commented out fields that don't exist yet
        # 'updated_at', 'last_used_at', 'usage_count'
    ]

    fieldsets = (
        ("Basic Information", {"fields": ("id", "name", "user", "is_active")}),
        (
            "Token Details",
            {
                "fields": ("token", "expires_at")
                # Temporarily commented out field that doesn't exist yet
                # 'scopes'
            },
        ),
        (
            "Usage Statistics",
            {
                "fields": (),
                "classes": ("collapse",),
                # Temporarily commented out fields that don't exist yet
                # 'fields': ('last_used_at', 'usage_count'),
            },
        ),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def token_preview(self, obj):
        """Show token preview for security"""
        if obj.token:
            preview = f"{obj.token[:8]}...{obj.token[-4:]}"
            return format_html(
                '<code style="background: #f8f9fa; padding: 2px 4px; border-radius: 3px;">{}</code>',
                preview,
            )
        return "-"

    token_preview.short_description = "Token Preview"

    def scopes_display(self, obj):
        """Display scopes as badges"""
        if not obj.scopes:
            return "-"

        scope_colors = {"read": "#28a745", "write": "#ffc107", "admin": "#dc3545"}

        badges = []
        for scope in obj.scopes:
            color = scope_colors.get(scope, "#6c757d")
            badges.append(
                f'<span style="background: {color}; color: white; '
                f"padding: 2px 6px; border-radius: 3px; font-size: 11px; "
                f'margin-right: 2px;">{scope}</span>'
            )

        return mark_safe("".join(badges))

    scopes_display.short_description = "Scopes"

    def get_queryset(self, request):
        """Optimize queryset"""
        return super().get_queryset(request).select_related("user")
        # Temporarily commented out: 'user__userprofile'

    actions = [
        "activate_tokens",
        "deactivate_tokens",
        "extend_expiration",
        "revoke_tokens",
    ]

    def activate_tokens(self, request, queryset):
        """Activate selected tokens"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f"Activated {updated} API tokens.")

    activate_tokens.short_description = "Activate selected tokens"

    def deactivate_tokens(self, request, queryset):
        """Deactivate selected tokens"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f"Deactivated {updated} API tokens.")

    deactivate_tokens.short_description = "Deactivate selected tokens"

    def extend_expiration(self, request, queryset):
        """Extend expiration by 30 days"""
        updated_count = 0

        for token in queryset:
            if token.expires_at:
                # Extend by 30 days from current expiration
                token.expires_at = token.expires_at + timedelta(days=30)
            else:
                # Set expiration to 30 days from now
                token.expires_at = timezone.now() + timedelta(days=30)

            token.save()
            updated_count += 1

        self.message_user(request, f"Extended expiration for {updated_count} API tokens by 30 days.")

    extend_expiration.short_description = "Extend expiration by 30 days"

    def revoke_tokens(self, request, queryset):
        """Revoke selected tokens (deactivate and set expiration to now)"""
        now = timezone.now()
        updated_count = 0

        for token in queryset:
            token.is_active = False
            token.expires_at = now
            token.save()
            updated_count += 1

        self.message_user(request, f"Revoked {updated_count} API tokens.")

    revoke_tokens.short_description = "Revoke selected tokens"

    def save_model(self, request, obj, form, change):
        """Custom save logic"""
        # Set default expiration if not specified (90 days)
        if not obj.expires_at and not change:
            obj.expires_at = timezone.now() + timedelta(days=90)

        # Validate scopes
        valid_scopes = ["read", "write", "admin"]
        if obj.scopes:
            invalid_scopes = [s for s in obj.scopes if s not in valid_scopes]
            if invalid_scopes:
                self.message_user(
                    request,
                    f"Warning: Invalid scopes detected: {', '.join(invalid_scopes)}",
                    level="WARNING",
                )

        super().save_model(request, obj, form, change)

    def changelist_view(self, request, extra_context=None):
        """Add extra context to changelist view"""
        extra_context = extra_context or {}

        # Token statistics
        total_tokens = APIToken.objects.count()
        active_tokens = APIToken.objects.filter(is_active=True).count()
        expired_tokens = APIToken.objects.filter(expires_at__lt=timezone.now()).count()

        # Recent usage
        recent_usage = APIToken.objects.filter(last_used_at__gte=timezone.now() - timedelta(days=7)).count()

        extra_context.update(
            {
                "total_tokens": total_tokens,
                "active_tokens": active_tokens,
                "expired_tokens": expired_tokens,
                "recent_usage": recent_usage,
            }
        )

        return super().changelist_view(request, extra_context=extra_context)


# Custom admin site configuration
class AuthenticationAdminSite(admin.AdminSite):
    site_header = "OSINT Platform - User Management"
    site_title = "Authentication Admin"
    index_title = "User & Authentication Administration"

    def index(self, request, extra_context=None):
        """Custom admin index with user statistics"""
        extra_context = extra_context or {}

        # User statistics
        from django.contrib.auth.models import User

        user_stats = {
            "total_users": User.objects.count(),
            "active_users": User.objects.filter(is_active=True).count(),
            "staff_users": User.objects.filter(is_staff=True).count(),
            "superusers": User.objects.filter(is_superuser=True).count(),
        }

        # Profile statistics
        profile_stats = {
            "total_profiles": UserProfile.objects.count(),
            "api_enabled": UserProfile.objects.filter(api_access_enabled=True).count(),
            "notifications_enabled": UserProfile.objects.filter(notifications_enabled=True).count(),
        }

        # Token statistics
        token_stats = {
            "total_tokens": APIToken.objects.count(),
            "active_tokens": APIToken.objects.filter(is_active=True).count(),
            "expired_tokens": APIToken.objects.filter(expires_at__lt=timezone.now()).count(),
        }

        # Role distribution
        from django.db.models import Count

        role_distribution = UserProfile.objects.values("role").annotate(count=Count("id")).order_by("-count")

        extra_context.update(
            {
                "user_stats": user_stats,
                "profile_stats": profile_stats,
                "token_stats": token_stats,
                "role_distribution": role_distribution,
            }
        )

        return super().index(request, extra_context=extra_context)
