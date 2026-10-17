"""Role-based access control helpers."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, Request, status

from .jwt import decode_access_token


ROLE_PERMISSIONS: dict[str, set[str]] = {
    "Student": {
        "withdrawal:read",
        "withdrawal:create",
        "documents:upload",
        "profile:read",
    },
    "Department Coordinator": {
        "withdrawal:read",
        "clearance:update",
        "grievance:update",
    },
    "Registrar": {
        "withdrawal:read",
        "withdrawal:update",
        "procedure:manage",
    },
    "Finance Department": {
        "withdrawal:read",
        "refund:update",
        "clearance:update",
    },
    "Administrator": {
        "withdrawal:read",
        "withdrawal:update",
        "procedure:manage",
        "users:manage",
        "audit:read",
    },
}


def get_bearer_token(request: Request) -> str | None:
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return None

    scheme, _, token = auth_header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header must use Bearer token format.",
        )
    return token


def get_current_user(request: Request) -> dict[str, Any] | None:
    token = get_bearer_token(request)
    if token is None:
        return None

    try:
        payload = decode_access_token(token)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
        ) from exc

    if not payload.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token missing subject claim.",
        )
    return payload


def require_permission(request: Request, permission: str) -> dict[str, Any] | None:
    user = get_current_user(request)
    if user is None:
        return None

    role = user.get("role")
    if permission not in ROLE_PERMISSIONS.get(role, set()):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to perform this action.",
        )
    return user


def require_student_access(request: Request, student_id: str) -> dict[str, Any] | None:
    user = get_current_user(request)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication is required to access student data.",
        )

    if user.get("role") != "Student":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This route is restricted to student accounts.",
        )

    if user.get("sub", "").upper() != student_id.upper().strip():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own student data.",
        )
    return user


def require_any_role(request: Request, allowed_roles: set[str]) -> dict[str, Any] | None:
    user = get_current_user(request)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication is required for this staff/admin route.",
        )

    if user.get("role") not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this staff/admin route.",
        )
    return user


def ensure_permission(role: str, permission: str) -> None:
    if permission not in ROLE_PERMISSIONS.get(role, set()):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to perform this action.",
        )
