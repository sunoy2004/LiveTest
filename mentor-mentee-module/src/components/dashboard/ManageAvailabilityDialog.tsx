import { useEffect, useState } from "react";
import { format, addHours, startOfHour } from "date-fns";
import { CalendarIcon, Clock, Loader2, Plus, Trash2, AlertCircle } from "lucide-react";
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
} from "@/api/userServiceMentoringApi";

interface ManageAvailabilityDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  token?: string | null;
}

const timeOptions = [
  "08:00", "08:30", "09:00", "09:30", "10:00", "10:30", "11:00", "11:30",
  "12:00", "12:30", "13:00", "13:30", "14:00", "14:30", "15:00", "15:30",
  "16:00", "16:30", "17:00", "17:30", "18:00", "18:30", "19:00", "19:30",
  "20:00"
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

  const { data: slots = [], isFetching, refetch } = useQuery({
    queryKey: ["user-service", "my-availability", token],
    queryFn: () => fetchMyAvailability(token!),
    enabled: Boolean(open && token),
  });

  const handleAddSlot = async () => {
    if (!token || !date || !startTime) return;
    
    const [hours, minutes] = startTime.split(":").map(Number);
    const start = new Date(date);
    start.setHours(hours, minutes, 0, 0);
    const end = addHours(start, 1);

    setBusy(true);
    try {
      await addAvailability(token, {
        start_time: start.toISOString(),
        end_time: end.toISOString(),
      });
      toast({ title: "Slot added", description: "Your availability has been updated." });
      void refetch();
      void queryClient.invalidateQueries({ queryKey: ["user-service", "mentoring"] });
    } catch (e) {
      toast({
        title: "Could not add slot",
        description: e instanceof Error ? e.message : "Request failed",
        variant: "destructive",
      });
    } finally {
      setBusy(null);
    }
  };

  const handleDeleteSlot = async (slotId: string) => {
    if (!token) return;
    setBusy(true);
    try {
      await deleteAvailability(token, slotId);
      toast({ title: "Slot removed" });
      void refetch();
      void queryClient.invalidateQueries({ queryKey: ["user-service", "mentoring"] });
    } catch (e) {
      toast({
        title: "Could not delete slot",
        description: e instanceof Error ? e.message : "Request failed",
        variant: "destructive",
      });
    } finally {
      setBusy(null);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[480px]">
        <DialogHeader>
          <DialogTitle>Update Availability</DialogTitle>
          <DialogDescription>
            Manage your open time slots. Mentees can only request sessions during these times.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-6 py-4">
          <div className="flex flex-col sm:flex-row gap-3 items-end bg-muted/30 p-3 rounded-lg border border-border">
            <div className="grid gap-2 flex-1 w-full">
              <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Date</label>
              <Popover>
                <PopoverTrigger asChild>
                  <Button
                    variant="outline"
                    className={cn(
                      "w-full justify-start text-left font-normal h-9",
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
                    onSelect={(d) => d && setDate(d)}
                    disabled={(d) => d < new Date(new Date().setHours(0,0,0,0))}
                    initialFocus
                  />
                </PopoverContent>
              </Popover>
            </div>

            <div className="grid gap-2 w-full sm:w-32">
              <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Start</label>
              <Select value={startTime} onValueChange={setStartTime}>
                <SelectTrigger className="h-9">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {timeOptions.map((t) => (
                    <SelectItem key={t} value={t}>{t}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <Button 
              onClick={() => void handleAddSlot()} 
              disabled={busy || !date}
              size="sm"
              className="h-9 gradient-primary border-0"
            >
              {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4 mr-1" />}
              Add
            </Button>
          </div>

          <div className="grid gap-2">
            <label className="text-xs font-medium text-muted-foreground uppercase tracking-wider px-1">Your active slots</label>
            <div className="grid max-h-[300px] overflow-y-auto gap-2 pr-1 custom-scrollbar">
              {isFetching && slots.length === 0 ? (
                <div className="flex items-center justify-center py-8 text-muted-foreground text-sm">
                  <Loader2 className="h-5 w-5 animate-spin mr-2" /> Loading availability...
                </div>
              ) : slots.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-10 text-center border-2 border-dashed border-border rounded-xl">
                   <AlertCircle className="h-8 w-8 text-muted-foreground/40 mb-2" />
                   <p className="text-sm text-muted-foreground">No availability slots added yet.</p>
                   <p className="text-[11px] text-muted-foreground/60 mt-1">Add slots above so mentees can book you.</p>
                </div>
              ) : (
                slots.map((slot: any) => (
                  <div 
                    key={slot.slot_id}
                    className={cn(
                      "flex items-center justify-between p-3 rounded-lg border bg-card transition-colors",
                      slot.is_booked ? "border-primary/30 bg-primary/5" : "border-border hover:border-primary/30"
                    )}
                  >
                    <div className="flex items-center gap-3">
                      <div className={cn(
                        "h-8 w-8 rounded-full flex items-center justify-center",
                        slot.is_booked ? "bg-primary/20 text-primary" : "bg-muted text-muted-foreground"
                      )}>
                        <Clock className="h-4 w-4" />
                      </div>
                      <div>
                        <p className="text-sm font-semibold text-foreground">
                          {format(new Date(slot.start_time), "EEE, MMM d")}
                        </p>
                        <p className="text-[11px] text-muted-foreground">
                          {format(new Date(slot.start_time), "h:mm a")} - {format(new Date(slot.end_time), "h:mm a")}
                          {slot.is_booked && <span className="ml-2 text-primary font-bold">• BOOKED</span>}
                          {slot.pending_request_id && !slot.is_booked && <span className="ml-2 text-warning font-bold">• PENDING</span>}
                        </p>
                      </div>
                    </div>
                    
                    {!slot.is_booked && !slot.pending_request_id && (
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 text-muted-foreground hover:text-destructive hover:bg-destructive/10"
                        onClick={() => void handleDeleteSlot(slot.slot_id)}
                        disabled={busy}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Close</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default ManageAvailabilityDialog;
