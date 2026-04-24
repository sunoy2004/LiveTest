import { useQuery } from "@tanstack/react-query";
import { Info } from "lucide-react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { fetchAdminSessions } from "@/api/adminApi";
import { useMentorShellAuth } from "@/context/MentorShellAuthContext";
import { cn } from "@/lib/utils";

export default function AdminSessionsPage() {
  const { token } = useMentorShellAuth();

  const q = useQuery({
    queryKey: ["admin", "sessions", token],
    queryFn: () => fetchAdminSessions(token!),
    enabled: Boolean(token),
  });

  return (
    <section className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold text-foreground">Sessions</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Scheduled sessions with resolved session price (stored at booking or derived from mentor tier / override).
        </p>
      </div>

      <div className="flex gap-2 rounded-lg border border-border bg-muted/30 px-3 py-2 text-sm text-muted-foreground">
        <Info className="mt-0.5 h-4 w-4 shrink-0 text-primary" aria-hidden />
        <p>
          <strong className="text-foreground">Session price (credits)</strong> is what was charged (or would be
          charged) for the booking — not a wallet balance.
        </p>
      </div>

      {q.error ? (
        <p className="text-sm text-destructive">{q.error instanceof Error ? q.error.message : "Load failed"}</p>
      ) : null}

      <div className="overflow-x-auto rounded-md border border-border">
        <Table>
          <TableHeader>
            <TableRow className="border-border hover:bg-muted/40">
              <TableHead>Mentor</TableHead>
              <TableHead>Mentee</TableHead>
              <TableHead>Scheduled time</TableHead>
              <TableHead>Session price (credits)</TableHead>
              <TableHead>Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {(q.data ?? []).map((s) => (
              <TableRow key={s.session_id} className="border-border">
                <TableCell className="font-medium">{s.mentor_name}</TableCell>
                <TableCell>{s.mentee_name}</TableCell>
                <TableCell className="text-sm text-muted-foreground">{s.start_time}</TableCell>
                <TableCell>{s.price}</TableCell>
                <TableCell>
                  <span className={cn("text-sm", s.status === "NO_SHOW" && "text-amber-400")}>{s.status}</span>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </section>
  );
}
