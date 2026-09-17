"""
Phase 23: Collaborative Digital Notesheet API router.
Provides endpoints for initiating, tracking, hierarchically approving,
and performing In-Flight Collaborative Editing on university notesheets.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from ..services.notesheet_service import NotesheetService, STAGE_HIERARCHY

router = APIRouter(prefix="/api/notesheets", tags=["Digital Notesheet"])


class NotesheetCreateRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    category: str = Field(..., description="e.g. Disciplinary, Academic, Fee Concession, Course Exemption, General")
    created_by: str = Field(..., min_length=2, max_length=50)
    content: Dict[str, Any] = Field(..., description="Structured notesheet payload")
    student_id: Optional[str] = Field(None, max_length=30)
    initial_stage: Optional[str] = Field("SUPERVISOR", description="Initial hierarchical stage")
    creator_name: Optional[str] = None
    creator_role: Optional[str] = None
    comments: Optional[str] = None


class NotesheetActionRequest(BaseModel):
    officer_id: str = Field(..., min_length=2, max_length=50)
    officer_name: str = Field(..., min_length=2, max_length=100)
    role: str = Field(..., min_length=2, max_length=50)
    action: str = Field(..., description="FORWARD, APPROVE, or REJECT")
    comments: Optional[str] = None


class NotesheetEditFieldRequest(BaseModel):
    officer_id: str = Field(..., min_length=2, max_length=50)
    officer_role: str = Field(..., min_length=2, max_length=50)
    field_name: str = Field(..., min_length=1, max_length=100)
    new_value: Any = Field(..., description="Updated value for the field")
    reason: str = Field(..., min_length=3, description="Mandatory audit justification for in-flight modification")


@router.post("", summary="Create Digital Notesheet")
async def create_notesheet(req: NotesheetCreateRequest):
    """Create a new digital notesheet and place it on the hierarchical approval track."""
    try:
        ns = NotesheetService.create_notesheet(
            title=req.title,
            category=req.category,
            created_by=req.created_by,
            content=req.content,
            student_id=req.student_id,
            initial_stage=req.initial_stage or "SUPERVISOR",
            creator_name=req.creator_name,
            creator_role=req.creator_role,
            initial_comments=req.comments,
        )
        return {"success": True, "notesheet": ns}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", summary="List Digital Notesheets")
async def list_notesheets(
    stage: Optional[str] = Query(None, description="Filter by hierarchical stage"),
    status: Optional[str] = Query(None, description="Filter by status (IN_REVIEW, APPROVED, REJECTED)"),
    student_id: Optional[str] = Query(None, description="Filter by student ID"),
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(50, ge=1, le=100),
):
    """List notesheets matching filter criteria."""
    items = NotesheetService.list_notesheets(
        stage=stage,
        status=status,
        student_id=student_id,
        category=category,
        limit=limit,
    )
    return {"total": len(items), "notesheets": items, "stages": STAGE_HIERARCHY}


@router.get("/{id_or_ref}", summary="Get Digital Notesheet Detail")
async def get_notesheet(id_or_ref: str):
    """Get complete notesheet details including content, signatures, and edit audit trail."""
    try:
        ns = NotesheetService.get_notesheet(id_or_ref)
        return ns
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{id_or_ref}/action", summary="Action Notesheet (Forward, Approve, Reject)")
async def action_notesheet(id_or_ref: str, req: NotesheetActionRequest):
    """Sign and forward/approve/reject a notesheet to progress along the hierarchy."""
    try:
        ns = NotesheetService.action_notesheet(
            id_or_ref=id_or_ref,
            officer_id=req.officer_id,
            officer_name=req.officer_name,
            role=req.role,
            action=req.action,
            comments=req.comments,
        )
        return {"success": True, "notesheet": ns}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{id_or_ref}/edit-field", summary="In-Flight Collaborative Edit")
async def edit_notesheet_field(id_or_ref: str, req: NotesheetEditFieldRequest):
    """Correct a typo, course code, or parameter in-flight with an audit annotation."""
    try:
        ns = NotesheetService.edit_notesheet_field(
            id_or_ref=id_or_ref,
            officer_id=req.officer_id,
            officer_role=req.officer_role,
            field_name=req.field_name,
            new_value=req.new_value,
            reason=req.reason,
        )
        return {"success": True, "notesheet": ns}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
