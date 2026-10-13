# FastAPI application entry point with hybrid voice guidance.

from contextlib import asynccontextmanager

from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from backend.config import settings
from backend.database.seed import init_db
from backend.middleware.security import SecurityHeadersMiddleware
from backend.middleware.observability import ObservabilityMiddleware, telemetry
from backend.database.connection import get_connection
from backend.services.cache_service import cache_service
from backend.security.rbac import require_any_role
from backend.routes import auth, chat, documents, status, admin, student, withdrawal, workflows, notifications, forms, reports, campuses, compliance, system, services, policy, voice, notesheet, registry, accreditation, institution, procedures

limiter = Limiter(key_func=get_remote_address, default_limits=[settings.rate_limit_default])

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise DB and ensure local Ollama AI daemon is active before accepting requests."""
    if settings.is_production and settings.jwt_secret_key == "change-me-in-production":
        raise RuntimeError("JWT_SECRET_KEY must be configured in production.")
    init_db()
    try:
        from backend.services.local_llm_service import ensure_ollama_daemon_running
        ensure_ollama_daemon_running()
    except Exception:
        pass
    yield


app = FastAPI(
    title=f"{settings.app_name} API",
    description=(
        "Workflow-centric student service and procedure guidance backend for "
        "university digital front desk operations."
    ),
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url=None,
    lifespan=lifespan,
)

# ── Static Files ──────────────────────────────────────────────────────────────
forms_dir = Path("backend/static/forms")
forms_dir.mkdir(parents=True, exist_ok=True)
app.mount("/forms", StaticFiles(directory=str(forms_dir)), name="forms")

# ── Rate limiting ─────────────────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

# ── Security headers ──────────────────────────────────────────────────────────
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(ObservabilityMiddleware)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=list(settings.allowed_hosts))

# ── CORS (added last so it wraps all other middleware — handles preflight first) ──
cors_kwargs = {"allow_origins": list(settings.cors_origins)} if settings.is_production else {"allow_origin_regex": ".*"}
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    **cors_kwargs
)

# ── Routes ────────────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(student.router)
app.include_router(documents.router)
app.include_router(status.router)
app.include_router(withdrawal.router)
app.include_router(workflows.router)
app.include_router(notifications.router)
app.include_router(admin.router)
app.include_router(reports.router)
app.include_router(campuses.router)
app.include_router(forms.router)
app.include_router(compliance.router)
app.include_router(system.router)
app.include_router(services.router)
app.include_router(policy.router)
app.include_router(voice.router)
app.include_router(notesheet.router)
app.include_router(registry.router)
app.include_router(accreditation.router)
app.include_router(institution.router)
app.include_router(procedures.router)



@app.get("/api/health", tags=["System"])
async def health_check():
    """Liveness probe endpoint."""
    return {
        "status": "ok",
        "service": settings.app_name.lower(),
        "environment": settings.environment,
        "version": "1.0.0",
    }


@app.get("/api/health/ready", tags=["System"])
async def readiness_check():
    """Readiness probe that confirms the local database and cache path respond."""
    try:
        get_connection().execute("SELECT 1").fetchone()
        cache_service.set_json("health:ready", {"ok": True}, ttl_seconds=10)
        cache_service.get_json("health:ready")
    except Exception:
        return {"status": "degraded"}
    return {"status": "ready"}


@app.get("/api/health/telemetry", tags=["System"])
async def telemetry_snapshot(request: Request):
    """Operational telemetry, restricted to staff administrators."""
    require_any_role(request, {"Registrar", "Administrator"})
    return telemetry.snapshot()


from fastapi.responses import FileResponse, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

# ── Web Frontend Mount & SPA Fallback ─────────────────────────────────────────
web_dir = Path("frontend_flutter/build/web")
if web_dir.exists() and (web_dir / "index.html").exists():
    @app.exception_handler(StarletteHTTPException)
    async def spa_fallback_handler(request: Request, exc: StarletteHTTPException):
        if exc.status_code == 404 and not request.url.path.startswith("/api/") and not request.url.path.startswith("/forms/"):
            index_path = web_dir / "index.html"
            if index_path.exists():
                return FileResponse(str(index_path))
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    app.mount("/", StaticFiles(directory=str(web_dir), html=True), name="frontend_web")
