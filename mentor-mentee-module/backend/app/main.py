import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

_origins = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173,http://127.0.0.1:4173,"
    "https://common-ui-1095720168864-1095720168864.us-central1.run.app,"
    "https://mentee-ui-1095720168864-1095720168864.us-central1.run.app,"
    "https://gamification-service-1095720168864-1095720168864.us-central1.run.app"
)
_origins_list = [o.strip() for o in _origins.split(",") if o.strip()]

if os.getenv("ALLOW_ALL_CORS", "true").lower() == "true":
    _origins_list = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins_list,
    allow_credentials=(_origins_list != ["*"]),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(api_router, prefix=settings.api_v1_prefix)
