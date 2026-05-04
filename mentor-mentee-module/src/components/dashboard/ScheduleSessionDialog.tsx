import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { format, parseISO } from "date-fns";
import { AlertCircle, CalendarIcon, Clock, Coins, Loader2 } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
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
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
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
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { toast } from "@/hooks/use-toast";
import {
  bookSessionSimple,
  fetchConnectedMentors,
  fetchMentorAvailability,
} from "@/api/userServiceMentoringApi";
import type { AvailableSlotItem, ConnectedMentorItem } from "@/types/userServiceMentoring";

interface ScheduleSessionDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  role: "mentor" | "mentee";
  token?: string | null;
  /** Gamification wallet balance for mentee scheduling UI. */
  cachedCreditScore?: number;
}

const partnerOptions = {
  mentee: [
    { id: "1", name: "David Kim" },
    { id: "2", name: "Maria Garcia" },
    { id: "3", name: "David Lee" },
  ],
  mentor: [
    { id: "4", name: "Alex Rivera" },
    { id: "5", name: "Priya Sharma" },
    { id: "6", name: "Liam Chen" },
  ],
};

const timeSlots = [
  "9:00 AM", "9:30 AM", "10:00 AM", "10:30 AM",
  "11:00 AM", "11:30 AM", "12:00 PM", "12:30 PM",
  "1:00 PM", "1:30 PM", "2:00 PM", "2:30 PM",
  "3:00 PM", "3:30 PM", "4:00 PM", "4:30 PM",
  "5:00 PM",
];

