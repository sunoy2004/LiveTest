import os
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:123456@/users_db?host=/cloudsql/yanc-website%3Aus-central1%3Amentor-mentee-db",
)

# Second Database for Mentoring Service Data (Internal Cloud SQL Socket)
MENTORING_DATABASE_URL = os.getenv(
    "MENTORING_DATABASE_URL",
    "postgresql://postgres:123456@/mentoring?host=/cloudsql/yanc-website%3Aus-central1%3Amentor-mentee-db"
)

class Base(DeclarativeBase):
    pass

# Main User DB
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Mentoring DB (Direct Access via synchronous driver)
# mentoring_engine = create_engine(MENTORING_DATABASE_URL, pool_pre_ping=True)
# MentoringSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=mentoring_engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# def get_mentoring_db():
#     db = MentoringSessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()
