from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.middleware.auth import require_admin
from app.models import MenteeProfile, MentorProfile, MentorTier, User
from app.schemas import (
    AdminConnectionCreateBody,
    AdminConnectionItem,
    AdminCreditGrantBody,
    AdminCreditTopUpBody,
    AdminCreditTopUpResponse,
    AdminDisputeItem,
    AdminMenteeListItem,
    AdminMentorListItem,
    AdminMentorPricingBody,
    AdminSessionItem,
    AdminUserListItem,
    AdminUserRoleUpdate,
    DisputeResolveBody,
    MentorTierUpdate,
)
from app.services import admin_service

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/credits", response_model=AdminCreditTopUpResponse)
def admin_grant_credits(
    body: AdminCreditGrantBody,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Grant credits by user id (same logic as POST /admin/users/{user_id}/credits)."""
    return admin_service.admin_topup_user_credits(db, body.user_id, body.amount)


@router.get("/users", response_model=list[AdminUserListItem])
def admin_list_users(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
    limit: int = Query(100, ge=1, le=500),
):
    return admin_service.list_admin_users(db, limit=limit)


@router.get("/mentors", response_model=list[AdminMentorListItem])
def admin_list_mentors(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
    limit: int = Query(200, ge=1, le=500),
):
    return admin_service.list_admin_mentors(db, limit=limit)


@router.get("/mentees", response_model=list[AdminMenteeListItem])
def admin_list_mentees(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
    limit: int = Query(200, ge=1, le=500),
):
    return admin_service.list_admin_mentees(db, limit=limit)


@router.get("/connections", response_model=list[AdminConnectionItem])
async def admin_list_connections(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
    limit: int = Query(200, ge=1, le=500),
):
    return await admin_service.list_admin_connections(db, limit=limit)


@router.post("/connections", response_model=AdminConnectionItem)
def admin_create_connection(
    body: AdminConnectionCreateBody,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    return admin_service.admin_ensure_connection(
        db,
        mentor_user_id=body.mentor_user_id,
        mentee_user_id=body.mentee_user_id,
    )


@router.put("/users/{user_id}/role", response_model=AdminUserListItem)
def admin_update_user_role(
    user_id: UUID,
    body: AdminUserRoleUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    return admin_service.set_user_roles(db, user_id, body)


@router.post("/users/{user_id}/credits", response_model=AdminCreditTopUpResponse)
def admin_topup_user_credits(
    user_id: UUID,
    body: AdminCreditTopUpBody,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    return admin_service.admin_topup_user_credits(db, user_id, body.amount)


@router.get("/sessions", response_model=list[AdminSessionItem])
def admin_list_sessions(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
    limit: int = Query(100, ge=1, le=500),
):
    return admin_service.list_admin_sessions(db, limit=limit)


@router.get("/disputes", response_model=list[AdminDisputeItem])
def admin_list_disputes(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
    limit: int = Query(100, ge=1, le=500),
):
    return admin_service.list_admin_disputes(db, limit=limit)


@router.post("/disputes/{dispute_id}/resolve")
def admin_resolve_dispute(
    dispute_id: UUID,
    body: DisputeResolveBody = DisputeResolveBody(),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    return admin_service.resolve_dispute(
        db,
        dispute_id,
        refund_credits=body.refund_credits,
        apply_mentor_penalty=body.apply_mentor_penalty,
    )


@router.put("/mentor/{mentor_id}")
def admin_update_mentor_pricing(
    mentor_id: UUID,
    body: AdminMentorPricingBody,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    row = admin_service.admin_update_mentor_pricing(db, mentor_id, body)
    return {
        "mentor_profile_id": str(row.id),
        "tier": row.pricing_tier,
        "base_credit_override": row.base_credit_override,
    }


@router.put("/tiers/{tier_id}")
def admin_upsert_tier(
    tier_id: str,
    body: MentorTierUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    row = db.query(MentorTier).filter(MentorTier.tier_id == tier_id).first()
    if row:
        if body.tier_name is not None:
            row.tier_name = body.tier_name
        if body.session_credit_cost is not None:
            row.session_credit_cost = body.session_credit_cost
    else:
        if not body.tier_name or body.session_credit_cost is None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="tier_name and session_credit_cost required for new tier",
            )
        row = MentorTier(
            tier_id=tier_id,
            tier_name=body.tier_name,
            session_credit_cost=body.session_credit_cost,
        )
        db.add(row)
    db.commit()
    db.refresh(row)
    return {
        "tier_id": row.tier_id,
        "tier_name": row.tier_name,
        "session_credit_cost": row.session_credit_cost,
    }


@router.put("/profiles/{mentee_profile_id}/revoke-consent")
def admin_revoke_consent(
    mentee_profile_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    prof = (
        db.query(MenteeProfile)
        .filter(MenteeProfile.id == mentee_profile_id)
        .first()
    )
    if not prof:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Mentee profile not found")
    prof.guardian_consent_status = "REVOKED"
    db.commit()
    return {"mentee_profile_id": str(prof.id), "guardian_consent_status": prof.guardian_consent_status}
