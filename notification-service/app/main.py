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


app = FastAPI(title="Notification Service", version="1.0.0", lifespan=lifespan)


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