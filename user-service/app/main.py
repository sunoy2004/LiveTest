import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, Query
from fastapi.middleware.cors import CORSMiddleware

from app.db import Base, engine
from app.db_patches import apply_schema_patches
from app.routes import router
from app.seed import seed_if_empty


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    apply_schema_patches()
    seed_if_empty()
    from app.realtime.redis_listener import start_listener, stop_listener

    await start_listener()
    try:
        yield
    finally:
        await stop_listener()


app = FastAPI(title="User Service", version="1.0.0", lifespan=lifespan)

_origins = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173,"
    "https://common-ui-1095720168864.us-central1.run.app,"
    "https://common-ui-1095720168864-1095720168864.us-central1.run.app,"
    "https://mentee-ui-1095720168864.us-central1.run.app",
)
_origins_list = [o.strip() for o in _origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.websocket("/ws/dashboard")
async def websocket_dashboard(
    websocket: WebSocket,
    token: str = Query(..., description="JWT from User Service"),
):
    from app.realtime.dashboard_ws import handle_dashboard_ws

    await handle_dashboard_ws(websocket, token)


@app.get("/health")
def health():
    return {"status": "ok"}
