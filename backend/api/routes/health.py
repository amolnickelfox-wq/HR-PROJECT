import os
from fastapi import APIRouter

from backend.app.state import _scheduler, _SCHEDULER_OK

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok", "service": "AI Recruitment Assistant"}


@router.get("/debug/config")
async def debug_config():
    return {
        "BASE_URL":            os.getenv("BASE_URL"),
        "TWILIO_ACCOUNT_SID":  os.getenv("TWILIO_ACCOUNT_SID"),
        "TWILIO_PHONE_NUMBER": os.getenv("TWILIO_PHONE_NUMBER"),
        "scheduler_running":   (_scheduler.running if _SCHEDULER_OK and _scheduler else False),
    }
