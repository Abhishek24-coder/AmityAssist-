"""
Phase 28: Multi-University White-Label Institutional Configurator API router.
Provides endpoints for super-admins to configure university branding,
dynamic clearance chains, and custom refund day slabs.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..services.institution_service import InstitutionService

router = APIRouter(prefix="/api/institution", tags=["Institution Configurator"])


class ConfigUpdateRequest(BaseModel):
    updates: Dict[str, str] = Field(..., description="Key-value pairs to update")


class ClearanceDeskItem(BaseModel):
    desk_code: str = Field(..., min_length=2, max_length=30)
    desk_name: str = Field(..., min_length=2, max_length=100)
    description: str = Field("", max_length=500)
    is_active: bool = True


class ClearanceChainUpdateRequest(BaseModel):
    desks: List[ClearanceDeskItem] = Field(..., min_length=1)


class AddDeskRequest(BaseModel):
    desk_code: str = Field(..., min_length=2, max_length=30)
    desk_name: str = Field(..., min_length=2, max_length=100)
    description: str = Field("", max_length=500)
    position: Optional[int] = None


class RemoveDeskRequest(BaseModel):
    desk_code: str = Field(..., min_length=2, max_length=30)


class RefundSlabItem(BaseModel):
    slab_label: str = Field(..., min_length=3, max_length=100)
    min_days: int = Field(..., ge=0)
    max_days: int = Field(..., ge=0)
    refund_percent: float = Field(..., ge=0, le=100)
    policy_note: str = Field("", max_length=500)


class RefundSlabsUpdateRequest(BaseModel):
    slabs: List[RefundSlabItem] = Field(..., min_length=1)


# ── Institution Branding ──────────────────────────────────────────────────────

@router.get("/config", summary="Get Institution Configuration")
async def get_config():
    """Retrieve current institution branding and settings."""
    return InstitutionService.get_config()


@router.put("/config", summary="Update Institution Configuration")
async def update_config(req: ConfigUpdateRequest):
    """Update institution configuration values (super-admin)."""
    try:
        result = InstitutionService.update_config(req.updates)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Dynamic Clearance Chain ───────────────────────────────────────────────────

@router.get("/clearance-chain", summary="Get Clearance Desk Chain")
async def get_clearance_chain():
    """Get the ordered clearance desk chain with all desk details."""
    chain = InstitutionService.get_clearance_chain()
    return {"total_desks": len(chain), "chain": chain}


@router.put("/clearance-chain", summary="Replace Clearance Chain")
async def update_clearance_chain(req: ClearanceChainUpdateRequest):
    """Replace the entire clearance chain with a new ordered list."""
    try:
        result = InstitutionService.update_clearance_chain(
            [desk.model_dump() for desk in req.desks]
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/clearance-chain/add", summary="Add Clearance Desk")
async def add_clearance_desk(req: AddDeskRequest):
    """Add a new clearance desk at the specified position."""
    try:
        result = InstitutionService.add_clearance_desk(
            desk_code=req.desk_code,
            desk_name=req.desk_name,
            description=req.description,
            position=req.position,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/clearance-chain/remove", summary="Remove Clearance Desk")
async def remove_clearance_desk(req: RemoveDeskRequest):
    """Remove a clearance desk from the chain."""
    try:
        result = InstitutionService.remove_clearance_desk(req.desk_code)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Custom Refund Slabs ───────────────────────────────────────────────────────

@router.get("/refund-slabs", summary="Get Refund Day Slabs")
async def get_refund_slabs():
    """Get all configured refund day slabs."""
    slabs = InstitutionService.get_refund_slabs()
    return {"total_slabs": len(slabs), "slabs": slabs}


@router.put("/refund-slabs", summary="Update Refund Slabs")
async def update_refund_slabs(req: RefundSlabsUpdateRequest):
    """Replace all refund slabs with new configuration."""
    try:
        result = InstitutionService.update_refund_slabs(
            [slab.model_dump() for slab in req.slabs]
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
