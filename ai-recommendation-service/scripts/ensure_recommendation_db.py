#!/usr/bin/env python3
"""
Create the application database if it is missing.

Docker Postgres only runs docker-entrypoint-initdb.d scripts on first volume
initialization, so existing volumes never get new CREATE DATABASE lines from
the repo. This script runs before Alembic so `recommendation_db` exists.
"""
from __future__ import annotations

import os
import sys

import psycopg2
from psycopg2 import sql
from sqlalchemy.engine.url import make_url


def _refresh_collation_versions(cur) -> None:
    """
    Fix CREATE DATABASE failing after Postgres image / host glibc drift reused an
    older data directory (collation version mismatch on template1 / postgres).
    See: https://www.postgresql.org/docs/current/sql-alterdatabase.html
    """
    for stmt in (
        "ALTER DATABASE postgres REFRESH COLLATION VERSION",
        "ALTER DATABASE template1 REFRESH COLLATION VERSION",
    ):
        try:
            cur.execute(stmt)
            print(f"ensure_recommendation_db: {stmt}")
        except Exception as e:  # noqa: BLE001
            print(
                f"ensure_recommendation_db: skipped ({stmt}): {e}",
                file=sys.stderr,
            )


def main() -> int:
    raw = os.environ.get("DATABASE_URL", "").strip()
    if not raw:
        print("ensure_recommendation_db: DATABASE_URL unset, skipping", file=sys.stderr)
        return 0
    try:
        url = make_url(raw)
    except Exception as e:  # noqa: BLE001
        print(f"ensure_recommendation_db: invalid DATABASE_URL: {e}", file=sys.stderr)
        return 1
    dbname = url.database
    if not dbname:
        print("ensure_recommendation_db: no database name in URL, skipping", file=sys.stderr)
        return 0

    conn = psycopg2.connect(
        host=url.host,
        port=url.port or 5432,
        user=url.username,
        password=url.password,
        dbname="postgres",
        connect_timeout=30,
    )
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s",
                (dbname,),
            )
            if cur.fetchone():
                print(f"ensure_recommendation_db: database {dbname!r} already exists")
                return 0
            _refresh_collation_versions(cur)
            create_ident = sql.SQL("CREATE DATABASE {}").format(sql.Identifier(dbname))
            try:
                cur.execute(create_ident)
            except psycopg2.InternalError as e:
                err = str(e).lower()
                if "collation" not in err and "template" not in err:
                    raise
                # template1 can still be unusable; template0 avoids copying a broken template1
                cur.execute(
                    sql.SQL("CREATE DATABASE {} WITH TEMPLATE template0").format(
                        sql.Identifier(dbname)
                    ),
                )
            print(f"ensure_recommendation_db: created database {dbname!r}")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
