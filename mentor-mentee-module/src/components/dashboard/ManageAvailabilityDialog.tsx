import { useEffect, useMemo, useState } from "react";
import { format, addHours, parseISO } from "date-fns";
import { CalendarIcon, Clock, Loader2, Plus, Trash2, AlertCircle, Pencil } from "lucide-react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Calendar } from "@/components/ui/calendar";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { toast } from "@/hooks/use-toast";
import {
  fetchMyAvailability,
  addAvailability,
  deleteAvailability,
  updateAvailability,
} from "@/api/userServiceMentoringApi";
import type { AvailableSlotItem } from "@/types/userServiceMentoring";

interface ManageAvailabilityDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  token?: string | null;
}

const timeOptions = [
  "08:00", "08:30", "09:00", "09:30", "10:00", "10:30", "11:00", "11:30",
  "12:00", "12:30", "13:00", "13:30", "14:00", "14:30", "15:00", "15:30",
  "16:00", "16:30", "17:00", "17:30", "18:00", "18:30", "19:00", "19:30",
  "20:00",
];

const ManageAvailabilityDialog = ({
  open,
  onOpenChange,
  token,
}: ManageAvailabilityDialogProps) => {
  const queryClient = useQueryClient();
  const [date, setDate] = useState<Date>(new Date());
  const [startTime, setStartTime] = useState("09:00");
  const [busy, setBusy] = useState(false);
  const [editingSlotId, setEditingSlotId] = useState<string | null>(null);

  const {
    data: slots = [],
    isFetching,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ["mentoring", "scheduling", "my-availability", token],
    queryFn: () => fetchMyAvailability(token!),
    enabled: Boolean(open && token),
    staleTime: 15_000,
  });

  const timeSelectChoices = useMemo(() => {
    const set = new Set(timeOptions);
    if (startTime) set.add(startTime);
    return Array.from(set).sort();
  }, [startTime]);

  useEffect(() => {
    if (!open) {
      setEditingSlotId(null);
    }
  }, [open]);

  const beginEdit = (slot: AvailableSlotItem) => {
    setEditingSlotId(slot.slot_id);
    try {
      const start = parseISO(slot.start_time);
      setDate(start);
      setStartTime(format(start, "HH:mm"));
    } catch {
      setDate(new Date());
      setStartTime("09:00");
    }
  };

  const cancelEdit = () => {
    setEditingSlotId(null);
    setDate(new Date());
    setStartTime("09:00");
  };

  const handleSaveSlot = async () => {
    if (!token || !date || !startTime) return;

    const [hours, minutes] = startTime.split(":").map(Number);
    const start = new Date(date);
    start.setHours(hours, minutes, 0, 0);
    const end = addHours(start, 1);
    const body = {
      start_time: start.toISOString(),
      end_time: end.toISOString(),
    };

    setBusy(true);
    try {
      if (editingSlotId) {
        await updateAvailability(token, editingSlotId, body);
        toast({ title: "Slot updated", description: "Your availability has been saved." });
        cancelEdit();
      } else {
        await addAvailability(token, body);
        toast({ title: "Slot added", description: "Your availability has been updated." });
      }
      void refetch();
      void queryClient.invalidateQueries({ queryKey: ["user-service", "mentoring"] });
      void queryClient.invalidateQueries({ queryKey: ["mentoring", "scheduling"] });
    } catch (e) {
      toast({
        title: editingSlotId ? "Could not update slot" : "Could not add slot",
        description: e instanceof Error ? e.message.slice(0, 280) : "Request failed",
        variant: "destructive",
      });
    } finally {
      setBusy(false);
    }
  };

  const handleDeleteSlot = async (slotId: string) => {
    if (!token) return;
    setBusy(true);
    try {
      await deleteAvailability(token, slotId);
      toast({ title: "Slot removed" });
      if (editingSlotId === slotId) cancelEdit();
      void refetch();
      void queryClient.invalidateQueries({ queryKey: ["user-service", "mentoring"] });
      void queryClient.invalidateQueries({ queryKey: ["mentoring", "scheduling"] });
    } catch (e) {
      toast({
        title: "Could not delete slot",
        description: e instanceof Error ? e.message.slice(0, 280) : "Request failed",
        variant: "destructive",
      });
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[480px]">
        <DialogHeader>
          <DialogTitle>Update availability</DialogTitle>
          <DialogDescription>
            Manage open times from mentoring <span className="font-mono text-xs">time_slots</span>. Mentees only see
            unbooked slots. Add, edit, or remove one-hour blocks.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-6 py-4">
          {isError && (
            <div
              className="flex gap-2 rounded-lg border border-border bg-muted/40 px-3 py-3 text-sm text-muted-foreground"
              role="status"
            >
              <AlertCircle className="h-4 w-4 shrink-0 text-muted-foreground mt-0.5" />
              <div>
                <p className="font-medium text-foreground">Could not load your slots</p>
                <p className="mt-1 text-xs leading-relaxed">
                  {error instanceof Error ? error.message.slice(0, 320) : "Check your network and mentoring service URL, then try again."}
                </p>
              </div>
            </div>
          )}

          <div className="flex flex-col sm:flex-row gap-3 items-end bg-muted/30 p-3 rounded-lg border border-border">
            <div className="grid gap-2 flex-1 w-full">
              <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                {editingSlotId ? "New date" : "Date"}
              </label>
              <Popover>
                <PopoverTrigger asChild>
                  <Button
                    variant="outline"
                    className={cn(
                      "w-full justify-start text-left font-normal h-9",
                      !date && "text-muted-foreground",
                    )}
                  >
                    <CalendarIcon className="mr-2 h-4 w-4" />
                    {date ? format(date, "PPP") : "Pick a date"}
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-auto p-0" align="start">
                  <Calendar
                    mode="single"
                    selected={date}
                    onSelect={(d) => d && setDate(d)}
                    disabled={(d) => d < new Date(new Date().setHours(0, 0, 0, 0))}
                    initialFocus
                  />
                </PopoverContent>
              </Popover>
            </div>

            <div className="grid gap-2 w-full sm:w-36">
              <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Start</label>
              <Select value={startTime} onValueChange={setStartTime}>
                <SelectTrigger className="h-9">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {timeSelectChoices.map((t) => (
                    <SelectItem key={t} value={t}>
                      {t}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="flex gap-2 w-full sm:w-auto">
              {editingSlotId ? (
                <Button type="button" variant="outline" size="sm" className="h-9" onClick={cancelEdit} disabled={busy}>
                  Cancel
                </Button>
              ) : null}
              <Button
                onClick={() => void handleSaveSlot()}
                disabled={busy || !date || isError}
                size="sm"
                className="h-9 gradient-primary border-0"
              >
                {busy ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : editingSlotId ? (
                  <>
                    <Pencil className="h-4 w-4 mr-1" /> Save
                  </>
                ) : (
                  <>
                    <Plus className="h-4 w-4 mr-1" /> Add
                  </>
                )}
              </Button>
            </div>
          </div>

          <div className="grid gap-2">
            <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider px-1">
              Your slots (mentoring DB)
            </label>
            <div className="grid max-h-[300px] overflow-y-auto gap-2 pr-1 custom-scrollbar">
              {isFetching && slots.length === 0 && !isError ? (
                <div className="flex items-center justify-center py-8 text-muted-foreground text-sm">
                  <Loader2 className="h-5 w-5 animate-spin mr-2" /> Loading from time_slots…
                </div>
              ) : !isError && slots.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-10 text-center border-2 border-dashed border-border rounded-xl">
                  <AlertCircle className="h-8 w-8 text-muted-foreground/40 mb-2" />
                  <p className="text-sm text-muted-foreground">No availability yet.</p>
                  <p className="text-[11px] text-muted-foreground/70 mt-1 max-w-xs">
                    Your database has no rows in <span className="font-mono">time_slots</span> for this mentor. Add a
                    one-hour block above — mentees will see it as bookable once published.
                  </p>
                </div>
              ) : isError ? null : (
                slots.map((slot) => (
                  <div
                    key={slot.slot_id}
                    className={cn(
                      "flex items-center justify-between p-3 rounded-lg border bg-card transition-colors",
                      editingSlotId === slot.slot_id ? "border-primary ring-1 ring-primary/30" : "border-border",
                      slot.is_booked ? "border-primary/30 bg-primary/5" : "hover:border-primary/30",
                    )}
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <div
                        className={cn(
                          "h-8 w-8 rounded-full flex items-center justify-center shrink-0",
                          slot.is_booked ? "bg-primary/20 text-primary" : "bg-muted text-muted-foreground",
                        )}
                      >
                        <Clock className="h-4 w-4" />
                      </div>
                      <div className="min-w-0">
                        <p className="text-sm font-semibold text-foreground truncate">
                          {format(new Date(slot.start_time), "EEE, MMM d")}
                        </p>
                        <p className="text-[11px] text-muted-foreground">
                          {format(new Date(slot.start_time), "h:mm a")} –{" "}
                          {format(new Date(slot.end_time), "h:mm a")}
                          {slot.is_booked && <span className="ml-2 text-primary font-bold">• BOOKED</span>}
                          {slot.pending_request_id && !slot.is_booked && (
                            <span className="ml-2 text-warning font-bold">• PENDING</span>
                          )}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-1 shrink-0">
                      {!slot.is_booked && !slot.pending_request_id && (
                        <>
                          <Button
                            type="button"
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8 text-muted-foreground hover:text-foreground"
                            onClick={() => beginEdit(slot)}
                            disabled={busy}
                            aria-label="Edit slot"
                          >
                            <Pencil className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8 text-muted-foreground hover:text-destructive hover:bg-destructive/10"
                            onClick={() => void handleDeleteSlot(slot.slot_id)}
                            disabled={busy}
                            aria-label="Delete slot"
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default ManageAvailabilityDialog;
