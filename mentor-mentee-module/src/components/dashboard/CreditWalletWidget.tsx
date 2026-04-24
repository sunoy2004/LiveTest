import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { format, formatDistanceToNow, parseISO } from "date-fns";
import { ArrowDownRight, ArrowUpRight, Coins, History, Loader2, TrendingUp } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ScrollArea } from "@/components/ui/scroll-area";
import goldenCoinUrl from "@/assets/golden-coin.svg?url";
import { creditWallet } from "@/data/mockData";
import { menteeEarnWaysLive, menteeEarnWaysRoadmap } from "@/data/menteeEarnCoinsGuide";
import { fetchWalletLedgerForUi } from "@/api/creditServiceApi";
import type { CreditLedgerItem } from "@/types/wallet";
import { cn } from "@/lib/utils";
import { Separator } from "@/components/ui/separator";

interface CreditWalletWidgetProps {
  /** Current balance from gamification GET /wallet/me */
  balance?: number;
  /** From gamification wallet (optional display) */
  lifetimeEarned?: number;
  token?: string | null;
}

function summarizeCurrentMonth(txs: CreditLedgerItem[]) {
  const now = new Date();
  let earned = 0;
  let spent = 0;
  for (const t of txs) {
    const d = parseISO(t.created_at);
    if (d.getMonth() !== now.getMonth() || d.getFullYear() !== now.getFullYear()) {
      continue;
    }
    if (t.delta >= 0) {
      earned += t.delta;
    } else {
      spent += Math.abs(t.delta);
    }
  }
  return { earned, spent };
}

