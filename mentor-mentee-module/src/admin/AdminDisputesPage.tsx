import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { format, parseISO } from "date-fns";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { AdminDisputeRow } from "@/api/adminApi";
import { fetchAdminDisputes, postResolveDispute } from "@/api/adminApi";
import { useMentorShellAuth } from "@/context/MentorShellAuthContext";
import { cn } from "@/lib/utils";

function safeFormatIso(iso: string): string {
  try {
    return format(parseISO(iso), "PPpp");
  } catch {
    return iso;
  }
}

export default function AdminDisputesPage() {
  const { token } = useMentorShellAuth();
  const queryClient = useQueryClient();
  const [viewing, setViewing] = useState<AdminDisputeRow | null>(null);

  const q = useQuery({
    queryKey: ["admin", "disputes", token],
    queryFn: () => fetchAdminDisputes(token!),
    enabled: Boolean(token),
  });

  const resolveMutation = useMutation({
    mutationFn: (id: string) => postResolveDispute(token!, id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["admin", "disputes", token] });
      void queryClient.invalidateQueries({ queryKey: ["admin", "sessions", token] });
    },
  });

  return (
    <section className="space-y-3">
      <div>
        <h2 className="text-lg font-semibold text-foreground">Disputes</h2>
        <p className="text-sm text-muted-foreground">Open disputes can be marked resolved (demo uses zero refund).</p>
      </div>

      {q.error ? (
        <p className="text-sm text-destructive">{q.error instanceof Error ? q.error.message : "Load failed"}</p>
      ) : null}

      <div className="overflow-x-auto rounded-md border border-border">
        <Table>
          <TableHeader>
            <TableRow className="border-border hover:bg-muted/40">
              <TableHead>Session</TableHead>
              <TableHead>Reason</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Action</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {(q.data ?? []).map((d) => (
              <TableRow key={d.id} className="border-border">
                <TableCell className="font-mono text-xs">{d.session_id ?? "—"}</TableCell>
                <TableCell className="max-w-xs truncate text-sm text-muted-foreground">{d.reason ?? d.kind}</TableCell>
                <TableCell>{d.status}</TableCell>
                <TableCell className="text-right">
                  <div className="flex flex-wrap justify-end gap-2">
                    <Button type="button" size="sm" variant="outline" onClick={() => setViewing(d)}>
                      View
                    </Button>
                    {d.status === "OPEN" ? (
                      <Button
                        type="button"
                        size="sm"
                        variant="secondary"
                        disabled={resolveMutation.isPending}
                        onClick={() => resolveMutation.mutate(d.id)}
                      >
                        Resolve
                      </Button>
                    ) : null}
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <Dialog open={viewing != null} onOpenChange={(open) => !open && setViewing(null)}>
        <DialogContent
          className={cn(
            "flex min-h-0 w-[calc(100vw-1.5rem)] max-w-lg flex-col gap-0 overflow-hidden p-0 sm:w-full",
            "max-h-[min(90dvh,90svh,36rem)]",
          )}
        >
          <DialogHeader className="shrink-0 space-y-1 border-b border-border/50 px-4 pb-4 pt-5 text-left sm:px-6">
            <DialogTitle className="pr-8 text-base sm:text-lg">Dispute details</DialogTitle>
            <DialogDescription className="break-all font-mono text-xs leading-relaxed">
              {viewing?.id ?? ""}
            </DialogDescription>
          </DialogHeader>
          {viewing ? (
            <div
              className="min-h-0 flex-1 overflow-y-auto overflow-x-hidden overscroll-y-contain px-4 py-4 sm:px-6 sm:py-5 [scrollbar-gutter:stable]"
              style={{ WebkitOverflowScrolling: "touch" }}
            >
              <dl className="space-y-3.5 text-sm">
                <div>
                  <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Status</dt>
                  <dd className="mt-0.5 font-medium text-foreground">{viewing.status}</dd>
                </div>
                <div>
                  <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Kind</dt>
                  <dd className="mt-0.5 text-foreground">{viewing.kind}</dd>
                </div>
                <div>
                  <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Session</dt>
                  <dd className="mt-0.5 break-all font-mono text-xs text-foreground">
                    {viewing.session_id ?? "—"}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                    Credits associated
                  </dt>
                  <dd className="mt-0.5 font-semibold tabular-nums text-foreground">
                    {typeof viewing.credits_associated === "number" && viewing.credits_associated >= 0
                      ? `${viewing.credits_associated} credits`
                      : "—"}
                  </dd>
                  <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
                    Credits charged to book this session (when a session is linked).
                  </p>
                </div>
                <div>
                  <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Reason</dt>
                  <dd className="mt-0.5 whitespace-pre-wrap text-foreground">{viewing.reason ?? "—"}</dd>
                </div>
                <div>
                  <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                    Opened by (user id)
                  </dt>
                  <dd className="mt-0.5 break-all font-mono text-xs text-foreground">
                    {viewing.opened_by_user_id ?? "—"}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Created</dt>
                  <dd className="mt-0.5 text-foreground">
                    {safeFormatIso(viewing.created_at)}
                  </dd>
                </div>
                {viewing.resolved_at ? (
                  <div>
                    <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Resolved</dt>
                    <dd className="mt-0.5 text-foreground">{safeFormatIso(viewing.resolved_at)}</dd>
                  </div>
                ) : null}
              </dl>
            </div>
          ) : null}
        </DialogContent>
      </Dialog>
    </section>
  );
}
