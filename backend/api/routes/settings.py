from fastapi import APIRouter, Depends, HTTPException
from backend.app.state import settings_store
from backend.app.database import _set_setting
from backend.api.routes.auth import _require_super_admin

router = APIRouter()


@router.get("/settings")
async def get_settings(session=Depends(_require_super_admin)):
    return {"call_provider": settings_store.get("call_provider", "twilio")}


@router.put("/settings")
async def update_settings(body: dict, session=Depends(_require_super_admin)):
    provider = body.get("call_provider", "twilio")
    if provider not in ("twilio", "plivo"):
        raise HTTPException(400, "Invalid provider. Must be 'twilio' or 'plivo'.")
    settings_store["call_provider"] = provider
    _set_setting("call_provider", provider)
    return {"call_provider": provider}
