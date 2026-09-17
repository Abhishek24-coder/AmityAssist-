"""
Phase 24: Centralized Real-Time Student Status Registry Service.
Maintains live operational statuses (ACTIVE, UNDER_CLEARANCE, WITHDRAWN, SUSPENDED, DEBARRED),
enforces security/entry locks across campus interfaces, records tamper-evident status audit logs,
and broadcasts events to connected clients.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, List, Optional, Set

from ..database.connection import get_connection

VALID_STATUSES = {"ACTIVE", "UNDER_CLEARANCE", "WITHDRAWN", "SUSPENDED", "DEBARRED"}
RESTRICTED_STATUSES = {"SUSPENDED", "DEBARRED"}

# In-memory subscriber queues for SSE events
_subscribers: Set[asyncio.Queue] = set()


class RegistryService:
    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    @classmethod
    def get_student_status(cls, student_id: str) -> Dict[str, Any]:
        """Fetch real-time operational status for a student with access clearance flags."""
        conn = get_connection()
        norm_id = student_id.upper().strip()
        row = conn.execute(
            """
            SELECT id, name, email, course, branch, semester, attendance,
                   COALESCE(status, 'ACTIVE') as status,
                   status_reason, status_updated_at, status_updated_by
            FROM students
            WHERE id = ?
            """,
            (norm_id,),
        ).fetchone()

        if not row:
            raise ValueError(f"Student '{student_id}' not found in registry")

        data = dict(row)
        status = data["status"]
        is_restricted = status in RESTRICTED_STATUSES

        data["entry_permitted"] = not is_restricted
        data["attendance_permitted"] = not is_restricted
        data["kiosk_restricted"] = is_restricted

        if status == "SUSPENDED":
            data["lock_reason"] = data["status_reason"] or "Disciplinary Suspension by Proctorial Board"
            data["alert_action"] = "Report immediately to Proctorial Board Office (Admin Block-3, Room 102)"
        elif status == "DEBARRED":
            data["lock_reason"] = data["status_reason"] or "Attendance Debarment (< 60% attendance threshold)"
            data["alert_action"] = "Contact Department HOD for Examination Eligibility Review"
        elif status == "UNDER_CLEARANCE":
            data["lock_reason"] = "Clearance in Progress"
            data["alert_action"] = "Complete department no-dues verification"
        else:
            data["lock_reason"] = None
            data["alert_action"] = None

        return data

    @classmethod
    def update_student_status(
        cls,
        student_id: str,
        new_status: str,
        reason: str,
        updated_by: str,
    ) -> Dict[str, Any]:
        """Update student operational status with mandatory reason and audit entry."""
        norm_id = student_id.upper().strip()
        new_status = new_status.upper().strip()

        if new_status not in VALID_STATUSES:
            raise ValueError(f"Invalid status '{new_status}'. Must be one of: {', '.join(sorted(VALID_STATUSES))}")

        if not reason or not reason.strip():
            raise ValueError("A clear reason is mandatory for student status modifications")

        current_data = cls.get_student_status(norm_id)
        prev_status = current_data["status"]

        if prev_status == new_status:
            return current_data

        now = cls._now_iso()
        conn = get_connection()
        cursor = conn.cursor()

        # Update student record
        cursor.execute(
            """
            UPDATE students
            SET status = ?, status_reason = ?, status_updated_at = ?, status_updated_by = ?
            WHERE id = ?
            """,
            (new_status, reason.strip(), now, updated_by, norm_id),
        )

        # Record audit history
        history_id = str(uuid.uuid4())
        cursor.execute(
            """
            INSERT INTO student_status_history (
                id, student_id, previous_status, new_status, reason, updated_by, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (history_id, norm_id, prev_status, new_status, reason.strip(), updated_by, now),
        )
        conn.commit()

        updated_info = cls.get_student_status(norm_id)

        # Broadcast event asynchronously to all connected clients
        event_payload = {
            "event": "student_status_changed",
            "student_id": norm_id,
            "previous_status": prev_status,
            "new_status": new_status,
            "reason": reason.strip(),
            "updated_by": updated_by,
            "timestamp": now,
        }
        cls._broadcast_event(event_payload)

        return updated_info

    @classmethod
    def get_status_history(cls, student_id: str) -> List[Dict[str, Any]]:
        """Retrieve complete audit history of status updates for a student."""
        norm_id = student_id.upper().strip()
        conn = get_connection()
        rows = conn.execute(
            """
            SELECT * FROM student_status_history
            WHERE student_id = ?
            ORDER BY updated_at DESC
            """,
            (norm_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    @classmethod
    def get_course_roster(cls, branch_or_course: str) -> List[Dict[str, Any]]:
        """Generate faculty attendance roster highlighting students with active warnings/suspensions."""
        conn = get_connection()
        rows = conn.execute(
            """
            SELECT id, name, email, course, branch, semester, attendance, cgpa,
                   COALESCE(status, 'ACTIVE') as status, status_reason
            FROM students
            WHERE UPPER(branch) = UPPER(?) OR UPPER(course) LIKE UPPER(?)
            ORDER BY id ASC
            """,
            (branch_or_course, f"%{branch_or_course}%"),
        ).fetchall()

        roster = []
        for r in rows:
            student = dict(r)
            status = student["status"]
            is_locked = status in RESTRICTED_STATUSES
            student["attendance_locked"] = is_locked
            student["badge_color"] = "RED" if is_locked else ("AMBER" if status == "UNDER_CLEARANCE" else "GREEN")
            student["status_label"] = status
            roster.append(student)
        return roster

    @classmethod
    def _broadcast_event(cls, payload: Dict[str, Any]) -> None:
        """Push an event to all active SSE subscribers."""
        dead_queues = set()
        for q in list(_subscribers):
            try:
                q.put_nowait(payload)
            except Exception:
                dead_queues.add(q)
        _subscribers.difference_update(dead_queues)

    @classmethod
    async def event_generator(cls) -> AsyncGenerator[Dict[str, Any], None]:
        """Async generator providing SSE stream to clients."""
        q: asyncio.Queue = asyncio.Queue()
        _subscribers.add(q)
        try:
            while True:
                data = await q.get()
                yield data
        finally:
            _subscribers.discard(q)
