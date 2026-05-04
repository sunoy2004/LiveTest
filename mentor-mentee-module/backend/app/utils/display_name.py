"""Display helpers. Prefer JWT email in API handlers; DB `users` replica has no email."""

from __future__ import annotations

import uuid


def from_email(email: str | None) -> str:
    if not email:
        return "User"
    local = email.split("@", 1)[0]
    return local.replace("_", " ").replace(".", " ").strip().title() or "User"


def split_local_parts(email: str | None) -> tuple[str | None, str | None]:
    """Rough first/last split from email local-part for API compatibility."""
    name = from_email(email)
    parts = name.split()
    if len(parts) <= 1:
        return parts[0] if parts else None, None
    return parts[0], " ".join(parts[1:])


def label_from_user_id(user_id: uuid.UUID | None) -> str:
    """Stable short label when `users.email` is not stored on domain replicas."""
    if user_id is None:
        return "User"
    s = str(user_id).replace("-", "")
    return f"User {s[:8]}"


def label_from_user_id_str(value: str | None) -> str:
    """Like `label_from_user_id` but accepts UUID text (or legacy email string)."""
    if not value or not str(value).strip():
        return "User"
    try:
        return label_from_user_id(uuid.UUID(str(value).strip()))
    except ValueError:
        return from_email(str(value).strip())
