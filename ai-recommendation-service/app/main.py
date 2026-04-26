import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import recommendations_router
from app.api.routes.internal import router as internal_router
from app.realtime.redis_listener import start_listener, stop_listener
from app.services.bootstrap import run_bootstrap_with_retry

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await run_bootstrap_with_retry()
    await start_listener()
    try:
        yield
    finally:
        await stop_listener()


app = FastAPI(title="AI Matching Service", version="1.0.0", lifespan=lifespan)

# Standard CORS Origins
_cors_origins = [
    o.strip()
    for o in os.getenv(
        "CORS_ORIGINS",
        ",".join(
            [
                "http://localhost:3000",
                "http://127.0.0.1:3000",
                "http://localhost:5001",
                "http://127.0.0.1:5001",
                "http://localhost:5173",
                "http://127.0.0.1:5173",
                "http://localhost:4173",
                "http://127.0.0.1:4173",
                "http://localhost:8080",
                "http://127.0.0.1:8080",
                "https://common-ui-1095720168864-1095720168864.us-central1.run.app",
                "https://mentee-ui-1095720168864-1095720168864.us-central1.run.app",
                "https://gamification-service-1095720168864-1095720168864.us-central1.run.app",
            ]
        ),
    ).split(",")
    if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    log.exception("Unhandled error at %s", request.url)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error", "error": str(exc)},
        headers={
            "Access-Control-Allow-Origin": request.headers.get("Origin", "*"),
            "Access-Control-Allow-Credentials": "true",
        },
    )


app.include_router(recommendations_router)
app.include_router(internal_router)


@app.get("/health")
def health():
    return {"status": "ok"}
