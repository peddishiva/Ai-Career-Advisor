"""Reusable ownership checks based on verified authentication identity."""

from typing import Any

from auth.models import AuthenticatedUser


class OwnershipError(PermissionError):
    """Raised when a verified user does not own a resource."""


def ensure_user_scope(current_user: AuthenticatedUser, resource_user_id: str) -> None:
    """Reject a resource whose owner differs from the verified token subject."""

    if not resource_user_id or current_user.user_id != str(resource_user_id):
        raise OwnershipError("resource is outside the authenticated user scope")


def assert_owner(current_user: AuthenticatedUser, resource: Any, owner_field: str = "user_id") -> Any:
    """Return a resource only after checking its owner field."""

    owner_id = getattr(resource, owner_field, None)
    ensure_user_scope(current_user, owner_id)
    return resource


def require_owned_resource(current_user: AuthenticatedUser, resource: Any, owner_field: str = "user_id") -> Any:
    """Alias for route/service code that wants an explicit ownership verb."""

    return assert_owner(current_user, resource, owner_field)
