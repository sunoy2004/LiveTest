import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Info, Search } from "lucide-react";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { fetchAdminMentees } from "@/api/adminApi";
import { useMentorShellAuth } from "@/context/MentorShellAuthContext";
import { matchesAdminSearch } from "@/lib/utils";

export default function AdminMenteesPage() {
  const { token } = useMentorShellAuth();
  const [search, setSearch] = useState("");

  const q = useQuery({
    queryKey: ["admin", "mentees", token],
    queryFn: () => fetchAdminMentees(token!),
    enabled: Boolean(token),
    refetchInterval: 10_000,
  });

  const filtered = useMemo(() => {
    const rows = q.data ?? [];
    return rows.filter((m) => matchesAdminSearch(search, m.name, m.email, m.status));
  }, [q.data, search]);

  return (
    <section className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold text-foreground">Mentees</h2>
        <p className="mt-1 text-sm text-muted-foreground">Directory of mentee profiles. Wallets are not managed here.</p>
      </div>

      <div className="flex gap-2 rounded-lg border border-border bg-muted/30 px-3 py-2 text-sm text-muted-foreground">
        <Info className="mt-0.5 h-4 w-4 shrink-0 text-primary" aria-hidden />
        <p>Wallet balances and credit movements are managed by the gamification service.</p>
      </div>

      {q.error ? (
        <p className="text-sm text-destructive">{q.error instanceof Error ? q.error.message : "Load failed"}</p>
      ) : null}

      <div className="relative max-w-xl">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" aria-hidden />
        <Input
          type="search"
          placeholder="Search by name, user ID, or status…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="bg-background pl-9"
          aria-label="Search mentees"
        />
      </div>

      <div className="overflow-x-auto rounded-md border border-border">
        <Table>
          <TableHeader>
            <TableRow className="border-border hover:bg-muted/40">
              <TableHead>Name</TableHead>
              <TableHead>User ID</TableHead>
              <TableHead>Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {(q.data ?? []).length === 0 ? (
              <TableRow>
                <TableCell colSpan={3} className="text-muted-foreground">
                  No mentee profiles found.
                </TableCell>
              </TableRow>
            ) : filtered.length === 0 ? (
              <TableRow>
                <TableCell colSpan={3} className="text-muted-foreground">
                  No mentees match your search.
                </TableCell>
              </TableRow>
            ) : (
              filtered.map((m) => (
                <TableRow key={m.id} className="border-border">
                  <TableCell className="font-medium">{m.name}</TableCell>
                  <TableCell>{m.email}</TableCell>
                  <TableCell>{m.status}</TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
    </section>
  );
}
