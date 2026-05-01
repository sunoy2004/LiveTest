"""Display names when profiles do not store first/last (schema: users.email is canonical)."""


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
