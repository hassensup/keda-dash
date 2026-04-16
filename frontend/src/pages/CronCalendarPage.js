import { useState, useEffect, useCallback, useMemo } from "react";
import api from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";
import { ChevronLeft, ChevronRight, Plus, Clock, Pencil, Trash2 } from "lucide-react";
import {
  startOfMonth, endOfMonth, startOfWeek, endOfWeek, addDays, addMonths, subMonths,
  format, isSameMonth, isSameDay, isToday, parseISO,
} from "date-fns";
import { fr } from "date-fns/locale";

const EMPTY_EVENT = {
  scaled_object_id: "", name: "", timezone_str: "UTC",
  desired_replicas: 1, event_date: "", start_time: "08:00", end_time: "18:00",
};

export default function CronCalendarPage() {
  const [currentMonth, setCurrentMonth] = useState(new Date());
  const [events, setEvents] = useState([]);
  const [scaledObjects, setScaledObjects] = useState([]);
  const [filterSoId, setFilterSoId] = useState("all");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editEvent, setEditEvent] = useState(null);
  const [form, setForm] = useState({ ...EMPTY_EVENT });
  const [deleteConfirm, setDeleteConfirm] = useState(null);
  const [saving, setSaving] = useState(false);

  const monthStr = format(currentMonth, "yyyy-MM");

  const fetchEvents = useCallback(async () => {
    try {
      const params = { month: monthStr };
      if (filterSoId && filterSoId !== "all") params.scaled_object_id = filterSoId;
      const [evRes, soRes] = await Promise.all([
        api.get("/cron-events", { params }),
        api.get("/scaled-objects"),
      ]);
      setEvents(evRes.data);
      setScaledObjects(soRes.data);
    } catch {
      toast.error("Failed to load events");
    }
  }, [monthStr, filterSoId]);

  useEffect(() => { fetchEvents(); }, [fetchEvents]);

  const calendarDays = useMemo(() => {
    const start = startOfWeek(startOfMonth(currentMonth), { weekStartsOn: 1 });
    const end = endOfWeek(endOfMonth(currentMonth), { weekStartsOn: 1 });
    const days = [];
    let day = start;
    while (day <= end) {
      days.push(day);
      day = addDays(day, 1);
    }
    return days;
  }, [currentMonth]);

  const eventsByDate = useMemo(() => {
    const map = {};
    events.forEach((e) => {
      if (!map[e.event_date]) map[e.event_date] = [];
      map[e.event_date].push(e);
    });
    return map;
  }, [events]);

  const openAddDialog = (date) => {
    const dateStr = format(date, "yyyy-MM-dd");
    setEditEvent(null);
    setForm({ ...EMPTY_EVENT, event_date: dateStr, scaled_object_id: scaledObjects[0]?.id || "" });
    setDialogOpen(true);
  };

  const openEditDialog = (event) => {
    setEditEvent(event);
    setForm({
      scaled_object_id: event.scaled_object_id,
      name: event.name,
      timezone_str: event.timezone_str,
      desired_replicas: event.desired_replicas,
      event_date: event.event_date,
      start_time: event.start_time,
      end_time: event.end_time,
    });
    setDialogOpen(true);
  };

  const handleSave = async () => {
    if (!form.name || !form.scaled_object_id) {
      toast.error("Please fill in all required fields");
      return;
    }
    setSaving(true);
    try {
      if (editEvent) {
        await api.put(`/cron-events/${editEvent.id}`, form);
        toast.success("Event updated");
      } else {
        await api.post("/cron-events", form);
        toast.success("Event created");
      }
      setDialogOpen(false);
      fetchEvents();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Save failed");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteConfirm) return;
    try {
      await api.delete(`/cron-events/${deleteConfirm}`);
      toast.success("Event deleted");
      setDeleteConfirm(null);
      fetchEvents();
    } catch {
      toast.error("Delete failed");
    }
  };

  const WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

  return (
    <div className="p-6 space-y-6 animate-fade-in" data-testid="cron-calendar-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl sm:text-3xl font-semibold text-slate-900 tracking-tight">Cron Calendar</h1>
          <p className="text-sm text-slate-500 mt-1">Schedule and manage cron-based autoscaling events</p>
        </div>
        <Select value={filterSoId} onValueChange={setFilterSoId}>
          <SelectTrigger className="w-56 h-9" data-testid="calendar-so-filter">
            <SelectValue placeholder="Filter by ScaledObject" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All ScaledObjects</SelectItem>
            {scaledObjects.map((so) => (
              <SelectItem key={so.id} value={so.id}>{so.name}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Month Nav */}
      <div className="flex items-center justify-between bg-white border border-slate-200 rounded-md px-4 py-3">
        <Button variant="ghost" size="icon" onClick={() => setCurrentMonth(subMonths(currentMonth, 1))} data-testid="prev-month-btn" className="h-8 w-8">
          <ChevronLeft className="w-4 h-4" />
        </Button>
        <h2 className="text-lg font-semibold text-slate-800 capitalize" data-testid="current-month-label">
          {format(currentMonth, "MMMM yyyy", { locale: fr })}
        </h2>
        <Button variant="ghost" size="icon" onClick={() => setCurrentMonth(addMonths(currentMonth, 1))} data-testid="next-month-btn" className="h-8 w-8">
          <ChevronRight className="w-4 h-4" />
        </Button>
      </div>

      {/* Calendar Grid */}
      <div>
        {/* Weekday headers */}
        <div className="grid grid-cols-7 mb-0">
          {WEEKDAYS.map((d) => (
            <div key={d} className="text-center py-2 text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">
              {d}
            </div>
          ))}
        </div>
        {/* Day cells */}
        <div className="calendar-grid">
          {calendarDays.map((day) => {
            const dateStr = format(day, "yyyy-MM-dd");
            const dayEvents = eventsByDate[dateStr] || [];
            const isCurrentMonth = isSameMonth(day, currentMonth);
            const isCurrentDay = isToday(day);
            return (
              <div
                key={dateStr}
                data-testid={`calendar-day-${dateStr}`}
                onClick={() => isCurrentMonth && openAddDialog(day)}
                className={`calendar-day-cell ${!isCurrentMonth ? "outside" : ""} ${isCurrentDay ? "today" : ""}`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className={`text-xs font-medium ${isCurrentDay ? "bg-slate-900 text-white w-6 h-6 rounded-full flex items-center justify-center" : isCurrentMonth ? "text-slate-700" : "text-slate-300"}`}>
                    {format(day, "d")}
                  </span>
                  {isCurrentMonth && dayEvents.length > 0 && (
                    <span className="text-[10px] text-slate-400">{dayEvents.length}</span>
                  )}
                </div>
                <div className="space-y-1">
                  {dayEvents.slice(0, 3).map((ev) => (
                    <div
                      key={ev.id}
                      data-testid={`event-${ev.id}`}
                      onClick={(e) => { e.stopPropagation(); openEditDialog(ev); }}
                      className="bg-blue-50 border border-blue-100 text-blue-800 rounded px-1.5 py-0.5 text-[10px] font-medium truncate cursor-pointer hover:bg-blue-100 transition-colors duration-150"
                    >
                      <span className="font-mono">{ev.start_time}</span> {ev.name}
                    </div>
                  ))}
                  {dayEvents.length > 3 && (
                    <p className="text-[10px] text-slate-400 pl-1">+{dayEvents.length - 3} more</p>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Add/Edit Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>{editEvent ? "Edit Cron Event" : "New Cron Event"}</DialogTitle>
            <DialogDescription>
              {editEvent ? "Modify the cron event configuration" : `Schedule a new event for ${form.event_date}`}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-1.5">
              <Label className="text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">ScaledObject</Label>
              <Select value={form.scaled_object_id} onValueChange={(v) => setForm((p) => ({ ...p, scaled_object_id: v }))}>
                <SelectTrigger data-testid="event-so-select" className="h-9"><SelectValue placeholder="Select..." /></SelectTrigger>
                <SelectContent>
                  {scaledObjects.map((so) => (
                    <SelectItem key={so.id} value={so.id}>{so.name} ({so.namespace})</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">Event Name</Label>
              <Input value={form.name} onChange={(e) => setForm((p) => ({ ...p, name: e.target.value }))} data-testid="event-name-input" className="h-9" placeholder="e.g., Business Hours Scale Up" />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label className="text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">Start Time</Label>
                <Input type="time" value={form.start_time} onChange={(e) => setForm((p) => ({ ...p, start_time: e.target.value }))} data-testid="event-start-time" className="h-9 font-mono" />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">End Time</Label>
                <Input type="time" value={form.end_time} onChange={(e) => setForm((p) => ({ ...p, end_time: e.target.value }))} data-testid="event-end-time" className="h-9 font-mono" />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label className="text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">Desired Replicas</Label>
                <Input type="number" value={form.desired_replicas} onChange={(e) => setForm((p) => ({ ...p, desired_replicas: parseInt(e.target.value) || 1 }))} data-testid="event-replicas-input" className="h-9 font-mono" />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">Timezone</Label>
                <Select value={form.timezone_str} onValueChange={(v) => setForm((p) => ({ ...p, timezone_str: v }))}>
                  <SelectTrigger data-testid="event-timezone-select" className="h-9 text-xs"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {["UTC", "Europe/Paris", "Europe/London", "US/Eastern", "US/Pacific", "Asia/Tokyo"].map((tz) => (
                      <SelectItem key={tz} value={tz}>{tz}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">Date</Label>
              <Input type="date" value={form.event_date} onChange={(e) => setForm((p) => ({ ...p, event_date: e.target.value }))} data-testid="event-date-input" className="h-9 font-mono" />
            </div>
          </div>
          <DialogFooter className="flex gap-2">
            {editEvent && (
              <Button variant="outline" className="text-red-600 border-red-200 hover:bg-red-50 mr-auto" onClick={() => { setDialogOpen(false); setDeleteConfirm(editEvent.id); }} data-testid="event-delete-btn">
                <Trash2 className="w-3.5 h-3.5 mr-1.5" /> Delete
              </Button>
            )}
            <Button variant="outline" onClick={() => setDialogOpen(false)} data-testid="event-cancel-btn">Cancel</Button>
            <Button onClick={handleSave} disabled={saving} data-testid="event-save-btn" className="bg-slate-900 hover:bg-slate-800 text-white">
              {saving ? "Saving..." : editEvent ? "Update" : "Create"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirm */}
      <Dialog open={!!deleteConfirm} onOpenChange={() => setDeleteConfirm(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Cron Event</DialogTitle>
            <DialogDescription>This will permanently remove this scheduled event.</DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteConfirm(null)} data-testid="cancel-event-delete-btn">Cancel</Button>
            <Button variant="destructive" onClick={handleDelete} data-testid="confirm-event-delete-btn">Delete</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
