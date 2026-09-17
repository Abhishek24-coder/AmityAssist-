"""
Phase 28: Multi-University White-Label Institutional Configurator Service.
Manages dynamic institution branding, clearance chain configuration,
and custom refund slab policies so any university can deploy without code changes.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..database.connection import get_connection


class InstitutionService:
    """CRUD service for white-label institutional configuration."""

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    # ── Institution Branding Configuration ────────────────────────────────────
    @classmethod
    def get_config(cls) -> Dict[str, Any]:
        """Retrieve all institution configuration key-value pairs."""
        conn = get_connection()
        rows = conn.execute(
            "SELECT key, value, updated_at FROM institution_config ORDER BY key"
        ).fetchall()
        config = {row["key"]: row["value"] for row in rows}
        config["_metadata"] = {
            "total_keys": len(rows),
            "retrieved_at": cls._now_iso(),
        }
        return config

    @classmethod
    def update_config(cls, updates: Dict[str, str]) -> Dict[str, Any]:
        """Update one or more institution configuration values."""
        if not updates:
            raise ValueError("No configuration values provided")

        conn = get_connection()
        now = cls._now_iso()
        updated_keys = []

        for key, value in updates.items():
            key = key.strip()
            if not key:
                continue
            conn.execute(
                """INSERT INTO institution_config (key, value, updated_at)
                   VALUES (?, ?, ?)
                   ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at""",
                (key, str(value), now),
            )
            updated_keys.append(key)

        conn.commit()
        return {
            "success": True,
            "updated_keys": updated_keys,
            "total_updated": len(updated_keys),
            "updated_at": now,
        }

    # ── Dynamic Clearance Chain ───────────────────────────────────────────────
    @classmethod
    def get_clearance_chain(cls) -> List[Dict[str, Any]]:
        """Get the ordered clearance desk chain."""
        conn = get_connection()
        rows = conn.execute(
            "SELECT * FROM institution_clearance_chain ORDER BY sequence_order"
        ).fetchall()
        return [dict(row) for row in rows]

    @classmethod
    def update_clearance_chain(cls, desks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Replace the entire clearance chain with a new ordered list."""
        if not desks:
            raise ValueError("At least one clearance desk is required")

        conn = get_connection()
        now = cls._now_iso()

        # Clear existing chain and rebuild
        conn.execute("DELETE FROM institution_clearance_chain")

        for idx, desk in enumerate(desks, 1):
            desk_code = desk.get("desk_code", "").strip().upper()
            desk_name = desk.get("desk_name", "").strip()
            description = desk.get("description", "")
            is_active = desk.get("is_active", True)

            if not desk_code or not desk_name:
                raise ValueError(f"Desk at position {idx} requires both desk_code and desk_name")

            conn.execute(
                """INSERT INTO institution_clearance_chain
                   (desk_code, desk_name, sequence_order, is_active, description)
                   VALUES (?, ?, ?, ?, ?)""",
                (desk_code, desk_name, idx, 1 if is_active else 0, description),
            )

        conn.commit()
        return {
            "success": True,
            "total_desks": len(desks),
            "chain": cls.get_clearance_chain(),
            "updated_at": now,
        }

    @classmethod
    def add_clearance_desk(
        cls,
        desk_code: str,
        desk_name: str,
        description: str = "",
        position: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Add a new clearance desk at the specified position (or end)."""
        conn = get_connection()
        desk_code = desk_code.strip().upper()

        # Check for duplicate
        existing = conn.execute(
            "SELECT id FROM institution_clearance_chain WHERE desk_code = ?",
            (desk_code,),
        ).fetchone()
        if existing:
            raise ValueError(f"Clearance desk '{desk_code}' already exists")

        # Determine sequence order
        max_order = conn.execute(
            "SELECT COALESCE(MAX(sequence_order), 0) as max_order FROM institution_clearance_chain"
        ).fetchone()["max_order"]

        if position is None or position > max_order:
            order = max_order + 1
        else:
            order = max(1, position)
            # Shift existing desks down
            conn.execute(
                "UPDATE institution_clearance_chain SET sequence_order = sequence_order + 1 WHERE sequence_order >= ?",
                (order,),
            )

        conn.execute(
            """INSERT INTO institution_clearance_chain
               (desk_code, desk_name, sequence_order, is_active, description)
               VALUES (?, ?, ?, 1, ?)""",
            (desk_code, desk_name, order, description),
        )
        conn.commit()
        return {"success": True, "desk_code": desk_code, "position": order, "chain": cls.get_clearance_chain()}

    @classmethod
    def remove_clearance_desk(cls, desk_code: str) -> Dict[str, Any]:
        """Remove a clearance desk from the chain."""
        conn = get_connection()
        desk_code = desk_code.strip().upper()

        existing = conn.execute(
            "SELECT sequence_order FROM institution_clearance_chain WHERE desk_code = ?",
            (desk_code,),
        ).fetchone()
        if not existing:
            raise ValueError(f"Clearance desk '{desk_code}' not found")

        removed_order = existing["sequence_order"]
        conn.execute("DELETE FROM institution_clearance_chain WHERE desk_code = ?", (desk_code,))
        # Re-compact sequence numbers
        conn.execute(
            "UPDATE institution_clearance_chain SET sequence_order = sequence_order - 1 WHERE sequence_order > ?",
            (removed_order,),
        )
        conn.commit()
        return {"success": True, "removed": desk_code, "chain": cls.get_clearance_chain()}

    # ── Custom Refund Slabs ───────────────────────────────────────────────────
    @classmethod
    def get_refund_slabs(cls) -> List[Dict[str, Any]]:
        """Get all refund day slabs ordered by min_days."""
        conn = get_connection()
        rows = conn.execute(
            "SELECT * FROM institution_refund_slabs ORDER BY min_days"
        ).fetchall()
        return [dict(row) for row in rows]

    @classmethod
    def update_refund_slabs(cls, slabs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Replace all refund slabs with new configuration."""
        if not slabs:
            raise ValueError("At least one refund slab is required")

        conn = get_connection()
        now = cls._now_iso()

        conn.execute("DELETE FROM institution_refund_slabs")

        for slab in slabs:
            conn.execute(
                """INSERT INTO institution_refund_slabs
                   (slab_label, min_days, max_days, refund_percent, policy_note)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    slab.get("slab_label", ""),
                    slab.get("min_days", 0),
                    slab.get("max_days", 9999),
                    slab.get("refund_percent", 0.0),
                    slab.get("policy_note", ""),
                ),
            )

        conn.commit()
        return {
            "success": True,
            "total_slabs": len(slabs),
            "slabs": cls.get_refund_slabs(),
            "updated_at": now,
        }
