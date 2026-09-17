from fastapi import APIRouter, HTTPException
from ..database.connection import get_connection
from ..services.withdrawal_workflow import get_latest_withdrawal_status

router = APIRouter(prefix="/api/status", tags=["Status"])

@router.get("/{student_id}")
async def get_status(student_id: str):
    try:
        workflow = get_latest_withdrawal_status(student_id)
        if not workflow["has_request"]:
            return {"has_request": False, "guide": workflow["guide"]}

        request = workflow["request"]
        return {
            "has_request": True,
            "status": request["status"],
            "timestamp": request["timestamp"],
            "reason": request["reason"],
            "reference_no": request.get("reference_no"),
            "current_step": request.get("current_step"),
            "checklist": workflow["checklist"],
            "events": workflow["events"],
            "gates": workflow.get("gates", []),
            "voucher": workflow.get("voucher"),
            "guide": workflow["guide"],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail="Database error while fetching status.")
