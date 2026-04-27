import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import api from "@/lib/api";
import { toast } from "sonner";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { ArrowLeft, Save, Plus, Trash2 } from "lucide-react";

const SCALER_FIELDS = {
  cron: [
    { key: "timezone", label: "Timezone", default: "UTC" },
    { key: "start", label: "Start Schedule", default: "0 8 * * 1-5", mono: true },
    { key: "end", label: "End Schedule", default: "0 20 * * 1-5", mono: true },
    { key: "desiredReplicas", label: "Desired Replicas", default: "5", type: "number" },
  ],
  prometheus: [
    { key: "serverAddress", label: "Server Address", default: "http://prometheus:9090" },
    { key: "metricName", label: "Metric Name", default: "" },
    { key: "threshold", label: "Threshold", default: "100" },
    { key: "query", label: "Query", default: "" },
  ],
  rabbitmq: [
    { key: "host", label: "Host", default: "amqp://guest:guest@rabbitmq:5672" },
    { key: "queueName", label: "Queue Name", default: "" },
    { key: "queueLength", label: "Queue Length", default: "50" },
  ],
  kafka: [
    { key: "bootstrapServers", label: "Bootstrap Servers", default: "kafka:9092" },
    { key: "consumerGroup", label: "Consumer Group", default: "" },
    { key: "topic", label: "Topic", default: "" },
    { key: "lagThreshold", label: "Lag Threshold", default: "10" },
  ],
  cpu: [
    { key: "metricType", label: "Type", default: "Utilization", options: ["Utilization", "AverageValue"] },
    { key: "value", label: "Value", default: "60" },
  ],
  memory: [
    { key: "metricType", label: "Type", default: "Utilization", options: ["Utilization", "AverageValue"] },
    { key: "value", label: "Value", default: "60" },
  ],
  redis: [
    { key: "address", label: "Address", default: "redis:6379" },
    { key: "listName", label: "List Name", default: "" },
    { key: "listLength", label: "List Length", default: "20" },
  ],
  postgresql: [
    { key: "connectionString", label: "Connection String", default: "" },
    { key: "query", label: "Query", default: "" },
    { key: "targetQueryValue", label: "Target Value", default: "1" },
  ],
  mysql: [
    { key: "connectionString", label: "Connection String", default: "" },
    { key: "query", label: "Query", default: "" },
    { key: "queryValue", label: "Query Value", default: "1" },
  ],
  external: [
    { key: "scalerAddress", label: "Scaler Address", default: "" },
  ],
};

const SCALER_TYPE_LIST = Object.keys(SCALER_FIELDS);

