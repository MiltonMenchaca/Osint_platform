import logging
import secrets
import string
from datetime import timedelta

from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .models import APIToken, UserProfile
from .permissions import HasAPIAccess
from .serializers import (
    APITokenCreateSerializer,
    APITokenSerializer,
    ChangePasswordSerializer,
    CustomTokenObtainPairSerializer,
    UserProfileSerializer,
    UserRegistrationSerializer,
    UserStatsSerializer,
    UserUpdateSerializer,
)

User = get_user_model()
logger = logging.getLogger(__name__)


class CustomTokenObtainPairView(TokenObtainPairView):
    """Custom JWT token obtain view with additional user info"""

    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as e:
            raise InvalidToken(e.args[0])

        # Get user and update last login
        user = authenticate(username=request.data.get("username"), password=request.data.get("password"))

        if user:
            user.last_login = timezone.now()
            user.save(update_fields=["last_login"])

            # Update user profile login stats
            profile, created = UserProfile.objects.get_or_create(user=user)
            profile.last_login_ip = self.get_client_ip(request)
            profile.login_count += 1
            profile.save()

            logger.info(f"User {user.username} logged in successfully")

        return Response(serializer.validated_data, status=status.HTTP_200_OK)

    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip


class CustomTokenRefreshView(TokenRefreshView):
    """Custom JWT token refresh view with logging"""

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)

        if response.status_code == 200:
            # Try to get user from refresh token
            try:
                refresh_token = RefreshToken(request.data.get("refresh"))
                user_id = refresh_token.payload.get("user_id")
                if user_id:
                    user = User.objects.get(id=user_id)
                    logger.info(f"Token refreshed for user {user.username}")
            except Exception:
                pass

        return response


class UserRegistrationView(generics.CreateAPIView):
    """User registration endpoint"""

    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]

    def perform_create(self, serializer):
        """Create user and profile"""
        with transaction.atomic():
            user = serializer.save()

            profile, _ = UserProfile.objects.get_or_create(
                user=user,
                defaults={
                    "role": "viewer",
                    "timezone": "UTC",
                },
            )
            ip = self.get_client_ip(self.request)
            if ip:
                profile.last_login_ip = ip
                profile.save(update_fields=["last_login_ip", "updated_at"])

            logger.info(f"New user registered: {user.username}")

    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip


class UserProfileView(generics.RetrieveUpdateAPIView):
    """User profile view"""

    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        """Get current user's profile"""
        profile, created = UserProfile.objects.get_or_create(user=self.request.user)
        return profile

    def perform_update(self, serializer):
        """Log profile updates"""
        profile = serializer.save()
        logger.info(f"Profile updated for user {profile.user.username}")


class UserUpdateView(generics.UpdateAPIView):
    """Update user information"""

    serializer_class = UserUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

    def perform_update(self, serializer):
        """Log user updates"""
        user = serializer.save()
        logger.info(f"User information updated: {user.username}")


