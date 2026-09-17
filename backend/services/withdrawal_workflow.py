"""Withdrawal workflow guidance and checklist helpers.

Phase 1 keeps the implementation self-contained while moving withdrawal
support away from a chatbot-only shape. Procedure content is seeded in SQLite
and exposed through structured APIs for the UI, kiosk, or future Flutter app.
"""

from __future__ import annotations

import secrets
import uuid
from datetime import datetime
from typing import Any

from ..database.connection import get_connection
from .audit_service import record_audit_event


PROCEDURE_CODE = "withdrawal"
CLEARANCE_DEPARTMENTS = ["LIBRARY", "HOSTEL", "ACCOUNTS", "REGISTRAR"]


def generate_reference() -> str:
    year = datetime.utcnow().year
    suffix = secrets.token_hex(2).upper()
    return f"AMITY-WTH-{year}-{suffix}"


def _ensure_clearance_tables() -> None:
    conn = get_connection()
    conn.execute(
        """CREATE TABLE IF NOT EXISTS clearance_gates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reference_no TEXT NOT NULL,
            department TEXT NOT NULL,
            sequence_order INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'PENDING',
            officer_name TEXT,
            officer_id TEXT,
            cleared_at TEXT,
            notes TEXT,
            dues_amount REAL DEFAULT 0.0
        );"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS caution_deposit_ledger (
            reference_no TEXT PRIMARY KEY,
            student_id TEXT NOT NULL,
            original_deposit REAL NOT NULL DEFAULT 10000.0,
            current_balance REAL NOT NULL DEFAULT 10000.0,
            updated_at TEXT
        );"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS caution_deposit_offsets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reference_no TEXT NOT NULL,
            department TEXT NOT NULL,
            amount REAL NOT NULL,
            reason TEXT NOT NULL,
            authorized_by TEXT,
            created_at TEXT NOT NULL
        );"""
    )
    conn.commit()


def get_withdrawal_guide() -> dict[str, Any]:
    conn = get_connection()
    steps = conn.execute(
        """SELECT step_number, title, description, department, timeline_text, status_after
           FROM procedure_steps
           WHERE procedure_code = ?
           ORDER BY step_number ASC""",
        (PROCEDURE_CODE,),
    ).fetchall()
    documents = conn.execute(
        """SELECT document_key, name, description, mandatory, applicable_reason, form_url
           FROM procedure_documents
           WHERE procedure_code = ?
           ORDER BY mandatory DESC, id ASC""",
        (PROCEDURE_CODE,),
    ).fetchall()
    forms = conn.execute(
        """SELECT form_key, name, description, download_url, issuing_department
           FROM procedure_forms
           WHERE procedure_code = ?
           ORDER BY id ASC""",
        (PROCEDURE_CODE,),
    ).fetchall()

    return {
        "procedure_code": PROCEDURE_CODE,
        "title": "Withdrawal Intelligence System",
        "summary": (
            "Structured guidance for students who want to understand, prepare, "
            "submit, and track an official university withdrawal request."
        ),
        "principle": (
            "UNIASSIST provides official procedure guidance and timeline bands. "
            "It does not predict approval, rejection, or exact refund dates."
        ),
        "steps": [dict(row) for row in steps],
        "documents": [_normalise_document(dict(row)) for row in documents],
        "forms": [dict(row) for row in forms],
        "departments": [
            "Student",
            "Academic Department",
            "Registrar Office",
            "Library",
            "Hostel Office",
            "Finance Office",
            "Accounts/Refund Desk",
        ],
        "official_timeline": [
            {
                "stage": "Initial verification",
                "timeline": "Generally 1-2 working days after submission.",
            },
            {
                "stage": "Department clearances",
                "timeline": "Generally 3-5 working days, depending on pending dues or records.",
            },
            {
                "stage": "Finance and refund processing",
                "timeline": "Generally 7-10 working days after all required clearances.",
            },
        ],
        "statuses": [
            "draft",
            "pending",
            "submitted",
            "under_review",
            "documents_pending",
            "department_clearance",
            "finance_processing",
            "completed",
            "rejected",
        ],
    }


