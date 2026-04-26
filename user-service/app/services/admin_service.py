from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, aliased

from app.models import (
    CreditLedgerEntry,
    MenteeProfile,
    MentorProfile,
    MentorshipConnection,
    ReportDispute,
    User,
)
from app.models import Session as MentorshipSession
from app.schemas import (
    AdminConnectionItem,
    AdminCreditTopUpResponse,
    AdminDisputeItem,
    AdminMenteeListItem,
    AdminMentorListItem,
    AdminMentorPricingBody,
    AdminSessionItem,
    AdminUserListItem,
    AdminUserRoleUpdate,
)
from app.services import credit_client
from app.services.mentor_pricing import resolve_mentor_session_price
from app.services.role_resolution import derived_roles


def _display_name_from_email(email: str | None) -> str:
    if not email:
        return "User"
    local = email.split("@")[0]
    return local.replace(".", " ").replace("_", " ").title()


def admin_update_mentor_pricing(
    db: Session,
    mentor_profile_id: UUID,
    body: AdminMentorPricingBody,
) -> MentorProfile:
    m = (
        db.query(MentorProfile)
        .filter(MentorProfile.id == mentor_profile_id)
        .first()
    )
    if not m:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mentor profile not found")
    m.pricing_tier = body.tier
    m.base_credit_override = body.base_credit_override
    db.commit()
    db.refresh(m)
    return m


def list_admin_mentors(db: Session, *, limit: int) -> list[AdminMentorListItem]:
    rows = (
        db.query(MentorProfile, User.email)
        .join(User, User.id == MentorProfile.user_id)
        .order_by(User.email.asc())
        .limit(limit)
        .all()
    )
    out: list[AdminMentorListItem] = []
    for mp, email in rows:
        em = email or ""
        out.append(
            AdminMentorListItem(
                id=mp.id,
                name=_display_name_from_email(em),
                email=em,
                tier=getattr(mp, "pricing_tier", None) or "TIER_2",
                base_credit_override=mp.base_credit_override,
            )
        )
    return out


def list_admin_mentees(db: Session, *, limit: int) -> list[AdminMenteeListItem]:
    rows = (
        db.query(MenteeProfile, User.email)
        .join(User, User.id == MenteeProfile.user_id)
        .order_by(User.email.asc())
        .limit(limit)
        .all()
    )
    out: list[AdminMenteeListItem] = []
    for mep, email in rows:
        em = email or ""
        out.append(
            AdminMenteeListItem(
                id=mep.id,
                name=_display_name_from_email(em),
                email=em,
                status="Active",
            )
        )
    return out