export default function ScaledObjectDetailPage() {
  const { "*" : id } = useParams();
  const isNew = id === "new";
  const navigate = useNavigate();
  const [loading, setLoading] = useState(!isNew);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    name: "", namespace: "default", scaler_type: "cron",
    target_deployment: "", min_replicas: 0, max_replicas: 10,
    cooldown_period: 300, polling_interval: 30, triggers: [], status: "Active",
  });

  useEffect(() => {
    if (!isNew) {
      api.get(`/scaled-objects/${id}`)
        .then(({ data }) => {
          console.log("ScaledObject data:", data);
          console.log("Triggers:", data.triggers);
          setForm(data);
        })
        .catch(() => { toast.error("Not found"); navigate("/"); })
        .finally(() => setLoading(false));
    }
  }, [id, isNew, navigate]);

  const updateField = (key, value) => setForm((prev) => ({ ...prev, [key]: value }));

  const updateTriggerField = (idx, key, value, isMeta = true) => {
    setForm((prev) => {
      const triggers = [...prev.triggers];
      if (isMeta) {
        triggers[idx] = { ...triggers[idx], metadata: { ...triggers[idx].metadata, [key]: value } };
      } else {
        triggers[idx] = { ...triggers[idx], [key]: value };
      }
      return { ...prev, triggers };
    });
  };

  const addTrigger = () => {
    const fields = SCALER_FIELDS[form.scaler_type] || [];
    const metadata = {};
    fields.forEach((f) => {
      if (f.key === "metricType") {
        // metricType will be handled at the top level of the trigger object
      } else {
        metadata[f.key] = f.default;
      }
    });
    setForm((prev) => ({
      ...prev,
      triggers: [...prev.triggers, { type: form.scaler_type, metricType: SCALER_FIELDS[form.scaler_type]?.find(f => f.key === 'metricType')?.default || "", metadata }],
    }));
  };

  const removeTrigger = (idx) => {
    setForm((prev) => ({
      ...prev,
      triggers: prev.triggers.filter((_, i) => i !== idx),
    }));
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      if (isNew) {
        await api.post("/scaled-objects", form);
        toast.success("ScaledObject created");
      } else {
        const { id: _id, ...updateData } = form;
        await api.put(`/scaled-objects/${id}`, updateData);
        toast.success("ScaledObject updated");
      }
      navigate("/");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Save failed");
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div className="p-6 text-slate-400">Loading...</div>;

  return (
    <div className="p-6 space-y-6 animate-fade-in" data-testid="scaled-object-detail-page">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate("/")} data-testid="back-btn" className="h-8 w-8">
          <ArrowLeft className="w-4 h-4" />
        </Button>
        <div className="flex-1">
          <h1 className="text-2xl font-semibold text-slate-900 tracking-tight">
            {isNew ? "New ScaledObject" : form.name}
          </h1>
          {!isNew && (
            <div className="flex items-center gap-2 mt-1 flex-wrap">
              <Badge variant="outline" className="font-mono text-xs">{form.namespace}</Badge>
              {(() => {
                const uniqueTypes = form.triggers.length > 0 
                  ? [...new Set(form.triggers.map(t => t.type))]
                  : [form.scaler_type];
                console.log("Unique scaler types:", uniqueTypes);
                return uniqueTypes.map((type, idx) => (
                  <Badge key={idx} variant="outline" className="text-xs capitalize">
                    {type}
                  </Badge>
                ));
              })()}
            </div>
          )}
        </div>
        <Button onClick={handleSave} disabled={saving} data-testid="save-btn"
          className="bg-slate-900 hover:bg-slate-800 text-white transition-all duration-150 hover:-translate-y-[1px]">
          <Save className="w-4 h-4 mr-2" />{saving ? "Saving..." : "Save"}
        </Button>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="general" className="space-y-4">
        <TabsList>
          <TabsTrigger value="general" data-testid="tab-general">General</TabsTrigger>
          <TabsTrigger value="scaling" data-testid="tab-scaling">Scaling</TabsTrigger>
          <TabsTrigger value="triggers" data-testid="tab-triggers">Triggers</TabsTrigger>
        </TabsList>

        <TabsContent value="general">
          <div className="bg-white border border-slate-200 rounded-md p-6 space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <FormField label="Name" value={form.name} onChange={(v) => updateField("name", v)} testId="field-name" mono />
              <FormField label="Namespace" value={form.namespace} onChange={(v) => updateField("namespace", v)} testId="field-namespace" mono />
              <FormField label="Target Deployment" value={form.target_deployment} onChange={(v) => updateField("target_deployment", v)} testId="field-target" mono />
              <div className="space-y-1.5">
                <Label className="text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">Scaler Type</Label>
                <Select value={form.scaler_type} onValueChange={(v) => updateField("scaler_type", v)}>
                  <SelectTrigger data-testid="field-scaler-type" className="h-9 font-mono text-sm">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {SCALER_TYPE_LIST.map((t) => (
                      <SelectItem key={t} value={t}>{t}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              {!isNew && (
                <div className="space-y-1.5">
                  <Label className="text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">Status</Label>
                  <Select value={form.status} onValueChange={(v) => updateField("status", v)}>
                    <SelectTrigger data-testid="field-status" className="h-9">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="Active">Active</SelectItem>
                      <SelectItem value="Paused">Paused</SelectItem>
                      <SelectItem value="Error">Error</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              )}
            </div>
          </div>
        </TabsContent>

        <TabsContent value="scaling">
          <div className="bg-white border border-slate-200 rounded-md p-6">
            <div className="grid grid-cols-2 gap-4">
              <NumField label="Min Replicas" value={form.min_replicas} onChange={(v) => updateField("min_replicas", v)} testId="field-min-replicas" />
              <NumField label="Max Replicas" value={form.max_replicas} onChange={(v) => updateField("max_replicas", v)} testId="field-max-replicas" />
              <NumField label="Cooldown Period (s)" value={form.cooldown_period} onChange={(v) => updateField("cooldown_period", v)} testId="field-cooldown" />
              <NumField label="Polling Interval (s)" value={form.polling_interval} onChange={(v) => updateField("polling_interval", v)} testId="field-polling" />
            </div>
          </div>
        </TabsContent>

        <TabsContent value="triggers">
          <div className="bg-white border border-slate-200 rounded-md p-6 space-y-4">
            <div className="flex items-center justify-between">
              <p className="text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">
                Triggers ({form.triggers.length})
              </p>
              <Button variant="outline" size="sm" onClick={addTrigger} data-testid="add-trigger-btn">
                <Plus className="w-3.5 h-3.5 mr-1.5" /> Add Trigger
              </Button>
            </div>
            {form.triggers.length === 0 && (
              <p className="text-sm text-slate-400 py-4 text-center">No triggers configured. Add one to get started.</p>
            )}
            {form.triggers.map((trigger, idx) => {
              const fields = SCALER_FIELDS[trigger.type] || SCALER_FIELDS[form.scaler_type] || [];
              return (
                <div key={idx} className="border border-slate-200 rounded-md p-4 space-y-3" data-testid={`trigger-${idx}`}>
                  <div className="flex items-center justify-between">
                    <Badge variant="outline" className="font-mono text-xs">{trigger.type}</Badge>
                    <Button variant="ghost" size="icon" className="h-7 w-7 text-red-500" onClick={() => removeTrigger(idx)} data-testid={`remove-trigger-${idx}`}>
                      <Trash2 className="w-3.5 h-3.5" />
                    </Button>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    {fields.map((field) => (
                      field.options ? (
                        <div key={field.key} className="space-y-1">
                          <Label className="text-xs text-slate-500">{field.label}</Label>
                          <Select
                            value={trigger.metadata?.[field.key] || field.default}
                            onValueChange={(v) => updateTriggerField(idx, field.key, v)}
                          >
                            <SelectTrigger className="h-8 text-xs"><SelectValue /></SelectTrigger>
                            <SelectContent>
                              {field.options.map((opt) => (
                                <SelectItem key={opt} value={opt}>{opt}</SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>
                      ) : (
                        <div key={field.key} className="space-y-1">
                          <Label className="text-xs text-slate-500">{field.label}</Label>
                          <Input
                            value={trigger.metadata?.[field.key] || ""}
                            onChange={(e) => updateTriggerField(idx, field.key, e.target.value)}
                            className={`h-8 text-xs ${field.mono ? "font-mono" : ""}`}
                            data-testid={`trigger-${idx}-${field.key}`}
                          />
                        </div>
                      )
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}

function FormField({ label, value, onChange, testId, mono }) {
  return (
    <div className="space-y-1.5">
      <Label className="text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">{label}</Label>
      <Input
        value={value || ""}
        onChange={(e) => onChange(e.target.value)}
        data-testid={testId}
        className={`h-9 ${mono ? "font-mono text-sm" : ""}`}
      />
    </div>
  );
}

function NumField({ label, value, onChange, testId }) {
  return (
    <div className="space-y-1.5">
      <Label className="text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">{label}</Label>
      <Input
        type="number"
        value={value ?? 0}
        onChange={(e) => onChange(parseInt(e.target.value) || 0)}
        data-testid={testId}
        className="h-9 font-mono text-sm"
      />
    </div>
  );
}
