"""Phase 29: Intelligent Policy Search & Guidance Router.

Exposes sub-5ms BM25 full-text policy ordinance search and personalized
hybrid RAG advice generation.
"""

from __future__ import annotations

from typing import Any, Optional
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel, Field

from ..services.policy_search_service import PolicySearchService, DEFAULT_POLICIES


router = APIRouter(prefix="/api/policy", tags=["Policy Intelligence & FTS5"])


class PolicyGuideRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=500, description="Inquiry regarding university policy")
    student_id: Optional[str] = Field(None, description="Optional student ID for personalization")


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
async def get_policy_guidance(body: PolicyGuideRequest) -> dict[str, Any]:
    """Hybrid RAG endpoint: combines student profile with FTS5 policy clauses for zero-hallucination guidance."""
    guidance = PolicySearchService.hybrid_guidance(query=body.query, student_id=body.student_id)
    return guidance


@router.get("/categories")
async def get_policy_categories() -> dict[str, Any]:
    """Return all indexed policy categories and total ordinance counts."""
    categories = sorted(list({p["category"] for p in DEFAULT_POLICIES}))
    return {
        "categories": categories,
        "total_ordinances": len(DEFAULT_POLICIES),
    }


@router.get("/{clause_code}")
async def get_policy_by_clause(clause_code: str) -> dict[str, Any]:
    """Retrieve an exact official university ordinance by its clause code."""
    clause_clean = clause_code.strip().upper()
    policy = next((p for p in DEFAULT_POLICIES if p["clause_code"].upper() == clause_clean), None)
    if not policy:
        raise HTTPException(status_code=404, detail=f"Ordinance clause '{clause_code}' not found.")
    return policy
