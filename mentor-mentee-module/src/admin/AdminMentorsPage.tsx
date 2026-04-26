import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Info, HelpCircle, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { fetchAdminMentors, putAdminMentorPricing, type AdminMentorRow } from "@/api/adminApi";
import { useMentorShellAuth } from "@/context/MentorShellAuthContext";
import { toast } from "@/hooks/use-toast";
import { useEffect, useMemo, useState } from "react";
import { matchesAdminSearch } from "@/lib/utils";

const TIERS = ["TIER_1", "TIER_2", "TIER_3"] as const;

function MentorPricingRow({
  row,
  token,
  onSaved,
}: {
  row: AdminMentorRow;
  token: string;
  onSaved: () => void;
}) {
  const [tier, setTier] = useState<(typeof TIERS)[number]>(
    TIERS.includes(row.tier as (typeof TIERS)[number]) ? (row.tier as (typeof TIERS)[number]) : "TIER_2",
  );
  const [sessionPrice, setSessionPrice] = useState(
    row.base_credit_override != null ? String(row.base_credit_override) : "",
  );

  useEffect(() => {
    setTier(TIERS.includes(row.tier as (typeof TIERS)[number]) ? (row.tier as (typeof TIERS)[number]) : "TIER_2");
    setSessionPrice(row.base_credit_override != null ? String(row.base_credit_override) : "");
  }, [row]);

  const saveMutation = useMutation({
    mutationFn: async () => {
      let base_credit_override: number | null = null;
      const t = sessionPrice.trim();
      if (t !== "") {
        const n = Number.parseInt(t, 10);
        if (!Number.isFinite(n) || n < 1) {
          throw new Error("Session price must be a whole number ≥ 1, or leave empty to use the tier default.");
        }
        base_credit_override = n;
      }
      return putAdminMentorPricing(token, row.id, { tier, base_credit_override });
    },
    onSuccess: () => {
      onSaved();
      toast({ title: "Mentor pricing saved" });
    },
    onError: (err) => {
      toast({
        title: "Save failed",
        description: err instanceof Error ? err.message : "Unknown error",
        variant: "destructive",
      });
    },
  });

  return (
    <TableRow className="border-border">
      <TableCell className="font-medium">{row.name}</TableCell>
      <TableCell className="text-muted-foreground">{row.email}</TableCell>
      <TableCell>
        <Label className="sr-only" htmlFor={`tier-${row.id}`}>
          Mentor level
        </Label>
        <select
          id={`tier-${row.id}`}
          className="flex h-9 w-full min-w-[7rem] rounded-md border border-input bg-background px-2 text-sm"
          value={tier}
          onChange={(e) => setTier(e.target.value as (typeof TIERS)[number])}
        >
          {TIERS.map((x) => (
            <option key={x} value={x}>
              {x}
            </option>
          ))}
        </select>
      </TableCell>
      <TableCell>
        <Label className="sr-only" htmlFor={`price-${row.id}`}>
          Session price credits
        </Label>
        <Input
          id={`price-${row.id}`}
          type="number"
          min={1}
          placeholder="Tier default"
          className="h-9 max-w-[9rem]"
          value={sessionPrice}
          onChange={(e) => setSessionPrice(e.target.value)}
        />
      </TableCell>
      <TableCell className="text-right">
        <Button type="button" size="sm" disabled={saveMutation.isPending} onClick={() => saveMutation.mutate()}>
          {saveMutation.isPending ? "Saving…" : "Save"}
        </Button>
      </TableCell>
    </TableRow>
  );
}

export default function AdminMentorsPage() {
  const { token } = useMentorShellAuth();
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");

  const q = useQuery({
    queryKey: ["admin", "mentors", token],
    queryFn: () => fetchAdminMentors(token!),
    enabled: Boolean(token),
    refetchInterval: 10_000,
  });

  const filtered = useMemo(() => {
    const rows = q.data ?? [];
    return rows.filter((m) =>
      matchesAdminSearch(search, m.name, m.email, m.tier, m.base_credit_override),
    );
  }, [q.data, search]);

  return (
    <section className="space-y-4">
      <div>
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="text-lg font-semibold text-foreground">Mentors</h2>
          <Tooltip>
            <TooltipTrigger asChild>
              <button
                type="button"
                className="inline-flex rounded-md text-muted-foreground hover:text-foreground"
                aria-label="Pricing help"
              >
                <HelpCircle className="h-4 w-4" />
              </button>
            </TooltipTrigger>
            <TooltipContent className="max-w-xs border-border">
              Admins can configure mentor pricing here. All payments are handled via the gamification system.
            </TooltipContent>
          </Tooltip>
        </div>
        <p className="mt-1 text-sm text-muted-foreground">
          <strong className="text-foreground">Mentor level</strong> (TIER_1–3) sets the default session price from
          tier rules. <strong className="text-foreground">Session price (credits)</strong> overrides that amount for
          bookings with this mentor only — it is not a wallet balance.
        </p>
      </div>

      <div className="flex gap-2 rounded-lg border border-border bg-muted/30 px-3 py-2 text-sm text-muted-foreground">
        <Info className="mt-0.5 h-4 w-4 shrink-0 text-primary" aria-hidden />
        <p>
          This sets the price for booking a session with each mentor. Wallet credits are managed by the gamification
          service.
        </p>
      </div>

      {q.error ? (
        <p className="text-sm text-destructive">{q.error instanceof Error ? q.error.message : "Load failed"}</p>
      ) : null}

      <div className="relative max-w-xl">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" aria-hidden />
        <Input
          type="search"
          placeholder="Search by name, email, mentor level, or session price…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="bg-background pl-9"
          aria-label="Search mentors"
        />
      </div>

      <div className="overflow-x-auto rounded-md border border-border">
        <Table>
          <TableHeader>
            <TableRow className="border-border hover:bg-muted/40">
              <TableHead>Mentor name</TableHead>
              <TableHead>Email</TableHead>
              <TableHead>
                <span className="inline-flex items-center gap-1">
                  Mentor level
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <span className="cursor-help text-muted-foreground">
                        <HelpCircle className="h-3.5 w-3.5" />
                      </span>
                    </TooltipTrigger>
                    <TooltipContent>TIER_1 / TIER_2 / TIER_3 — default band before session price override.</TooltipContent>
                  </Tooltip>
                </span>
              </TableHead>
              <TableHead>Session price (credits)</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {(q.data ?? []).length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} className="text-muted-foreground">
                  No mentor profiles found. Create mentor accounts via User Service / seed data.
                </TableCell>
              </TableRow>
            ) : filtered.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} className="text-muted-foreground">
                  No mentors match your search.
                </TableCell>
              </TableRow>
            ) : (
              filtered.map((m) => (
                <MentorPricingRow
                  key={m.id}
                  row={m}
                  token={token!}
                  onSaved={() => void queryClient.invalidateQueries({ queryKey: ["admin", "mentors", token] })}
                />
              ))
            )}
          </TableBody>
        </Table>
      </div>
    </section>
  );
}
