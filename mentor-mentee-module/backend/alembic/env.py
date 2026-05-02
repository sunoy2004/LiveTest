import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool
from sqlalchemy.engine import Connection

from app.core.config import settings
from app.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _asyncpg_to_sync(url: str) -> str:
    """Alembic runs migrations on a sync engine; app runtime uses asyncpg."""
    if url.startswith("postgresql+asyncpg"):
        return url.replace("postgresql+asyncpg", "postgresql+psycopg", 1)
    return url


def get_migration_url() -> str:
    """
    URL for Alembic (sync ``postgresql+psycopg``).

    On Windows, Cloud SQL Unix socket URLs (``host=/cloudsql/...``) are not supported
    by asyncio/asyncpg — set ``ALEMBIC_DATABASE_URL`` or ``DATABASE_URL_TCP`` to a TCP URL,
    e.g. ``postgresql+psycopg://USER:PASS@127.0.0.1:5432/mentoring``.
    """
    override = (os.getenv("ALEMBIC_DATABASE_URL") or "").strip()
    if override:
        return _asyncpg_to_sync(override)

    raw = settings.database_url
    if sys.platform == "win32" and ("host=/cloudsql" in raw or "host=%2Fcloudsql" in raw):
        tcp = (os.getenv("DATABASE_URL_TCP") or "").strip()
        if tcp:
            return _asyncpg_to_sync(tcp)
        raise RuntimeError(
            "Alembic on Windows cannot use a Cloud SQL Unix socket (asyncpg). "
            "Set DATABASE_URL_TCP or ALEMBIC_DATABASE_URL to a TCP PostgreSQL URL, "
            "e.g. postgresql+psycopg://postgres:postgres@127.0.0.1:5432/mentoring "
            "(matching your local Docker Postgres)."
        )
    return _asyncpg_to_sync(raw)


def run_migrations_offline() -> None:
    context.configure(
        url=get_migration_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(get_migration_url(), poolclass=pool.NullPool)

    with connectable.connect() as connection:
        do_run_migrations(connection)

    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
