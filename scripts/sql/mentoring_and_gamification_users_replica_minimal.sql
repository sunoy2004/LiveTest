-- =============================================================================
-- Minimal `users` replica: keep user_id, role, created_at only.
-- Run on MENTORING and GAMIFICATION databases only — NEVER on User Service.
--
-- Prefer Alembic (applies migrations in order):
--   mentoring:    010_users_replica_trim + 011_users_drop_email
--   gamification: 007_users_replica_trim_if_present
--
-- Manual SQL: run each section against the correct database (`\c mentoring` etc.).
-- =============================================================================

-- --- Mentoring DB -------------------------------------------------------------
BEGIN;

ALTER TABLE users DROP CONSTRAINT IF EXISTS uq_users_email;
ALTER TABLE users DROP CONSTRAINT IF EXISTS users_email_key;

ALTER TABLE users DROP COLUMN IF EXISTS email;
ALTER TABLE users DROP COLUMN IF EXISTS password_hash;
ALTER TABLE users DROP COLUMN IF EXISTS is_admin;

COMMIT;

-- --- Gamification DB (runs only if `public.users` exists) --------------------
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name = 'users'
  ) THEN
    ALTER TABLE users DROP CONSTRAINT IF EXISTS uq_users_email;
    ALTER TABLE users DROP CONSTRAINT IF EXISTS users_email_key;
    ALTER TABLE users DROP COLUMN IF EXISTS email;
    ALTER TABLE users DROP COLUMN IF EXISTS password_hash;
    ALTER TABLE users DROP COLUMN IF EXISTS full_name;
    ALTER TABLE users DROP COLUMN IF EXISTS first_name;
    ALTER TABLE users DROP COLUMN IF EXISTS last_name;
    ALTER TABLE users DROP COLUMN IF EXISTS is_admin;
  END IF;
END $$;
