from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.app.state import opening_store
from backend.app.database import _save_opening, _delete_opening

router = APIRouter()


class OpeningCreate(BaseModel):
    id: str
    title: str
    jd: str = ''
    createdAt: str = ''


class OpeningUpdate(BaseModel):
    title: str | None = None
    jd: str | None = None


@router.post("/openings", status_code=201)
async def create_opening(req: OpeningCreate):
    opening_store[req.id] = {
        "id":        req.id,
        "title":     req.title,
        "jd":        req.jd,
        "createdAt": req.createdAt,
    }
    _save_opening(req.id, opening_store[req.id])
    return opening_store[req.id]


@router.get("/openings")
async def list_openings():
    return list(opening_store.values())


@router.get("/openings/{opening_id}")
async def get_opening(opening_id: str):
    o = opening_store.get(opening_id)
    if not o:
        raise HTTPException(404, "Opening not found.")
    return o


@router.put("/openings/{opening_id}")
async def update_opening(opening_id: str, req: OpeningUpdate):
    o = opening_store.get(opening_id)
    if not o:
        raise HTTPException(404, "Opening not found.")
    if req.title is not None:
        o["title"] = req.title
    if req.jd is not None:
        o["jd"] = req.jd
    _save_opening(opening_id, o)
    return o


@router.delete("/openings/{opening_id}", status_code=204)
async def delete_opening(opening_id: str):
    opening_store.pop(opening_id, None)
    _delete_opening(opening_id)
