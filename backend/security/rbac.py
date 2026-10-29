# ==============================================================================
# UniAssist — Role-Based Access Control (RBAC) Specification
# Lead Architect: Abhishek Shrivastava
# ==============================================================================
from __future__ import annotations

from typing import Any, Dict, Set

from fastapi import HTTPException, Request, status

from .jwt import decode_access_token

# Complete 6-Tier Academic Hierarchy + Isolated Desk Officers
ROLE_PERMISSIONS: Dict[str, Set[str]] = {
    # ── Tier 1: Student ───────────────────────────────────────────────────────
    "Student": {
        "withdrawal:read_own",
        "withdrawal:create",
        "documents:upload",
        "profile:read_own",
        "grievance:create",
        "grievance:read_own",
    },
    # ── Tier 2: Specialized Desk Officers (Isolated Clearances) ───────────────
    "Librarian": {
        "clearance:read_library",
        "clearance:sign_library",
        "documents:read_assigned",
    },
    "Hostel Warden": {
        "clearance:read_hostel",
        "clearance:sign_hostel",
        "documents:read_assigned",
    },
    "Accounts Officer": {
        "clearance:read_accounts",
        "clearance:sign_accounts",
        "refund:calculate",
        "refund:disburse",
        "bank_proof:read_unmasked",     # Only Finance can see unmasked cheques
        "deposit_offset:approve",
    },
    "Registrar": {
        "clearance:read_all",
        "clearance:final_seal",
        "procedure:manage",
        "status:update_official",
    },
    # ── Tier 3: Faculty Supervisor / Coordinator ──────────────────────────────
    "Supervisor": {
        "notesheet:create",
        "notesheet:read_assigned",
        "notesheet:sign_tier1",
        "student:view_attendance",
    },
    # ── Tier 4: Head of Department (HOD) ──────────────────────────────────────
    "HOD": {
        "notesheet:read_department",
        "notesheet:sign_tier2",
        "notesheet:edit_inflight",      # Allowed to correct course codes/typos
        "accreditation:view_dept",
        "student:view_attendance",
    },
    # ── Tier 5: Head of Institution (HOI) / Dean ──────────────────────────────
    "Dean": {
        "notesheet:read_institution",
        "notesheet:sign_tier3",
        "notesheet:edit_inflight",      # Allowed to annotate with audit trail
        "grievance:resolve_escalated",
        "accreditation:view_inst",
        "student:status_proctorial",
    },
    # ── Tier 6: Executive Officers (Pro-VC & Vice Chancellor) ─────────────────
    "Pro-VC": {
        "notesheet:read_all",
        "notesheet:sign_tier4",
        "notesheet:edit_inflight",
        "accreditation:view_all",
    },
    "Vice Chancellor": {
        "notesheet:read_all",
        "notesheet:final_seal",         # Highest executive approval seal
        "notesheet:edit_inflight",
        "university:executive_override",
    },
    # ── Super Administrator (System & IT Maintenance) ─────────────────────────
    "Administrator": {
        "users:manage",
        "system:configure",
        "institution:white_label",
        "audit:read_full",
    },
}

# Mapping hierarchical approval stages to required signing roles
STAGE_REQUIRED_ROLE: Dict[str, str] = {
    "SUPERVISOR": "Supervisor",
    "HOD": "HOD",
    "HOI": "Dean",
    "PRO_VC": "Pro-VC",
    "VC": "Vice Chancellor",
}


def validate_notesheet_signing_authority(user_role: str, current_stage: str) -> None:
    """
    Enforces that only the designated authority for the current hierarchical
    stage can sign, forward, or apply the final seal to a notesheet.
    """
    if user_role in ("Administrator", "Vice Chancellor"):
        return   # VC and Super-Admin retain executive override privileges
    expected_role = STAGE_REQUIRED_ROLE.get(current_stage.upper())
    if not expected_role or user_role.upper() != expected_role.upper():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Unauthorized signing attempt: Notesheet is currently at '{current_stage}' stage. "
                f"Requires '{expected_role}' role credentials, but user has '{user_role}'."
            ),
        )


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
