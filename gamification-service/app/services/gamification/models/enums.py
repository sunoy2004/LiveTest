from __future__ import annotations

import enum


class TransactionType(str, enum.Enum):
    EARN = "EARN"
    SPEND = "SPEND"
