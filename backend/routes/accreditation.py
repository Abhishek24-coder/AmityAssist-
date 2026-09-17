"""
Phase 27: Academic Accreditation & CO/PO Reporting API router.
Provides endpoints for Course Outcome attainment, Program Outcome
attainment matrix, cohort summaries, and NAAC Criterion 2.6 exports.
"""

from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from ..services.accreditation_service import AccreditationService

router = APIRouter(prefix="/api/accreditation", tags=["Accreditation & CO/PO"])


@router.get("/co-attainment", summary="CO Attainment Report")
async def co_attainment(
    branch: str = Query(..., min_length=2, max_length=20, description="Branch code (e.g., CSE, ECE)"),
    semester: Optional[int] = Query(None, ge=1, le=12, description="Optional semester filter"),
):
    """Calculate Course Outcome attainment percentages for a branch and optional semester."""
    report = AccreditationService.get_co_attainment(branch, semester)
    return report


@router.get("/po-attainment", summary="PO Attainment Matrix")
async def po_attainment(
    branch: str = Query(..., min_length=2, max_length=20, description="Branch code (e.g., CSE, ECE)"),
):
    """Generate Program Outcome attainment matrix aggregated from CO→PO mappings."""
    report = AccreditationService.get_po_attainment(branch)
    return report


@router.get("/cohort-summary", summary="Annual Cohort Summary")
async def cohort_summary(
    branch: str = Query(..., min_length=2, max_length=20),
    year: Optional[int] = Query(None, ge=2020, le=2030, description="Academic year"),
):
    """Generate comprehensive cohort-level CO and PO attainment summary."""
    summary = AccreditationService.get_cohort_summary(branch, year)
    return summary


@router.get("/export", summary="Export NAAC Criterion 2.6 Report")
async def export_report(
    branch: str = Query(..., min_length=2, max_length=20),
    semester: Optional[int] = Query(None, ge=1, le=12),
    format: str = Query("csv", description="Export format: csv or pdf"),
):
    """Export CO/PO attainment data as CSV or PDF for NAAC submission."""
    fmt = format.lower().strip()

    if fmt == "csv":
        content = AccreditationService.csv_export(branch, semester)
        return Response(
            content=content,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=naac_co_attainment_{branch}.csv"},
        )
    elif fmt == "pdf":
        content = AccreditationService.pdf_export(branch)
        return Response(
            content=content,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=naac_co_po_summary_{branch}.pdf"},
        )
    else:
        raise HTTPException(status_code=400, detail="Format must be 'csv' or 'pdf'")
