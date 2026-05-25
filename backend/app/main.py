import backend.app.config  # noqa: F401 — loads .env before anything else

import os
from contextlib import asynccontextmanager

import httpx as _httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.state import _scheduler, _SCHEDULER_OK
from backend.app.database import _init_db, load_stores
from backend.app.state import interview_store, batch_store, opening_store
from backend.app.callbacks import _reschedule_pending_callbacks

from backend.api.routes.health    import router as health_router
from backend.api.routes.resume    import router as resume_router
from backend.api.routes.interview import router as interview_router
from backend.api.routes.batch     import router as batch_router
from backend.api.routes.openings  import router as openings_router


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if _SCHEDULER_OK:
        _scheduler.start()
        print("[Startup] APScheduler started — callback scheduling enabled")
    _init_db()
    loaded_ivs, loaded_batches, loaded_openings = load_stores()
    interview_store.update(loaded_ivs)
    batch_store.update(loaded_batches)
    opening_store.update(loaded_openings)
    _reschedule_pending_callbacks()
    try:
        r = _httpx.get("http://localhost:4040/api/tunnels", timeout=2)
        tunnels = r.json().get("tunnels", [])
        https_url = next(
            (t["public_url"] for t in tunnels if t["public_url"].startswith("https")), None
        )
        if https_url:
            os.environ["BASE_URL"] = https_url
            print(f"[Startup] ngrok auto-detected → BASE_URL={https_url}")
        else:
            print(f"[Startup] ngrok running but no HTTPS tunnel. BASE_URL={os.getenv('BASE_URL', 'NOT SET')}")
    except Exception:
        print(f"[Startup] ngrok not detected. BASE_URL={os.getenv('BASE_URL', 'NOT SET')}")
    yield
    if _SCHEDULER_OK:
        _scheduler.shutdown(wait=False)


app = FastAPI(title="AI Recruitment Assistant", version="2.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

app.include_router(health_router)
app.include_router(resume_router)
app.include_router(interview_router)
app.include_router(batch_router)
app.include_router(openings_router)
