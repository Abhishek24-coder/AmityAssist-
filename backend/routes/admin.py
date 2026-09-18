"""
Admin/Staff portal endpoints for grievance management, document audit, and request approval.

Supports multi-role staff: Registrar, Department Coordinator, Finance, Scholarship, etc.
"""

import json

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from ..database.connection import get_connection
from ..models.schemas import DocumentVerification
from ..security.rbac import require_any_role

router = APIRouter(prefix="/api/admin", tags=["Admin"])

# ── Request Status Models ──────────────────────────────────────────────────────
class StatusUpdate(BaseModel):
    status: str

# ── Withdrawal Requests Management ──────────────────────────────────────────────
@router.get("/requests")
async def get_all_requests(request: Request = None):
    """Get all withdrawal requests for admin review."""
    require_any_role(request, {"Registrar", "Administrator", "Department Coordinator", "Finance Department", "Scholarship Department", "Examination Cell"})
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT w.id, w.student_id, COALESCE(s.name, w.student_id) AS name, 
                      w.reason, w.status, w.timestamp, w.reference_no, d.file_path 
               FROM withdrawal_requests w
               LEFT JOIN students s ON w.student_id = s.id
               LEFT JOIN documents d ON w.student_id = d.student_id
               ORDER BY w.timestamp DESC"""
        ).fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to fetch requests.")

@router.get("/conversation/{student_id}")
async def get_conversation(student_id: str, request: Request = None):
    """Get conversation history for a student's withdrawal session."""
    require_any_role(request, {"Registrar", "Administrator", "Department Coordinator", "Finance Department", "Scholarship Department", "Examination Cell"})
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT sender, message, timestamp FROM conversations WHERE student_id = ? ORDER BY timestamp ASC",
            (student_id.upper().strip(),)
        ).fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to fetch conversation log.")