const ScheduleSessionDialog = ({
  open,
  onOpenChange,
  role,
  token,
  cachedCreditScore = 100,
}: ScheduleSessionDialogProps) => {
  const queryClient = useQueryClient();
  const [date, setDate] = useState<Date>();
  const [time, setTime] = useState("");
  const [partner, setPartner] = useState("");
  const [topic, setTopic] = useState("");
  const [selectedMentor, setSelectedMentor] = useState<ConnectedMentorItem | null>(null);
  const [availableSlots, setAvailableSlots] = useState<AvailableSlotItem[]>([]);
  const [selectedSlot, setSelectedSlot] = useState<AvailableSlotItem | null>(null);
  const [loadingSlots, setLoadingSlots] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const useLiveSchedule = role === "mentee" && Boolean(token);

  const {
    data: connectedMentors = [],
    isFetching: loadingMentors,
    isError: mentorsError,
    error: mentorsErr,
  } = useQuery({
    queryKey: ["mentoring", "connected-mentors", token],
    queryFn: () => fetchConnectedMentors(token!),
    enabled: Boolean(open && role === "mentee" && token),
    /** Always refetch when opening — `session_credit_cost` tracks live gamification BOOK_MENTOR_SESSION. */
    staleTime: 0,
    refetchOnMount: "always",
  });

  useEffect(() => {
    if (!open) return;
    setDate(undefined);
    setTime("");
    setPartner("");
    setTopic("");
    setSelectedMentor(null);
    setAvailableSlots([]);
    setSelectedSlot(null);
    setLoadingSlots(false);
    setSubmitting(false);
  }, [open]);

  useEffect(() => {
    if (!open || role !== "mentee") return;
    if (connectedMentors.length === 1) {
      setSelectedMentor(connectedMentors[0]);
    }
  }, [open, role, connectedMentors]);

  useEffect(() => {
    if (!selectedMentor) return;
    const still = connectedMentors.some(
      (c) => c.connection_id === selectedMentor.connection_id,
    );
    if (!still) setSelectedMentor(null);
  }, [connectedMentors, selectedMentor]);

  useEffect(() => {
    if (!open || role !== "mentee" || !token || !selectedMentor) return;
    setLoadingSlots(true);
    setAvailableSlots([]);
    setSelectedSlot(null);
    fetchMentorAvailability(token, selectedMentor.mentor_id)
      .then((rows) =>
        setAvailableSlots(
          rows.map((r) => ({
            ...r,
            cost_credits: typeof r.cost_credits === "number" ? r.cost_credits : 0,
          })),
        ),
      )
      .catch((e) => {
        toast({
          title: "Could not load slots",
          description: e instanceof Error ? e.message.slice(0, 280) : "Request failed",
        });
      })
      .finally(() => setLoadingSlots(false));
  }, [open, role, token, selectedMentor?.mentor_id]);

  const partners = role === "mentee" ? partnerOptions.mentee : partnerOptions.mentor;
  const partnerLabel = role === "mentee" ? "Mentor" : "Mentee";

  /** Matches server: mentor `session_credit_cost` and slot `cost_credits` (gamification BOOK_MENTOR_SESSION base, with PEER tier fallback). */
  const sessionBookingCost =
    selectedMentor == null
      ? 0
      : (selectedMentor.session_credit_cost ??
          selectedSlot?.cost_credits ??
          availableSlots[0]?.cost_credits ??
          0);

  const handleMenteeLiveSubmit = async () => {
    if (!token || !selectedMentor || !selectedSlot) {
      toast({ title: "Pick a mentor and time slot", variant: "destructive" });
      return;
    }
    const slotCost = sessionBookingCost;
    setSubmitting(true);
    try {
      await bookSessionSimple(token, {
        connection_id: selectedMentor.connection_id,
        slot_id: selectedSlot.slot_id,
      });
      toast({
        title: "Request sent",
        description: `${format(parseISO(selectedSlot.start_time), "PPP p")} · awaiting mentor approval (${slotCost} YANC if accepted)`,
      });
      void queryClient.invalidateQueries({ queryKey: ["user-service"] });
      void queryClient.invalidateQueries({ queryKey: ["user-service", "mentoring"] });
      void queryClient.invalidateQueries({ queryKey: ["mentoring", "dashboard", "session-booking-requests"] });
      void queryClient.invalidateQueries({ queryKey: ["gamification", "wallet"] });
      onOpenChange(false);
    } catch (e) {
      toast({
        title: "Could not send request",
        description: e instanceof Error ? e.message : "Request failed",
        variant: "destructive",
      });
    } finally {
      setSubmitting(false);
    }
  };

  const handleMentorMockSubmit = () => {
    if (!date || !time || !partner || !topic) {
      toast({ title: "Please fill in all fields", variant: "destructive" });
      return;
    }
    toast({
      title: "Session Scheduled! 🎉",
      description: `${format(date, "PPP")} at ${time} — ${topic}`,
    });
    setDate(undefined);
    setTime("");
    setPartner("");
    setTopic("");
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[440px]">
        <DialogHeader>
          <DialogTitle>{useLiveSchedule ? "Request a session" : "Schedule a Session"}</DialogTitle>
          <DialogDescription>
            {useLiveSchedule
              ? "Pick a mentor and slot. Your mentor must approve before credits are charged and the session is scheduled."
              : `Pick a ${partnerLabel.toLowerCase()}, date, and time for your next session.`}
          </DialogDescription>
        </DialogHeader>

        {useLiveSchedule && (
          <div className="grid gap-4 py-2">
            <TooltipProvider delayDuration={300}>
              <Tooltip>
                <TooltipTrigger asChild>
                  <div className="flex items-center justify-between rounded-lg border border-border bg-muted/40 px-3 py-2 text-xs cursor-default">
                    <span className="text-muted-foreground">YANC wallet</span>
                    <span className="font-semibold text-foreground inline-flex items-center gap-1">
                      <Coins className="h-3.5 w-3.5 text-primary" />
                      {cachedCreditScore}
                    </span>
                  </div>
                </TooltipTrigger>
                <TooltipContent side="bottom" className="max-w-xs text-xs">
                  Credits are charged only after your mentor accepts the request.
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
            <div className="grid gap-2">
              <Label>Mentor</Label>
              {mentorsError && (
                <p className="text-xs text-destructive">
                  {mentorsErr instanceof Error ? mentorsErr.message.slice(0, 240) : "Could not load mentors."}
                </p>
              )}
              <Select
                value={selectedMentor?.connection_id ?? ""}
                onValueChange={(v) => {
                  const m = connectedMentors.find((x) => x.connection_id === v) ?? null;
                  setSelectedMentor(m);
                }}
                disabled={loadingMentors}
              >
                <SelectTrigger>
                  <SelectValue
                    placeholder={loadingMentors ? "Loading mentors…" : "Select a mentor"}
                  />
                </SelectTrigger>
                <SelectContent>
                  {connectedMentors.map((m) => (
                    <SelectItem
                      key={m.connection_id}
                      value={m.connection_id}
                      textValue={m.mentor_name}
                    >
                      {m.mentor_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {selectedMentor == null ? (
              <div className="text-sm text-muted-foreground text-center py-4 px-1 space-y-1">
                <p>{loadingMentors ? "Loading mentors…" : "No active mentors to book yet."}</p>
                {!loadingMentors && (
                  <p className="text-xs text-muted-foreground/80">
                    You need at least one <span className="font-mono">ACTIVE</span> row in{" "}
                    <span className="font-mono">mentorship_connections</span> with this mentee. Ask a mentor to accept
                    a connection request first.
                  </p>
                )}
              </div>
            ) : loadingSlots ? (
              <p className="text-sm text-muted-foreground text-center py-4">
                Loading slots…
              </p>
            ) : availableSlots.length === 0 ? (
              <div className="text-sm text-muted-foreground text-center py-4 px-1 space-y-1">
                <p>No open time slots for {selectedMentor.mentor_name}.</p>
                <p className="text-xs text-muted-foreground/80">
                  Their <span className="font-mono">time_slots</span> may be empty, or every slot is already booked.
                  They can add availability from the mentor dashboard.
                </p>
              </div>
            ) : (
              <>
                <div className="grid gap-2">
                  <Label>Open slots</Label>
                  <div className="grid max-h-52 gap-2 overflow-y-auto pr-1">
                    {availableSlots.map((slot) => {
                      const rowCost = selectedMentor.session_credit_cost ?? slot.cost_credits ?? 0;
                      const costTooHigh = cachedCreditScore < rowCost;
                      return (
                        <button
                          key={slot.slot_id}
                          type="button"
                          onClick={() => setSelectedSlot(slot)}
                          className={cn(
                            "flex w-full items-center rounded-lg border px-3 py-2.5 text-left text-sm transition-all",
                            selectedSlot?.slot_id === slot.slot_id
                              ? "border-primary bg-primary/10"
                              : "border-border bg-card hover:border-primary/40",
                            costTooHigh && "border-destructive/40",
                          )}
                        >
                          <span className="flex min-w-0 flex-1 flex-wrap items-center gap-x-2 gap-y-1 font-medium">
                            <Clock className="h-4 w-4 shrink-0 text-muted-foreground" />
                            <span className="text-foreground">
                              {format(parseISO(slot.start_time), "EEE MMM d · h:mm a")}
                            </span>
                            <span className="text-muted-foreground">·</span>
                            <span
                              className={cn(
                                "inline-flex items-center gap-1 text-xs font-medium tabular-nums",
                                costTooHigh ? "text-destructive" : "text-muted-foreground",
                              )}
                            >
                              <Coins className="h-3.5 w-3.5 shrink-0" />
                              {rowCost} credits
                            </span>
                          </span>
                        </button>
                      );
                    })}
                  </div>
                </div>
                {selectedSlot &&
                  sessionBookingCost > 0 &&
                  cachedCreditScore < sessionBookingCost && (
                  <div className="flex items-center gap-2 rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-xs text-destructive">
                    <AlertCircle className="h-4 w-4 shrink-0" />
                    Insufficient credits ({sessionBookingCost} required for this mentor).
                  </div>
                )}
              </>
            )}
            <DialogFooter className="gap-2 sm:gap-0">
              <Button variant="outline" onClick={() => onOpenChange(false)} disabled={submitting}>
                Cancel
              </Button>
              <Button
                onClick={() => void handleMenteeLiveSubmit()}
                disabled={
                  submitting ||
                  !selectedMentor ||
                  !selectedSlot ||
                  availableSlots.length === 0
                }
                className="gradient-primary border-0"
              >
                {submitting ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" /> Sending…
                  </>
                ) : (
                  "Request session"
                )}
              </Button>
            </DialogFooter>
          </div>
        )}

        {!useLiveSchedule && role === "mentee" && (
          <div className="py-6 text-center text-sm text-muted-foreground">
            Sign in to schedule a session.
          </div>
        )}

        {!useLiveSchedule && role === "mentor" && (
          <>
            <div className="grid gap-4 py-2">
              <div className="grid gap-2">
                <Label>{partnerLabel}</Label>
                <Select value={partner} onValueChange={setPartner}>
                  <SelectTrigger>
                    <SelectValue placeholder={`Select a ${partnerLabel.toLowerCase()}`} />
                  </SelectTrigger>
                  <SelectContent>
                    {partners.map((p) => (
                      <SelectItem key={p.id} value={p.id}>{p.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="grid gap-2">
                <Label>Date</Label>
                <Popover>
                  <PopoverTrigger asChild>
                    <Button
                      variant="outline"
                      className={cn(
                        "w-full justify-start text-left font-normal",
                        !date && "text-muted-foreground"
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
                      onSelect={setDate}
                      disabled={(d) => d < new Date()}
                      initialFocus
                      className="p-3 pointer-events-auto"
                    />
                  </PopoverContent>
                </Popover>
              </div>

              <div className="grid gap-2">
                <Label>Time</Label>
                <Select value={time} onValueChange={setTime}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select a time">
                      {time && (
                        <span className="flex items-center gap-2">
                          <Clock className="h-3.5 w-3.5" /> {time}
                        </span>
                      )}
                    </SelectValue>
                  </SelectTrigger>
                  <SelectContent>
                    {timeSlots.map((t) => (
                      <SelectItem key={t} value={t}>{t}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="grid gap-2">
                <Label>Topic</Label>
                <Input
                  placeholder="e.g. Career Growth, Code Review"
                  value={topic}
                  onChange={(e) => setTopic(e.target.value)}
                />
              </div>
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
              <Button onClick={handleMentorMockSubmit}>Schedule</Button>
            </DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
};

export default ScheduleSessionDialog;
