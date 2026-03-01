from rest_framework import permissions


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed for any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to the owner of the object.
        owner = getattr(obj, "created_by", None)
        if owner is None and hasattr(obj, "investigation"):
            owner = getattr(getattr(obj, "investigation", None), "created_by", None)
        return owner == request.user


class HasAPIAccess(permissions.BasePermission):
    """
    Custom permission to check if user has API access.
    """

    def has_permission(self, request, view):
        # For now, all authenticated users have API access
        # This can be extended to check for specific user attributes
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)
