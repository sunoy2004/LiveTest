/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** User Service (identity + domain profiles) — GET /profile/full, POST /login */
  readonly VITE_USER_SERVICE_URL?: string;
  /** Mentoring FastAPI base URL (API Gateway origin); paths use /api/v1/... */
  readonly VITE_MENTORING_API_BASE_URL?: string;
  /** AI Matching / Graph service — Workflow 2: GET /recommendations */
  readonly VITE_AI_API_BASE_URL?: string;
  /** Simulates API Gateway header X-User-Id (RS256 identity from User Service) */
  readonly VITE_DEV_USER_ID?: string;
  /** Set "true" to send X-Is-Admin: true for admin routes */
  readonly VITE_DEV_IS_ADMIN?: string;
  /** DPDP dev toggle — minor user */
  readonly VITE_DEV_IS_MINOR?: string;
  /** PENDING | GRANTED | NOT_REQUIRED — mentee guardian_consent_status when API offline */
  readonly VITE_DEV_GUARDIAN_CONSENT?: string;
  /** Gamification Service (credit ledger) base URL */
  readonly VITE_GAMIFICATION_SERVICE_URL?: string;
  /** Legacy Credit Service fallback URL */
  readonly VITE_CREDIT_SERVICE_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
