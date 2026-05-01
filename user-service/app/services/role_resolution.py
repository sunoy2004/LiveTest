from sqlalchemy.orm import Session

from app.models import MenteeProfile, MentorProfile, User


def user_has_mentor_profile(db: Session, user_id) -> bool:
    return (
        db.query(MentorProfile.id).filter(MentorProfile.user_id == user_id).first()
        is not None
    )


def user_has_mentee_profile(db: Session, user_id) -> bool:
    return (
        db.query(MenteeProfile.id).filter(MenteeProfile.user_id == user_id).first()
        is not None
    )


def user_has_admin_profile(db: Session, user_id) -> bool:
    """True when ``users.role`` is 'ADMIN' (authoritative RBAC flag)."""
    row = db.query(User.role).filter(User.id == user_id).first()
    return bool(row and "ADMIN" in (row[0] or []))


def derived_roles(db: Session, *, user: User) -> tuple[bool, bool]:
    return (
        user_has_mentor_profile(db, user.id),
        user_has_mentee_profile(db, user.id),
    )
