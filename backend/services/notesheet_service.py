"""
Phase 23: Collaborative Digital Notesheet Service.
Implements multi-tier hierarchical approvals:
Supervisor -> HOD -> HOI -> Pro-VC -> Vice Chancellor
with In-Flight Collaborative Editing and tamper-evident audit trails.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..database.connection import get_connection

STAGE_HIERARCHY = ["SUPERVISOR", "HOD", "HOI", "PRO_VC", "VC"]

class NotesheetService:
    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    @classmethod
    def generate_reference_no(cls) -> str:
        year = datetime.now(timezone.utc).year
        suffix = uuid.uuid4().hex[:6].upper()
        return f"NS-{year}-{suffix}"

    @classmethod
    def create_notesheet(
        cls,
        title: str,
        category: str,
        created_by: str,
        content: Dict[str, Any],
        student_id: Optional[str] = None,
        initial_stage: str = "SUPERVISOR",
        creator_name: Optional[str] = None,
        creator_role: Optional[str] = None,
        initial_comments: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new digital notesheet with structured fields and initial signature."""
        conn = get_connection()
        notesheet_id = str(uuid.uuid4())
        ref_no = cls.generate_reference_no()
        now = cls._now_iso()
        content_json = json.dumps(content)

        if initial_stage not in STAGE_HIERARCHY:
            initial_stage = "SUPERVISOR"

        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO notesheets (
                id, reference_no, title, category, student_id, created_by,
                current_stage, content, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'IN_REVIEW', ?, ?)
            """,
            (notesheet_id, ref_no, title, category, student_id, created_by, initial_stage, content_json, now, now),
        )

        # Record initial creation/signature
        sig_id = str(uuid.uuid4())
        c_name = creator_name or created_by
        c_role = creator_role or initial_stage
        cursor.execute(
            """
            INSERT INTO notesheet_signatures (
                id, notesheet_id, stage, officer_id, officer_name, role, action, comments, signed_at
            ) VALUES (?, ?, ?, ?, ?, ?, 'FORWARD', ?, ?)
            """,
            (sig_id, notesheet_id, initial_stage, created_by, c_name, c_role, initial_comments or "Notesheet initiated", now),
        )
        conn.commit()

        return cls.get_notesheet(ref_no)

    @classmethod
    def get_notesheet(cls, id_or_ref: str) -> Dict[str, Any]:
        """Fetch notesheet by ID or reference_no, including full signature and edit history."""
        conn = get_connection()
        row = conn.execute(
            "SELECT * FROM notesheets WHERE id = ? OR reference_no = ?",
            (id_or_ref, id_or_ref),
        ).fetchone()

        if not row:
            raise ValueError(f"Notesheet '{id_or_ref}' not found")

        ns = dict(row)
        try:
            ns["content"] = json.loads(ns["content"])
        except Exception:
            ns["content"] = {}

        # Fetch signatures
        sigs = conn.execute(
            "SELECT * FROM notesheet_signatures WHERE notesheet_id = ? ORDER BY signed_at ASC",
            (ns["id"],),
        ).fetchall()
        ns["signatures"] = [dict(s) for s in sigs]

        # Fetch edits (In-Flight Collaborative Editing audit)
        edits = conn.execute(
            "SELECT * FROM notesheet_edits WHERE notesheet_id = ? ORDER BY edited_at ASC",
            (ns["id"],),
        ).fetchall()
        ns["edits"] = [dict(e) for e in edits]

        # Calculate next expected stage
        if ns["status"] == "IN_REVIEW":
            current_stage = ns["current_stage"]
            if current_stage in STAGE_HIERARCHY:
                idx = STAGE_HIERARCHY.index(current_stage)
                ns["next_stage"] = STAGE_HIERARCHY[idx + 1] if idx + 1 < len(STAGE_HIERARCHY) else "FINAL_APPROVAL"
            else:
                ns["next_stage"] = None
        else:
            ns["next_stage"] = None

        return ns

    @classmethod
    def list_notesheets(
        cls,
        stage: Optional[str] = None,
        status: Optional[str] = None,
        student_id: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """List notesheets with optional filtering by stage, status, or student."""
        conn = get_connection()
        query = "SELECT * FROM notesheets WHERE 1=1"
        params: List[Any] = []

        if stage:
            query += " AND current_stage = ?"
            params.append(stage)
        if status:
            query += " AND status = ?"
            params.append(status)
        if student_id:
            query += " AND student_id = ?"
            params.append(student_id)
        if category:
            query += " AND category = ?"
            params.append(category)

        query += " ORDER BY updated_at DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(query, params).fetchall()
        result = []
        for r in rows:
            item = dict(r)
            try:
                item["content"] = json.loads(item["content"])
            except Exception:
                item["content"] = {}
            result.append(item)
        return result

    @classmethod
    def action_notesheet(
        cls,
        id_or_ref: str,
        officer_id: str,
        officer_name: str,
        role: str,
        action: str,  # FORWARD, APPROVE, REJECT
        comments: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Advance, approve, or reject notesheet along the approval hierarchy."""
        action = action.upper().strip()
        if action not in ("FORWARD", "APPROVE", "REJECT"):
            raise ValueError("Action must be FORWARD, APPROVE, or REJECT")

        ns = cls.get_notesheet(id_or_ref)
        if ns["status"] != "IN_REVIEW":
            raise ValueError(f"Cannot action notesheet with status '{ns['status']}'")

        current_stage = ns["current_stage"]
        now = cls._now_iso()
        conn = get_connection()
        cursor = conn.cursor()

        new_stage = current_stage
        new_status = ns["status"]

        if action == "REJECT":
            new_status = "REJECTED"
        elif action == "APPROVE":
            # If approved at VC or marked as final approve
            if current_stage == "VC":
                new_status = "APPROVED"
                new_stage = "APPROVED"
            else:
                # Forward to next stage
                idx = STAGE_HIERARCHY.index(current_stage) if current_stage in STAGE_HIERARCHY else 0
                if idx + 1 < len(STAGE_HIERARCHY):
                    new_stage = STAGE_HIERARCHY[idx + 1]
                else:
                    new_status = "APPROVED"
                    new_stage = "APPROVED"
        elif action == "FORWARD":
            idx = STAGE_HIERARCHY.index(current_stage) if current_stage in STAGE_HIERARCHY else 0
            if idx + 1 < len(STAGE_HIERARCHY):
                new_stage = STAGE_HIERARCHY[idx + 1]
            else:
                new_status = "APPROVED"
                new_stage = "APPROVED"

        # Record signature
        sig_id = str(uuid.uuid4())
        cursor.execute(
            """
            INSERT INTO notesheet_signatures (
                id, notesheet_id, stage, officer_id, officer_name, role, action, comments, signed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (sig_id, ns["id"], current_stage, officer_id, officer_name, role, action, comments or f"Action: {action}", now),
        )

        # Update notesheet record
        cursor.execute(
            """
            UPDATE notesheets
            SET current_stage = ?, status = ?, updated_at = ?
            WHERE id = ?
            """,
            (new_stage, new_status, now, ns["id"]),
        )
        conn.commit()

        return cls.get_notesheet(ns["id"])

    @classmethod
    def edit_notesheet_field(
        cls,
        id_or_ref: str,
        officer_id: str,
        officer_role: str,
        field_name: str,
        new_value: Any,
        reason: str,
    ) -> Dict[str, Any]:
        """In-Flight Collaborative Editing:

        Allows senior officers (HOD, HOI, Pro-VC, VC) to correct typos, course
        codes, or dates in-flight with an audit annotation without rejecting the
        entire document down the chain.
        """
        if not reason or not reason.strip():
            raise ValueError("A clear reason for in-flight modification is mandatory for audit compliance")

        ns = cls.get_notesheet(id_or_ref)
        if ns["status"] != "IN_REVIEW":
            raise ValueError("In-flight edits are only allowed while notesheet is IN_REVIEW")

        content = ns["content"]
        old_val_str = str(content.get(field_name, ""))
        new_val_str = str(new_value)

        # Update content
        content[field_name] = new_value
        now = cls._now_iso()

        conn = get_connection()
        cursor = conn.cursor()

        # Insert audit record
        edit_id = str(uuid.uuid4())
        cursor.execute(
            """
            INSERT INTO notesheet_edits (
                id, notesheet_id, officer_id, officer_role, field_name, old_value, new_value, reason, edited_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (edit_id, ns["id"], officer_id, officer_role, field_name, old_val_str, new_val_str, reason.strip(), now),
        )

        # Update notesheet content
        cursor.execute(
            "UPDATE notesheets SET content = ?, updated_at = ? WHERE id = ?",
            (json.dumps(content), now, ns["id"]),
        )
        conn.commit()

        return cls.get_notesheet(ns["id"])
