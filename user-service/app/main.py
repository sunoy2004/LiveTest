import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, Query
from fastapi.middleware.cors import CORSMiddleware

from app.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.realtime.redis_listener import start_listener, stop_listener

    await start_listener()
    try:
        yield
    finally:
        await stop_listener()


app = FastAPI(title="User Service", version="1.0.0", lifespan=lifespan)

_origins = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173,http://127.0.0.1:4173,"
    "https://common-ui-1095720168864-1095720168864.us-central1.run.app,"
    "https://mentee-ui-1095720168864-1095720168864.us-central1.run.app,"
    "https://gamification-service-1095720168864-1095720168864.us-central1.run.app"
)
_origins_list = [o.strip() for o in _origins.split(",") if o.strip()]

# If we want to allow everything during local testing:
if os.getenv("ALLOW_ALL_CORS", "true").lower() == "true":
    _origins_list = ["*"]

# If origins is ["*"], we can't use allow_credentials=True.
# However, if we want to support credentials while being flexible, 
# we should ideally set allow_origins to specific domains.
_allow_all = "*" in _origins_list

app.add_middleware(
    CORSMiddleware,
    allow_origins=[] if _allow_all else _origins_list,
    allow_origin_regex=".*" if _allow_all else None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.responses import JSONResponse
from fastapi import Request

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc), "type": type(exc).__name__},
        headers={
            "Access-Control-Allow-Origin": request.headers.get("Origin", "*"),
            "Access-Control-Allow-Credentials": "true",
        }
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