def get_required_documents(reason: str | None = None) -> list[dict[str, Any]]:
    guide = get_withdrawal_guide()
    reason_text = (reason or "").lower()
    selected: list[dict[str, Any]] = []
    for document in guide["documents"]:
        applicability = str(document.get("applicable_reason") or "all").lower()
        if applicability == "all" or applicability in reason_text:
            selected.append(document)

    keys = {item["document_key"] for item in selected}
    for document in guide["documents"]:
        if document["mandatory"] and document["document_key"] not in keys:
            selected.append(document)
    return selected


def create_withdrawal_request(student_id: str, reason: str, intent: str) -> str:
    _ensure_clearance_tables()
    conn = get_connection()
    reference = generate_reference()
    
    # Calculate standardized UGC fee refund (Default gross: 120,000, 80% refund slab, 1,000 deduction)
    gross_fee = 120000.0
    refund_pct = 80.0 if "disciplinary" not in reason.lower() else 50.0
    deduction = 1000.0
    net_refund = round((gross_fee * (refund_pct / 100.0)) - deduction, 2)

    conn.execute(
        """INSERT INTO withdrawal_requests
           (student_id, reason, detected_intent, refund_amount, status, reference_no, current_step)
           VALUES (?, ?, ?, ?, 'pending', ?, 1)""",
        (student_id, reason, intent, net_refund, reference),
    )
    request_id = conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]

    for document in get_required_documents(reason):
        conn.execute(
            """INSERT INTO withdrawal_checklist_items
               (request_id, document_key, label, description, status)
               VALUES (?, ?, ?, ?, 'pending')""",
            (
                request_id,
                document["document_key"],
                document["name"],
                document["description"],
            ),
        )

    # Initialize 4 sequential clearance gates
    for order, dept in enumerate(CLEARANCE_DEPARTMENTS, start=1):
        conn.execute(
            """INSERT INTO clearance_gates
               (reference_no, department, sequence_order, status, dues_amount)
               VALUES (?, ?, ?, 'PENDING', 0.0)""",
            (reference, dept, order),
        )

    conn.execute(
        """INSERT INTO workflow_events
           (request_id, status, title, description, actor)
           VALUES (?, 'submitted', 'Withdrawal request submitted',
                   'Student confirmed intent. Clearance gates and fee voucher generated.',
                   'student')""",
        (request_id,),
    )
    conn.commit()
    record_audit_event(
        action="withdrawal.submitted",
        entity_type="withdrawal_request",
        entity_id=str(request_id),
        actor_id=student_id,
        actor_role="Student",
        metadata={"reference_no": reference, "refund_amount": net_refund},
    )
    return reference


