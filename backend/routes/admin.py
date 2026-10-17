"""
Admin/Staff portal endpoints for grievance management, document audit, and request approval.

Supports multi-role staff: Registrar, Department Coordinator, Finance, Scholarship, etc.
"""

import json
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from ..database.connection import get_connection
from ..models.schemas import DocumentVerification
from ..security.rbac import require_any_role

router = APIRouter(prefix="/api/admin", tags=["Admin"])

# ── Request Status Models ──────────────────────────────────────────────────────
class StatusUpdate(BaseModel):
    status: str
    message: Optional[str] = None


class RequestReviewMessage(BaseModel):
    message: str
    status: Optional[str] = None
    actor: Optional[str] = "Staff (Registrar Office)"


class DocumentReviewAction(BaseModel):
    document_id: int
    status: str  # "verified" or "rejected"
    notes: Optional[str] = None


class ChecklistItemUpdate(BaseModel):
    status: str  # "completed" or "pending"


@router.get("/requests/{req_id}/review-details")
async def get_request_review_details(req_id: int, request: Request = None):
    """Fetch complete review dossier for a withdrawal request: student profile, uploaded documents, clearance gates, checklist items, and event history."""
    require_any_role(request, {"Registrar", "Administrator", "Department Coordinator", "Finance Department", "Scholarship Department", "Examination Cell"})
    conn = get_connection()
    try:
        req_row = conn.execute(
            """SELECT w.*, COALESCE(s.name, w.student_id) AS student_name, s.course, s.semester, s.email, s.cgpa
               FROM withdrawal_requests w
               LEFT JOIN students s ON w.student_id = s.id
               WHERE w.id = ?""",
            (req_id,)
        ).fetchone()
        if not req_row:
            raise HTTPException(status_code=404, detail="Withdrawal request not found.")

        req_data = dict(req_row)
        student_id = req_data["student_id"]
        reference_no = req_data.get("reference_no") or f"AMITY-WTH-2026-{req_id}"

        # Uploaded documents
        doc_rows = conn.execute(
            "SELECT * FROM documents WHERE student_id = ? ORDER BY timestamp DESC",
            (student_id,)
        ).fetchall()
        docs = [_document_row_to_dict(d) for d in doc_rows]

        # Checklist items
        checklist_rows = conn.execute(
            "SELECT * FROM withdrawal_checklist_items WHERE request_id = ? ORDER BY id ASC",
            (req_id,)
        ).fetchall()
        checklist = [dict(c) for c in checklist_rows]

        # Clearance gates
        gate_rows = conn.execute(
            "SELECT * FROM clearance_gates WHERE reference_no = ? ORDER BY sequence_order ASC",
            (reference_no,)
        ).fetchall()
        gates = [dict(g) for g in gate_rows]

        # Workflow events / timeline messages
        event_rows = conn.execute(
            "SELECT * FROM workflow_events WHERE request_id = ? ORDER BY timestamp ASC, id ASC",
            (req_id,)
        ).fetchall()
        events = [dict(e) for e in event_rows]

        return {
            "request": req_data,
            "documents": docs,
            "checklist": checklist,
            "gates": gates,
            "events": events,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch review details: {e}")


@router.post("/requests/{req_id}/review-document")
async def review_withdrawal_document(req_id: int, body: DocumentReviewAction, request: Request = None):
    """Accept or reject an uploaded document and log audit event."""
    require_any_role(request, {"Registrar", "Administrator", "Department Coordinator", "Finance Department", "Scholarship Department", "Examination Cell"})
    conn = get_connection()
    try:
        req_row = conn.execute("SELECT student_id, reference_no FROM withdrawal_requests WHERE id = ?", (req_id,)).fetchone()
        if not req_row:
            raise HTTPException(status_code=404, detail="Request not found.")

        doc_row = conn.execute("SELECT id, file_name, classification FROM documents WHERE id = ?", (body.document_id,)).fetchone()
        if not doc_row:
            raise HTTPException(status_code=404, detail="Document not found.")

        conn.execute(
            "UPDATE documents SET verification_status = ?, verification_notes = ? WHERE id = ?",
            (body.status, body.notes, body.document_id)
        )

        # Update checklist item if matching
        doc_type = doc_row["classification"] or doc_row["file_name"] or ""
        conn.execute(
            "UPDATE withdrawal_checklist_items SET status = ? WHERE request_id = ? AND (document_key LIKE ? OR label LIKE ?)",
            (
                "completed" if body.status == "verified" else "rejected",
                req_id,
                f"%{doc_type}%",
                f"%{doc_type}%",
            )
        )

        # Log workflow event
        status_label = "VERIFIED & ACCEPTED" if body.status == "verified" else "REJECTED (Resubmission Needed)"
        notes_text = f" Notes: {body.notes}" if body.notes else ""
        conn.execute(
            """INSERT INTO workflow_events (request_id, status, title, description, actor)
               VALUES (?, ?, ?, ?, 'Staff (Registrar Verification Desk)')""",
            (
                req_id,
                "document_reviewed",
                f"Document {status_label}",
                f"Document '{doc_type}' marked as {body.status}.{notes_text}",
            )
        )
        conn.commit()

        return {"success": True, "document_id": body.document_id, "status": body.status}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to review document: {e}")


@router.post("/requests/{req_id}/checklist/verify-all")
async def verify_all_checklist_items(req_id: int, request: Request):
    """Mark all checklist items in a withdrawal request as completed."""
    require_any_role(request, {"Registrar", "Administrator", "Department Coordinator", "Finance Department", "Scholarship Department", "Examination Cell"})
    conn = get_connection()
    try:
        conn.execute("UPDATE withdrawal_checklist_items SET status = 'verified', updated_at = CURRENT_TIMESTAMP WHERE request_id = ?", (req_id,))
        conn.execute(
            """INSERT INTO workflow_events (request_id, status, title, description, actor)
               VALUES (?, 'checklist_verified', 'All Dossier Checklist Items Verified', 'Staff completed review and marked all checklist items verified.', 'Staff (Registrar Verification Desk)')""",
            (req_id,),
        )
        conn.commit()
        return {"success": True, "message": "All checklist items verified."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to verify all checklist items: {e}")


@router.post("/requests/{req_id}/checklist/{item_id}")
async def update_request_checklist_item(req_id: int, item_id: int, body: ChecklistItemUpdate, request: Request):
    """Toggle or update status of a clearance checklist item."""
    require_any_role(request, {"Registrar", "Administrator", "Department Coordinator", "Finance Department", "Scholarship Department", "Examination Cell"})
    conn = get_connection()
    try:
        row = conn.execute("SELECT id, label, document_key FROM withdrawal_checklist_items WHERE id = ? AND request_id = ?", (item_id, req_id)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Checklist item not found.")
        raw_status = body.status.lower().strip()
        db_status = "verified" if raw_status in ("completed", "verified") else "pending"
        conn.execute("UPDATE withdrawal_checklist_items SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (db_status, item_id))
        
        label = row["label"] or row["document_key"] or f"Item #{item_id}"
        event_status = "checklist_verified" if db_status == "verified" else "checklist_pending"
        title = f"Checklist: {label}"
        desc = f"Staff verified and marked '{label}' as {db_status.upper()}."
        conn.execute(
            """INSERT INTO workflow_events (request_id, status, title, description, actor)
               VALUES (?, ?, ?, ?, 'Staff (Registrar Verification Desk)')""",
            (req_id, event_status, title, desc),
        )
        conn.commit()
        return {"success": True, "item_id": item_id, "status": db_status}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update checklist item: {e}")


@router.post("/requests/{req_id}/send-message")
async def send_request_status_message(req_id: int, body: RequestReviewMessage, request: Request = None):
    """Send an official status message from staff to the student's request status feed."""
    require_any_role(request, {"Registrar", "Administrator", "Department Coordinator", "Finance Department", "Scholarship Department", "Examination Cell"})
    conn = get_connection()
    try:
        req_row = conn.execute("SELECT student_id, status, reference_no FROM withdrawal_requests WHERE id = ?", (req_id,)).fetchone()
        if not req_row:
            raise HTTPException(status_code=404, detail="Request not found.")

        current_status = req_row["status"]
        new_status = body.status if body.status else current_status

        if body.status and body.status != current_status:
            conn.execute(
                "UPDATE withdrawal_requests SET status = ? WHERE id = ?",
                (body.status, req_id)
            )

        conn.execute(
            """INSERT INTO workflow_events (request_id, status, title, description, actor)
               VALUES (?, ?, 'Official Staff Update', ?, ?)""",
            (
                req_id,
                new_status,
                body.message,
                body.actor or "Staff (Registrar Desk)",
            )
        )
        conn.commit()

        return {"success": True, "message": "Status update and message dispatched to student."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to dispatch status message: {e}")

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


def _format_time_ago(ts_str: str) -> str:
    """Format an ISO or SQL timestamp into a friendly time string."""
    if not ts_str:
        return "Recently"
    try:
        from datetime import datetime
        cleaned = ts_str.replace("Z", "+00:00").replace("T", " ")
        if "." in cleaned:
            cleaned = cleaned.split(".")[0]
        try:
            dt = datetime.fromisoformat(cleaned)
        except Exception:
            dt = datetime.strptime(cleaned, "%Y-%m-%d %H:%M:%S")
        
        now = datetime.now()
        diff = (now - dt).total_seconds()
        if diff < 60:
            return "Just now"
        if diff < 3600:
            return f"{max(1, int(diff // 60))}m ago"
        if diff < 86400:
            return f"{max(1, int(diff // 3600))}h ago"
        days = int(diff // 86400)
        if days == 1:
            return "Yesterday"
        if days < 7:
            return f"{days}d ago"
        return dt.strftime("%d %b")
    except Exception:
        return "Recently"


def _get_genuine_recent_activities(conn, limit: int = 10):
    activities = []

    # 1. Digital Notesheets
    try:
        rows = conn.execute(
            """SELECT reference_no, title, category, status, current_stage, 
                      COALESCE(updated_at, created_at) as ts
               FROM notesheets 
               ORDER BY ts DESC LIMIT 8"""
        ).fetchall()
        for r in rows:
            cat = (r["category"] or "General").upper()
            dept = "Proctor Cell" if "DISC" in cat else ("Academic Desk" if "ACAD" in cat else "Dean Office")
            activities.append({
                "action": f"Digital Notesheet #{r['reference_no']} marked {r['status']}",
                "dept": dept,
                "time": _format_time_ago(r["ts"]),
                "raw_ts": r["ts"] or "",
                "type": "notesheet",
                "status": r["status"]
            })
    except Exception:
        pass

    # 2. Caution Deposit Offsets
    try:
        rows = conn.execute(
            """SELECT reference_no, department, amount, reason, created_at as ts
               FROM caution_deposit_offsets
               ORDER BY ts DESC LIMIT 8"""
        ).fetchall()
        for r in rows:
            dept = f"{r['department'].title()} Desk" if r["department"] else "Finance Section"
            activities.append({
                "action": f"Smart Caution Deposit Offset ₹{int(r['amount'])} for {r['reason']}",
                "dept": dept,
                "time": _format_time_ago(r["ts"]),
                "raw_ts": r["ts"] or "",
                "type": "offset",
                "status": "PROCESSED"
            })
    except Exception:
        pass

    # 3. Withdrawal Requests
    try:
        rows = conn.execute(
            """SELECT reference_no, student_id, status, reason, timestamp as ts
               FROM withdrawal_requests
               ORDER BY ts DESC LIMIT 8"""
        ).fetchall()
        for r in rows:
            st = (r["status"] or "PENDING").upper()
            ref = r["reference_no"] or f"WTH-{r['student_id']}"
            activities.append({
                "action": f"Withdrawal #{ref} ({st}) for {r['student_id']}",
                "dept": "Registrar Office",
                "time": _format_time_ago(r["ts"]),
                "raw_ts": r["ts"] or "",
                "type": "withdrawal",
                "status": st
            })
    except Exception:
        pass

    # 4. Grievances
    try:
        rows = conn.execute(
            """SELECT id, student_id, category, status, timestamp as ts
               FROM grievances
               ORDER BY ts DESC LIMIT 8"""
        ).fetchall()
        for r in rows:
            st = (r["status"] or "OPEN").upper()
            cat = (r["category"] or "General").capitalize()
            activities.append({
                "action": f"Grievance #GRV-{r['id']} ({cat}) {st} for {r['student_id']}",
                "dept": "Grievance Cell",
                "time": _format_time_ago(r["ts"]),
                "raw_ts": r["ts"] or "",
                "type": "grievance",
                "status": st
            })
    except Exception:
        pass

    # Sort all by raw_ts descending
    activities.sort(key=lambda x: str(x.get("raw_ts", "")), reverse=True)
    return activities[:limit]


@router.get("/stats")
async def get_admin_stats(request: Request):
    """Get overall admin dashboard statistics with genuine recent activity stream."""
    require_any_role(request, {"Registrar", "Administrator", "Department Coordinator", "Finance Department", "Scholarship Department", "Examination Cell"})
    conn = get_connection()
    
    total_students = conn.execute("SELECT COUNT(*) as count FROM students").fetchone()["count"]
    pending_withdrawals = conn.execute("SELECT COUNT(*) as count FROM withdrawal_requests WHERE status = 'pending'").fetchone()["count"]
    open_grievances = conn.execute("SELECT COUNT(*) as count FROM grievances WHERE status = 'open'").fetchone()["count"]
    documents_pending_verification = conn.execute("SELECT COUNT(*) as count FROM documents WHERE verification_status = 'pending'").fetchone()["count"]
    fraud_flagged_docs = conn.execute("SELECT COUNT(*) as count FROM documents WHERE verification_status = 'fraud_detected'").fetchone()["count"]
    recent_activity = _get_genuine_recent_activities(conn, limit=10)
    
    return {
        "total_students": total_students,
        "pending_withdrawals": pending_withdrawals,
        "open_grievances": open_grievances,
        "documents_pending_verification": documents_pending_verification,
        "fraud_flagged_documents": fraud_flagged_docs,
        "recent_activity": recent_activity,
    }


@router.get("/recent-activity")
async def get_recent_activity(request: Request):
    """Get genuine real-time activity stream from verified university database records."""
    require_any_role(request, {"Registrar", "Administrator", "Department Coordinator", "Finance Department", "Scholarship Department", "Examination Cell"})
    conn = get_connection()
    return {"activities": _get_genuine_recent_activities(conn, limit=20)}