async def list_admin_connections(db: Session, *, limit: int) -> list[AdminConnectionItem]:
    # --- CROSS-SERVICE BRIDGE ---
    from app.services.mentoring_client import get_active_connections_from_mentoring_service
    # For admin, we need to fetch for all users or just get the global list.
    # Since our bridge get_active_connections takes a user_id, we can either 
    # update the bridge or call it for the current list of mentees.
    # A better way is to call a global admin list on the mentoring service.
    
    import os
    import httpx
    MENTORING_SERVICE_URL = os.getenv("MENTORING_SERVICE_URL", "http://localhost:8000")
    url = f"{MENTORING_SERVICE_URL}/api/v1/requests/admin/connections"
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url)
            if response.status_code == 200:
                remote_rows = response.json()
                out: list[AdminConnectionItem] = []
                for r in remote_rows:
                    # Enrich with local user data for emails
                    m_user = db.query(User).filter(User.id == uuid.UUID(str(r["mentor_user_id"]))).first()
                    me_user = db.query(User).filter(User.id == uuid.UUID(str(r["mentee_user_id"]))).first()
                    out.append(
                        AdminConnectionItem(
                            connection_id=uuid.UUID(str(r["id"])),
                            mentor_profile_id=uuid.UUID(str(r["mentor_id"])),
                            mentee_profile_id=uuid.UUID(str(r["mentee_id"])),
                            mentor_user_id=m_user.id if m_user else uuid.UUID(str(r["mentor_user_id"])),
                            mentee_user_id=me_user.id if me_user else uuid.UUID(str(r["mentee_user_id"])),
                            mentor_email=m_user.email if m_user else "unknown@test.com",
                            mentee_email=me_user.email if me_user else "unknown@test.com",
                            status=r["status"],
                        )
                    )
                return out
    except Exception as e:
        logger.error("Admin bridge failed: %s", e)
    # --- END BRIDGE ---

    MentorUser = aliased(User)
    MenteeUser = aliased(User)
    # ... fallback to local
    rows = (
        db.query(
            MentorshipConnection,
            MentorProfile,
            MenteeProfile,
            MentorUser,
            MenteeUser,
        )
        .join(MentorProfile, MentorshipConnection.mentor_id == MentorProfile.id)
        .join(MenteeProfile, MentorshipConnection.mentee_id == MenteeProfile.id)
        .join(MentorUser, MentorProfile.user_id == MentorUser.id)
        .join(MenteeUser, MenteeProfile.user_id == MenteeUser.id)
        .order_by(MentorshipConnection.id.asc())
        .limit(limit)
        .all()
    )
    out: list[AdminConnectionItem] = []
    for conn, _mp, _mep, mentor_u, mentee_u in rows:
        out.append(
            AdminConnectionItem(
                connection_id=conn.id,
                mentor_profile_id=conn.mentor_id,
                mentee_profile_id=conn.mentee_id,
                mentor_user_id=mentor_u.id,
                mentee_user_id=mentee_u.id,
                mentor_email=mentor_u.email or "",
                mentee_email=mentee_u.email or "",
                status=conn.status,
            )
        )
    return out


def admin_ensure_connection(
    db: Session,
    *,
    mentor_user_id: UUID,
    mentee_user_id: UUID,
) -> AdminConnectionItem:
    if mentor_user_id == mentee_user_id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Mentor user and mentee user must be different accounts",
        )
    mu = db.query(User).filter(User.id == mentor_user_id).first()
    meu = db.query(User).filter(User.id == mentee_user_id).first()
    if not mu or not meu:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User not found")
    mp = db.query(MentorProfile).filter(MentorProfile.user_id == mentor_user_id).first()
    mep = db.query(MenteeProfile).filter(MenteeProfile.user_id == mentee_user_id).first()
    if not mp:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Mentor user has no mentor profile — enable Mentor role first",
        )
    if not mep:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Mentee user has no mentee profile — enable Mentee role first",
        )
    row = (
        db.query(MentorshipConnection)
        .filter(
            MentorshipConnection.mentor_id == mp.id,
            MentorshipConnection.mentee_id == mep.id,
        )
        .first()
    )
    if row:
        row.status = "ACTIVE"
    else:
        row = MentorshipConnection(
            mentee_id=mep.id,
            mentor_id=mp.id,
            status="ACTIVE",
        )
        db.add(row)
    db.commit()
    db.refresh(row)
    return AdminConnectionItem(
        connection_id=row.id,
        mentor_profile_id=row.mentor_id,
        mentee_profile_id=row.mentee_id,
        mentor_user_id=mu.id,
        mentee_user_id=meu.id,
        mentor_email=mu.email or "",
        mentee_email=meu.email or "",
        status=row.status,
    )


def list_admin_users(db: Session, *, limit: int) -> list[AdminUserListItem]:
    rows = db.query(User).order_by(User.email.asc()).limit(limit).all()
    out: list[AdminUserListItem] = []
    for u in rows:
        is_m, is_me = derived_roles(db, user=u)
        out.append(
            AdminUserListItem(
                user_id=u.id,
                email=u.email,
                is_admin=bool(u.is_admin),
                is_mentor=is_m,
                is_mentee=is_me,
            )
        )
    return out


def _default_mentor_profile(user_id: UUID) -> MentorProfile:
    return MentorProfile(
        user_id=user_id,
        tier_id="PROFESSIONAL",
        is_accepting_requests=True,
        expertise_areas=[],
        total_hours_mentored=0,
    )