def process_department_clearance(
    reference_no: str,
    department: str,
    action: str,
    officer_name: str,
    officer_id: str,
    notes: str | None = None,
    dues_amount: float = 0.0,
) -> dict[str, Any]:
    """Process a department sign-off (CLEAR or FLAG_DUES) on a withdrawal clearance gate."""
    _ensure_clearance_tables()
    conn = get_connection()
    dept = department.upper().strip()
    if dept not in CLEARANCE_DEPARTMENTS:
        raise ValueError(f"Invalid department gate '{department}'. Must be one of: {CLEARANCE_DEPARTMENTS}")

    gate = conn.execute(
        "SELECT * FROM clearance_gates WHERE reference_no = ? AND department = ?",
        (reference_no, dept),
    ).fetchone()
    if not gate:
        raise ValueError(f"No clearance gate found for reference {reference_no} in department {dept}")

    status = "CLEARED" if action.upper() == "CLEAR" else "DUES_FLAGGED"
    cleared_at = datetime.utcnow().isoformat() if status == "CLEARED" else None

    conn.execute(
        """UPDATE clearance_gates
           SET status = ?, officer_name = ?, officer_id = ?, cleared_at = ?, notes = ?, dues_amount = ?
           WHERE reference_no = ? AND department = ?""",
        (status, officer_name, officer_id, cleared_at, notes or "", dues_amount or 0.0, reference_no, dept),
    )

    all_gates = conn.execute(
        "SELECT department, sequence_order, status, officer_name, officer_id, cleared_at, notes, dues_amount FROM clearance_gates WHERE reference_no = ? ORDER BY sequence_order ASC",
        (reference_no,),
    ).fetchall()

    is_all_cleared = all(g["status"] == "CLEARED" for g in all_gates)
    has_dues = any(g["status"] == "DUES_FLAGGED" for g in all_gates)

    parent = conn.execute(
        "SELECT id, student_id, status FROM withdrawal_requests WHERE reference_no = ?",
        (reference_no,),
    ).fetchone()

    if parent:
        new_parent_status = "completed" if is_all_cleared else ("under_review" if has_dues else "under_review")
        conn.execute(
            "UPDATE withdrawal_requests SET status = ? WHERE reference_no = ?",
            (new_parent_status, reference_no),
        )
        conn.execute(
            """INSERT INTO workflow_events (request_id, status, title, description, actor)
               VALUES (?, ?, ?, ?, ?)""",
            (
                parent["id"],
                new_parent_status,
                f"{dept} clearance marked as {status}",
                notes or f"Updated by {officer_name} ({officer_id})",
                officer_id,
            ),
        )

    conn.commit()

    record_audit_event(
        action=f"clearance.{dept.lower()}.{status.lower()}",
        entity_type="clearance_gate",
        entity_id=reference_no,
        actor_id=officer_id,
        actor_role=f"Staff_{dept.capitalize()}",
        metadata={"department": dept, "status": status, "dues_amount": dues_amount, "notes": notes},
    )

    return {
        "reference_no": reference_no,
        "department": dept,
        "status": status,
        "is_all_cleared": is_all_cleared,
        "cleared_at": cleared_at,
        "all_gates": [dict(g) for g in all_gates],
    }


def get_clearance_voucher(reference_no: str) -> dict[str, Any] | None:
    """Generate standardized pre-itemized fee and refund voucher citing UGC regulations."""
    _ensure_clearance_tables()
    conn = get_connection()
    row = conn.execute(
        """SELECT wr.*, s.name AS student_name, s.course, s.semester
           FROM withdrawal_requests wr
           LEFT JOIN students s ON s.id = wr.student_id
           WHERE wr.reference_no = ?""",
        (reference_no,),
    ).fetchone()
    if not row:
        return None

    data = dict(row)
    gates = conn.execute(
        """SELECT department, sequence_order, status, officer_name, officer_id, cleared_at, notes, dues_amount
           FROM clearance_gates
           WHERE reference_no = ?
           ORDER BY sequence_order ASC""",
        (reference_no,),
    ).fetchall()

    gross_fee = 120000.0
    refund_pct = 80.0 if float(data.get("refund_amount") or 0) > 60000 else 50.0
    deduction = 1000.0
    net_refund = float(data.get("refund_amount") or round(gross_fee * (refund_pct / 100.0) - deduction, 2))

    ledger_row = conn.execute(
        "SELECT current_balance FROM caution_deposit_ledger WHERE reference_no = ?",
        (reference_no,),
    ).fetchone()
    caution_balance = float(ledger_row["current_balance"]) if ledger_row else 10000.0

    return {
        "reference_no": reference_no,
        "student_id": data.get("student_id", ""),
        "student_name": data.get("student_name") or "Student",
        "course": data.get("course") or "Undergraduate Program",
        "semester": data.get("semester") or 1,
        "submission_date": data.get("timestamp") or datetime.utcnow().isoformat(),
        "current_status": data.get("status") or "pending",
        "ordinance_clause": "Amity Academic Regulations & UGC Fee Refund Policy Section 4.2",
        "gross_fee_paid": gross_fee,
        "refund_percentage": refund_pct,
        "deductions": deduction,
        "net_refundable_amount": net_refund,
        "caution_deposit_balance": caution_balance,
        "gates": [dict(g) for g in gates],
    }


