"""Resolve person labels from profile tables using actual DB columns (ORM may omit e.g. full_name)."""

from __future__ import annotations

import uuid
from collections.abc import Iterable

from sqlalchemy import bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.display_name import label_from_user_id


async def mentor_display_name_map(
    session: AsyncSession,
    user_ids: Iterable[uuid.UUID],
) -> dict[uuid.UUID, str]:
    """Batch-load mentor display strings (first/last, full_name, headline-like columns)."""
    from app.services.admin_catalog import _columns, _mentor_person_name_expr

    id_set = {u for u in user_ids if u is not None}
    if not id_set:
        return {}
    ids = list(id_set)
    mp_cols = await _columns(session, "mentor_profiles")
    expr = _mentor_person_name_expr(mp_cols, "mp")
    stmt = text(
        f"SELECT mp.user_id::text AS uid, {expr} AS nm FROM mentor_profiles mp WHERE mp.user_id IN :uids"
    ).bindparams(bindparam("uids", expanding=True))
    rows = (await session.execute(stmt, {"uids": ids})).fetchall()
    out: dict[uuid.UUID, str] = {}
    for uid_str, nm in rows:
        uid = uuid.UUID(str(uid_str))
        label = (nm or "").strip() if nm is not None else ""
        out[uid] = label if label else label_from_user_id(uid)
    for uid in id_set:
        if uid not in out:
            out[uid] = label_from_user_id(uid)
    return out


async def mentee_display_name_map(
    session: AsyncSession,
    user_ids: Iterable[uuid.UUID],
) -> dict[uuid.UUID, str]:
    """Batch-load mentee display strings from physical mentee_profiles columns."""
    from app.services.admin_catalog import _columns, _mentee_person_name_expr

    id_set = {u for u in user_ids if u is not None}
    if not id_set:
        return {}
    ids = list(id_set)
    me_cols = await _columns(session, "mentee_profiles")
    expr = _mentee_person_name_expr(me_cols, "mp")
    stmt = text(
        f"SELECT mp.user_id::text AS uid, {expr} AS nm FROM mentee_profiles mp WHERE mp.user_id IN :uids"
    ).bindparams(bindparam("uids", expanding=True))
    rows = (await session.execute(stmt, {"uids": ids})).fetchall()
    out: dict[uuid.UUID, str] = {}
    for uid_str, nm in rows:
        uid = uuid.UUID(str(uid_str))
        label = (nm or "").strip() if nm is not None else ""
        out[uid] = label if label else label_from_user_id(uid)
    for uid in id_set:
        if uid not in out:
            out[uid] = label_from_user_id(uid)
    return out