def _default_mentee_profile(user_id: UUID) -> MenteeProfile:
    return MenteeProfile(
        user_id=user_id,
        learning_goals=[],
        education_level=None,
        is_minor=False,
        guardian_consent_status="NOT_REQUIRED",
        cached_credit_score=100,
    )


def set_user_roles(db: Session, user_id: UUID, body: AdminUserRoleUpdate) -> AdminUserListItem:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User not found")

    mp = db.query(MentorProfile).filter(MentorProfile.user_id == user_id).first()
    if body.is_mentor:
        if not mp:
            db.add(_default_mentor_profile(user_id))
    elif mp:
        db.delete(mp)

    mep = db.query(MenteeProfile).filter(MenteeProfile.user_id == user_id).first()
    if body.is_mentee:
        if not mep:
            db.add(_default_mentee_profile(user_id))
    elif mep:
        db.delete(mep)

    db.commit()
    db.refresh(user)
    from app.services.event_bus import publish_profile_matching_event

    publish_profile_matching_event({"user_id": str(user_id)})
    is_m, is_me = derived_roles(db, user=user)
    return AdminUserListItem(
        user_id=user.id,
        email=user.email,
        is_admin=bool(user.is_admin),
        is_mentor=is_m,
        is_mentee=is_me,
    )


def list_admin_sessions(db: Session, *, limit: int) -> list[AdminSessionItem]:
    MentorUser = aliased(User)
    MenteeUser = aliased(User)
    rows = (
        db.query(
            MentorshipSession,
            MentorshipConnection,
            MentorProfile,
            MentorUser.email,
            MenteeUser.email,
        )
        .join(MentorshipConnection, MentorshipSession.connection_id == MentorshipConnection.id)
        .join(MentorProfile, MentorshipConnection.mentor_id == MentorProfile.id)
        .join(MentorUser, MentorProfile.user_id == MentorUser.id)
        .join(MenteeProfile, MentorshipConnection.mentee_id == MenteeProfile.id)
        .join(MenteeUser, MenteeProfile.user_id == MenteeUser.id)
        .order_by(MentorshipSession.start_time.desc())
        .limit(limit)
        .all()
    )
    out: list[AdminSessionItem] = []
    for sess, _conn, mp, mentor_email, mentee_email in rows:
        me = mentor_email or ""
        ee = mentee_email or ""
        if sess.price_charged is not None:
            price = int(sess.price_charged)
        else:
            price = resolve_mentor_session_price(db, mp)
        out.append(
            AdminSessionItem(
                session_id=sess.id,
                connection_id=sess.connection_id,
                mentor_name=_display_name_from_email(me),
                mentee_name=_display_name_from_email(ee),
                start_time=sess.start_time,
                status=sess.status,
                price=price,
            )
        )
    return out


def _dispute_reason(payload: Any, kind: str) -> str | None:
    if isinstance(payload, dict):
        for key in ("reason", "note", "description"):
            v = payload.get(key)
            if isinstance(v, str) and v.strip():
                return v.strip()
    return kind or None


def admin_topup_user_credits(db: Session, user_id: UUID, amount: int) -> AdminCreditTopUpResponse:
    if amount < 1:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="amount must be at least 1",
        )
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail=(
                f"No user account exists for user_id={user_id}. "
                "Use a user_id from GET /admin/users (not mentee_profile.id or other ids)."
            ),
        )

    mentee = db.query(MenteeProfile).filter(MenteeProfile.user_id == user_id).first()
    has_remote = bool(credit_client.GAMIFICATION_SERVICE_URL)

    remote_balance: int | None = None
    if has_remote:
        if not credit_client.add_credits(user_id, amount):
            raise HTTPException(
                status.HTTP_502_BAD_GATEWAY,
                detail="Credit service failed to apply top-up",
            )
        bal = credit_client.get_balance(user_id)
        if not bal or bal.get("balance") is None:
            raise HTTPException(
                status.HTTP_502_BAD_GATEWAY,
                detail="Credit service did not return a balance after top-up",
            )
        remote_balance = int(bal["balance"])
    elif not mentee:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Credit service is not configured; user must have a mentee profile for local wallet top-up.",
        )

    if mentee:
        if remote_balance is not None:
            mentee.cached_credit_score = remote_balance
        else:
            mentee.cached_credit_score = int(mentee.cached_credit_score) + amount
        after = int(mentee.cached_credit_score)
        db.add(
            CreditLedgerEntry(
                user_id=user_id,
                delta=amount,
                balance_after=after,
                reason="Admin credit grant",
            )
        )
        db.commit()
        return AdminCreditTopUpResponse(user_id=user_id, amount=amount, balance_after=after)

    return AdminCreditTopUpResponse(
        user_id=user_id,
        amount=amount,
        balance_after=remote_balance,
    )


