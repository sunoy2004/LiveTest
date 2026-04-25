from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.services.gamification.admin.auth_routes import router as admin_auth_router
from app.services.gamification.admin.router import router as admin_router
from app.services.gamification.api.internal import router as internal_router
from app.services.gamification.api.internal_rules import router as internal_rules_router
from app.services.gamification.api.leaderboard import router as leaderboard_router
from app.services.gamification.api.legacy import router as legacy_router
from app.services.gamification.api.wallet import router as wallet_router
from app.services.gamification.events.consumer import start_listener, stop_listener


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Run migrations at startup
    try:
        from alembic import command
        from alembic.config import Config
        import os
        
        # Determine the path to alembic.ini relative to this file
        base_dir = Path(__file__).resolve().parent.parent
        alembic_cfg = Config(str(base_dir / "alembic.ini"))
        alembic_cfg.set_main_option("script_location", str(base_dir / "alembic"))
        
        # Override sqlalchemy.url with the environment variable
        db_url = os.getenv("DATABASE_URL")
        if db_url:
            # Convert asyncpg to psycopg2 for alembic
            if "+asyncpg" in db_url:
                db_url = db_url.replace("+asyncpg", "+psycopg2", 1)
            alembic_cfg.set_main_option("sqlalchemy.url", db_url)
            
        command.upgrade(alembic_cfg, "head")
    except Exception as e:
        print(f"Migration failed: {e}")

    await start_listener()
    try:
        yield
    finally:
        await stop_listener()


app = FastAPI(title="Gamification Service", version="1.0.0", lifespan=lifespan)


@app.get("/")
def service_root():
    """Identify this process as the gamification FastAPI app (useful when debugging port/proxy mismatches)."""
    return {
        "service": "gamification-service",
        "framework": "fastapi",
        "docs": "/docs",
        "openapi": "/openapi.json",
        "admin_ui": "/ui/",
        "health": "/health",
    }


_default_cors = (
    "http://localhost:3000,http://127.0.0.1:3000,"
    "http://localhost:8080,http://127.0.0.1:8080,"
    "http://localhost:5001,http://127.0.0.1:5001,"
    "http://localhost:5173,http://127.0.0.1:5173,"
    "http://localhost:5176,http://127.0.0.1:5176,"
    "http://localhost:4173,http://127.0.0.1:4173,"
    "http://localhost:8002,http://127.0.0.1:8002,"
    "https://common-ui-1095720168864.us-central1.run.app,"
    "https://common-ui-1095720168864-1095720168864.us-central1.run.app,"
    "https://mentee-ui-1095720168864-1095720168864.us-central1.run.app"
)
cors_origins = [o.strip() for o in os.getenv("CORS_ALLOW_ORIGINS", _default_cors).split(",") if o.strip()]
_cors_regex = os.getenv("CORS_ALLOW_ORIGIN_REGEX", "").strip() or None
_session_secret = os.getenv("GAMIFICATION_ADMIN_SESSION_SECRET", os.getenv("JWT_SECRET", "secret"))
app.add_middleware(
    SessionMiddleware,
    secret_key=_session_secret,
    session_cookie="gamification_session",
    max_age=60 * 60 * 8,
    same_site="lax",
    https_only=os.getenv("GAMIFICATION_ADMIN_SESSION_HTTPS_ONLY", "").lower() in ("1", "true", "yes"),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=_cors_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Admin session + CRUD routes first so /admin/* is clearly owned by this app (FastAPI matches in order).
app.include_router(admin_auth_router)
app.include_router(admin_router)
app.include_router(wallet_router)
app.include_router(leaderboard_router)
app.include_router(internal_router)
app.include_router(internal_rules_router)
app.include_router(legacy_router)

# REST API uses /admin/* — serve SPA at /ui to avoid shadowing routes.
_static = Path(__file__).resolve().parent / "static" / "admin"
if _static.is_dir():
    app.mount("/ui", StaticFiles(directory=_static, html=True), name="admin_ui")


@app.get("/health")
def health():
    return {"status": "ok"}
