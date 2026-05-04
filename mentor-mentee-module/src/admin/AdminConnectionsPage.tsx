import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Info, Search } from "lucide-react";
import { fetchAdminConnections, type AdminConnectionRow } from "@/api/adminApi";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { cn } from "@/lib/utils";
import { useMentorShellAuth } from "@/context/MentorShellAuthContext";

type MentorGroup = {
  mentorUserId: string;
  mentorEmail: string;
  mentorName: string;
  mentees: {
    connectionId: string;
    menteeUserId: string;
    menteeEmail: string;
    menteeName: string;
    status: string;
  }[];
};

function groupConnections(rows: AdminConnectionRow[]): MentorGroup[] {
  const map = new Map<string, MentorGroup>();
  const seenPair = new Set<string>();
  for (const r of rows) {
    let g = map.get(r.mentor_user_id);
    if (!g) {
      g = {
        mentorUserId: r.mentor_user_id,
        mentorEmail: r.mentor_email,
        mentorName: r.mentor_name?.trim() || r.mentor_email || "User",
        mentees: [],
      };
      map.set(r.mentor_user_id, g);
    }
    const pair = `${r.mentor_user_id}:${r.mentee_user_id}`;
    if (seenPair.has(pair)) continue;
    seenPair.add(pair);
    g.mentees.push({
      connectionId: r.connection_id,
      menteeUserId: r.mentee_user_id,
      menteeEmail: r.mentee_email,
      menteeName: r.mentee_name?.trim() || r.mentee_email || "User",
      status: r.status,
    });
  }
  for (const g of map.values()) {
    g.mentees.sort((a, b) => a.menteeEmail.localeCompare(b.menteeEmail));
  }
  return [...map.values()].sort((a, b) => a.mentorEmail.localeCompare(b.mentorEmail));
}

function rowMatches(q: string, ...parts: (string | undefined)[]): boolean {
  if (!q) return true;
  const s = q.toLowerCase();
  return parts.some((p) => (p ?? "").toLowerCase().includes(s));
}

export default function AdminConnectionsPage() {
  const { token } = useMentorShellAuth();
  const [search, setSearch] = useState("");
  const [selectedMentorId, setSelectedMentorId] = useState<string | null>(null);

  const q = useQuery({
    queryKey: ["admin", "connections", token],
    queryFn: () => fetchAdminConnections(token!),
    enabled: Boolean(token),
    refetchInterval: 10_000,
  });

  const groups = useMemo(() => groupConnections(q.data ?? []), [q.data]);

  const filtered = useMemo(() => {
    const sq = search.trim();
    if (!sq) return groups;
    return groups.filter((g) => {
      const mentorHit = rowMatches(sq, g.mentorEmail, g.mentorName);
      const menteeHit = g.mentees.some((m) => rowMatches(sq, m.menteeEmail, m.menteeName));
      return mentorHit || menteeHit;
    });
  }, [groups, search]);

  useEffect(() => {
    if (filtered.length === 0) {
      setSelectedMentorId(null);
      return;
    }
    setSelectedMentorId((prev) => {
      if (prev && filtered.some((g) => g.mentorUserId === prev)) return prev;
      return filtered[0].mentorUserId;
    });
  }, [filtered]);

  const selected = filtered.find((g) => g.mentorUserId === selectedMentorId) ?? null;

  const menteesVisible = useMemo(() => {
    if (!selected) return [];
    const sq = search.trim();
    if (!sq) return selected.mentees;
    const mentorHit = rowMatches(sq, selected.mentorEmail, selected.mentorName);
    if (mentorHit) return selected.mentees;
    return selected.mentees.filter((m) => rowMatches(sq, m.menteeEmail, m.menteeName));
  }, [selected, search]);

  return (
    <section className="flex min-h-0 flex-1 flex-col gap-4">
      <div>
        <h2 className="text-lg font-semibold text-foreground">Connections</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Mentor–mentee links. Select a mentor to see every mentee they are connected to.
        </p>
      </div>

      <div className="flex gap-2 rounded-lg border border-border bg-muted/30 px-3 py-2 text-sm text-muted-foreground">
        <Info className="mt-0.5 h-4 w-4 shrink-0 text-primary" aria-hidden />
        <p>
          Search matches mentor or mentee name, user ID, or status. Mentors with no matching mentees are hidden when the query only
          matches a mentee elsewhere.
        </p>
      </div>

      <div className="relative max-w-xl">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" aria-hidden />
        <Input
          type="search"
          placeholder="Search mentor or mentee…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="bg-background pl-9"
          aria-label="Search connections"
        />
      </div>

      {q.error ? (
        <p className="text-sm text-destructive">{q.error instanceof Error ? q.error.message : "Load failed"}</p>
      ) : null}

      <div className="grid min-h-0 flex-1 gap-4 md:grid-cols-[minmax(0,280px)_1fr] md:gap-6">
        <div className="flex min-h-0 flex-col rounded-md border border-border bg-card/40">
          <div className="border-b border-border px-3 py-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Mentors ({filtered.length})
          </div>
          <div className="min-h-[200px] max-h-[min(60vh,520px)] overflow-y-auto p-2">
            {filtered.length === 0 ? (
              <p className="px-2 py-4 text-sm text-muted-foreground">
                {groups.length === 0 ? "No connections yet." : "No matches for this search."}
              </p>
            ) : (
              <ul className="space-y-1">
                {filtered.map((g) => {
                  const active = g.mentorUserId === selectedMentorId;
                  return (
                    <li key={g.mentorUserId}>
                      <button
                        type="button"
                        onClick={() => setSelectedMentorId(g.mentorUserId)}
                        className={cn(
                          "w-full rounded-md px-3 py-2.5 text-left text-sm transition-colors",
                          active
                            ? "bg-primary text-primary-foreground"
                            : "bg-muted/40 text-foreground hover:bg-muted",
                        )}
                      >
                        <div className="font-medium">{g.mentorName}</div>
                        <div className={cn("truncate text-xs", active ? "text-primary-foreground/90" : "text-muted-foreground")}>
                          {g.mentorEmail}
                        </div>
                        <div className={cn("mt-1 text-xs", active ? "text-primary-foreground/80" : "text-muted-foreground")}>
                          {g.mentees.length} mentee{g.mentees.length === 1 ? "" : "s"}
                        </div>
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        </div>

        <div className="flex min-h-0 min-w-0 flex-col overflow-hidden rounded-md border border-border">
          <div className="border-b border-border px-4 py-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Mentees for selected mentor
          </div>
          <div className="min-h-[200px] flex-1 overflow-x-auto overflow-y-auto">
            {!selected ? (
              <p className="p-4 text-sm text-muted-foreground">Select a mentor on the left.</p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow className="border-border hover:bg-muted/40">
                    <TableHead>Name</TableHead>
                    <TableHead>User ID</TableHead>
                    <TableHead>Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {menteesVisible.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={3} className="text-muted-foreground">
                        No mentees match this search for this mentor.
                      </TableCell>
                    </TableRow>
                  ) : (
                    menteesVisible.map((m) => (
                      <TableRow key={m.connectionId} className="border-border">
                        <TableCell className="font-medium">{m.menteeName}</TableCell>
                        <TableCell>{m.menteeEmail}</TableCell>
                        <TableCell>{m.status}</TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