def _session_booking_credit_cost(db: Session, session_id: UUID) -> int | None:
    """Credits charged at booking: prefer persisted price_charged, else resolved mentor price."""
    sess = (
        db.query(MentorshipSession)
        .filter(MentorshipSession.id == session_id)
        .first()
    )
    if not sess:
        return None
    if sess.price_charged is not None:
        return int(sess.price_charged)
    conn = (
        db.query(MentorshipConnection)
        .filter(MentorshipConnection.id == sess.connection_id)
        .first()
    )
    if not conn:
        return None
    mp = (
        db.query(MentorProfile)
        .filter(MentorProfile.id == conn.mentor_id)
        .first()
    )
    if not mp:
        return None
    return resolve_mentor_session_price(db, mp)


def _mentor_user_id_for_session(db: Session, session_id: UUID) -> UUID | None:
    sess = (
        db.query(MentorshipSession)
        .filter(MentorshipSession.id == session_id)
        .first()
    )
    if not sess:
        return None
    conn = (
        db.query(MentorshipConnection)
        .filter(MentorshipConnection.id == sess.connection_id)
        .first()
    )
    if not conn:
        return None
    mp = (
        db.query(MentorProfile)
        .filter(MentorProfile.id == conn.mentor_id)
        .first()
    )
    return mp.user_id if mp else None


def _no_show_refund_amount(
    db: Session,
    dispute: ReportDispute,
    refund_credits_override: int,
) -> int:
    if dispute.session_id:
        cost = _session_booking_credit_cost(db, dispute.session_id)
        if cost is not None and cost > 0:
            return cost
    return refund_credits_override if refund_credits_override > 0 else 0


def _apply_no_show_refund_credits(
    db: Session,
    *,
    mentee_user_id: UUID,
    amount: int,
    idempotency_key: str,
) -> None:
    """Restore mentee credits via gamification ledger when configured; else legacy/local wallet."""
    if amount < 1:
        return

    has_url = bool(credit_client.GAMIFICATION_SERVICE_URL)
    has_internal = bool(credit_client.INTERNAL_API_TOKEN)

    if has_url and has_internal:
        ok, bal = credit_client.earn_internal(
            user_id=mentee_user_id,
            rule_code=credit_client.RULE_RESOLVE_NO_SHOW_REFUND,
            amount=amount,
            idempotency_key=idempotency_key,
        )
        if not ok:
            raise HTTPException(
                status.HTTP_502_BAD_GATEWAY,
                detail="Gamification service could not apply the no-show refund",
            )
        mentee = (
            db.query(MenteeProfile)
            .filter(MenteeProfile.user_id == mentee_user_id)
            .first()
        )
        if mentee and bal is not None:
            mentee.cached_credit_score = bal
        elif mentee:
            bal_json = credit_client.get_balance(mentee_user_id)
            if bal_json and bal_json.get("balance") is not None:
                mentee.cached_credit_score = int(bal_json["balance"])
        return

    if has_url:
        if not credit_client.add_credits(mentee_user_id, amount):
            raise HTTPException(
                status.HTTP_502_BAD_GATEWAY,
                detail="Credit service failed to apply refund",
            )
        bal = credit_client.get_balance(mentee_user_id)
        if not bal or bal.get("balance") is None:
            raise HTTPException(
                status.HTTP_502_BAD_GATEWAY,
                detail="Credit service did not return a balance after refund",
            )
        remote_balance = int(bal["balance"])
        mentee = (
            db.query(MenteeProfile)
            .filter(MenteeProfile.user_id == mentee_user_id)
            .first()
        )
        if mentee:
            mentee.cached_credit_score = remote_balance
        return

    mentee = (
        db.query(MenteeProfile)
        .filter(MenteeProfile.user_id == mentee_user_id)
        .first()
    )
    if not mentee:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Mentee profile required for local credit refund (gamification not configured).",
        )
    after = int(mentee.cached_credit_score) + amount
    mentee.cached_credit_score = after
    db.add(
        CreditLedgerEntry(
            user_id=mentee_user_id,
            delta=amount,
            balance_after=after,
            reason="No-show dispute resolved (refund)",
        )
    )


