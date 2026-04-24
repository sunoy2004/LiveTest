"""Well-known activity rule codes."""

BOOK_MENTOR_SESSION = "BOOK_MENTOR_SESSION"
BOOKING_SPEND = "BOOKING_SPEND"
LEGACY_CREDIT_ADD = "LEGACY_CREDIT_ADD"
ADMIN_GRANT = "ADMIN_GRANT"
ADMIN_DEDUCT = "ADMIN_DEDUCT"
DELIVER_MENTOR_SESSION = "DELIVER_MENTOR_SESSION"
ATTEND_MENTEE_SESSION = "ATTEND_MENTEE_SESSION"
# Admin-approved refund after no-show dispute: credits mentee for the booking amount.
RESOLVE_NO_SHOW_REFUND = "RESOLVE_NO_SHOW_REFUND"
# Mentor charged when admin resolves a no-show (amount usually equals session booking cost).
MENTOR_NO_SHOW_PENALTY = "MENTOR_NO_SHOW_PENALTY"
