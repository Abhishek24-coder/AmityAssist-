"""Structured withdrawal workflow endpoints for Phase 1 UNIASSIST MVP & Phase 21 Clearance Pipeline."""

from typing import Optional
from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field

from ..models.schemas import DepartmentClearActionRequest, OffsetDepositRequest, DepositLedgerResponse
from ..services.token_pdf_service import generate_token_slip_pdf
from ..services.withdrawal_workflow import (
    create_withdrawal_request,
    get_clearance_voucher,
    get_deposit_ledger,
    get_latest_withdrawal_status,
    get_required_documents,
    get_withdrawal_guide,
    offset_dues_from_caution_deposit,
    process_department_clearance,
)

router = APIRouter(prefix="/api/withdrawal", tags=["Withdrawal Workflow"])


class WithdrawalApplyRequest(BaseModel):
    student_id: str = Field(..., min_length=2, max_length=50)
    reason: str = Field(..., min_length=2, max_length=200)
    intent: Optional[str] = "withdrawal_official"


@router.get("/guide")
async def withdrawal_guide():
    """Return official steps, documents, forms, departments, and timelines."""
    return get_withdrawal_guide()


@router.get("/documents")
async def withdrawal_documents(reason: str | None = None):
    """Return required documents for a withdrawal reason."""
    return {"documents": get_required_documents(reason)}


@router.get("/status/{student_id}")
async def withdrawal_status(student_id: str):
    """Return latest withdrawal request, generated checklist, 4-gate clearance pipeline, and voucher."""
    return get_latest_withdrawal_status(student_id)


@router.post("/apply")
async def apply_withdrawal(req: WithdrawalApplyRequest):
    """Submit an official withdrawal application, initializing 4 sequential clearance gates and voucher."""
    reference_no = create_withdrawal_request(req.student_id, req.reason, req.intent or "withdrawal_official")
    voucher = get_clearance_voucher(reference_no)
    return {
        "success": True,
        "reference_no": reference_no,
        "message": "Withdrawal clearance pipeline initiated successfully.",
        "voucher": voucher,
    }


@router.post("/{reference_no}/clear/{department}")
async def clear_department_gate(
    reference_no: str,
    department: str,
    payload: DepartmentClearActionRequest,
):
    """Sign off on a department clearance gate (CLEAR or FLAG_DUES) with officer details and audit notes."""
    try:
        result = process_department_clearance(
            reference_no=reference_no,
            department=department,
            action=payload.action,
            officer_name=payload.officer_name,
            officer_id=payload.officer_id,
            notes=payload.notes,
            dues_amount=payload.dues_amount or 0.0,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/voucher/{reference_no}")
async def fetch_clearance_voucher(reference_no: str):
    """Fetch standardized pre-itemized fee voucher citing UGC regulations."""
    voucher = get_clearance_voucher(reference_no)
    if not voucher:
        raise HTTPException(status_code=404, detail=f"Clearance voucher not found for reference {reference_no}")
    return voucher


@router.post("/{reference_no}/offset-dues")
async def offset_department_dues(reference_no: str, payload: OffsetDepositRequest):
    """Smart financial offsetting: Deduct minor asset/book fines from caution deposit instead of freezing refunds."""
    try:
        result = offset_dues_from_caution_deposit(
            reference_no=reference_no,
            department=payload.department,
            amount=payload.amount,
            reason=payload.reason,
            authorized_by=payload.authorized_by or "Finance Officer",
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{reference_no}/deposit-ledger")
async def fetch_deposit_ledger(reference_no: str):
    """Fetch caution deposit ledger balance and deduction transaction history."""
    ledger = get_deposit_ledger(reference_no)
    if not ledger:
        raise HTTPException(status_code=404, detail=f"Deposit ledger not found for reference {reference_no}")
    return ledger


@router.get("/{reference_no}/slip")
async def download_token_slip(reference_no: str):
    """Generate and return official printable 1-page PDF token slip with 2D vector QR code."""
    voucher = get_clearance_voucher(reference_no)
    if not voucher:
        raise HTTPException(status_code=404, detail=f"Clearance record not found for reference {reference_no}")

    tracking_url = f"https://kiosk.amity.edu/track?ref={reference_no}"
    pdf_bytes = generate_token_slip_pdf(reference_no, voucher, tracking_url=tracking_url)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="TOKEN-{reference_no}.pdf"',
        },
    )


@router.get("/track/{reference_no}")
async def public_track_clearance(reference_no: str):
    """Public remote tracking endpoint accessible via smartphone camera QR scan anywhere in the world."""
    voucher = get_clearance_voucher(reference_no)
    if not voucher:
        raise HTTPException(status_code=404, detail=f"Tracking record not found for reference {reference_no}")

    return {
        "reference_no": voucher["reference_no"],
        "student_id": voucher["student_id"],
        "student_name": voucher["student_name"],
        "course": voucher["course"],
        "submission_date": voucher["submission_date"],
        "current_status": voucher["current_status"],
        "ordinance_clause": voucher["ordinance_clause"],
        "gates": voucher["gates"],
        "net_refundable_amount": voucher["net_refundable_amount"],
        "caution_deposit_balance": voucher["caution_deposit_balance"],
        "tracking_url": f"https://kiosk.amity.edu/track?ref={reference_no}",
        "is_completed": voucher["current_status"].lower() == "completed",
    }
