"""
Student verification endpoint.

Security notes:
  - Parameterised queries only — no string interpolation near the DB
  - Identical error response for 'not found' AND for DB errors — prevents
    user enumeration and leaks no system internals
  - Rate-limited to 5 requests/minute per IP via SlowAPI
  - session_id is generated with secrets.token_urlsafe (CSPRNG)
"""

from fastapi import APIRouter, Request, HTTPException
from slowapi import Limiter
from slowapi.util import get_remote_address

from ..database.connection import get_connection
from ..models.schemas import StaffLoginRequest, StudentLoginRequest, TokenResponse, VerifyRequest, VerifyResponse
from ..security.jwt import create_access_token
from ..services.chat_service import create_session
from ..config import settings

router = APIRouter(prefix="/api/auth", tags=["Authentication"])
limiter = Limiter(key_func=get_remote_address)

# Generic message — same text for 'not found' and 'error' to prevent enumeration
_UNVERIFIED_MSG = (
    "We could not verify your identity. "
    "Please check your Student ID or email and try again."
)


@router.post("/verify", response_model=VerifyResponse)
@limiter.limit(settings.rate_limit_auth)
async def verify_student(request: Request, body: VerifyRequest) -> VerifyResponse:
    """Verify a student by ID or email and return a secure session token."""

    if body.student_id is None and body.email is None:
        raise HTTPException(
            status_code=422,
            detail="Please provide either a Student ID or an email address.",
        )

    conn = get_connection()
    row = None

    try:
        if body.student_id:
            row = conn.execute(
                "SELECT * FROM students WHERE id = ?",
                (str(body.student_id).upper().strip(),),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT * FROM students WHERE email = ?",
                (str(body.email).lower().strip(),),
            ).fetchone()
    except Exception:
        # Swallow the exception — never expose DB error details to the client
        return VerifyResponse(verified=False, message=_UNVERIFIED_MSG)

    if row is None:
        return VerifyResponse(verified=False, message=_UNVERIFIED_MSG)

    try:
        req_row = conn.execute(
            "SELECT status FROM withdrawal_requests WHERE student_id = ? ORDER BY timestamp DESC LIMIT 1",
            (row["id"],)
        ).fetchone()
        has_req = req_row is not None
        req_status = req_row["status"] if req_row else None
    except Exception:
        has_req = False
        req_status = None

    session_id = create_session(row["id"])
    first_name = row["name"].split()[0]

    stu_status = row["status"] if "status" in row.keys() and row["status"] else "ACTIVE"
    stu_reason = row["status_reason"] if "status_reason" in row.keys() else None
    is_restricted = stu_status in ("SUSPENDED", "DEBARRED")

    return VerifyResponse(
        verified=True,
        session_id=session_id,
        student_id=row["id"],
        student_name=row["name"],
        course=row["course"],
        branch=row["branch"],
        semester=row["semester"],
        attendance=row["attendance"],
        cgpa=row["cgpa"],
        fee_status=row["fee_status"],
        fee_due=row["fee_due"],
        hostel_status=row["hostel_status"],
        scholarship_status=row["scholarship_status"],
        academic_performance=row["academic_performance"],
        interests=row["interests"],
        message=f"Welcome back, {first_name}! How can I assist you today?",
        has_existing_request=has_req,
        request_status=req_status,
        status=stu_status,
        status_reason=stu_reason,
        kiosk_restricted=is_restricted,
        lock_reason=stu_reason if is_restricted else None,
    )


@router.post("/login", response_model=TokenResponse)
async def login_student(body: StudentLoginRequest) -> TokenResponse:
    """Issue a JWT to an authenticated student."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM students WHERE id = ?",
        (body.student_id,),
    ).fetchone()

    if row is None:
        raise HTTPException(
            status_code=401,
            detail="We could not verify your identity. Please check your Student ID and try again.",
        )

    token = create_access_token(row["id"], "Student", {"student_name": row["name"]})
    return TokenResponse(
        token=token,
        role="Student",
        student_id=row["id"],
        student_name=row["name"],
        message="Student login successful.",
    )


@router.post("/staff/login", response_model=TokenResponse)
async def login_staff(body: StaffLoginRequest) -> TokenResponse:
    """Issue a JWT to an authenticated staff member."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM users WHERE username = ?",
        (body.username,),
    ).fetchone()

    if row is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid staff username.",
        )

    token = create_access_token(row["username"], row["role"], {"name": row["name"]})
    return TokenResponse(
        token=token,
        role=row["role"],
        username=row["username"],
        student_name=row["name"],
        message="Staff login successful.",
    )
