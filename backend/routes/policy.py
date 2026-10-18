"""Phase 29: Intelligent Policy Search & Guidance Router.

Exposes sub-5ms BM25 full-text policy ordinance search and personalized
hybrid RAG advice generation.
"""

from __future__ import annotations

from typing import Any, Optional
from fastapi import APIRouter, Query, HTTPException, Request
from pydantic import BaseModel, Field

from ..services.policy_search_service import PolicySearchService, DEFAULT_POLICIES


router = APIRouter(prefix="/api/policy", tags=["Policy Intelligence & FTS5"])


class PolicyGuideRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=500, description="Inquiry regarding university policy")
    student_id: Optional[str] = Field(None, description="Optional student ID for personalization")
    is_staff: Optional[bool] = Field(False, description="Whether the requester is an authorized staff member")
    staff_role: Optional[str] = Field(None, description="Staff role e.g. Registrar, Hostel, Accounts")
    staff_username: Optional[str] = Field(None, description="Staff username")
    language: str = Field("en-IN", description="Selected language e.g. en-IN, hi-IN, hi-Latn")
    page_context: Optional[dict[str, Any]] = Field(None, description="Active client screen context")
    conversation_history: Optional[list[dict[str, Any]]] = Field(None, description="Recent conversation turns")


@router.get("/search")
async def search_policies(
    q: str = Query(..., min_length=1, max_length=200, description="Search term"),
    category: Optional[str] = Query(None, description="Filter category"),
    limit: int = Query(5, ge=1, le=20),
) -> dict[str, Any]:
    """Execute sub-5ms BM25 keyword search over university ordinances using SQLite FTS5."""
    results = PolicySearchService.search_policies(query=q, category=category, limit=limit)
    return {
        "query": q,
        "count": len(results),
        "results": results,
    }


@router.post("/guide")
async def get_policy_guidance(body: PolicyGuideRequest, request: Request) -> dict[str, Any]:
    """Hybrid RAG endpoint: combines student profile with FTS5 policy clauses for zero-hallucination guidance."""
    is_staff = body.is_staff or False
    staff_role = body.staff_role
    effective_sid = body.student_id

    # Check page_context for staff indicators
    if body.page_context and isinstance(body.page_context, dict):
        if body.page_context.get("is_staff") or "/staff" in str(body.page_context.get("route", "")).lower():
            is_staff = True
            staff_role = staff_role or body.page_context.get("staff_role") or "Registrar Staff"
            effective_sid = None

    auth_hdr = request.headers.get("Authorization", "")
    if auth_hdr.startswith("Bearer "):
        token = auth_hdr.split(" ", 1)[1].strip()
        try:
            from ..security.jwt import decode_access_token
            payload = decode_access_token(token)
            if payload.get("role") == "staff":
                is_staff = True
                staff_role = staff_role or payload.get("staff_role") or "Registrar Staff"
                effective_sid = None
            elif not effective_sid and not is_staff and payload.get("role") == "student":
                effective_sid = payload.get("sub")
        except Exception:
            pass

    guidance = PolicySearchService.hybrid_guidance(
        query=body.query,
        student_id=effective_sid,
        page_context=body.page_context,
        language=body.language,
        history=body.conversation_history,
        is_staff=is_staff,
        staff_role=staff_role,
    )
    return guidance


@router.get("/categories")
async def get_policy_categories() -> dict[str, Any]:
    """Return all indexed policy categories and total ordinance counts."""
    categories = sorted(list({p["category"] for p in DEFAULT_POLICIES}))
    return {
        "categories": categories,
        "total_ordinances": len(DEFAULT_POLICIES),
    }


@router.get("/llm/status")
async def get_llm_status() -> dict[str, Any]:
    """Return active LLM provider configuration and local Ollama daemon connectivity status."""
    from ..config import settings
    from ..services.local_llm_service import check_ollama_status

    ollama_info = check_ollama_status()
    return {
        "active_provider": settings.llm_provider,
        "is_ollama_enabled": settings.is_ollama_enabled,
        "is_gemini_enabled": settings.llm_enabled,
        "gemini_model": settings.gemini_model if settings.llm_enabled else None,
        "ollama": ollama_info,
    }


@router.get("/admin/list")
async def list_admin_policies() -> dict[str, Any]:
    """List all university policies with customization flags and last updated timestamps."""
    policies = PolicySearchService.list_policies()
    return {
        "status": "success",
        "count": len(policies),
        "policies": policies,
    }


class PolicyUpsertRequest(BaseModel):
    doc_id: str = Field(..., min_length=2, max_length=50)
    category: str = Field(..., min_length=2, max_length=50)
    title: str = Field(..., min_length=3, max_length=200)
    clause_code: str = Field(..., min_length=2, max_length=50)
    content: str = Field(..., min_length=10, max_length=2000)
    action_url: Optional[str] = "/forms"
    action_label: Optional[str] = "View Policy"


@router.post("/admin/save")
async def save_policy(payload: PolicyUpsertRequest) -> dict[str, Any]:
    """Create or update a university policy ordinance with real-time FTS5 sync."""
    saved = PolicySearchService.upsert_policy(
        doc_id=payload.doc_id,
        category=payload.category,
        title=payload.title,
        clause_code=payload.clause_code,
        content=payload.content,
        action_url=payload.action_url or "/forms",
        action_label=payload.action_label or "View Policy",
        is_custom=True,
    )
    return {
        "status": "success",
        "message": f"Policy '{payload.doc_id}' saved and indexed into FTS5 successfully.",
        "policy": saved,
    }


@router.delete("/admin/{doc_id}")
async def delete_or_reset_policy(doc_id: str) -> dict[str, Any]:
    """Delete a custom policy or reset a default policy to original seed."""
    result = PolicySearchService.delete_policy(doc_id)
    return result


@router.get("/{clause_code}")
async def get_policy_by_clause(clause_code: str) -> dict[str, Any]:
    """Retrieve an exact official university ordinance by its clause code."""
    clause_clean = clause_code.strip().upper()
    all_policies = PolicySearchService.list_policies()
    policy = next((p for p in all_policies if p["clause_code"].upper() == clause_clean), None)
    if not policy:
        policy = next((p for p in DEFAULT_POLICIES if p["clause_code"].upper() == clause_clean), None)
    if not policy:
        raise HTTPException(status_code=404, detail=f"Ordinance clause '{clause_code}' not found.")
    return policy
