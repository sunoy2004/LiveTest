import { useState, useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { format, parseISO } from "date-fns";
import { CalendarIcon, Clock, Coins, CheckCircle, Loader2, AlertCircle, ArrowRight } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Calendar } from "@/components/ui/calendar";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { toast } from "@/hooks/use-toast";
import { bookSession } from "@/api/schedulingApi";
import type { BookingSchedulingContext, SchedulingSlot } from "@/types/scheduling";
import { MatchProfile, creditWallet } from "@/data/mockData";
import type { MentorTierId } from "@/types/domain";

const tierLabels: Record<MentorTierId, string> = {
  PEER: "Peer",
  PROFESSIONAL: "Professional",
  EXPERT: "Expert",
};

interface BookingDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  match: MatchProfile | null;
  /** Overrides mock wallet — use mentee cached_credit_score from profiles/me */
  cachedCreditScore?: number;
  /** User Service scheduling context (mentee + active connection). */
  bookingContext?: BookingSchedulingContext | null;
  token?: string | null;
}

type BookingStep = "slot" | "confirm" | "processing" | "success" | "error";

const availableSlots = [
  "9:00 AM", "10:00 AM", "11:00 AM",
  "1:00 PM", "2:00 PM", "3:00 PM", "4:00 PM",
];

