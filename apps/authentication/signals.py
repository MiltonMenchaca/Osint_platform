import logging

from django.conf import settings
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.mail import send_mail
from django.db.models.signals import post_delete, post_save, pre_delete
from django.dispatch import receiver
from django.utils import timezone

from .models import APIToken, UserProfile

logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Automatically create UserProfile when a new User is created
    """
    if created:
        try:
            UserProfile.objects.get_or_create(
                user=instance,
                defaults={
                    "role": "viewer",
                    "timezone": "UTC",
                },
            )

            logger.info(f"Created user profile for user: {instance.username} " f"(ID: {instance.id})")

        except Exception as e:
            logger.error(f"Error creating user profile for {instance.username}: {str(e)}")


@receiver(post_save, sender=UserProfile)
def user_profile_post_save(sender, instance, created, **kwargs):
    """
    Handle post-save operations for UserProfile
    """
    try:
        # Clear user cache
        cache_key = f"user_profile_{instance.user.id}"
        cache.delete(cache_key)

        # Clear role-based cache
        role_cache_key = f"users_role_{instance.role}"
        cache.delete(role_cache_key)

        if created:
            logger.info(
                f"User profile created: {instance.user.username} "
                f"(Role: {instance.role}, Organization: {instance.organization})"
            )
        else:
            logger.info(f"User profile updated: {instance.user.username} " f"(Role: {instance.role})")

        # Update user permissions based on role
        _update_user_permissions(instance)

        # Send notification if role changed
        if not created and "role" in getattr(instance, "_changed_fields", []):
            _send_role_change_notification(instance)

    except Exception as e:
        logger.error(f"Error in user_profile post_save signal for {instance.user.username}: {str(e)}")


@receiver(pre_delete, sender=UserProfile)
def user_profile_pre_delete(sender, instance, **kwargs):
    """
    Handle pre-delete operations for UserProfile
    """
    try:
        # Revoke all API tokens for this user
        api_tokens = APIToken.objects.filter(user=instance.user, is_active=True)
        revoked_count = 0

        for token in api_tokens:
            token.is_active = False
            token.expires_at = timezone.now()
            token.save()
            revoked_count += 1

        if revoked_count > 0:
            logger.info(f"Revoked {revoked_count} API tokens for user {instance.user.username}")

        # Clear caches
        cache_key = f"user_profile_{instance.user.id}"
        cache.delete(cache_key)

        role_cache_key = f"users_role_{instance.role}"
        cache.delete(role_cache_key)

        logger.info(f"User profile deleted: {instance.user.username}")

    except Exception as e:
        logger.error(f"Error in user_profile pre_delete signal for {instance.user.username}: {str(e)}")


@receiver(post_save, sender=APIToken)
def api_token_post_save(sender, instance, created, **kwargs):
    """
    Handle post-save operations for APIToken
    """
    try:
        # Clear user token cache
        cache_key = f"user_tokens_{instance.user.id}"
        cache.delete(cache_key)

        # Clear active tokens cache
        cache.delete("active_api_tokens")

        if created:
            logger.info(
                f"API token created: {instance.name} for user {instance.user.username} " f"(Scope: {instance.scope})"
            )

            # Send notification if user has email notifications enabled
            profile = getattr(instance.user, "profile", None)
            if profile is not None and getattr(profile, "email_notifications", False):
                _send_token_created_notification(instance)
        else:
            logger.info(f"API token updated: {instance.name} for user {instance.user.username}")

        # Check for security concerns
        _check_token_security(instance)

    except Exception as e:
        logger.error(f"Error in api_token post_save signal for {instance.name}: {str(e)}")


@receiver(post_delete, sender=APIToken)
def api_token_post_delete(sender, instance, **kwargs):
    """
    Handle post-delete operations for APIToken
    """
    try:
        # Clear caches
        cache_key = f"user_tokens_{instance.user.id}"
        cache.delete(cache_key)
        cache.delete("active_api_tokens")

        logger.info(f"API token deleted: {instance.name} for user {instance.user.username}")

        # Send notification if user has email notifications enabled
        profile = getattr(instance.user, "profile", None)
        if profile is not None and getattr(profile, "email_notifications", False):
            _send_token_deleted_notification(instance)

    except Exception as e:
        logger.error(f"Error in api_token post_delete signal for {instance.name}: {str(e)}")


def _update_user_permissions(user_profile):
    """
    Update user permissions based on role
    """
    try:
        user = user_profile.user

        # Define role-based permissions
        role_permissions = {
            "admin": {
                "is_staff": True,
                "is_superuser": False,  # Only true superuser should have this
                "groups": ["admin_group"],
            },
            "analyst": {
                "is_staff": False,
                "is_superuser": False,
                "groups": ["analyst_group"],
            },
            "investigator": {
                "is_staff": False,
                "is_superuser": False,
                "groups": ["investigator_group"],
            },
            "viewer": {
                "is_staff": False,
                "is_superuser": False,
                "groups": ["viewer_group"],
            },
        }

        permissions = role_permissions.get(user_profile.role, role_permissions["viewer"])

        # Update user flags (but don't override superuser status)
        if not user.is_superuser:
            User.objects.filter(id=user.id).update(is_staff=permissions["is_staff"])

        logger.debug(f"Updated permissions for user {user.username} with role {user_profile.role}")

    except Exception as e:
        logger.error(f"Error updating permissions for user {user_profile.user.username}: {str(e)}")


def _send_welcome_email(user):
    """
    Send welcome email to new user
    """
    try:
        if not user.email:
            return

        subject = "Welcome to OSINT Platform"
        message = f"""Hello {user.first_name or user.username},

