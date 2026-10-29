# ==============================================================================
# UniAssist — Multi-University White-Label Configurator Router
# Lead Architect: Abhishek Shrivastava
# ==============================================================================
from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from ..services.institution_service import InstitutionService
from ..security.rbac import require_any_role

# Compatibility alias for get_all_config
if not hasattr(InstitutionService, "get_all_config"):
    InstitutionService.get_all_config = InstitutionService.get_config

router = APIRouter(prefix="/api/institution", tags=["Institutional Configurator"])


# ── Pydantic Request Schemas ──────────────────────────────────────────────────

class InstitutionBrandingRequest(BaseModel):
    institution_name: str = Field(..., min_length=3, max_length=150, example="Manipal University Jaipur")
    crest_logo_url: str = Field(..., min_length=5, example="/assets/logos/manipal_logo.png")
    primary_color: str = Field("#E05A2B", pattern="^#([A-Fa-f0-9]{6})$", description="Hex brand color")
    secondary_color: str = Field("#1A2B4C", pattern="^#([A-Fa-f0-9]{6})$")
    contact_email: str = Field(..., example="registrar@jaipur.manipal.edu")
    contact_phone: str = Field("+91-141-3999100", example="+91-141-3999100")
    kiosk_welcome_title: str = Field("Welcome to Student Services Hub")


class ClearanceDeskItem(BaseModel):
    desk_code: str = Field(..., min_length=2, max_length=30, example="LAB_INCHARGE")
    desk_name: str = Field(..., min_length=2, max_length=100, example="Central Labs & Equipment")
    description: str = Field("", max_length=500)
    sequence_order: int = Field(1, ge=1, le=10)
    is_active: bool = True


class DynamicChainUpdateRequest(BaseModel):
    chain: List[ClearanceDeskItem] = Field(..., min_length=1)


class ClearanceChainLegacyUpdateRequest(BaseModel):
    desks: List[ClearanceDeskItem] = Field(..., min_length=1)


class AddDeskRequest(BaseModel):
    desk_code: str = Field(..., min_length=2, max_length=30)
    desk_name: str = Field(..., min_length=2, max_length=100)
    description: str = Field("", max_length=500)
    position: Optional[int] = None


class RemoveDeskRequest(BaseModel):
    desk_code: str = Field(..., min_length=2, max_length=30)


class RefundSlabItem(BaseModel):
    slab_label: str = Field(..., min_length=3, max_length=100, example="15 Days Prior to Orientation")
    min_days: int = Field(..., ge=0)
    max_days: int = Field(..., ge=0)
    refund_percent: float = Field(..., ge=0, le=100)
    policy_note: str = Field("", max_length=500)


class RefundSlabsUpdateRequest(BaseModel):
    slabs: List[RefundSlabItem] = Field(..., min_length=1)


class ConfigUpdateRequest(BaseModel):
    updates: Dict[str, str] = Field(..., description="Key-value pairs to update")


class ModulesUpdateRequest(BaseModel):
    modules: Dict[str, bool] = Field(..., description="Map of module IDs to enabled boolean")


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/config", summary="Get Active Institutional Profile")
async def get_institution_config():
    """Returns the soft-coded university identity, active theme colors, and contacts."""
    return InstitutionService.get_all_config()


@router.put("/config", summary="Update Institution Configuration")
async def update_config(req: ConfigUpdateRequest):
    """Update institution configuration values (super-admin)."""
    try:
        result = InstitutionService.update_config(req.updates)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/branding", summary="Update University Branding (Super-Admin)")
async def update_branding(req: InstitutionBrandingRequest):
    """Saves university name, logo URL, brand hex colors, and kiosk welcome text."""
    updates = {
        "institution_name": req.institution_name,
        "crest_logo_url": req.crest_logo_url,
        "primary_color": req.primary_color,
        "secondary_color": req.secondary_color,
        "contact_email": req.contact_email,
        "contact_phone": req.contact_phone,
        "kiosk_welcome_title": req.kiosk_welcome_title,
    }
    InstitutionService.update_config(updates)
    return {
        "success": True,
        "message": f"Institutional identity updated for '{req.institution_name}'. All kiosk screens refreshed."
    }


@router.get("/clearance-chain", summary="Get Clearance Desk Chain")
async def get_clearance_chain():
    """Get the ordered clearance desk chain with all desk details."""
    chain = InstitutionService.get_clearance_chain()
    return {"total_desks": len(chain), "chain": chain}


@router.post("/clearance-chain", summary="Reconfigure Dynamic Clearance Chain")
async def update_clearance_chain(req: DynamicChainUpdateRequest):
    """
    Overwrites the sequential clearance desks (e.g. 3 desks for Manipal, 4 for Amity).
    Stored in 'institution_clearance_chain' table.
    """
    desks_data = [d.model_dump() for d in req.chain]
    # Sort desks by sequence_order to maintain strictly enforced approval pipeline
    desks_data.sort(key=lambda x: x["sequence_order"])
    InstitutionService.update_clearance_chain(desks_data)
    return {
        "success": True,
        "message": f"Clearance chain reconfigured with {len(desks_data)} dynamic desks.",
        "active_chain": desks_data
    }


@router.put("/clearance-chain", summary="Replace Clearance Chain")
async def update_clearance_chain_put(req: ClearanceChainLegacyUpdateRequest):
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


@router.get("/refund-slabs", summary="Get Refund Day Slabs")
async def get_refund_slabs():
    """Get all configured refund day slabs."""
    slabs = InstitutionService.get_refund_slabs()
    return {"total_slabs": len(slabs), "slabs": slabs}


@router.post("/refund-slabs", summary="Set Custom Refund Day Brackets")
async def update_refund_slabs(req: RefundSlabsUpdateRequest):
    """Configures custom fee refund policy slabs without editing any backend math code."""
    slabs_data = [s.model_dump() for s in req.slabs]
    InstitutionService.update_refund_slabs(slabs_data)
    return {
        "success": True,
        "message": f"Updated {len(slabs_data)} refund ordinance brackets successfully."
    }


@router.put("/refund-slabs", summary="Update Refund Slabs")
async def update_refund_slabs_put(req: RefundSlabsUpdateRequest):
    """Replace all refund slabs with new configuration."""
    try:
        result = InstitutionService.update_refund_slabs(
            [slab.model_dump() for slab in req.slabs]
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/modules", summary="Get Active Modules Switchboard")
async def get_modules():
    """Retrieve all system modules and their active/disabled toggle states."""
    modules = InstitutionService.get_modules()
    return {"status": "success", "modules": modules}


@router.put("/modules", summary="Update Active Modules Switchboard")
async def update_modules(req: ModulesUpdateRequest):
    """Update module activation states across the institution."""
    try:
        result = InstitutionService.update_modules(req.modules)
        return {"status": "success", "message": "Modules switchboard updated successfully", **result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
