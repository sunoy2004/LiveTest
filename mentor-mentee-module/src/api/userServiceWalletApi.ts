import { getUserServiceBase } from "@/api/userService";
import type { CreditLedgerItem } from "@/types/wallet";

function headers(token: string): HeadersInit {
  return {
    Authorization: `Bearer ${token}`,
    Accept: "application/json",
  };
}

export async function fetchWalletTransactions(
  token: string,
  limit = 50,
): Promise<CreditLedgerItem[]> {
  const q = new URLSearchParams({ limit: String(limit) });
  const res = await fetch(`${getUserServiceBase()}/wallet/transactions?${q}`, {
    headers: headers(token),
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || `Wallet history failed (${res.status})`);
  }
  return res.json() as Promise<CreditLedgerItem[]>;
}
