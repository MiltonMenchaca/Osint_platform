from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import APIToken, UserProfile

User = get_user_model()


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom JWT token serializer with additional user info"""

    def validate(self, attrs):
        data = super().validate(attrs)

        # Add custom user data
        user = self.user
        profile, created = UserProfile.objects.get_or_create(user=user)

        data.update(
            {
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "is_active": user.is_active,
                    "date_joined": user.date_joined,
                    "last_login": user.last_login,
                },
                "profile": {
                    "role": profile.role,
                    "api_access_enabled": profile.api_access_enabled,
                    "login_count": profile.login_count,
                    "last_login_ip": profile.last_login_ip,
                },
            }
        )

        return data

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Add custom claims
        token["username"] = user.username
        token["email"] = user.email

        # Add profile info
        try:
            profile = user.userprofile
            token["role"] = profile.role
            token["api_access"] = profile.api_access_enabled
        except UserProfile.DoesNotExist:
            token["role"] = "viewer"
            token["api_access"] = False

        return token


class UserRegistrationSerializer(serializers.ModelSerializer):
    """User registration serializer"""

    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = (
            "username",
            "email",
            "password",
            "password_confirm",
            "first_name",
            "last_name",
        )
        extra_kwargs = {
            "email": {"required": True},
            "first_name": {"required": False},
            "last_name": {"required": False},
        }

    def validate(self, attrs):
        """Validate password confirmation"""
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError("Passwords don't match")
        return attrs

    def validate_email(self, value):
        """Validate email uniqueness"""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate_username(self, value):
        """Validate username"""
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError(
                "A user with this username already exists."
            )

        # Additional username validation
        if len(value) < 3:
            raise serializers.ValidationError(
                "Username must be at least 3 characters long."
            )

        if not value.replace("_", "").replace("-", "").isalnum():
            raise serializers.ValidationError(
                "Username can only contain letters, numbers, underscores, and hyphens."
            )

        return value

    def create(self, validated_data):
        """Create user"""
        validated_data.pop("password_confirm")
        password = validated_data.pop("password")

        user = User.objects.create_user(password=password, **validated_data)

        return user


class UserProfileSerializer(serializers.ModelSerializer):
    """User profile serializer"""

    username = serializers.CharField(source="user.username", read_only=True)
    email = serializers.CharField(source="user.email", read_only=True)
    first_name = serializers.CharField(source="user.first_name", read_only=True)
    last_name = serializers.CharField(source="user.last_name", read_only=True)
    date_joined = serializers.DateTimeField(source="user.date_joined", read_only=True)
    last_login = serializers.DateTimeField(source="user.last_login", read_only=True)
    is_active = serializers.BooleanField(source="user.is_active", read_only=True)

    class Meta:
        model = UserProfile
        fields = (
            "username",
            "email",
            "first_name",
            "last_name",
            "date_joined",
            "last_login",
            "is_active",
            "role",
            "api_access_enabled",
            "login_count",
            "last_login_ip",
            "registration_ip",
            "password_changed_at",
            "preferences",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "username",
            "email",
            "first_name",
            "last_name",
            "date_joined",
            "last_login",
            "is_active",
            "login_count",
            "last_login_ip",
            "registration_ip",
            "password_changed_at",
            "created_at",
            "updated_at",
        )

    def validate_role(self, value):
        """Validate role changes"""
        request = self.context.get("request")
        if request and request.user:
            # Only admins can change roles
            user_profile = getattr(request.user, "userprofile", None)
            if not user_profile or user_profile.role != "admin":
                if self.instance and self.instance.role != value:
                    raise serializers.ValidationError(
                        "You don't have permission to change roles."
                    )
        return value

    def validate_api_access_enabled(self, value):
        """Validate API access changes"""
        request = self.context.get("request")
        if request and request.user:
            # Only admins can enable/disable API access
            user_profile = getattr(request.user, "userprofile", None)
            if not user_profile or user_profile.role != "admin":
                if self.instance and self.instance.api_access_enabled != value:
                    raise serializers.ValidationError(
                        "You don't have permission to change API access."
                    )
        return value


class UserUpdateSerializer(serializers.ModelSerializer):
    """User update serializer"""

    class Meta:
        model = User
        fields = ("first_name", "last_name", "email")

    def validate_email(self, value):
        """Validate email uniqueness"""
        if self.instance and self.instance.email == value:
            return value

        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value


class ChangePasswordSerializer(serializers.Serializer):
    """Change password serializer"""

    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(required=True)

    def validate(self, attrs):
        """Validate password confirmation"""
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError("New passwords don't match")
        return attrs


class APITokenSerializer(serializers.ModelSerializer):
    """API token serializer"""

    token_preview = serializers.SerializerMethodField()
    is_expired = serializers.SerializerMethodField()
    days_until_expiry = serializers.SerializerMethodField()
    scopes_display = serializers.SerializerMethodField()

    class Meta:
        model = APIToken
        fields = (
            "id",
            "name",
            "token_preview",
            "scopes",
            "scopes_display",
            "is_active",
            "expires_at",
            "is_expired",
            "days_until_expiry",
            "last_used_at",
            "usage_count",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "token_preview",
            "last_used_at",
            "usage_count",
            "created_at",
            "updated_at",
        )

    def get_token_preview(self, obj):
        """Get token preview (first 8 and last 4 characters)"""
        if hasattr(obj, "token_preview"):
            return obj.token_preview  # Full token (only shown once after creation)

        if obj.token:
            return f"{obj.token[:8]}...{obj.token[-4:]}"
        return None

    def get_is_expired(self, obj):
        """Check if token is expired"""
        if not obj.expires_at:
            return False
        return obj.expires_at <= timezone.now()

    def get_days_until_expiry(self, obj):
        """Get days until token expires"""
        if not obj.expires_at:
            return None

        delta = obj.expires_at - timezone.now()
        return delta.days if delta.days >= 0 else 0

    def get_scopes_display(self, obj):
        """Get human-readable scopes"""
        scope_map = {
            "read": "Read Access",
            "write": "Write Access",
            "execute": "Execute Transforms",
            "admin": "Admin Access",
        }

        if obj.scopes:
            return [scope_map.get(scope, scope.title()) for scope in obj.scopes]
        return []


class APITokenCreateSerializer(serializers.ModelSerializer):
    """API token creation serializer"""

    expires_in_days = serializers.IntegerField(
        write_only=True, required=False, default=90
    )

    class Meta:
        model = APIToken
        fields = ("name", "scopes", "expires_in_days")

    def validate_name(self, value):
        """Validate token name uniqueness for user"""
        request = self.context.get("request")
        if request and request.user:
            if APIToken.objects.filter(user=request.user, name=value).exists():
                raise serializers.ValidationError(
                    "You already have a token with this name."
                )
        return value

    def validate_scopes(self, value):
        """Validate scopes"""
        valid_scopes = ["read", "write", "execute", "admin"]

        if not value:
            raise serializers.ValidationError("At least one scope is required.")

        for scope in value:
            if scope not in valid_scopes:
                raise serializers.ValidationError(f"Invalid scope: {scope}")

        # Check if user can assign admin scope
        request = self.context.get("request")
        if "admin" in value and request and request.user:
            user_profile = getattr(request.user, "userprofile", None)
            if not user_profile or user_profile.role != "admin":
                raise serializers.ValidationError(
                    "You don't have permission to create admin tokens."
                )

        return value

    def validate_expires_in_days(self, value):
        """Validate expiry days"""
        if value <= 0:
            raise serializers.ValidationError("Expiry days must be positive.")

        if value > 365:
            raise serializers.ValidationError(
                "Token cannot expire more than 365 days from now."
            )

        return value

    def create(self, validated_data):
        """Create API token with expiry"""
        expires_in_days = validated_data.pop("expires_in_days")

        # Set expiry date
        validated_data["expires_at"] = timezone.now() + timedelta(days=expires_in_days)

        return super().create(validated_data)


class UserStatsSerializer(serializers.ModelSerializer):
    """User statistics serializer (for admin)"""

    profile = UserProfileSerializer(source="userprofile", read_only=True)
    investigation_count = serializers.SerializerMethodField()
    execution_count = serializers.SerializerMethodField()
    api_token_count = serializers.SerializerMethodField()
    last_activity = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "is_active",
            "is_staff",
            "date_joined",
            "last_login",
            "profile",
            "investigation_count",
            "execution_count",
            "api_token_count",
            "last_activity",
        )

    def get_investigation_count(self, obj):
        """Get user's investigation count"""
        return getattr(obj, "investigation_count", 0)

    def get_execution_count(self, obj):
        """Get user's execution count"""
        return getattr(obj, "execution_count", 0)

    def get_api_token_count(self, obj):
        """Get user's API token count"""
        return APIToken.objects.filter(user=obj).count()

    def get_last_activity(self, obj):
        """Get user's last activity"""
        # This could be enhanced to track more detailed activity
        return obj.last_login


