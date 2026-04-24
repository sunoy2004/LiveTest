from __future__ import annotations

from fastapi import HTTPException, status

from app.services.gamification.services.exceptions import (
    CooldownActiveError,
    GamificationError,
    InsufficientFundsError,
    InvalidAmountError,
    RuleInactiveError,
    RuleNotFoundError,
)


def raise_http(exc: GamificationError) -> None:
    if isinstance(exc, RuleNotFoundError):
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail=f"Unknown activity rule: {exc.rule_code}",
        ) from exc
    if isinstance(exc, RuleInactiveError):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f"Activity rule is disabled: {exc.rule_code}",
        ) from exc
    if isinstance(exc, CooldownActiveError):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, detail="Rule cooldown active") from exc
    if isinstance(exc, InsufficientFundsError):
        raise HTTPException(status.HTTP_402_PAYMENT_REQUIRED, detail="Insufficient credits") from exc
    if isinstance(exc, InvalidAmountError):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Gamification error") from exc
