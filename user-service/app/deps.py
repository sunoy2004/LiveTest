"""FastAPI dependencies (re-exported from middleware for stable imports)."""

from app.middleware.auth import get_current_user, require_admin

__all__ = ["get_current_user", "require_admin"]
