import { type FormEvent, useCallback, useEffect, useState } from "react";

type Rule = {
  rule_code: string;
  transaction_type: string;
  base_credit_value: number;
  is_active: boolean;
  cooldown_seconds: number;
};

type LedgerRow = {
  transaction_id: string;
  user_id: string;
  user_name?: string;
  rule_code: string;
  amount: number;
  balance_after: number;
  idempotency_key: string;
  created_at: string;
};

type WalletRow = {
  user_id: string;
  user_name?: string;
  current_balance: number;
  lifetime_earned: number;
};

/**
 * Build an absolute API URL on the site origin so paths stay `/admin/...` even when this SPA is
 * served from `/ui/` (otherwise a mistaken relative URL becomes `/ui/admin/...` → 404 Not Found).
 */
function apiUrl(path: string): string {
  const normalized = path.startsWith("/") ? path : `/${path}`;
  if (typeof window === "undefined") return normalized;
  return new URL(normalized, window.location.origin).href;
}

/** Shown under the rule code — helps admins find no-show and booking rules. */
const RULE_HINTS: Record<string, string> = {
  DELIVER_MENTOR_SESSION: "Mentor earns when a session is completed (event-driven).",
  ATTEND_MENTEE_SESSION: "Mentee earns when a session is completed (event-driven).",
  BOOKING_SPEND: "Legacy generic spend label.",
  BOOK_MENTOR_SESSION: "Mentee pays when booking a session (internal deduct; amount from tier).",
  LEGACY_CREDIT_ADD: "Legacy balance top-up compatibility endpoint.",
  ADMIN_GRANT: "Admin UI / API grant to a user wallet.",
  ADMIN_DEDUCT: "Admin UI / API deduction from a user wallet.",
  RESOLVE_NO_SHOW_REFUND:
    "User-service: mentee refund when an admin resolves a no-show dispute (earn; amount = session cost).",
  MENTOR_NO_SHOW_PENALTY:
    "User-service: mentor penalty on the same resolution (spend; amount = session cost).",
};

const fetchOpts: RequestInit = { credentials: "include" };

function jsonHeaders(): HeadersInit {
  return { Accept: "application/json", "Content-Type": "application/json" };
}