class ChangePasswordView(APIView):
    """Change user password"""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        old_password = serializer.validated_data["old_password"]
        new_password = serializer.validated_data["new_password"]

        # Check old password
        if not user.check_password(old_password):
            return Response({"error": "Invalid old password"}, status=status.HTTP_400_BAD_REQUEST)

        # Validate new password
        try:
            validate_password(new_password, user)
        except ValidationError as e:
            return Response(
                {"error": "Password validation failed", "details": list(e.messages)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Set new password
        user.set_password(new_password)
        user.save()

        # Update profile
        profile, created = UserProfile.objects.get_or_create(user=user)
        profile.password_changed_at = timezone.now()
        profile.save()

        logger.info(f"Password changed for user {user.username}")

        return Response({"message": "Password changed successfully"})


class LogoutView(APIView):
    """Logout user and blacklist refresh token"""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get("refresh_token")
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()

            logger.info(f"User {request.user.username} logged out")

            return Response({"message": "Successfully logged out"}, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Logout error for user {request.user.username}: {str(e)}")
            return Response(
                {"error": "Logout failed", "details": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class APITokenListCreateView(generics.ListCreateAPIView):
    """List and create API tokens"""

    permission_classes = [permissions.IsAuthenticated, HasAPIAccess]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return APITokenCreateSerializer
        return APITokenSerializer

    def get_queryset(self):
        """Get current user's API tokens"""
        return APIToken.objects.filter(user=self.request.user).order_by("-created_at")

    def perform_create(self, serializer):
        """Create API token for current user"""
        # Generate secure token
        token = self.generate_api_token()

        api_token = serializer.save(user=self.request.user, token=token)

        logger.info(f"API token '{api_token.name}' created for user {self.request.user.username}")

        # Return token in response (only time it's shown)
        api_token.token_preview = token

    def generate_api_token(self, length=64):
        """Generate secure API token"""
        alphabet = string.ascii_letters + string.digits
        return "".join(secrets.choice(alphabet) for _ in range(length))


class APITokenDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update or delete API token"""

    serializer_class = APITokenSerializer
    permission_classes = [permissions.IsAuthenticated, HasAPIAccess]

    def get_queryset(self):
        """Get current user's API tokens"""
        return APIToken.objects.filter(user=self.request.user)

    def perform_update(self, serializer):
        """Log token updates"""
        token = serializer.save()
        logger.info(f"API token '{token.name}' updated by user {self.request.user.username}")

    def perform_destroy(self, instance):
        """Log token deletion"""
        logger.info(f"API token '{instance.name}' deleted by user {self.request.user.username}")
        instance.delete()


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated, HasAPIAccess])
def regenerate_api_token(request, pk):
    """Regenerate API token"""
    try:
        token = APIToken.objects.get(pk=pk, user=request.user)
    except APIToken.DoesNotExist:
        return Response({"error": "API token not found"}, status=status.HTTP_404_NOT_FOUND)

    # Generate new token
    alphabet = string.ascii_letters + string.digits
    new_token = "".join(secrets.choice(alphabet) for _ in range(64))

    token.token = new_token
    token.save()

    logger.info(f"API token '{token.name}' regenerated for user {request.user.username}")

    return Response(
        {
            "message": "Token regenerated successfully",
            "token": new_token,  # Only time the full token is shown
            "token_id": token.id,
            "name": token.name,
        }
    )


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated, HasAPIAccess])
def extend_token_expiry(request, pk):
    """Extend API token expiry"""
    try:
        token = APIToken.objects.get(pk=pk, user=request.user)
    except APIToken.DoesNotExist:
        return Response({"error": "API token not found"}, status=status.HTTP_404_NOT_FOUND)

    # Extend expiry by 30 days
    if token.expires_at:
        token.expires_at = max(token.expires_at, timezone.now()) + timedelta(days=30)
    else:
        token.expires_at = timezone.now() + timedelta(days=30)

    token.save()

    logger.info(f"API token '{token.name}' expiry extended for user {request.user.username}")

    return Response(
        {
            "message": "Token expiry extended successfully",
            "new_expiry": token.expires_at,
            "token_id": token.id,
            "name": token.name,
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def current_user(request):
    """
    Get current authenticated user information
    """
    user = request.user
    profile, created = UserProfile.objects.get_or_create(user=user)

    return Response(
        {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "is_staff": user.is_staff,
            "is_superuser": user.is_superuser,
            "date_joined": user.date_joined,
            "last_login": user.last_login,
            "profile": {
                "id": str(profile.id),
                "role": profile.role,
                "organization": profile.organization,
                "phone_number": profile.phone_number,
                "timezone": profile.timezone,
                "is_verified": profile.is_verified,
                "has_api_key": bool(profile.api_key),
                "created_at": profile.created_at,
                "updated_at": profile.updated_at,
            },
        }
    )


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def user_stats(request):
    """Get current user statistics"""
    user = request.user
    profile, created = UserProfile.objects.get_or_create(user=user)

    # Get user's investigations and executions
    from apps.investigations.models import Investigation, TransformExecution
    from apps.entities.models import Entity

    investigations = Investigation.objects.filter(created_by=user)
    executions = TransformExecution.objects.filter(investigation__created_by=user)
    entities = Entity.objects.filter(investigation__created_by=user)

    # Time-based statistics
    now = timezone.now()
    last_24h = now - timedelta(hours=24)
    last_7d = now - timedelta(days=7)
    last_30d = now - timedelta(days=30)
    last_24h_investigations = investigations.filter(created_at__gte=last_24h)
    last_7d_investigations = investigations.filter(created_at__gte=last_7d)
    last_30d_investigations = investigations.filter(created_at__gte=last_30d)

    last_24h_executions = executions.filter(created_at__gte=last_24h)
    last_7d_executions = executions.filter(created_at__gte=last_7d)
    last_30d_executions = executions.filter(created_at__gte=last_30d)

    last_24h_entities = entities.filter(created_at__gte=last_24h)
    last_7d_entities = entities.filter(created_at__gte=last_7d)
    last_30d_entities = entities.filter(created_at__gte=last_30d)

    investigations_by_status = {key: 0 for key in ["active", "completed", "paused", "archived"]}
    investigations_by_status.update(
        dict(investigations.values("status").annotate(count=Count("id")).values_list("status", "count"))
    )

    entities_by_type = dict(
        entities.values("entity_type").annotate(count=Count("id")).values_list("entity_type", "count")
    )

    stats = {
        "user": {
            "username": user.username,
            "email": user.email,
            "date_joined": user.date_joined,
            "last_login": user.last_login,
            "is_active": user.is_active,
        },
        "profile": {
            "role": profile.role,
            "organization": profile.organization,
            "timezone": profile.timezone,
            "is_verified": profile.is_verified,
            "has_api_key": bool(profile.api_key),
            "created_at": profile.created_at,
            "updated_at": profile.updated_at,
        },
        "investigations": {
            "total": investigations.count(),
            "by_status": investigations_by_status,
            "active": investigations_by_status.get("active", 0),
            "completed": investigations_by_status.get("completed", 0),
            "paused": investigations_by_status.get("paused", 0),
            "archived": investigations_by_status.get("archived", 0),
            "recent": last_24h_investigations.count(),
            "last_24h": last_24h_investigations.count(),
            "last_7d": last_7d_investigations.count(),
            "last_30d": last_30d_investigations.count(),
        },
        "executions": {
            "total": executions.count(),
            "successful": executions.filter(status="completed").count(),
            "failed": executions.filter(status="failed").count(),
            "running": executions.filter(status="running").count(),
            "recent": last_24h_executions.count(),
            "last_24h": last_24h_executions.count(),
            "last_7d": last_7d_executions.count(),
            "last_30d": last_30d_executions.count(),
        },
        "entities": {
            "total": entities.count(),
            "by_type": entities_by_type,
            "recent": last_24h_entities.count(),
            "last_24h": last_24h_entities.count(),
            "last_7d": last_7d_entities.count(),
            "last_30d": last_30d_entities.count(),
        },
        "api_tokens": {
            "total": APIToken.objects.filter(user=user).count(),
            "active": APIToken.objects.filter(user=user, is_active=True, expires_at__gt=timezone.now()).count(),
            "expired": APIToken.objects.filter(user=user, expires_at__lte=timezone.now()).count(),
        },
    }

    return Response(stats)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def user_activity(request):
    """Get user activity log"""
    user = request.user

    # Get recent investigations
    from apps.investigations.models import Investigation, TransformExecution

    recent_investigations = Investigation.objects.filter(created_by=user).order_by("-created_at")[:10]

    recent_executions = TransformExecution.objects.filter(investigation__created_by=user).order_by("-created_at")[:20]

    activity = {
        "recent_investigations": [
            {
                "id": inv.id,
                "name": inv.name,
                "status": inv.status,
                "created_at": inv.created_at,
                "updated_at": inv.updated_at,
            }
            for inv in recent_investigations
        ],
        "recent_executions": [
            {
                "id": exec.id,
                "transform_name": exec.transform.name,
                "status": exec.status,
                "created_at": exec.created_at,
                "started_at": exec.started_at,
                "ended_at": exec.ended_at,
                "investigation_name": exec.investigation.name,
            }
            for exec in recent_executions
        ],
    }

    return Response(activity)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def validate_token(request):
    """Validate JWT token"""
    # If we reach here, the token is valid (due to IsAuthenticated permission)
    user = request.user

    return Response(
        {
            "valid": True,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "is_active": user.is_active,
                "date_joined": user.date_joined,
                "last_login": user.last_login,
            },
            "validated_at": timezone.now(),
        }
    )


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def check_permissions(request):
    """Check user permissions and access levels"""
    user = request.user
    profile, created = UserProfile.objects.get_or_create(user=user)

    permissions_info = {
        "user": {
            "id": user.id,
            "username": user.username,
            "is_active": user.is_active,
            "is_staff": user.is_staff,
            "is_superuser": user.is_superuser,
        },
        "profile": {
            "role": profile.role,
            "api_access_enabled": profile.api_access_enabled,
            "can_create_investigations": profile.role in ["admin", "analyst", "investigator"],
            "can_execute_transforms": profile.role in ["admin", "analyst", "investigator"],
            "can_manage_transforms": profile.role in ["admin"],
            "can_view_all_investigations": profile.role in ["admin"],
            "can_manage_users": profile.role in ["admin"],
        },
        "api_tokens": {
            "can_create": profile.api_access_enabled,
            "active_tokens": APIToken.objects.filter(user=user, is_active=True, expires_at__gt=timezone.now()).count(),
        },
    }

    return Response(permissions_info)


class UserListView(generics.ListAPIView):
    """List users (admin only)"""

    queryset = User.objects.all().order_by("-date_joined")
    serializer_class = UserStatsSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]

    def get_queryset(self):
        """Filter users with search"""
        queryset = super().get_queryset()

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(username__icontains=search)
                | Q(email__icontains=search)
                | Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
            )

        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            active = is_active.lower() in ["true", "1", "yes"]
            queryset = queryset.filter(is_active=active)

        role = self.request.query_params.get("role")
        if role:
            queryset = queryset.filter(userprofile__role=role)

        return queryset


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated, permissions.IsAdminUser])
def admin_stats(request):
    """Get admin statistics"""
    from apps.investigations.models import Investigation, TransformExecution
    from apps.transforms.models import Transform

    now = timezone.now()
    last_24h = now - timedelta(hours=24)
    last_7d = now - timedelta(days=7)
    last_30d = now - timedelta(days=30)

    stats = {
        "users": {
            "total": User.objects.count(),
            "active": User.objects.filter(is_active=True).count(),
            "inactive": User.objects.filter(is_active=False).count(),
            "new_last_24h": User.objects.filter(date_joined__gte=last_24h).count(),
            "new_last_7d": User.objects.filter(date_joined__gte=last_7d).count(),
            "new_last_30d": User.objects.filter(date_joined__gte=last_30d).count(),
            "by_role": dict(
                UserProfile.objects.values("role").annotate(count=Count("id")).values_list("role", "count")
            ),
        },
        "investigations": {
            "total": Investigation.objects.count(),
            "active": Investigation.objects.filter(status="active").count(),
            "completed": Investigation.objects.filter(status="completed").count(),
            "new_last_24h": Investigation.objects.filter(created_at__gte=last_24h).count(),
            "new_last_7d": Investigation.objects.filter(created_at__gte=last_7d).count(),
            "new_last_30d": Investigation.objects.filter(created_at__gte=last_30d).count(),
        },
        "executions": {
            "total": TransformExecution.objects.count(),
            "successful": TransformExecution.objects.filter(status="completed").count(),
            "failed": TransformExecution.objects.filter(status="failed").count(),
            "running": TransformExecution.objects.filter(status="running").count(),
            "last_24h": TransformExecution.objects.filter(created_at__gte=last_24h).count(),
            "last_7d": TransformExecution.objects.filter(created_at__gte=last_7d).count(),
            "last_30d": TransformExecution.objects.filter(created_at__gte=last_30d).count(),
        },
        "transforms": {
            "total": Transform.objects.count(),
            "enabled": Transform.objects.filter(is_enabled=True).count(),
            "available": Transform.objects.filter(is_available=True).count(),
        },
        "api_tokens": {
            "total": APIToken.objects.count(),
            "active": APIToken.objects.filter(is_active=True, expires_at__gt=now).count(),
            "expired": APIToken.objects.filter(expires_at__lte=now).count(),
        },
    }

    return Response(stats)