def list_admin_disputes(db: Session, *, limit: int) -> list[AdminDisputeItem]:
    rows = (
        db.query(ReportDispute)
        .order_by(ReportDispute.created_at.desc())
        .limit(limit)
        .all()
    )
    out: list[AdminDisputeItem] = []
    for r in rows:
        base = AdminDisputeItem.model_validate(r)
        credits: int | None = None
        if r.session_id:
            credits = _session_booking_credit_cost(db, r.session_id)
        out.append(
            base.model_copy(
                update={
                    "reason": _dispute_reason(r.payload, r.kind),
                    "credits_associated": credits,
                },
            )
        )
    return out


def resolve_dispute(
    db: Session,
    dispute_id: UUID,
    *,
    refund_credits: int = 0,
    apply_mentor_penalty: bool = True,
) -> dict[str, Any]:
    d = db.query(ReportDispute).filter(ReportDispute.id == dispute_id).first()
    if not d:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Dispute not found")
    if d.status == "RESOLVED":
        return {"id": str(d.id), "status": d.status, "idempotent": True}

    refund_amount = _no_show_refund_amount(db, d, refund_credits)
    mentor_uid = _mentor_user_id_for_session(db, d.session_id) if d.session_id else None
    penalty_amount = 0
    if (
        apply_mentor_penalty
        and mentor_uid is not None
        and d.session_id
        and refund_amount > 0
    ):
        penalty_amount = refund_amount

    has_gam_internal = bool(
        credit_client.GAMIFICATION_SERVICE_URL and credit_client.INTERNAL_API_TOKEN
    )

    if has_gam_internal and penalty_amount > 0 and mentor_uid is not None:
        bal = credit_client.get_balance(mentor_uid)
        if not bal or bal.get("balance") is None:
            raise HTTPException(
                status.HTTP_502_BAD_GATEWAY,
                detail="Could not read mentor credit balance for no-show penalty check",
            )
        if int(bal["balance"]) < penalty_amount:
            raise HTTPException(
                status.HTTP_402_PAYMENT_REQUIRED,
                detail="Mentor has insufficient credits for the no-show penalty",
            )

    if refund_amount > 0 and d.opened_by_user_id:
        _apply_no_show_refund_credits(
            db,
            mentee_user_id=d.opened_by_user_id,
            amount=refund_amount,
            idempotency_key=f"no_show_resolve:{d.id}",
        )

    mentor_penalty_applied = 0
    if has_gam_internal and penalty_amount > 0 and mentor_uid is not None:
        ok, _bal = credit_client.deduct_booking(
            user_id=mentor_uid,
            amount=penalty_amount,
            idempotency_key=f"mentor_no_show_penalty:{d.id}",
            rule_code=credit_client.RULE_MENTOR_NO_SHOW_PENALTY,
        )
        if not ok:
            raise HTTPException(
                status.HTTP_502_BAD_GATEWAY,
                detail="Gamification service could not apply mentor no-show penalty",
            )
        mentor_penalty_applied = penalty_amount

    d.status = "RESOLVED"
    d.resolved_at = datetime.now(timezone.utc)

    if d.session_id:
        sess = (
            db.query(MentorshipSession)
            .filter(MentorshipSession.id == d.session_id)
            .first()
        )
        if sess:
            sess.status = "NO_SHOW"

    db.commit()
    return {
        "id": str(d.id),
        "status": d.status,
        "refund_credits_applied": refund_amount,
        "mentor_penalty_credits_applied": mentor_penalty_applied,
    }
