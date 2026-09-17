"""
Pydantic v2 request/response schemas.

Security note: Strict field validators and length limits act as a first line
of defence against malformed or oversized payloads before they reach the DB layer.
"""

from __future__ import annotations

import re
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


class VerifyRequest(BaseModel):
    """Accepts either student_id OR email — at least one must be provided."""

    student_id: Optional[str] = Field(None, min_length=3, max_length=20)
    email: Optional[EmailStr] = None

    @field_validator("student_id", mode="before")
    @classmethod
    def sanitize_student_id(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        # Whitelist: alphanumeric + hyphen/underscore only.
        # Rejects SQL meta-characters: ', ", ;, --, etc.
        if not re.match(r"^[A-Za-z0-9_\-]+$", v):
            raise ValueError("student_id contains invalid characters")
        return v.upper().strip()


class VerifyResponse(BaseModel):
    verified: bool
    session_id: Optional[str] = None
    student_name: Optional[str] = None
    course: Optional[str] = None
    student_id: Optional[str] = None
    branch: Optional[str] = None
    semester: Optional[int] = None
    attendance: Optional[float] = None
    cgpa: Optional[float] = None
    fee_status: Optional[str] = None
    fee_due: Optional[float] = None
    hostel_status: Optional[str] = None
    scholarship_status: Optional[str] = None
    academic_performance: Optional[str] = None
    interests: Optional[str] = None
    message: str
    has_existing_request: bool = False
    request_status: Optional[str] = None
    status: Optional[str] = "ACTIVE"
    status_reason: Optional[str] = None
    kiosk_restricted: bool = False
    lock_reason: Optional[str] = None


class StudentLoginRequest(BaseModel):
    student_id: str = Field(..., min_length=3, max_length=20)

    @field_validator("student_id", mode="before")
    @classmethod
    def sanitize_student_id(cls, v: str) -> str:
        if not re.match(r"^[A-Za-z0-9_\-]+$", v):
            raise ValueError("student_id contains invalid characters")
        return v.upper().strip()


class StaffLoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)

    @field_validator("username", mode="before")
    @classmethod
    def sanitize_username(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("username cannot be empty")
        return stripped


class TokenResponse(BaseModel):
    token: str
    role: str
    student_id: Optional[str] = None
    username: Optional[str] = None
    student_name: Optional[str] = None
    message: str


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------


class ChatRequest(BaseModel):
    session_id: Optional[str] = Field(None, min_length=16, max_length=64)
    student_id: Optional[str] = Field(None, min_length=3, max_length=20)
    message: str = Field(..., min_length=1, max_length=2000)

    @field_validator("message", mode="before")
    @classmethod
    def strip_and_validate(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Message cannot be empty or whitespace only")
        return stripped


class ChatResponse(BaseModel):
    reply: str
    state: Literal[
        "ASK_REASON",
        "SUGGEST",
        "CONFIRM",
        "DONE",
        "RESOLVED",
        "INVALID",
        "ROUTED",
        "GRIEVANCE_CATEGORY",
        "GRIEVANCE_DESCRIPTION",
        "GRIEVANCE_CONFIRM",
    ]
    intent: Optional[str] = None
    sentiment: Optional[str] = None
    ai_source: Optional[str] = None
    memory_summary: Optional[str] = None
    escalation_recommended: bool = False
    withdrawal_submitted: bool = False


# ---------------------------------------------------------------------------
# Student lifecycle APIs
# ---------------------------------------------------------------------------


class BackpaperRequest(BaseModel):
    student_id: str = Field(..., min_length=3, max_length=20)
    exam_id: int

    @field_validator("student_id", mode="before")
    @classmethod
    def sanitize_student_id(cls, v: str) -> str:
        if not re.match(r"^[A-Za-z0-9_\-]+$", v):
            raise ValueError("student_id contains invalid characters")
        return v.upper().strip()


class ScholarshipApply(BaseModel):
    student_id: str = Field(..., min_length=3, max_length=20)
    scholarship_id: int

    @field_validator("student_id", mode="before")
    @classmethod
    def sanitize_student_id(cls, v: str) -> str:
        if not re.match(r"^[A-Za-z0-9_\-]+$", v):
            raise ValueError("student_id contains invalid characters")
        return v.upper().strip()


class GrievanceCreate(BaseModel):
    student_id: str = Field(..., min_length=3, max_length=20)
    category: Literal["academic", "fee", "hostel", "exam", "scholarship"]
    description: str = Field(..., min_length=5, max_length=2000)

    @field_validator("student_id", mode="before")
    @classmethod
    def sanitize_student_id(cls, v: str) -> str:
        if not re.match(r"^[A-Za-z0-9_\-]+$", v):
            raise ValueError("student_id contains invalid characters")
        return v.upper().strip()

    @field_validator("description", mode="before")
    @classmethod
    def strip_description(cls, v: str) -> str:
        return v.strip()


# ---------------------------------------------------------------------------
# Admin and document APIs
# ---------------------------------------------------------------------------


class StatusUpdate(BaseModel):
    status: Literal["approved", "rejected"]


class GrievanceResolve(BaseModel):
    resolution: str = Field(..., min_length=3, max_length=2000)

    @field_validator("resolution", mode="before")
    @classmethod
    def strip_resolution(cls, v: str) -> str:
        return v.strip()


class ScholarshipApplicationUpdate(BaseModel):
    status: Literal["approved", "rejected"]


class BackpaperPaymentUpdate(BaseModel):
    status: Literal["registered", "paid"]


class DocumentVerification(BaseModel):
    status: Literal["verified", "fraud_detected", "error"]
    notes: Optional[str] = Field(None, max_length=2000)

    @field_validator("notes", mode="before")
    @classmethod
    def strip_notes(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if isinstance(v, str) else v


# ---------------------------------------------------------------------------
# Multi-Department Clearance & Voucher Schemas (Phase 21)
# ---------------------------------------------------------------------------


class ClearanceGateItem(BaseModel):
    department: Literal["LIBRARY", "HOSTEL", "ACCOUNTS", "REGISTRAR"]
    sequence_order: int
    status: Literal["PENDING", "CLEARED", "DUES_FLAGGED"] = "PENDING"
    officer_name: Optional[str] = None
    officer_id: Optional[str] = None
    cleared_at: Optional[str] = None
    notes: Optional[str] = None
    dues_amount: float = 0.0


class DepartmentClearActionRequest(BaseModel):
    action: Literal["CLEAR", "FLAG_DUES"]
    officer_name: str = Field(..., min_length=2, max_length=100)
    officer_id: str = Field(..., min_length=2, max_length=50)
    notes: Optional[str] = Field(None, max_length=1000)
    dues_amount: Optional[float] = 0.0


class ClearanceVoucherResponse(BaseModel):
    reference_no: str
    student_id: str
    student_name: str
    course: str
    semester: int
    submission_date: str
    current_status: str
    ordinance_clause: str
    gross_fee_paid: float
    refund_percentage: float
    deductions: float
    net_refundable_amount: float
    caution_deposit_balance: float
    gates: list[ClearanceGateItem] = []


class OffsetDepositRequest(BaseModel):
    department: Literal["LIBRARY", "HOSTEL", "ACCOUNTS", "REGISTRAR"]
    amount: float = Field(..., gt=0, description="Dues amount to offset against caution deposit")
    reason: str = Field(..., min_length=3, max_length=255, description="Reason for fine, e.g. 'Lost ID Card replacement fee'")
    student_consent: bool = Field(True, description="Explicit acknowledgment to deduct from refundable deposit")
    authorized_by: Optional[str] = Field("Finance Officer", max_length=100)


class DepositLedgerTransaction(BaseModel):
    id: int
    department: str
    amount: float
    reason: str
    authorized_by: str
    created_at: str


class DepositLedgerResponse(BaseModel):
    reference_no: str
    student_id: str
    original_deposit: float
    total_offset: float
    remaining_balance: float
    transactions: list[DepositLedgerTransaction] = []

