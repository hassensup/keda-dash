import { useState, useEffect, useCallback, useMemo } from "react";
import api from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";
import { ChevronLeft, ChevronRight, Plus, Clock, Pencil, Trash2, RefreshCw } from "lucide-react";
import {
  startOfMonth, endOfMonth, startOfWeek, endOfWeek, addDays, addMonths, subMonths,
  format, isSameMonth, isSameDay, isToday, parseISO,
} from "date-fns";
import { fr } from "date-fns/locale";
import cronParser from "cron-parser";

const EMPTY_TRIGGER = {
  type: "cron",
  metadata: {
    timezone: "UTC",
    start: "0 8 * * 1-5",
    end: "0 20 * * 1-5",
    desiredReplicas: "10"
  }
};

export default function CronCalendarPage() {
  const [currentMonth, setCurrentMonth] = useState(new Date());
  const [scaledObjects, setScaledObjects] = useState([]);
  const [filterSoId, setFilterSoId] = useState("all");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editTrigger, setEditTrigger] = useState(null);
  const [form, setForm] = useState({ ...EMPTY_TRIGGER });
  const [saving, setSaving] = useState(false);

  const monthStr = format(currentMonth, "yyyy-MM");

  const fetchScaledObjects = useCallback(async () => {
    try {
      const res = await api.get("/scaled-objects");
      setScaledObjects(res.data);
    } catch {
      toast.error("Failed to load ScaledObjects");
    }
  }, []);

  useEffect(() => { fetchScaledObjects(); }, [fetchScaledObjects]);

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

  const projectedEvents = useMemo(() => {
    const map = {};
    const start = startOfMonth(currentMonth);
    const end = endOfMonth(currentMonth);

    scaledObjects.forEach((so) => {
      if (filterSoId !== "all" && so.id !== filterSoId) return;

      so.triggers.forEach((trigger, triggerIdx) => {
        if (trigger.type !== "cron") return;

        try {
          const cronExpr = trigger.metadata?.start;
          if (!cronExpr) return;

          const interval = cronParser.parseExpression(cronExpr, {
            currentDate: start,
          });
          let nextDate = interval.next();

          while (nextDate <= end) {
            const dateStr = format(nextDate, "yyyy-MM-dd");
            if (!map[dateStr]) map[dateStr] = [];

            map[dateStr].push({
              id: `so-${so.id}-tr-${triggerIdx}`,
              soId: so.id,
              soName: so.name,
              triggerIdx,
              trigger: trigger,
              time: format(nextDate, "HH:mm"),
              date: dateStr
            });
            nextDate = interval.next();
          }
        } catch (e) {
          console.error(`Invalid cron expression for ${so.name}: ${trigger.metadata?.start}`, e);
        }
      });
    });
    return map;
  }, [scaledObjects, currentMonth, filterSoId]);

  const openAddDialog = (date) => {
    const dateStr = format(date, "yyyy-MM-dd");
    setEditTrigger(null);
    setForm({ ...EMPTY_TRIGGER });
    setDialogOpen(true);
  };

  const openEditDialog = (event) => {
    setEditTrigger(event);
    setForm({
      ...event.trigger,
      metadata: { ...event.trigger.metadata }
    });
    setDialogOpen(true);
  };

  const handleSave = async () => {
    if (!editTrigger && !form.metadata?.start) {
      toast.error("Please specify a cron start expression");
      return;
    }
    setSaving(true);
    try {
      const soId = editTrigger ? editTrigger.soId : scaledObjects[0]?.id;
      if (!soId) {
        toast.error("No ScaledObject selected");
        setSaving(false);
        return;
      }

      const so = scaledObjects.find(s => s.id === soId);
      let triggers = [...so.triggers];

      if (editTrigger) {
        triggers[editTrigger.triggerIdx] = form;
      } else {
        triggers.push(form);
      }

      await api.put(`/scaled-objects/${soId}`, { triggers });
      toast.success("Trigger updated");
      setDialogOpen(false);
      fetchScaledObjects();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Save failed");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!editTrigger) return;
    try {
      const soId = editTrigger.soId;
      const so = scaledObjects.find(s => s.id === soId);
      let triggers = [...so.triggers];
      triggers.splice(editTrigger.triggerIdx, 1);

      await api.put(`/scaled-objects/${soId}`, { triggers });
      toast.success("Trigger deleted");
      setDialogOpen(false);
      fetchScaledObjects();
    } catch {
      toast.error("Delete failed");
    }
  };

  const WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

  return (
    <div className="p-6 space-y-6 animate-fade-in" data-testid="cron-calendar-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div>
            <h1 className="text-2xl sm:text-3xl font-semibold text-slate-900 tracking-tight">Cron Calendar</h1>
            <p className="text-sm text-slate-500 mt-1">Visualize and manage KEDA cron triggers</p>
          </div>
          <Button variant="outline" size="sm" onClick={fetchScaledObjects} className="h-8 w-8 p-0" data-testid="calendar-refresh-btn">
            <RefreshCw className="w-4 h-4" />
          </Button>
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
            const dayEvents = projectedEvents[dateStr] || [];
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
                      <span className="font-mono">{ev.time}</span> {ev.soName}
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
            <DialogTitle>{editTrigger ? "Edit Cron Trigger" : "New Cron Trigger"}</DialogTitle>
            <DialogDescription>
              {editTrigger ? "Modify the KEDA cron trigger configuration" : "Add a new cron trigger to a ScaledObject"}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-1.5">
              <Label className="text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">ScaledObject</Label>
              <Select
                value={editTrigger ? editTrigger.soId : (scaledObjects[0]?.id || "")}
                onValueChange={(v) => {
                  if (!editTrigger) {
                    setForm(p => ({ ...p, soId: v }));
                  }
                }}
              >
                <SelectTrigger data-testid="event-so-select" className="h-9"><SelectValue placeholder="Select..." /></SelectTrigger>
                <SelectContent>
                  {scaledObjects.map((so) => (
                    <SelectItem key={so.id} value={so.id}>{so.name} ({so.namespace})</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">Cron Start Expression</Label>
              <Input
                value={form.metadata?.start || ""}
                onChange={(e) => setForm((p) => ({ ...p, metadata: { ...p.metadata, start: e.target.value } }))}
                data-testid="event-cron-start"
                className="h-9 font-mono"
                placeholder="0 8 * * 1-5"
              />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">Cron End Expression</Label>
              <Input
                value={form.metadata?.end || ""}
                onChange={(e) => setForm((p) => ({ ...p, metadata: { ...p.metadata, end: e.target.value } }))}
                data-testid="event-cron-end"
                className="h-9 font-mono"
                placeholder="0 20 * * 1-5"
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label className="text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">Desired Replicas</Label>
                <Input
                  type="number"
                  value={form.metadata?.desiredReplicas || "1"}
                  onChange={(e) => setForm((p) => ({ ...p, metadata: { ...p.metadata, desiredReplicas: e.target.value } }))}
                  data-testid="event-replicas-input"
                  className="h-9 font-mono"
                />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">Timezone</Label>
                <Select
                  value={form.metadata?.timezone || "UTC"}
                  onValueChange={(v) => setForm((p) => ({ ...p, metadata: { ...p.metadata, timezone: v } }))}
                >
                  <SelectTrigger data-testid="event-timezone-select" className="h-9 text-xs"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {["UTC", "Europe/Paris", "Europe/London", "US/Eastern", "US/Pacific", "Asia/Tokyo"].map((tz) => (
                      <SelectItem key={tz} value={tz}>{tz}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>
          <DialogFooter className="flex gap-2">
            {editTrigger && (
              <Button variant="outline" className="text-red-600 border-red-200 hover:bg-red-50 mr-auto" onClick={() => { handleDelete(); }} data-testid="event-delete-btn">
                <Trash2 className="w-3.5 h-3.5 mr-1.5" /> Delete
              </Button>
            )}
            <Button variant="outline" onClick={() => setDialogOpen(false)} data-testid="event-cancel-btn">Cancel</Button>
            <Button onClick={handleSave} disabled={saving} data-testid="event-save-btn" className="bg-slate-900 hover:bg-slate-800 text-white">
              {saving ? "Saving..." : editTrigger ? "Update" : "Create"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirm */}
      {/* Legacy Delete Confirm removed as trigger-based deletion is now integrated into handleSave/handleDelete */}
    </div>
  );
}
