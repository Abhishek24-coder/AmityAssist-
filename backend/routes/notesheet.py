"""
Phase 23: Collaborative Digital Notesheet API router.
Provides endpoints for initiating, tracking, hierarchically approving,
and performing In-Flight Collaborative Editing on university notesheets.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field

from ..services.notesheet_service import NotesheetService, STAGE_HIERARCHY

try:
    from ..services.notesheet_docx_service import generate_notesheet_docx
except ImportError:
    generate_notesheet_docx = None

try:
    from ..services.notesheet_pdf_service import generate_notesheet_pdf
except ImportError:
    generate_notesheet_pdf = None

from ..security.rbac import validate_notesheet_signing_authority

# Ensure edit_field compatibility alias on NotesheetService
if not hasattr(NotesheetService, "edit_field"):
    NotesheetService.edit_field = NotesheetService.edit_notesheet_field

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


@router.post("/{id_or_ref}/action", summary="Sign & Advance Notesheet")
async def action_notesheet(id_or_ref: str, req: NotesheetActionRequest, request: Request):
    """
    Signs and advances a notesheet to the next stage in the hierarchy.
    Enforces Abhishek Shrivastava's Tier-Based Authority Rule.
    """
    # 1. Fetch current notesheet state
    try:
        notesheet = NotesheetService.get_notesheet(id_or_ref)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    current_stage = notesheet.get("current_stage", "SUPERVISOR")

    # 2. Enforce Role Authority check
    role_map = {"HOI": "Dean", "VC": "Vice Chancellor"}
    effective_role = role_map.get(req.role.strip(), req.role.strip()) if req.role else req.role
    validate_notesheet_signing_authority(
        user_role=effective_role,
        current_stage=current_stage,
    )

    # 3. Process the hierarchical sign-off
    try:
        updated = NotesheetService.action_notesheet(
            id_or_ref=id_or_ref,
            officer_id=req.officer_id,
            officer_name=req.officer_name,
            role=req.role,
            action=req.action,  # "FORWARD", "APPROVE", or "REJECT"
            comments=req.comments,
        )
        return {
            "success": True,
            "message": f"Notesheet signed and forwarded by {req.role} ({req.officer_name}).",
            "notesheet": updated,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{id_or_ref}/edit-field", summary="In-Flight Collaborative Edit")
async def edit_notesheet_field(id_or_ref: str, req: NotesheetEditFieldRequest):
    """
    Allows authorized senior officers (HOD, Dean, Pro-VC, VC) to correct minor
    typos, wrong subject codes, or dates with an inline audit annotation.
    """
    # 1. Enforce that lower tiers cannot alter existing filed content
    allowed_edit_roles = {"HOD", "Dean", "HOI", "Pro-VC", "Vice Chancellor", "VC", "Administrator"}
    if req.officer_role not in allowed_edit_roles:
        raise HTTPException(
            status_code=403,
            detail=f"In-Flight field corrections require HOD or higher authority. Role '{req.officer_role}' is not permitted.",
        )

    # 2. Mandatory audit justification check
    if not req.reason or len(req.reason.strip()) < 5:
        raise HTTPException(
            status_code=400,
            detail="A detailed audit reason is mandatory for in-flight corrections (e.g. 'Corrected course code from CS101 to CSE101').",
        )

    # 3. Apply modification with permanent annotation
    try:
        updated = NotesheetService.edit_field(
            id_or_ref=id_or_ref,
            officer_id=req.officer_id,
            officer_role=req.officer_role,
            field_name=req.field_name,
            new_value=req.new_value,
            reason=req.reason,
        )
        return {
            "success": True,
            "message": f"Field '{req.field_name}' updated with audit annotation.",
            "notesheet": updated,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{id_or_ref}/docx", summary="Download Notesheet as Word Document")
async def download_notesheet_docx(id_or_ref: str):
    """Generate and download the notesheet as a formatted .docx Word document."""
    try:
        ns = NotesheetService.get_notesheet(id_or_ref)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    if generate_notesheet_docx is None:
        raise HTTPException(status_code=500, detail="DOCX generation library (python-docx) is not installed.")

    docx_bytes = generate_notesheet_docx(ns)
    ref = ns.get("reference_no", id_or_ref)
    filename = f"Notesheet_{ref}.docx"

    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{id_or_ref}/pdf", summary="Download Notesheet as PDF")
async def download_notesheet_pdf(id_or_ref: str):
    """Generate and download the notesheet as a high-fidelity vector PDF."""
    try:
        ns = NotesheetService.get_notesheet(id_or_ref)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    if generate_notesheet_pdf is None:
        raise HTTPException(status_code=500, detail="PDF generation library is not installed.")

    pdf_bytes = generate_notesheet_pdf(ns)
    ref = ns.get("reference_no", id_or_ref)
    filename = f"Notesheet_{ref}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
