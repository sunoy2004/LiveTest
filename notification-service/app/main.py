from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from sqlalchemy.orm import Session

from app.db.db import Base, engine, get_db
from app.models import NotificationLog
from app.realtime.redis_listener import start_listener, stop_listener
from app.schemas import NotificationLogItem


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    await start_listener()
    try:
        yield
    finally:
        await stop_listener()


from fastapi.middleware.cors import CORSMiddleware
import os

app = FastAPI(title="Notification Service", version="1.0.0", lifespan=lifespan)

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


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/notifications", response_model=list[NotificationLogItem])
def list_notifications(db: Session = Depends(get_db)):
    rows = (
        db.query(NotificationLog)
        .order_by(NotificationLog.created_at.desc())
        .limit(50)
        .all()
    )
    return [NotificationLogItem.model_validate(r) for r in rows]