Welcome to the OSINT Platform! Your account has been successfully created.

You can now log in and start using the platform for your investigations.

If you have any questions, please contact our support team.

Best regards,
OSINT Platform Team
"""

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=True,
        )

        logger.info(f"Welcome email sent to {user.email}")

    except Exception as e:
        logger.error(f"Error sending welcome email to {user.email}: {str(e)}")


def _send_role_change_notification(user_profile):
    """
    Send notification when user role changes
    """
    try:
        user = user_profile.user
        if not user.email or not user_profile.email_notifications:
            return

        subject = "Role Updated - OSINT Platform"
        message = f"""Hello {user.first_name or user.username},

Your role on the OSINT Platform has been updated to: {user_profile.get_role_display()}

This change may affect your access permissions. Please log in to see your updated capabilities.

If you have any questions about this change, please contact your administrator.

Best regards,
OSINT Platform Team
"""

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=True,
        )

        logger.info(f"Role change notification sent to {user.email}")

    except Exception as e:
        logger.error(f"Error sending role change notification: {str(e)}")


def _send_token_created_notification(api_token):
    """
    Send notification when API token is created
    """
    try:
        user = api_token.user
        if not user.email:
            return

        subject = "New API Token Created - OSINT Platform"
        message = f"""Hello {user.first_name or user.username},

A new API token has been created for your account:

Token Name: {api_token.name}
Scope: {api_token.scope}
Expires: {api_token.expires_at.strftime('%Y-%m-%d %H:%M:%S UTC') if api_token.expires_at else 'Never'}

Please keep your API token secure and do not share it with others.

If you did not create this token, please contact your administrator immediately.

Best regards,
OSINT Platform Team
"""

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=True,
        )

        logger.info(f"Token creation notification sent to {user.email}")

    except Exception as e:
        logger.error(f"Error sending token creation notification: {str(e)}")


def _send_token_deleted_notification(api_token):
    """
    Send notification when API token is deleted
    """
    try:
        user = api_token.user
        if not user.email:
            return

        subject = "API Token Deleted - OSINT Platform"
        message = f"""Hello {user.first_name or user.username},

An API token has been deleted from your account:

Token Name: {api_token.name}

If you did not delete this token, please contact your administrator immediately.

Best regards,
OSINT Platform Team
"""

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=True,
        )

        logger.info(f"Token deletion notification sent to {user.email}")

    except Exception as e:
        logger.error(f"Error sending token deletion notification: {str(e)}")


def _check_token_security(api_token):
    """
    Check for potential security issues with API token
    """
    try:
        warnings = []

        # Check if token has admin scope but user is not admin
        if api_token.scope == "admin":
            profile = getattr(api_token.user, "profile", None)
            if profile is not None and profile.role != "admin":
                warnings.append("Token has admin scope but user is not admin")

        # Check if token never expires
        if not api_token.expires_at:
            warnings.append("Token has no expiration date")

        # Check if token expires too far in the future (more than 1 year)
        elif api_token.expires_at:
            from datetime import timedelta

            one_year_from_now = timezone.now() + timedelta(days=365)
            if api_token.expires_at > one_year_from_now:
                warnings.append("Token expires more than 1 year in the future")

        # Log warnings
        for warning in warnings:
            logger.warning(
                f"Security concern for token '{api_token.name}' " f"(User: {api_token.user.username}): {warning}"
            )

    except Exception as e:
        logger.error(f"Error checking token security: {str(e)}")


def cleanup_expired_tokens():
    """
    Cleanup expired API tokens
    """
    try:
        expired_tokens = APIToken.objects.filter(expires_at__lt=timezone.now(), is_active=True)

        count = expired_tokens.count()
        if count > 0:
            expired_tokens.update(is_active=False)
            logger.info(f"Deactivated {count} expired API tokens")

        return count

    except Exception as e:
        logger.error(f"Error cleaning up expired tokens: {str(e)}")
        return 0


def get_user_statistics():
    """
    Get comprehensive user statistics
    """
    try:
        from django.db.models import Count, Q

        # User statistics
        total_users = User.objects.count()
        active_users = User.objects.filter(is_active=True).count()

        # Profile statistics
        profile_stats = UserProfile.objects.aggregate(
            total_profiles=Count("id"),
            api_enabled=Count("id", filter=Q(api_access_enabled=True)),
            notifications_enabled=Count("id", filter=Q(notifications_enabled=True)),
        )

        # Role distribution
        role_distribution = UserProfile.objects.values("role").annotate(count=Count("id")).order_by("-count")

        # Token statistics
        token_stats = APIToken.objects.aggregate(
            total_tokens=Count("id"),
            active_tokens=Count("id", filter=Q(is_active=True)),
            expired_tokens=Count("id", filter=Q(expires_at__lt=timezone.now(), is_active=True)),
        )

        statistics = {
            "total_users": total_users,
            "active_users": active_users,
            "profile_stats": profile_stats,
            "role_distribution": list(role_distribution),
            "token_stats": token_stats,
        }

        # Cache statistics
        cache.set("user_statistics", statistics, timeout=1800)  # 30 minutes

        return statistics

    except Exception as e:
        logger.error(f"Error getting user statistics: {str(e)}")
        return {}
