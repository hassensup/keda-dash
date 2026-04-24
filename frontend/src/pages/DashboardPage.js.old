import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import api from "@/lib/api";
import { toast } from "sonner";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";
import { Plus, Search, Pencil, Trash2, Activity, Clock, Database, MessageSquare, Cpu, BarChart3, HardDrive } from "lucide-react";

const SCALER_ICONS = {
  cron: Clock,
  prometheus: BarChart3,
  rabbitmq: MessageSquare,
  kafka: MessageSquare,
  cpu: Cpu,
  memory: HardDrive,
  redis: Database,
  postgresql: Database,
  mysql: Database,
};

const STATUS_STYLES = {
  Active: "bg-emerald-50 text-emerald-700 border-emerald-200",
  Paused: "bg-amber-50 text-amber-700 border-amber-200",
  Error: "bg-red-50 text-red-700 border-red-200",
};

export default function DashboardPage() {
  const [objects, setObjects] = useState([]);
  const [namespaces, setNamespaces] = useState([]);
  const [filterNs, setFilterNs] = useState("all");
  const [filterType, setFilterType] = useState("all");
  const [searchTerm, setSearchTerm] = useState("");
  const [loading, setLoading] = useState(true);
  const [deleteId, setDeleteId] = useState(null);
  const navigate = useNavigate();

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const params = {};
      if (filterNs && filterNs !== "all") params.namespace = filterNs;
      if (filterType && filterType !== "all") params.scaler_type = filterType;
      const [objRes, nsRes] = await Promise.all([
        api.get("/scaled-objects", { params }),
        api.get("/namespaces"),
      ]);
      setObjects(objRes.data);
      setNamespaces(nsRes.data);
    } catch {
      toast.error("Failed to load data");
    } finally {
      setLoading(false);
    }
  }, [filterNs, filterType]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleDelete = async () => {
    if (!deleteId) return;
    try {
      await api.delete(`/scaled-objects/${deleteId}`);
      toast.success("ScaledObject deleted");
      setDeleteId(null);
      fetchData();
    } catch {
      toast.error("Failed to delete");
    }
  };

  const filtered = objects.filter((o) =>
    o.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    o.target_deployment.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const scalerTypes = [...new Set(objects.map((o) => o.scaler_type))];
  const stats = {
    total: objects.length,
    active: objects.filter((o) => o.status === "Active").length,
    paused: objects.filter((o) => o.status === "Paused").length,
  };

  return (
    <div className="p-6 space-y-6 animate-fade-in" data-testid="dashboard-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl sm:text-3xl font-semibold text-slate-900 tracking-tight">Scaled Objects</h1>
          <p className="text-sm text-slate-500 mt-1">Manage KEDA autoscaling configurations</p>
        </div>
        <Button
          onClick={() => navigate("/scaled-objects/new")}
          data-testid="create-scaled-object-btn"
          className="bg-slate-900 hover:bg-slate-800 text-white transition-all duration-150 hover:-translate-y-[1px]"
        >
          <Plus className="w-4 h-4 mr-2" /> New ScaledObject
        </Button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4">
        <StatCard label="Total" value={stats.total} icon={Activity} />
        <StatCard label="Active" value={stats.active} icon={Activity} color="text-emerald-600" />
        <StatCard label="Paused" value={stats.paused} icon={Clock} color="text-amber-600" />
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-xs">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <Input
            placeholder="Search by name or deployment..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            data-testid="search-input"
            className="pl-9 h-9"
          />
        </div>
        <Select value={filterNs} onValueChange={setFilterNs}>
          <SelectTrigger className="w-44 h-9" data-testid="namespace-filter">
            <SelectValue placeholder="Namespace" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Namespaces</SelectItem>
            {namespaces.map((ns) => (
              <SelectItem key={ns} value={ns}>{ns}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={filterType} onValueChange={setFilterType}>
          <SelectTrigger className="w-44 h-9" data-testid="type-filter">
            <SelectValue placeholder="Scaler Type" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Types</SelectItem>
            {scalerTypes.map((t) => (
              <SelectItem key={t} value={t}>{t}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Table */}
      <div className="bg-white border border-slate-200 rounded-md shadow-sm">
        <Table>
          <TableHeader>
            <TableRow className="hover:bg-transparent">
              <TableHead className="text-xs font-semibold uppercase tracking-[0.05em] text-slate-500">Name</TableHead>
              <TableHead className="text-xs font-semibold uppercase tracking-[0.05em] text-slate-500">Namespace</TableHead>
              <TableHead className="text-xs font-semibold uppercase tracking-[0.05em] text-slate-500">Scaler</TableHead>
              <TableHead className="text-xs font-semibold uppercase tracking-[0.05em] text-slate-500">Target</TableHead>
              <TableHead className="text-xs font-semibold uppercase tracking-[0.05em] text-slate-500">Replicas</TableHead>
              <TableHead className="text-xs font-semibold uppercase tracking-[0.05em] text-slate-500">Status</TableHead>
              <TableHead className="text-xs font-semibold uppercase tracking-[0.05em] text-slate-500 text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow><TableCell colSpan={7} className="text-center py-12 text-slate-400">Loading...</TableCell></TableRow>
            ) : filtered.length === 0 ? (
              <TableRow><TableCell colSpan={7} className="text-center py-12 text-slate-400">No ScaledObjects found</TableCell></TableRow>
            ) : (
              filtered.map((obj) => {
                const Icon = SCALER_ICONS[obj.scaler_type] || Activity;
                return (
                  <TableRow key={obj.id} data-testid={`so-row-${obj.id}`} className="group">
                    <TableCell className="font-medium text-slate-900">
                      <span className="font-mono text-sm">{obj.name}</span>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" className="font-mono text-xs">{obj.namespace}</Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1.5">
                        <Icon className="w-3.5 h-3.5 text-slate-400" />
                        <span className="text-sm text-slate-600">{obj.scaler_type}</span>
                      </div>
                    </TableCell>
                    <TableCell className="font-mono text-xs text-slate-600">{obj.target_deployment}</TableCell>
                    <TableCell>
                      <span className="font-mono text-xs text-slate-600">{obj.min_replicas} / {obj.max_replicas}</span>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" className={`text-xs ${STATUS_STYLES[obj.status] || ""}`}>
                        {obj.status === "Active" && <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 mr-1.5 pulse-dot inline-block" />}
                        {obj.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-1">
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8"
                          onClick={() => navigate(`/scaled-objects/${obj.id}`)}
                          data-testid={`edit-so-${obj.id}`}
                        >
                          <Pencil className="w-3.5 h-3.5" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8 text-red-500 hover:text-red-700 hover:bg-red-50"
                          onClick={() => setDeleteId(obj.id)}
                          data-testid={`delete-so-${obj.id}`}
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                );
              })
            )}
          </TableBody>
        </Table>
      </div>

      {/* Delete Dialog */}
      <Dialog open={!!deleteId} onOpenChange={() => setDeleteId(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete ScaledObject</DialogTitle>
            <DialogDescription>This action cannot be undone. The ScaledObject and all associated cron events will be permanently removed.</DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteId(null)} data-testid="cancel-delete-btn">Cancel</Button>
            <Button variant="destructive" onClick={handleDelete} data-testid="confirm-delete-btn">Delete</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function StatCard({ label, value, icon: Icon, color = "text-slate-600" }) {
  return (
    <div className="bg-white border border-slate-200 rounded-md p-4 flex items-center gap-3">
      <div className={`w-9 h-9 rounded-md bg-slate-50 flex items-center justify-center ${color}`}>
        <Icon className="w-4 h-4" />
      </div>
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">{label}</p>
        <p className="text-xl font-semibold text-slate-900">{value}</p>
      </div>
    </div>
  );
}
