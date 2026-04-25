import type { CreditLedgerItem } from "@/types/wallet";
import { fetchWalletTransactions } from "@/api/userServiceWalletApi";

export type CreditBalanceResponse = {
  user_id: string;
  balance: number;
  xp: number;
};

/** GET /wallet/me on gamification-service (Bearer = user-service JWT; same JWT_SECRET). */
export type GamificationWalletMe = {
  user_id: string;
  current_balance: number;
  lifetime_earned: number;
};

export function getCreditServiceBase(): string {
  const g = import.meta.env.VITE_GAMIFICATION_SERVICE_URL as string | undefined;
  const legacy = import.meta.env.VITE_CREDIT_SERVICE_URL as string | undefined;
  const base = g ?? legacy;
  return (base ?? "http://localhost:8002").replace(/\/$/, "");
}

/** @deprecated Prefer fetchGamificationWallet — balance is authoritative in gamification ledger. */
export async function fetchCreditBalance(userId: string): Promise<CreditBalanceResponse> {
  const res = await fetch(`${getCreditServiceBase()}/balance/${encodeURIComponent(userId)}`, {
    headers: { Accept: "application/json" },
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || `Credit balance failed (${res.status})`);
  }
  return res.json() as Promise<CreditBalanceResponse>;
}

export async function fetchGamificationWallet(token: string): Promise<GamificationWalletMe> {
  const res = await fetch(`${getCreditServiceBase()}/wallet/me`, {
    headers: {
      Accept: "application/json",
      Authorization: `Bearer ${token}`,
    },
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || `Wallet failed (${res.status})`);
  }
  return res.json() as Promise<GamificationWalletMe>;
}

/** GET /wallet/history on gamification-service (same JWT as User Service). */
export type GamificationLedgerRow = {
  transaction_id: string;
  rule_code: string;
  amount: number;
  balance_after: number;
  created_at: string;
};

export function labelGamificationRuleCode(ruleCode: string): string {
  const map: Record<string, string> = {
    BOOK_MENTOR_SESSION: "Session booking",
    RESOLVE_NO_SHOW_REFUND: "Refund (dispute resolution)",
    MENTOR_NO_SHOW_PENALTY: "Mentor no-show penalty",
  };
  return map[ruleCode] ?? ruleCode.replace(/_/g, " ");
}

export async function fetchGamificationWalletHistory(
  token: string,
  limit = 80,
): Promise<GamificationLedgerRow[]> {
  const q = new URLSearchParams({ limit: String(Math.min(Math.max(limit, 1), 200)) });
  const res = await fetch(`${getCreditServiceBase()}/wallet/history?${q}`, {
    headers: {
      Accept: "application/json",
      Authorization: `Bearer ${token}`,
    },
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || `Wallet history failed (${res.status})`);
  }
  return res.json() as Promise<GamificationLedgerRow[]>;
}

/**
 * Ledger lines for the dashboard wallet widget: gamification ledger first (source of truth),
 * User Service mirror (`/wallet/transactions`) if gamification is unreachable.
 */
export async function fetchWalletLedgerForUi(token: string, limit = 80): Promise<CreditLedgerItem[]> {
  try {
    const rows = await fetchGamificationWalletHistory(token, limit);
    return rows.map((r) => ({
      id: r.transaction_id,
      delta: r.amount,
      balance_after: r.balance_after,
      reason: labelGamificationRuleCode(r.rule_code),
      created_at: r.created_at,
    }));
  } catch {
    return fetchWalletTransactions(token, limit);
  }
}