const CreditWalletWidget = ({
  balance: balanceProp,
  lifetimeEarned,
  token,
}: CreditWalletWidgetProps) => {
  const { balance: mockBalance, lastTransaction: mockLast, monthlyEarned, monthlySpent } =
    creditWallet;
  const balance = balanceProp ?? mockBalance;
  const [historyOpen, setHistoryOpen] = useState(false);
  const [earnOpen, setEarnOpen] = useState(false);

  const { data: ledgerRows, isFetching: ledgerLoading } = useQuery({
    queryKey: ["gamification", "wallet", "ledger", token],
    queryFn: () => fetchWalletLedgerForUi(token!, 80),
    enabled: Boolean(token),
    staleTime: 20_000,
  });

  const { monthlyEarnedDisplay, monthlySpentDisplay, lastTransactionLabel, lastDelta } =
    useMemo(() => {
      if (!token) {
        return {
          monthlyEarnedDisplay: monthlyEarned,
          monthlySpentDisplay: monthlySpent,
          lastTransactionLabel: mockLast.description,
          lastDelta: mockLast.amount,
        };
      }
      if (!ledgerRows) {
        return {
          monthlyEarnedDisplay: monthlyEarned,
          monthlySpentDisplay: monthlySpent,
          lastTransactionLabel: mockLast.description,
          lastDelta: mockLast.amount,
        };
      }
      if (ledgerRows.length === 0) {
        return {
          monthlyEarnedDisplay: 0,
          monthlySpentDisplay: 0,
          lastTransactionLabel: "No activity yet",
          lastDelta: 0,
        };
      }
      const { earned, spent } = summarizeCurrentMonth(ledgerRows);
      const last = ledgerRows[0];
      return {
        monthlyEarnedDisplay: earned,
        monthlySpentDisplay: spent,
        lastTransactionLabel: last.reason,
        lastDelta: last.delta,
      };
    }, [
      token,
      ledgerRows,
      monthlyEarned,
      monthlySpent,
      mockLast.amount,
      mockLast.description,
    ]);

  return (
    <>
      <div
        className={cn(
          "relative col-span-full rounded-2xl p-6 overflow-hidden",
          "bg-card border border-border shadow-card",
          "animate-slide-up",
        )}
      >
        <div className="absolute top-0 right-0 w-48 h-48 rounded-full gradient-primary opacity-[0.04] -translate-y-1/2 translate-x-1/4 pointer-events-none" />

        <div className="relative flex flex-col sm:flex-row sm:items-center gap-6">
          <div className="flex items-center gap-4 flex-1">
            <div className="shrink-0 h-12 w-12 rounded-2xl overflow-hidden shadow-md shadow-primary/25 ring-2 ring-primary/15 bg-card">
              <img
                src={goldenCoinUrl}
                alt=""
                width={48}
                height={48}
                className="h-full w-full object-cover"
                aria-hidden
              />
            </div>
            <div>
              <p className="text-xs font-medium text-muted-foreground tracking-wider">Wallet</p>
              <div className="flex items-baseline gap-2 mt-0.5 flex-wrap">
                <span className="text-3xl font-bold text-foreground tracking-tight">{balance}</span>
                <span className="text-sm font-medium text-muted-foreground">coins</span>
              </div>
              {typeof lifetimeEarned === "number" && (
                <p className="text-xs text-muted-foreground mt-1">
                  Lifetime earned: <span className="font-medium text-foreground">{lifetimeEarned}</span>
                </p>
              )}
            </div>
          </div>

          <div className="flex gap-4 sm:gap-6">
            <div className="flex items-center gap-2 px-3 py-2 rounded-xl bg-success/10">
              <ArrowUpRight className="h-4 w-4 text-success" />
              <div>
                <p className="text-xs text-muted-foreground">Earned (month)</p>
                <p className="text-sm font-bold text-success">+{monthlyEarnedDisplay}</p>
              </div>
            </div>
            <div className="flex items-center gap-2 px-3 py-2 rounded-xl bg-destructive/10">
              <ArrowDownRight className="h-4 w-4 text-destructive" />
              <div>
                <p className="text-xs text-muted-foreground">Spent (month)</p>
                <p className="text-sm font-bold text-destructive">-{monthlySpentDisplay}</p>
              </div>
            </div>
          </div>

          <div className="hidden lg:flex items-center gap-2 px-3 py-2 rounded-xl bg-muted/60 text-xs text-muted-foreground max-w-[220px]">
            <TrendingUp className="h-3.5 w-3.5 shrink-0" />
            <span className="truncate">Last: {lastTransactionLabel}</span>
            <span
              className={cn(
                "font-bold shrink-0",
                lastDelta < 0 ? "text-destructive" : "text-success",
              )}
            >
              {lastDelta > 0 ? "+" : ""}
              {lastDelta}
            </span>
          </div>

          <div className="flex gap-2">
            <Button
              size="sm"
              variant="outline"
              className="text-xs"
              type="button"
              onClick={() => setHistoryOpen(true)}
              disabled={!token}
            >
              <History className="h-3.5 w-3.5 mr-1" /> History
            </Button>
            <Button
              size="sm"
              type="button"
              className="text-xs gradient-primary border-0 shadow-sm shadow-primary/20"
              onClick={() => setEarnOpen(true)}
            >
              <Coins className="h-3.5 w-3.5 mr-1" /> Earn Coins
            </Button>
          </div>
        </div>
      </div>

      <Dialog open={earnOpen} onOpenChange={setEarnOpen}>
        <DialogContent
          className={cn(
            "flex min-h-0 w-[calc(100vw-1.5rem)] max-w-lg flex-col gap-0 overflow-hidden p-0 sm:w-full",
            "max-h-[min(90dvh,90svh,44rem)]",
          )}
        >
          <DialogHeader className="shrink-0 space-y-2 border-b border-border/50 px-4 pb-4 pt-5 text-left sm:px-6 sm:pb-4 sm:pt-6">
            <DialogTitle className="pr-8 text-base sm:text-lg">How to earn coins</DialogTitle>
            <DialogDescription className="text-xs leading-relaxed sm:text-sm">
              Rewards post to your gamification wallet. Base amounts match the seeded activity rules;
              admins can change values in the gamification service.
            </DialogDescription>
          </DialogHeader>
          <div
            className="min-h-0 flex-1 overflow-y-auto overflow-x-hidden overscroll-y-contain px-4 py-4 sm:px-6 sm:py-5 [scrollbar-gutter:stable]"
            style={{ WebkitOverflowScrolling: "touch" }}
          >
            <div className="mx-auto w-full max-w-prose space-y-4 pb-1">
              <div>
                <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-primary">
                  Available in this platform
                </p>
                <ul className="space-y-3">
                  {menteeEarnWaysLive.map((row) => (
                    <li
                      key={row.title}
                      className="rounded-lg border border-border bg-muted/25 px-3 py-2.5 text-sm sm:px-4 sm:py-3"
                    >
                      <div className="flex flex-col gap-1.5 sm:flex-row sm:items-start sm:justify-between sm:gap-3">
                        <p className="min-w-0 flex-1 font-medium leading-snug text-foreground">{row.title}</p>
                        <span className="shrink-0 text-left text-xs font-semibold tabular-nums text-success sm:text-right sm:whitespace-nowrap">
                          {row.reward}
                        </span>
                      </div>
                      <p className="mt-1.5 text-xs leading-relaxed text-muted-foreground">{row.description}</p>
                    </li>
                  ))}
                </ul>
              </div>

              <Separator />

              <div>
                <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  More ways (roadmap)
                </p>
                <p className="mb-3 text-xs leading-relaxed text-muted-foreground">
                  From the product gamification dictionary — not all flows are wired yet; when enabled,
                  amounts are set per environment in admin.
                </p>
                <ul className="space-y-2.5">
                  {menteeEarnWaysRoadmap.map((row) => (
                    <li
                      key={row.title}
                      className="rounded-lg border border-dashed border-border/80 bg-muted/15 px-3 py-2.5 text-sm sm:px-4"
                    >
                      <div className="flex flex-col gap-1 sm:flex-row sm:items-baseline sm:justify-between sm:gap-3">
                        <span className="min-w-0 font-medium leading-snug text-foreground">{row.title}</span>
                        <span className="shrink-0 text-xs text-muted-foreground">{row.reward}</span>
                      </div>
                      <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{row.description}</p>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      <Dialog open={historyOpen} onOpenChange={setHistoryOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Credit history</DialogTitle>
            <DialogDescription>
              Ledger from the gamification service (bookings, rewards, adjustments). Current balance:{" "}
              <span className="font-semibold text-foreground">{balance}</span>.
            </DialogDescription>
          </DialogHeader>
          {!token ? (
            <p className="text-sm text-muted-foreground py-6 text-center">Sign in to view history.</p>
          ) : ledgerLoading && !ledgerRows?.length ? (
            <div className="flex justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
          ) : !ledgerRows?.length ? (
            <p className="text-sm text-muted-foreground py-6 text-center">
              No transactions yet. Book a session to see credits spent here.
            </p>
          ) : (
            <ScrollArea className="h-[min(360px,50vh)] pr-3">
              <ul className="space-y-3">
                {ledgerRows.map((row) => (
                  <li
                    key={row.id}
                    className="rounded-lg border border-border bg-muted/30 px-3 py-2.5 text-sm"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <p className="text-foreground leading-snug">{row.reason}</p>
                      <span
                        className={cn(
                          "shrink-0 font-semibold tabular-nums",
                          row.delta < 0 ? "text-destructive" : "text-success",
                        )}
                      >
                        {row.delta > 0 ? "+" : ""}
                        {row.delta}
                      </span>
                    </div>
                    <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-[11px] text-muted-foreground">
                      <span>{format(parseISO(row.created_at), "MMM d, yyyy · h:mm a")}</span>
                      <span>
                        Balance after:{" "}
                        <span className="font-medium text-foreground">{row.balance_after}</span>
                      </span>
                      <span className="text-muted-foreground/80">
                        {formatDistanceToNow(parseISO(row.created_at), { addSuffix: true })}
                      </span>
                    </div>
                  </li>
                ))}
              </ul>
            </ScrollArea>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
};

export default CreditWalletWidget;
