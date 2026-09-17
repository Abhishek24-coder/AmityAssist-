"""
Phase 24: Centralized Real-Time Student Status Registry API router.
Provides real-time access checks, status modification endpoints,
faculty roster warning matrix, and SSE event streaming.
"""

from __future__ import annotations

import json
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ..services.registry_service import RegistryService, VALID_STATUSES

router = APIRouter(prefix="/api/registry", tags=["Student Status Registry"])


class StatusUpdateRequest(BaseModel):
    student_id: str = Field(..., min_length=3, max_length=30)
    new_status: str = Field(..., description="ACTIVE, UNDER_CLEARANCE, WITHDRAWN, SUSPENDED, DEBARRED")
    reason: str = Field(..., min_length=3, description="Mandatory official justification")
    updated_by: str = Field(..., min_length=2, max_length=50, description="Officer / Proctor ID")


@router.get("/status/{student_id}", summary="Get Student Status & Access Clearance")
async def get_student_status(student_id: str):
    """Retrieve real-time student operational status, entry flags, and disciplinary locks."""
    try:
        data = RegistryService.get_student_status(student_id)
        return data
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/status/update", summary="Update Student Status (Proctorial / Admin Action)")
async def update_student_status(req: StatusUpdateRequest):
    """Update student operational status with mandatory audit reason and real-time broadcast."""
    try:
        updated = RegistryService.update_student_status(
            student_id=req.student_id,
            new_status=req.new_status,
            reason=req.reason,
            updated_by=req.updated_by,
        )
        return {"success": True, "student": updated}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/history/{student_id}", summary="Get Student Status Audit History")
async def get_status_history(student_id: str):
    """Retrieve complete audit trail of status transitions for a student."""
    history = RegistryService.get_status_history(student_id)
    return {"student_id": student_id.upper(), "total": len(history), "history": history}


@router.get("/roster/{branch_or_course}", summary="Faculty Attendance Roster with Real-Time Warning Flags")
async def get_faculty_roster(branch_or_course: str):
    """Return course roster highlighting suspended or debarred students with red alert banners."""
    roster = RegistryService.get_course_roster(branch_or_course)
    return {
        "branch_or_course": branch_or_course,
        "total_enrolled": len(roster),
        "suspended_count": sum(1 for s in roster if s["status"] == "SUSPENDED"),
        "debarred_count": sum(1 for s in roster if s["status"] == "DEBARRED"),
        "roster": roster,
    }


@router.get("/events", summary="Real-Time Server-Sent Events Stream for Status Updates")
async def sse_status_events():
    """Stream real-time student status change events to connected kiosks and portals."""
    async def event_publisher():
        async for event in RegistryService.event_generator():
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(event_publisher(), media_type="text/event-stream")