@router.post("/requests/{req_id}/status")
async def update_request_status(req_id: int, body: StatusUpdate, request: Request = None):
    """Update withdrawal request status (approved/rejected)."""
    require_any_role(request, {"Registrar", "Administrator", "Department Coordinator", "Finance Department", "Scholarship Department", "Examination Cell"})
    if body.status not in ("approved", "rejected"):
        raise HTTPException(status_code=400, detail="Invalid status. Use 'approved' or 'rejected'.")
        
    conn = get_connection()
    try:
        row = conn.execute("SELECT student_id FROM withdrawal_requests WHERE id = ?", (req_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Request not found")
            
        conn.execute(
            "UPDATE withdrawal_requests SET status = ? WHERE id = ?",
            (body.status, req_id)
        )
        conn.commit()
        
        # Mock email notification (in production, integrate with email service)
        return {
            "message": f"Request {req_id} marked as {body.status}",
            "student_id": row["student_id"],
            "notification_sent": True
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail="Database error updating status.")


# ── Grievance Management ────────────────────────────────────────────────────────
class GrievanceResolve(BaseModel):
    resolution: str

@router.get("/grievances")
async def get_all_grievances(request: Request = None):
    """Get all grievances for admin/coordinator review."""
    require_any_role(request, {"Registrar", "Administrator", "Department Coordinator", "Finance Department", "Scholarship Department", "Examination Cell"})
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT g.*, s.name as student_name 
               FROM grievances g
               JOIN students s ON g.student_id = s.id
               ORDER BY g.timestamp DESC"""
        ).fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to fetch grievances.")

@router.get("/grievances/{grievance_id}")
async def get_grievance(grievance_id: int):
    """Get details of a specific grievance."""
    conn = get_connection()
    row = conn.execute(
        """SELECT g.*, s.name as student_name, s.email
           FROM grievances g
           JOIN students s ON g.student_id = s.id
           WHERE g.id = ?""",
        (grievance_id,)
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Grievance not found.")
    return dict(row)

@router.post("/grievances/{grievance_id}/resolve")
async def resolve_grievance(grievance_id: int, body: GrievanceResolve, request: Request = None):
    """Mark grievance as resolved with resolution notes."""
    require_any_role(request, {"Registrar", "Administrator", "Department Coordinator", "Finance Department", "Scholarship Department", "Examination Cell"})
    conn = get_connection()
    row = conn.execute("SELECT id FROM grievances WHERE id = ?", (grievance_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Grievance not found.")
    
    conn.execute(
        "UPDATE grievances SET status = 'resolved', resolution = ? WHERE id = ?",
        (body.resolution, grievance_id)
    )
    conn.commit()
    
    return {
        "message": f"Grievance {grievance_id} resolved successfully",
        "resolution": body.resolution,
        "notification_sent": True
    }

@router.post("/grievances/{grievance_id}/in-progress")
async def mark_grievance_in_progress(grievance_id: int):
    """Mark a grievance as 'in progress' by a staff member."""
    conn = get_connection()
    row = conn.execute("SELECT id FROM grievances WHERE id = ?", (grievance_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Grievance not found.")
    
    conn.execute(
        "UPDATE grievances SET status = 'in_progress' WHERE id = ?",
        (grievance_id,)
    )
    conn.commit()
    
    return {"message": f"Grievance {grievance_id} marked as in progress"}


# ── Scholarship Applications Management ──────────────────────────────────────────
@router.get("/scholarship-applications")
async def get_scholarship_applications():
    """Get all scholarship applications for review."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT sa.*, s.name as student_name, sch.name as scholarship_name 
               FROM scholarship_applications sa
               JOIN students s ON sa.student_id = s.id
               JOIN scholarships sch ON sa.scholarship_id = sch.id
               ORDER BY sa.timestamp DESC"""
        ).fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to fetch applications.")

class ScholarshipApplicationUpdate(BaseModel):
    status: str  # "approved" or "rejected"

@router.post("/scholarship-applications/{app_id}/status")
async def update_scholarship_application(app_id: int, body: ScholarshipApplicationUpdate):
    """Approve or reject a scholarship application."""
    if body.status not in ("approved", "rejected"):
        raise HTTPException(status_code=400, detail="Status must be 'approved' or 'rejected'.")
    
    conn = get_connection()
    row = conn.execute("SELECT student_id FROM scholarship_applications WHERE id = ?", (app_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Application not found.")
    
    conn.execute(
        "UPDATE scholarship_applications SET status = ? WHERE id = ?",
        (body.status, app_id)
    )
    conn.commit()
    
    return {
        "message": f"Scholarship application {app_id} marked as {body.status}",
        "notification_sent": True
    }


# ── Back Paper Payment Tracking ──────────────────────────────────────────────────
@router.get("/backpapers")
async def get_backpaper_registrations():
    """Get all back-paper registrations for tracking."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """SELECT e.*, s.name as student_name 
               FROM examinations e
               JOIN students s ON e.student_id = s.id
               WHERE e.backpaper_status != 'none'
               ORDER BY e.exam_date ASC"""
        ).fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to fetch back papers.")

class BackpaperPaymentUpdate(BaseModel):
    status: str  # "registered" or "paid"

@router.post("/backpapers/{exam_id}/payment")
async def update_backpaper_payment(exam_id: int, body: BackpaperPaymentUpdate):
    """Mark back-paper fee as paid."""
    if body.status not in ("registered", "paid"):
        raise HTTPException(status_code=400, detail="Status must be 'registered' or 'paid'.")
    
    conn = get_connection()
    row = conn.execute("SELECT id FROM examinations WHERE id = ?", (exam_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Exam record not found.")
    
    conn.execute(
        "UPDATE examinations SET backpaper_status = ? WHERE id = ?",
        (body.status, exam_id)
    )
    conn.commit()
    
    return {"message": f"Back-paper {exam_id} marked as {body.status}"}


# ── Dashboard Stats ────────────────────────────────────────────────────────────
# Document Audit & Verification
def _document_row_to_dict(row):
    data = dict(row)
    if data.get("ocr_data"):
        try:
            data["ocr_data"] = json.loads(data["ocr_data"])
        except json.JSONDecodeError:
            data["ocr_data"] = None
    return data


@router.get("/documents")
async def get_documents_for_audit(request: Request):
    """Fetch uploaded documents with OCR/fraud audit data for staff review."""
    require_any_role(request, {"Registrar", "Administrator", "Department Coordinator", "Finance Department", "Scholarship Department", "Examination Cell"})
    conn = get_connection()
    rows = conn.execute(
        """SELECT d.*, s.name as student_name
           FROM documents d
           JOIN students s ON d.student_id = s.id
           ORDER BY d.timestamp DESC"""
    ).fetchall()
    return [_document_row_to_dict(r) for r in rows]


@router.post("/documents/{doc_id}/verify")
async def verify_audited_document(doc_id: int, body: DocumentVerification, request: Request):
    """Mark an uploaded document as verified, fraudulent, or errored."""
    require_any_role(request, {"Registrar", "Administrator", "Department Coordinator", "Finance Department", "Scholarship Department", "Examination Cell"})
    conn = get_connection()
    row = conn.execute("SELECT id FROM documents WHERE id = ?", (doc_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Document not found.")

    conn.execute(
        "UPDATE documents SET verification_status = ?, verification_notes = ? WHERE id = ?",
        (body.status, body.notes, doc_id)
    )
    conn.commit()
    return {"message": f"Document {doc_id} marked as {body.status}.", "notes": body.notes}


@router.get("/stats")
async def get_admin_stats(request: Request):
    """Get overall admin dashboard statistics."""
    require_any_role(request, {"Registrar", "Administrator", "Department Coordinator", "Finance Department", "Scholarship Department", "Examination Cell"})
    conn = get_connection()
    
    total_students = conn.execute("SELECT COUNT(*) as count FROM students").fetchone()["count"]
    pending_withdrawals = conn.execute("SELECT COUNT(*) as count FROM withdrawal_requests WHERE status = 'pending'").fetchone()["count"]
    open_grievances = conn.execute("SELECT COUNT(*) as count FROM grievances WHERE status = 'open'").fetchone()["count"]
    documents_pending_verification = conn.execute("SELECT COUNT(*) as count FROM documents WHERE verification_status = 'pending'").fetchone()["count"]
    fraud_flagged_docs = conn.execute("SELECT COUNT(*) as count FROM documents WHERE verification_status = 'fraud_detected'").fetchone()["count"]
    
    return {
        "total_students": total_students,
        "pending_withdrawals": pending_withdrawals,
        "open_grievances": open_grievances,
        "documents_pending_verification": documents_pending_verification,
        "fraud_flagged_documents": fraud_flagged_docs
    }