export default function App() {
  const [authenticated, setAuthenticated] = useState<boolean | null>(null);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [tab, setTab] = useState<"rules" | "wallet" | "ledger">("rules");
  const [error, setError] = useState<string | null>(null);

  const [rules, setRules] = useState<Rule[]>([]);
  const [ledger, setLedger] = useState<{ total: number; items: LedgerRow[] } | null>(null);
  const [ledgerPage, setLedgerPage] = useState(1);
  const [ledgerUser, setLedgerUser] = useState("");

  const [walletUser, setWalletUser] = useState("");
  const [walletAmount, setWalletAmount] = useState("10");
  const [walletIdem, setWalletIdem] = useState("");
  const [wallets, setWallets] = useState<{ total: number; items: WalletRow[] } | null>(null);
  const [walletPage, setWalletPage] = useState(1);

  const checkStatus = useCallback(async () => {
    setError(null);
    try {
      const res = await fetch(apiUrl("/admin/auth/status"), { ...fetchOpts });
      if (!res.ok) {
        setAuthenticated(false);
        return;
      }
      const data = (await res.json()) as { authenticated?: boolean };
      setAuthenticated(Boolean(data.authenticated));
    } catch {
      setAuthenticated(false);
    }
  }, []);

  useEffect(() => {
    void checkStatus();
  }, [checkStatus]);

  const loadRules = useCallback(async () => {
    setError(null);
    const res = await fetch(apiUrl("/admin/rules"), { ...fetchOpts, headers: { Accept: "application/json" } });
    if (res.status === 401) {
      setAuthenticated(false);
      return;
    }
    if (!res.ok) {
      setError(await res.text());
      return;
    }
    setRules(await res.json());
  }, []);

  const loadWallets = useCallback(async () => {
    setError(null);
    const q = new URLSearchParams({ page: String(walletPage), page_size: "50" });
    const res = await fetch(apiUrl(`/admin/wallets?${q}`), {
      ...fetchOpts,
      headers: { Accept: "application/json" },
    });
    if (res.status === 401) {
      setAuthenticated(false);
      return;
    }
    if (!res.ok) {
      setError(await res.text());
      return;
    }
    setWallets(await res.json());
  }, [walletPage]);

  const loadLedger = useCallback(async () => {
    setError(null);
    const q = new URLSearchParams({ page: String(ledgerPage), page_size: "15" });
    if (ledgerUser.trim()) q.set("user_id", ledgerUser.trim());
    const res = await fetch(apiUrl(`/admin/ledger?${q}`), { ...fetchOpts, headers: { Accept: "application/json" } });
    if (res.status === 401) {
      setAuthenticated(false);
      return;
    }
    if (!res.ok) {
      setError(await res.text());
      return;
    }
    const data = await res.json();
    setLedger({ total: data.total, items: data.items });
  }, [ledgerPage, ledgerUser]);

  useEffect(() => {
    if (authenticated !== true) return;
    if (tab === "rules") void loadRules();
    if (tab === "wallet") void loadWallets();
    if (tab === "ledger") void loadLedger();
  }, [authenticated, tab, loadRules, loadWallets, loadLedger]);

  async function onLogin(e: FormEvent) {
    e.preventDefault();
    setError(null);
    const res = await fetch(apiUrl("/admin/auth/login"), {
      method: "POST",
      headers: jsonHeaders(),
      credentials: "include",
      body: JSON.stringify({ username, password }),
    });
    if (!res.ok) {
      setError((await res.text()) || res.statusText);
      return;
    }
    setPassword("");
    await checkStatus();
  }

  async function onLogout() {
    await fetch(apiUrl("/admin/auth/logout"), { method: "POST", credentials: "include" });
    setAuthenticated(false);
    setRules([]);
    setWallets(null);
    setLedger(null);
  }

  async function saveRule(r: Rule) {
    setError(null);
    const res = await fetch(apiUrl(`/admin/rules/${encodeURIComponent(r.rule_code)}`), {
      method: "PUT",
      headers: jsonHeaders(),
      credentials: "include",
      body: JSON.stringify({
        base_credit_value: r.base_credit_value,
        is_active: r.is_active,
        cooldown_seconds: r.cooldown_seconds,
      }),
    });
    if (res.status === 401) {
      setAuthenticated(false);
      return;
    }
    if (!res.ok) {
      setError(await res.text());
      return;
    }
    await loadRules();
  }

  async function grant(op: "grant" | "deduct") {
    setError(null);
    if (!walletUser.trim() || !walletAmount.trim()) {
      setError("User id and amount required");
      return;
    }
    const idem = walletIdem.trim() || `admin-${op}-${crypto.randomUUID()}`;
    const res = await fetch(
      apiUrl(`/admin/wallet/${encodeURIComponent(walletUser.trim())}/${op}`),
      {
        method: "POST",
        headers: jsonHeaders(),
        credentials: "include",
        body: JSON.stringify({ amount: Number(walletAmount), idempotency_key: idem }),
      },
    );
    if (res.status === 401) {
      setAuthenticated(false);
      return;
    }
    if (!res.ok) {
      setError(await res.text());
      return;
    }
    setWalletIdem("");
    await loadWallets();
  }

  if (authenticated === null) {
    return (
      <div className="layout">
        <h1>Gamification admin</h1>
        <p>Checking session…</p>
      </div>
    );
  }

  if (!authenticated) {
    return (
      <div className="layout">
        <h1>Gamification admin</h1>
        <div className="panel">
          <p>Sign in with the gamification admin username and password (from server environment).</p>
          <form onSubmit={onLogin}>
            <div className="row">
              <div style={{ flex: 1, minWidth: "200px" }}>
                <label htmlFor="user">Username</label>
                <input
                  id="user"
                  autoComplete="username"
                  style={{ width: "100%" }}
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                />
              </div>
              <div style={{ flex: 1, minWidth: "200px" }}>
                <label htmlFor="pass">Password</label>
                <input
                  id="pass"
                  type="password"
                  autoComplete="current-password"
                  style={{ width: "100%" }}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </div>
              <button type="submit">Sign in</button>
            </div>
          </form>
          {error ? <p className="err">{error}</p> : null}
        </div>
      </div>
    );
  }

  return (
    <div className="layout">
      <h1>Gamification admin</h1>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
        <div className="tabs" style={{ marginBottom: 0 }}>
          <button type="button" className={tab === "rules" ? "active" : ""} onClick={() => setTab("rules")}>
            Rules
          </button>
          <button type="button" className={tab === "wallet" ? "active" : ""} onClick={() => setTab("wallet")}>
            Wallets
          </button>
          <button type="button" className={tab === "ledger" ? "active" : ""} onClick={() => setTab("ledger")}>
            Ledger
          </button>
        </div>
        <button type="button" onClick={() => void onLogout()}>
          Sign out
        </button>
      </div>
      {error ? <p className="err">{error}</p> : null}

      {tab === "rules" ? (
        <div className="panel">
          <div className="row" style={{ marginBottom: "0.75rem", alignItems: "center", gap: "1rem" }}>
            <button type="button" onClick={() => void loadRules()}>
              Refresh rules
            </button>
            <span style={{ fontSize: "0.85rem", color: "#64748b" }}>
              {rules.length} rule{rules.length === 1 ? "" : "s"} from the database (run{" "}
              <code style={{ fontSize: "0.8rem" }}>alembic upgrade head</code> if rows are missing).
            </span>
          </div>
          <table>
            <thead>
              <tr>
                <th>Rule</th>
                <th>Type</th>
                <th>Base</th>
                <th>Cooldown (s)</th>
                <th>Active</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {rules.map((r) => (
                <RuleRow key={r.rule_code} initial={r} onSave={saveRule} hints={RULE_HINTS} />
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      {tab === "wallet" ? (
        <div className="panel">
          <div className="row">
            <div>
              <label>User id (UUID)</label>
              <input value={walletUser} onChange={(e) => setWalletUser(e.target.value)} />
            </div>
            <div>
              <label>Amount</label>
              <input value={walletAmount} onChange={(e) => setWalletAmount(e.target.value)} />
            </div>
            <div>
              <label>Idempotency key (optional)</label>
              <input value={walletIdem} onChange={(e) => setWalletIdem(e.target.value)} />
            </div>
          </div>
          <div className="row">
            <button type="button" onClick={() => void grant("grant")}>
              Grant
            </button>
            <button type="button" onClick={() => void grant("deduct")}>
              Deduct
            </button>
          </div>

          <div style={{ marginTop: "1.5rem", borderTop: "1px solid #e2e8f0", paddingTop: "1rem" }}>
            <div className="row" style={{ marginBottom: "0.75rem", alignItems: "center", gap: "1rem" }}>
              <h2 style={{ margin: 0, fontSize: "1.1rem" }}>All wallets</h2>
              <button type="button" onClick={() => void loadWallets()}>
                Refresh
              </button>
              <span style={{ fontSize: "0.85rem", color: "#64748b" }}>
                {wallets?.total ?? "—"} wallet{wallets && wallets.total === 1 ? "" : "s"} (ordered by lifetime earned, highest first)
              </span>
            </div>
            <p style={{ fontSize: "0.85rem", color: "#64748b", marginTop: 0 }}>
              Each row shows the user&apos;s current wallet balance (credits available now, after any spending).
            </p>
            <table>
              <thead>
                <tr>
                  <th>User id</th>
                  <th>Name</th>
                  <th>Balance (wallet)</th>
                </tr>
              </thead>
              <tbody>
                {(wallets?.items ?? []).map((w) => (
                  <tr key={w.user_id}>
                    <td style={{ fontFamily: "monospace", fontSize: "0.75rem" }}>{w.user_id}</td>
                    <td>{w.user_name || "—"}</td>
                    <td>{w.current_balance}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="row">
              <button type="button" disabled={walletPage <= 1} onClick={() => setWalletPage((p) => Math.max(1, p - 1))}>
                Prev
              </button>
              <span>
                Page {walletPage}
                {wallets ? ` of ${Math.max(1, Math.ceil(wallets.total / 50))}` : ""}
              </span>
              <button
                type="button"
                disabled={wallets ? walletPage * 50 >= wallets.total : true}
                onClick={() => setWalletPage((p) => p + 1)}
              >
                Next
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {tab === "ledger" ? (
        <div className="panel">
          <div className="row">
            <div>
              <label>Filter by user id</label>
              <input value={ledgerUser} onChange={(e) => setLedgerUser(e.target.value)} />
            </div>
            <button type="button" onClick={() => void loadLedger()}>
              Refresh
            </button>
          </div>
          <p style={{ fontSize: "0.85rem", color: "#64748b" }}>
            Total rows: {ledger?.total ?? "—"}
          </p>
          <table>
            <thead>
              <tr>
                <th>Time</th>
                <th>User</th>
                <th>Name</th>
                <th>Rule</th>
                <th>Amount</th>
                <th>Balance after</th>
              </tr>
            </thead>
            <tbody>
              {(ledger?.items ?? []).map((row) => (
                <tr key={row.transaction_id}>
                  <td>{row.created_at}</td>
                  <td style={{ fontFamily: "monospace", fontSize: "0.75rem" }}>{row.user_id}</td>
                  <td>{row.user_name || "—"}</td>
                  <td>{row.rule_code}</td>
                  <td>{row.amount}</td>
                  <td>{row.balance_after}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="row">
            <button type="button" disabled={ledgerPage <= 1} onClick={() => setLedgerPage((p) => p - 1)}>
              Prev
            </button>
            <span>Page {ledgerPage}</span>
            <button type="button" onClick={() => setLedgerPage((p) => p + 1)}>
              Next
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}

function RuleRow({
  initial,
  onSave,
  hints,
}: {
  initial: Rule;
  onSave: (r: Rule) => void;
  hints: Record<string, string>;
}) {
  const [r, setR] = useState(initial);
  useEffect(() => setR(initial), [initial]);
  const hint = hints[r.rule_code];
  return (
    <tr>
      <td>
        <div style={{ fontFamily: "monospace", fontSize: "0.85rem" }}>{r.rule_code}</div>
        {hint ? (
          <div style={{ fontSize: "0.75rem", color: "#64748b", maxWidth: "26rem", marginTop: "0.25rem" }}>
            {hint}
          </div>
        ) : null}
      </td>
      <td>{r.transaction_type}</td>
      <td>
        <input
          type="number"
          min={1}
          value={r.base_credit_value}
          onChange={(e) => setR({ ...r, base_credit_value: Number(e.target.value) })}
          style={{ width: "5rem" }}
        />
      </td>
      <td>
        <input
          type="number"
          min={0}
          value={r.cooldown_seconds}
          onChange={(e) => setR({ ...r, cooldown_seconds: Number(e.target.value) })}
          style={{ width: "4rem" }}
        />
      </td>
      <td>
        <input
          type="checkbox"
          checked={r.is_active}
          onChange={(e) => setR({ ...r, is_active: e.target.checked })}
        />
      </td>
      <td>
        <button type="button" onClick={() => onSave(r)}>
          Save
        </button>
      </td>
    </tr>
  );
}
