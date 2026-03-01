import uuid

from django.contrib.auth.models import User
from django.db import models


class UserProfile(models.Model):
    """
    Extended user profile for OSINT platform users
    """

    ROLE_CHOICES = [
        ("analyst", "Analyst"),
        ("investigator", "Investigator"),
        ("admin", "Administrator"),
        ("viewer", "Viewer"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default="analyst",
        help_text="User role in the platform",
    )
    organization = models.CharField(
        max_length=255, blank=True, help_text="Organization the user belongs to"
    )
    phone_number = models.CharField(
        max_length=20, blank=True, help_text="User's phone number"
    )
    timezone = models.CharField(
        max_length=50, default="UTC", help_text="User's preferred timezone"
    )
    preferences = models.JSONField(
        default=dict, blank=True, help_text="User preferences and settings"
    )
    api_key = models.CharField(
        max_length=255, blank=True, help_text="API key for programmatic access"
    )
    api_key_created_at = models.DateTimeField(
        null=True, blank=True, help_text="When the API key was created"
    )
    last_login_ip = models.GenericIPAddressField(
        null=True, blank=True, help_text="IP address of last login"
    )
    is_verified = models.BooleanField(
        default=False, help_text="Whether the user's email is verified"
    )
    created_at = models.DateTimeField(
        auto_now_add=True, help_text="When the profile was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True, help_text="When the profile was last updated"
    )

    class Meta:
        db_table = "user_profiles"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["role"]),
            models.Index(fields=["organization"]),
            models.Index(fields=["api_key"]),
        ]

    def __str__(self):
        return f"{self.user.username} ({self.role})"

    def get_full_name(self):
        """Get user's full name"""
        return f"{self.user.first_name} {self.user.last_name}".strip()

    def can_create_investigations(self):
        """Check if user can create investigations"""
        return self.role in ["analyst", "investigator", "admin"]

    def can_execute_transforms(self):
        """Check if user can execute transforms"""
        return self.role in ["analyst", "investigator", "admin"]

    def can_manage_users(self):
        """Check if user can manage other users"""
        return self.role == "admin"

    def can_view_all_investigations(self):
        """Check if user can view all investigations"""
        return self.role in ["admin"]

    def generate_api_key(self):
        """Generate a new API key for the user"""
        import secrets

        from django.utils import timezone

        self.api_key = f"osint_{secrets.token_urlsafe(32)}"
        self.api_key_created_at = timezone.now()
        self.save(update_fields=["api_key", "api_key_created_at", "updated_at"])
        return self.api_key

    def revoke_api_key(self):
        """Revoke the user's API key"""
        self.api_key = ""
        self.api_key_created_at = None
        self.save(update_fields=["api_key", "api_key_created_at", "updated_at"])

    def set_preference(self, key, value):
        """Set a user preference"""
        if not self.preferences:
            self.preferences = {}
        self.preferences[key] = value
        self.save(update_fields=["preferences", "updated_at"])

    def get_preference(self, key, default=None):
        """Get a user preference"""
        return self.preferences.get(key, default) if self.preferences else default


class APIToken(models.Model):
    """
    Model for API tokens with expiration and scopes
    """

    SCOPE_CHOICES = [
        ("read", "Read Only"),
        ("write", "Read/Write"),
        ("admin", "Administrative"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="api_tokens")
    name = models.CharField(max_length=255, help_text="Descriptive name for the token")
    token = models.CharField(
        max_length=255, unique=True, help_text="The actual token value"
    )
    scope = models.CharField(
        max_length=20,
        choices=SCOPE_CHOICES,
        default="read",
        help_text="Scope of permissions for this token",
    )
    is_active = models.BooleanField(
        default=True, help_text="Whether the token is active"
    )
    expires_at = models.DateTimeField(
        null=True, blank=True, help_text="When the token expires (null = never)"
    )
    last_used_at = models.DateTimeField(
        null=True, blank=True, help_text="When the token was last used"
    )
    last_used_ip = models.GenericIPAddressField(
        null=True, blank=True, help_text="IP address where token was last used"
    )
    created_at = models.DateTimeField(
        auto_now_add=True, help_text="When the token was created"
    )

    class Meta:
        db_table = "api_tokens"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["token"]),
            models.Index(fields=["user"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["expires_at"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.user.username})"

    def is_expired(self):
        """Check if the token is expired"""
        if not self.expires_at:
            return False
        from django.utils import timezone

        return timezone.now() > self.expires_at

    def is_valid(self):
        """Check if the token is valid for use"""
        return self.is_active and not self.is_expired()

    def record_usage(self, ip_address=None):
        """Record token usage"""
        from django.utils import timezone

        self.last_used_at = timezone.now()
        if ip_address:
            self.last_used_ip = ip_address
        self.save(update_fields=["last_used_at", "last_used_ip"])
