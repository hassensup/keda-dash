import { useState, useEffect, useCallback, useMemo } from "react";
import api from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";
import { ChevronLeft, ChevronRight, Trash2, RefreshCw } from "lucide-react";
import {
  startOfMonth, endOfMonth, startOfWeek, endOfWeek,
  addDays, addMonths, subMonths,
  format, isSameMonth, isToday,
} from "date-fns";
import { fr } from "date-fns/locale";
import parser from "cron-parser"; // ✅ FIXED IMPORT

const EMPTY_TRIGGER = {
  type: "cron",
  metadata: {
    timezone: "UTC",
    start: "0 8 * * 1-5",
    end: "0 20 * * 1-5",
    desiredReplicas: "10"
  }
};

// ✅ normalize cron (fix leading zeros + weird formats)
function normalizeCron(expr) {
  if (!expr) return expr;
  return expr
    .trim()
    .replace(/\b0+(\d)/g, "$1"); // "00 07" -> "0 7"
}

export default function CronCalendarPage() {
  const [currentMonth, setCurrentMonth] = useState(new Date());
  const [scaledObjects, setScaledObjects] = useState([]);
  const [filterSoId, setFilterSoId] = useState("all");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editTrigger, setEditTrigger] = useState(null);
  const [form, setForm] = useState({ ...EMPTY_TRIGGER });
  const [saving, setSaving] = useState(false);

  const fetchScaledObjects = useCallback(async () => {
    try {
      const res = await api.get("/scaled-objects");
      setScaledObjects(res.data || []);
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

      (so.triggers || []).forEach((trigger, triggerIdx) => {
        if (trigger.type !== "cron") return;

        const cronExprRaw = trigger.metadata?.start;
        if (!cronExprRaw) return;

        const cronExpr = normalizeCron(cronExprRaw);

        try {
          const interval = parser.parseExpression(cronExpr, {
            currentDate: new Date(start.getTime() - 1000),
            tz: trigger.metadata?.timezone || "UTC",
          });

          while (true) {
            let nextDate;

            try {
              nextDate = interval.next().toDate();
            } catch {
              break; // no more occurrences
            }

            if (nextDate > end) break;

            const dateStr = format(nextDate, "yyyy-MM-dd");

            if (!map[dateStr]) map[dateStr] = [];

            map[dateStr].push({
              id: `so-${so.id}-tr-${triggerIdx}`,
              soId: so.id,
              soName: so.name,
              triggerIdx,
              trigger,
              time: format(nextDate, "HH:mm"),
              date: dateStr
            });
          }

        } catch (e) {
          console.error(`Invalid cron for ${so.name}:`, cronExpr, e);
        }
      });
    });

    return map;
  }, [scaledObjects, currentMonth, filterSoId]);

  const handleSave = async () => {
    if (!editTrigger && !form.metadata?.start) {
      toast.error("Cron start required");
      return;
    }

    setSaving(true);

    try {
      const soId = editTrigger ? editTrigger.soId : form.soId;
      if (!soId) throw new Error("No ScaledObject selected");

      const so = scaledObjects.find(s => s.id === soId);
      if (!so) throw new Error("ScaledObject not found");

      let triggers = [...(so.triggers || [])];

      if (editTrigger) {
        triggers[editTrigger.triggerIdx] = form;
      } else {
        triggers.push(form);
      }

      await api.put(`/scaled-objects/${soId}`, { triggers });

      toast.success("Saved");
      setDialogOpen(false);
      fetchScaledObjects();

    } catch (err) {
      toast.error(err.message || "Save failed");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!editTrigger) return;

    try {
      const so = scaledObjects.find(s => s.id === editTrigger.soId);
      let triggers = [...(so.triggers || [])];

      triggers.splice(editTrigger.triggerIdx, 1);

      await api.put(`/scaled-objects/${editTrigger.soId}`, { triggers });

      toast.success("Deleted");
      setDialogOpen(false);
      fetchScaledObjects();

    } catch {
      toast.error("Delete failed");
    }
  };

  return (
    <div className="p-6 space-y-6">
      
      {/* Header */}
      <div className="flex justify-between">
        <h1 className="text-2xl font-semibold">Cron Calendar</h1>

        <Button onClick={fetchScaledObjects}>
          <RefreshCw className="w-4 h-4" />
        </Button>
      </div>

      {/* Month Nav */}
      <div className="flex justify-between">
        <Button onClick={() => setCurrentMonth(subMonths(currentMonth, 1))}>
          <ChevronLeft />
        </Button>

        <h2>{format(currentMonth, "MMMM yyyy", { locale: fr })}</h2>

        <Button onClick={() => setCurrentMonth(addMonths(currentMonth, 1))}>
          <ChevronRight />
        </Button>
      </div>

      {/* Calendar */}
      <div className="grid grid-cols-7 gap-2">
        {calendarDays.map((day) => {
          const dateStr = format(day, "yyyy-MM-dd");
          const events = projectedEvents[dateStr] || [];

          return (
            <div key={dateStr} className="border p-2 text-xs">
              <div>{format(day, "d")}</div>

              {events.map(ev => (
                <div key={ev.id}>
                  {ev.time} {ev.soName}
                </div>
              ))}
            </div>
          );
        })}
      </div>

      {/* Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editTrigger ? "Edit" : "Create"} Trigger</DialogTitle>
            <DialogDescription />
          </DialogHeader>

          <Input
            value={form.metadata?.start || ""}
            onChange={(e) =>
              setForm(p => ({
                ...p,
                metadata: { ...p.metadata, start: e.target.value }
              }))
            }
          />

          <DialogFooter>
            {editTrigger && (
              <Button onClick={handleDelete}>
                <Trash2 /> Delete
              </Button>
            )}
            <Button onClick={handleSave} disabled={saving}>
              Save
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