const BookingDialog = ({
  open,
  onOpenChange,
  match,
  cachedCreditScore,
  bookingContext,
  token,
}: BookingDialogProps) => {
  const queryClient = useQueryClient();
  const [step, setStep] = useState<BookingStep>("slot");
  const [date, setDate] = useState<Date>();
  const [time, setTime] = useState("");
  const [selectedApiSlot, setSelectedApiSlot] = useState<SchedulingSlot | null>(null);

  const useLiveBooking = Boolean(token && bookingContext);

  useEffect(() => {
    if (open) {
      setStep("slot");
      setDate(undefined);
      setTime("");
      setSelectedApiSlot(null);
    }
  }, [open]);

  if (!match) return null;

  const walletBalance = useLiveBooking
    ? (bookingContext!.cached_credit_score)
    : (cachedCreditScore ?? creditWallet.balance);

  const mentorLabel = useLiveBooking ? bookingContext!.mentor_display_name : match.name;

  const sessionCost = useLiveBooking && selectedApiSlot
    ? selectedApiSlot.cost_credits
    : match.sessionCostCredits;

  const hasEnoughCredits = walletBalance >= sessionCost;

  const handleConfirm = () => {
    if (useLiveBooking && bookingContext && selectedApiSlot && token) {
      void (async () => {
        setStep("processing");
        try {
          await bookSession(token, {
            connection_id: bookingContext.connection_id,
            slot_id: selectedApiSlot.id,
            agreed_cost: selectedApiSlot.cost_credits,
          });
          void queryClient.invalidateQueries({ queryKey: ["user-service", "mentoring"] });
          void queryClient.invalidateQueries({ queryKey: ["gamification", "wallet"] });
          void queryClient.invalidateQueries({ queryKey: ["user-service", "dashboard"] });
          void queryClient.invalidateQueries({ queryKey: ["user-service", "profile-full"] });
          setStep("success");
        } catch (e) {
          toast({
            title: "Booking failed",
            description: e instanceof Error ? e.message : "Request failed",
            variant: "destructive",
          });
          setStep("error");
        }
      })();
      return;
    }

    setStep("processing");
    setTimeout(() => {
      const success = Math.random() > 0.15;
      if (success) {
        setStep("success");
      } else {
        setStep("error");
      }
    }, 2500);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[440px]">
        <DialogHeader>
          <DialogTitle>
            {step === "slot" && "Select Time Slot"}
            {step === "confirm" && (useLiveBooking ? "Confirm request" : "Confirm Booking")}
            {step === "processing" && "Processing..."}
            {step === "success" && (useLiveBooking ? "Request sent!" : "Session Booked!")}
            {step === "error" && "Booking Failed"}
          </DialogTitle>
          <DialogDescription>
            {step === "slot" && (useLiveBooking ? `Request a session with ${mentorLabel}` : `Book a session with ${mentorLabel}`)}
            {step === "confirm" && "Review the details below"}
            {step === "processing" && (useLiveBooking ? "Sending your request…" : "Please wait while we secure your slot")}
            {step === "success" && (useLiveBooking ? "Your mentor will be notified. Credits apply only if they accept." : "Your session has been confirmed")}
            {step === "error" && "Something went wrong"}
          </DialogDescription>
        </DialogHeader>

        <div className="flex items-center justify-center gap-2 py-2">
          {["slot", "confirm", "processing"].map((s, i) => (
            <div key={s} className="flex items-center gap-2">
              <div className={cn(
                "h-2 w-2 rounded-full transition-all",
                step === s ? "w-6 gradient-primary" :
                  (["slot", "confirm", "processing"].indexOf(step) > i || step === "success")
                    ? "bg-success" : "bg-muted"
              )} />
            </div>
          ))}
        </div>

        {step === "slot" && useLiveBooking && (
          <div className="grid gap-4 py-2">
            {bookingContext!.slots.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-6">
                No open slots from your mentor right now.
              </p>
            ) : (
              <>
                <div className="grid gap-2">
                  <Label>Open slots (User Service)</Label>
                  <div className="grid grid-cols-1 gap-2 max-h-48 overflow-y-auto pr-1">
                    {bookingContext!.slots.map((slot) => (
                      <button
                        key={slot.id}
                        type="button"
                        onClick={() => setSelectedApiSlot(slot)}
                        className={cn(
                          "flex items-center justify-between rounded-lg border px-3 py-2.5 text-left text-sm transition-all",
                          selectedApiSlot?.id === slot.id
                            ? "border-primary bg-primary/10 shadow-sm"
                            : "border-border bg-card hover:border-primary/40",
                        )}
                      >
                        <span className="flex items-center gap-2 font-medium">
                          <Clock className="h-4 w-4 shrink-0 text-muted-foreground" />
                          {format(parseISO(slot.start_time), "EEE MMM d · h:mm a")}
                        </span>
                        <span className="text-xs text-muted-foreground">{slot.cost_credits} cr</span>
                      </button>
                    ))}
                  </div>
                </div>
                <p className="text-xs text-muted-foreground">
                  Wallet: <span className="font-semibold text-foreground">{walletBalance}</span> credits
                </p>
                <Button
                  disabled={!selectedApiSlot}
                  onClick={() => setStep("confirm")}
                  className="w-full gradient-primary border-0"
                >
                  Continue <ArrowRight className="h-4 w-4 ml-1" />
                </Button>
              </>
            )}
          </div>
        )}

        {step === "slot" && !useLiveBooking && (
          <div className="grid gap-4 py-2">
            <div className="grid gap-2">
              <Label>Date</Label>
              <Popover>
                <PopoverTrigger asChild>
                  <Button
                    variant="outline"
                    className={cn("w-full justify-start text-left font-normal", !date && "text-muted-foreground")}
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
              <Label>Available Slots</Label>
              <div className="grid grid-cols-3 gap-2">
                {availableSlots.map((slot) => (
                  <button
                    key={slot}
                    type="button"
                    onClick={() => setTime(slot)}
                    className={cn(
                      "px-3 py-2 rounded-lg text-xs font-medium border transition-all",
                      time === slot
                        ? "gradient-primary text-primary-foreground border-primary shadow-sm"
                        : "border-border bg-card hover:border-primary/50 text-foreground"
                    )}
                  >
                    <Clock className="h-3 w-3 mx-auto mb-1" />
                    {slot}
                  </button>
                ))}
              </div>
            </div>

            <Button
              disabled={!date || !time}
              onClick={() => setStep("confirm")}
              className="w-full gradient-primary border-0"
            >
              Continue <ArrowRight className="h-4 w-4 ml-1" />
            </Button>
          </div>
        )}

        {step === "confirm" && (
          <div className="grid gap-4 py-2">
            <div className="rounded-xl border border-border p-4 space-y-3">
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Mentor</span>
                <span className="font-semibold text-foreground">{mentorLabel}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">When</span>
                <span className="font-semibold text-foreground">
                  {useLiveBooking && selectedApiSlot
                    ? format(parseISO(selectedApiSlot.start_time), "PPP p")
                    : (date && format(date, "PPP"))}
                </span>
              </div>
              {!useLiveBooking && (
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Time</span>
                  <span className="font-semibold text-foreground">{time}</span>
                </div>
              )}
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Tier</span>
                <span className="font-semibold text-foreground">{tierLabels[match.tier]}</span>
              </div>
              <div className="border-t border-border pt-3 flex justify-between items-center">
                <span className="text-sm font-semibold text-foreground">Session Cost</span>
                <span className="flex items-center gap-1 text-sm font-bold text-primary">
                  <Coins className="h-4 w-4" /> {sessionCost} credits
                </span>
              </div>
            </div>

            <div
              className={cn(
                "flex items-center gap-2 p-3 rounded-lg text-xs",
                useLiveBooking
                  ? "bg-muted/50 text-muted-foreground"
                  : hasEnoughCredits
                    ? "bg-success/10 text-success"
                    : "bg-destructive/10 text-destructive",
              )}
            >
              {useLiveBooking ? (
                <span>
                  Balance: {walletBalance} credits — charged only after mentor accepts ({sessionCost} for this slot).
                </span>
              ) : hasEnoughCredits ? (
                <>
                  <CheckCircle className="h-4 w-4" />
                  <span>Balance: {walletBalance} credits — sufficient</span>
                </>
              ) : (
                <>
                  <AlertCircle className="h-4 w-4" />
                  <span>Insufficient credits ({walletBalance} available, {sessionCost} required)</span>
                </>
              )}
            </div>

            <div className="flex gap-2">
              <Button variant="outline" className="flex-1" onClick={() => setStep("slot")}>Back</Button>
              <Button
                className="flex-1 gradient-primary border-0"
                disabled={!useLiveBooking && !hasEnoughCredits}
                onClick={handleConfirm}
              >
                <Coins className="h-4 w-4 mr-1" />{" "}
                {useLiveBooking ? "Send request" : "Confirm & Pay"}
              </Button>
            </div>
          </div>
        )}

        {step === "processing" && (
          <div className="flex flex-col items-center gap-4 py-8">
            <Loader2 className="h-10 w-10 text-primary animate-spin" />
            <div className="text-center space-y-1">
              <p className="text-sm font-semibold text-foreground">Reserving your slot...</p>
              <p className="text-xs text-muted-foreground">
                {useLiveBooking ? "Locking slot → Notifying mentor" : "Checking credits → Locking slot → Confirming"}
              </p>
            </div>
            <div className="flex gap-2 mt-2">
              {(useLiveBooking ? ["Locking slot", "Notifying mentor"] : ["Checking credits", "Locking slot", "Confirming"]).map((label) => (
                <span
                  key={label}
                  className={cn(
                    "text-[10px] px-2 py-1 rounded-full animate-pulse",
                    "bg-primary/10 text-primary font-medium"
                  )}
                >
                  {label}
                </span>
              ))}
            </div>
          </div>
        )}

        {step === "success" && (
          <div className="flex flex-col items-center gap-4 py-8">
            <div className="h-16 w-16 rounded-full bg-success/10 flex items-center justify-center">
              <CheckCircle className="h-8 w-8 text-success" />
            </div>
            <div className="text-center space-y-1">
              <p className="text-sm font-semibold text-foreground">Session Booked! 🎉</p>
              <p className="text-xs text-muted-foreground">
                {useLiveBooking && selectedApiSlot
                  ? `${format(parseISO(selectedApiSlot.start_time), "PPP p")} with ${mentorLabel}`
                  : `${date && format(date, "PPP")} at ${time} with ${match.name}`}
              </p>
              {!useLiveBooking ? (
                <p className="text-xs text-muted-foreground">{sessionCost} credits deducted</p>
              ) : (
                <p className="text-xs text-muted-foreground">No credits charged yet</p>
              )}
            </div>
            <Button className="w-full gradient-primary border-0" onClick={() => onOpenChange(false)}>
              Done
            </Button>
          </div>
        )}

        {step === "error" && (
          <div className="flex flex-col items-center gap-4 py-8">
            <div className="h-16 w-16 rounded-full bg-destructive/10 flex items-center justify-center">
              <AlertCircle className="h-8 w-8 text-destructive" />
            </div>
            <div className="text-center space-y-1">
              <p className="text-sm font-semibold text-foreground">Booking Failed</p>
              <p className="text-xs text-muted-foreground">
                {useLiveBooking
                  ? "Slot may have been taken or credits insufficient. No partial charge was applied."
                  : "The time slot may have been taken or a temporary error occurred. No credits were deducted."}
              </p>
            </div>
            <div className="flex gap-2 w-full">
              <Button variant="outline" className="flex-1" onClick={() => onOpenChange(false)}>Cancel</Button>
              <Button className="flex-1 gradient-primary border-0" onClick={() => setStep("slot")}>Try Again</Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
};

export default BookingDialog;
