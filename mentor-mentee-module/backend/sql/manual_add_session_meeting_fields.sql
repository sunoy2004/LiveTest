-- Run against mentoring_db PostgreSQL when not using Alembic.
-- Adds shared editable fields for mentor + mentee (see PATCH /api/v1/sessions/{session_id}/meeting-fields).

ALTER TABLE sessions ADD COLUMN IF NOT EXISTS meeting_notes TEXT NULL;
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS meeting_outcome TEXT NULL;