class UserListSerializer(serializers.ModelSerializer):
    """Simple user list serializer"""

    role = serializers.CharField(source="userprofile.role", read_only=True)
    api_access_enabled = serializers.BooleanField(
        source="userprofile.api_access_enabled", read_only=True
    )

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "is_active",
            "date_joined",
            "last_login",
            "role",
            "api_access_enabled",
        )


class TokenValidationSerializer(serializers.Serializer):
    """Token validation serializer"""

    token = serializers.CharField(required=True)

    def validate_token(self, value):
        """Validate token format"""
        if len(value) < 32:
            raise serializers.ValidationError("Invalid token format.")
        return value


class PasswordResetRequestSerializer(serializers.Serializer):
    """Password reset request serializer"""

    email = serializers.EmailField(required=True)

    def validate_email(self, value):
        """Validate email exists"""
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError("No user found with this email address.")
        return value


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Password reset confirmation serializer"""

    token = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(required=True)

    def validate(self, attrs):
        """Validate password confirmation"""
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError("Passwords don't match")
        return attrs


class UserPreferencesSerializer(serializers.Serializer):
    """User preferences serializer"""

    theme = serializers.ChoiceField(choices=["light", "dark", "auto"], default="auto")
    language = serializers.ChoiceField(choices=["en", "es", "fr", "de"], default="en")
    timezone = serializers.CharField(max_length=50, default="UTC")
    notifications_enabled = serializers.BooleanField(default=True)
    email_notifications = serializers.BooleanField(default=True)
    auto_refresh_interval = serializers.IntegerField(
        min_value=5, max_value=300, default=30
    )
    items_per_page = serializers.IntegerField(min_value=10, max_value=100, default=20)

    def validate_timezone(self, value):
        """Validate timezone"""
        import pytz

        try:
            pytz.timezone(value)
        except pytz.exceptions.UnknownTimeZoneError:
            raise serializers.ValidationError("Invalid timezone.")
        return value