def offset_dues_from_caution_deposit(
    reference_no: str,
    department: str,
    amount: float,
    reason: str,
    authorized_by: str = "Finance Officer",
) -> dict[str, Any]:
    """Offset outstanding department dues (e.g. ₹200 lost ID fine) against refundable caution deposit."""
    _ensure_clearance_tables()
    conn = get_connection()
    dept = department.upper().strip()
    if dept not in CLEARANCE_DEPARTMENTS:
        raise ValueError(f"Invalid department {department}. Must be one of {CLEARANCE_DEPARTMENTS}")

    wr = conn.execute(
        "SELECT id, student_id, status FROM withdrawal_requests WHERE reference_no = ?",
        (reference_no,),
    ).fetchone()
    if not wr:
        raise ValueError(f"Withdrawal request with reference {reference_no} not found.")

    student_id = wr["student_id"]

    ledger_row = conn.execute(
        "SELECT original_deposit, current_balance FROM caution_deposit_ledger WHERE reference_no = ?",
        (reference_no,),
    ).fetchone()
    if not ledger_row:
        conn.execute(
            """INSERT INTO caution_deposit_ledger (reference_no, student_id, original_deposit, current_balance, updated_at)
               VALUES (?, ?, 10000.0, 10000.0, ?)""",
            (reference_no, student_id, datetime.utcnow().isoformat()),
        )
        current_balance = 10000.0
        original_deposit = 10000.0
    else:
        current_balance = float(ledger_row["current_balance"])
        original_deposit = float(ledger_row["original_deposit"])

    if amount <= 0:
        raise ValueError("Offset amount must be greater than zero.")

    if amount > current_balance:
        raise ValueError(
            f"Offset amount ₹{amount:0.2f} exceeds available caution deposit balance ₹{current_balance:0.2f}."
        )

    new_balance = round(current_balance - amount, 2)
    now_iso = datetime.utcnow().isoformat()

    conn.execute(
        "UPDATE caution_deposit_ledger SET current_balance = ?, updated_at = ? WHERE reference_no = ?",
        (new_balance, now_iso, reference_no),
    )

    conn.execute(
        """INSERT INTO caution_deposit_offsets (reference_no, department, amount, reason, authorized_by, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (reference_no, dept, amount, reason, authorized_by, now_iso),
    )

    conn.execute(
        """UPDATE clearance_gates
           SET status = 'CLEARED',
               dues_amount = 0.0,
               cleared_at = ?,
               officer_name = ?,
               notes = ?
           WHERE reference_no = ? AND department = ?""",
        (
            now_iso,
            authorized_by,
            f"Cleared via Caution Deposit offset of ₹{amount:0.2f} ({reason})",
            reference_no,
            dept,
        ),
    )

    conn.execute(
        """INSERT INTO workflow_events (request_id, status, title, description, actor)
           VALUES (?, ?, ?, ?, ?)""",
        (
            wr["id"],
            wr["status"],
            f"{dept} dues offset from caution deposit",
            f"₹{amount:0.2f} deducted for '{reason}'. Remaining deposit: ₹{new_balance:0.2f}.",
            authorized_by,
        ),
    )

    all_gates = conn.execute(
        "SELECT status FROM clearance_gates WHERE reference_no = ?",
        (reference_no,),
    ).fetchall()
    if all(g["status"] == "CLEARED" for g in all_gates):
        conn.execute(
            "UPDATE withdrawal_requests SET status = 'completed' WHERE reference_no = ?",
            (reference_no,),
        )

    conn.commit()

    return {
        "reference_no": reference_no,
        "department": dept,
        "offset_amount": amount,
        "remaining_balance": new_balance,
        "status": "CLEARED",
        "voucher": get_clearance_voucher(reference_no),
    }


def get_deposit_ledger(reference_no: str) -> dict[str, Any] | None:
    _ensure_clearance_tables()
    conn = get_connection()
    wr = conn.execute(
        "SELECT student_id FROM withdrawal_requests WHERE reference_no = ?",
        (reference_no,),
    ).fetchone()
    if not wr:
        return None

    student_id = wr["student_id"]
    ledger_row = conn.execute(
        "SELECT original_deposit, current_balance FROM caution_deposit_ledger WHERE reference_no = ?",
        (reference_no,),
    ).fetchone()
    if not ledger_row:
        conn.execute(
            """INSERT INTO caution_deposit_ledger (reference_no, student_id, original_deposit, current_balance, updated_at)
               VALUES (?, ?, 10000.0, 10000.0, ?)""",
            (reference_no, student_id, datetime.utcnow().isoformat()),
        )
        conn.commit()
        original_deposit = 10000.0
        current_balance = 10000.0
    else:
        original_deposit = float(ledger_row["original_deposit"])
        current_balance = float(ledger_row["current_balance"])

    tx_rows = conn.execute(
        """SELECT id, department, amount, reason, authorized_by, created_at
           FROM caution_deposit_offsets
           WHERE reference_no = ?
           ORDER BY id ASC""",
        (reference_no,),
    ).fetchall()

    return {
        "reference_no": reference_no,
        "student_id": student_id,
        "original_deposit": original_deposit,
        "total_offset": round(original_deposit - current_balance, 2),
        "remaining_balance": current_balance,
        "transactions": [dict(tx) for tx in tx_rows],
    }


def get_latest_withdrawal_status(student_id: str) -> dict[str, Any]:
    _ensure_clearance_tables()
    conn = get_connection()
    row = conn.execute(
        """SELECT *
           FROM withdrawal_requests
           WHERE student_id = ?
           ORDER BY timestamp DESC
           LIMIT 1""",
        (student_id.upper().strip(),),
    ).fetchone()
    if not row:
        return {"has_request": False, "guide": get_withdrawal_guide()}

    request = dict(row)
    request_id = request["id"]
    reference_no = request["reference_no"]

    checklist_rows = conn.execute(
        """SELECT id, document_key, label, description, status, updated_at
           FROM withdrawal_checklist_items
           WHERE request_id = ?
           ORDER BY id ASC""",
        (request_id,),
    ).fetchall()
    event_rows = conn.execute(
        """SELECT status, title, description, actor, timestamp
           FROM workflow_events
           WHERE request_id = ?
           ORDER BY timestamp ASC, id ASC""",
        (request_id,),
    ).fetchall()

    # Fetch clearance gates, seeding them if they didn't exist for older test records
    gates_rows = conn.execute(
        """SELECT department, sequence_order, status, officer_name, officer_id, cleared_at, notes, dues_amount
           FROM clearance_gates
           WHERE reference_no = ?
           ORDER BY sequence_order ASC""",
        (reference_no,),
    ).fetchall()

    if not gates_rows:
        for order, dept in enumerate(CLEARANCE_DEPARTMENTS, start=1):
            conn.execute(
                """INSERT INTO clearance_gates
                   (reference_no, department, sequence_order, status, dues_amount)
                   VALUES (?, ?, ?, 'PENDING', 0.0)""",
                (reference_no, dept, order),
            )
        conn.commit()
        gates_rows = conn.execute(
            """SELECT department, sequence_order, status, officer_name, officer_id, cleared_at, notes, dues_amount
               FROM clearance_gates
               WHERE reference_no = ?
               ORDER BY sequence_order ASC""",
            (reference_no,),
        ).fetchall()

    voucher = get_clearance_voucher(reference_no)

    return {
        "has_request": True,
        "request": request,
        "checklist": [dict(row) for row in checklist_rows],
        "events": [dict(row) for row in event_rows],
        "gates": [dict(row) for row in gates_rows],
        "voucher": voucher,
        "guide": get_withdrawal_guide(),
    }


def _normalise_document(document: dict[str, Any]) -> dict[str, Any]:
    document["mandatory"] = bool(document.get("mandatory"))
    return document

