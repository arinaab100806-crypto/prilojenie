from __future__ import annotations

from contextlib import asynccontextmanager
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from .bootstrap import ensure_admin, ensure_demo_accounts
from .config import LANGUAGES, judge_label, judge_mode
from .database import Base, SessionLocal, engine
from .routers import admin, arena, auth, contest_reports, contests, dashboard, fairplay, organizations, problems, submissions, teams
from .schema_sync import ensure_columns
from .schemas import SystemOut
from .seed import ensure_seed_categories, seed_if_empty


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(bind=engine)
    ensure_columns(engine)
    db = SessionLocal()
    try:
        seed_if_empty(db)
        ensure_seed_categories(db)
        ensure_admin(db)
        ensure_demo_accounts(db)
    finally:
        db.close()
    yield


app = FastAPI(title="ВолгаКод", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(organizations.router, prefix="/api")
app.include_router(teams.router, prefix="/api")
app.include_router(problems.router, prefix="/api")
app.include_router(submissions.router, prefix="/api")
app.include_router(contests.router, prefix="/api")
app.include_router(fairplay.router, prefix="/api")
app.include_router(contest_reports.router, prefix="/api")
app.include_router(arena.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")


@app.get("/api/health")
def health() -> dict[str, bool]:
    return {"ok": True}


@app.get("/api/system", response_model=SystemOut)
def system() -> SystemOut:
    return SystemOut(judge_mode=judge_mode(), judge_label=judge_label(), languages=list(LANGUAGES))


def _static_dir() -> Path | None:
    raw = os.getenv("STATIC_DIR", "").strip()
    if not raw:
        return None
    path = Path(raw)
    if path.is_dir() and (path / "index.html").is_file():
        return path
    return None


_STATIC = _static_dir()
if _STATIC is not None:

    @app.get("/", include_in_schema=False)
    def site_index() -> FileResponse:
        return FileResponse(_STATIC / "index.html")

    @app.get("/{full_path:path}", include_in_schema=False)
    def site_files(full_path: str) -> FileResponse:
        root = _STATIC.resolve()
        candidate = (root / full_path).resolve()
        if candidate.is_file() and (candidate == root or root in candidate.parents):
            return FileResponse(candidate)
        return FileResponse(root / "index.html")
