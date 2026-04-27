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
  const [namespaces, setNamespaces] = useState([]);
  const [deployments, setDeployments] = useState([]);
  const [selectedTriggerType, setSelectedTriggerType] = useState("cron");
  const [form, setForm] = useState({
    name: "", namespace: "default", scaler_type: "cron",
    target_deployment: "", min_replicas: 0, max_replicas: 10,
    cooldown_period: 300, polling_interval: 30, triggers: [], status: "Active",
    scaling_behavior: {
      scale_up: null,
      scale_down: null,
    }
  });

  useEffect(() => {
    const fetchNamespaces = async () => {
      try {
        const nsRes = await api.get("/namespaces");
        setNamespaces(nsRes.data);
      } catch (err) {
        console.error("Failed to fetch namespaces:", err);
      }
    };
    fetchNamespaces();
  }, []);

  useEffect(() => {
    const fetchDeployments = async () => {
      try {
        const params = form.namespace ? { namespace: form.namespace } : {};
        const depRes = await api.get("/deployments", { params });
        setDeployments(depRes.data);
      } catch (err) {
        console.error("Failed to fetch deployments:", err);
        setDeployments([]);
      }
    };
    if (form.namespace) {
      fetchDeployments();
    }
  }, [form.namespace]);

  useEffect(() => {
    if (!isNew) {
      api.get(`/scaled-objects/${id}`)
        .then(({ data }) => {
          console.log("ScaledObject data:", data);
          console.log("Triggers:", data.triggers);
          // Initialiser scaling_behavior avec la structure correcte si null
          if (!data.scaling_behavior) {
            data.scaling_behavior = {
              scale_up: null,
              scale_down: null,
            };
          }
          setForm(data);
        })
        .catch(() => { toast.error("Not found"); navigate("/"); })
        .finally(() => setLoading(false));
    }
  }, [id, isNew, navigate]);

  const updateField = (key, value) => {
    setForm((prev) => {
      const updated = { ...prev, [key]: value };
      // Si on change le namespace, réinitialiser le target_deployment
      if (key === "namespace" && value !== prev.namespace) {
        updated.target_deployment = "";
      }
      return updated;
    });
  };

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
    const fields = SCALER_FIELDS[selectedTriggerType] || [];
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
      triggers: [...prev.triggers, { type: selectedTriggerType, metricType: SCALER_FIELDS[selectedTriggerType]?.find(f => f.key === 'metricType')?.default || "", metadata }],
    }));
  };

  const removeTrigger = (idx) => {
    setForm((prev) => ({
      ...prev,
      triggers: prev.triggers.filter((_, i) => i !== idx),
    }));
  };

  const toggleScalingBehavior = (type) => {
    setForm((prev) => ({
      ...prev,
      scaling_behavior: {
        ...prev.scaling_behavior,
        [type]: prev.scaling_behavior[type] === null ? {
          stabilization_window_seconds: 300,
          select_policy: "Max",
          policies: []
        } : null
      }
    }));
  };

  const updateScalingBehaviorField = (type, field, value) => {
    setForm((prev) => ({
      ...prev,
      scaling_behavior: {
        ...prev.scaling_behavior,
        [type]: {
          ...prev.scaling_behavior[type],
          [field]: value
        }
      }
    }));
  };

  const addScalingPolicy = (type) => {
    setForm((prev) => ({
      ...prev,
      scaling_behavior: {
        ...prev.scaling_behavior,
        [type]: {
          ...prev.scaling_behavior[type],
          policies: [
            ...prev.scaling_behavior[type].policies,
            { type: "Percent", value: 100, period_seconds: 15 }
          ]
        }
      }
    }));
  };

  const removeScalingPolicy = (type, idx) => {
    setForm((prev) => ({
      ...prev,
      scaling_behavior: {
        ...prev.scaling_behavior,
        [type]: {
          ...prev.scaling_behavior[type],
          policies: prev.scaling_behavior[type].policies.filter((_, i) => i !== idx)
        }
      }
    }));
  };

  const updateScalingPolicy = (type, idx, field, value) => {
    setForm((prev) => ({
      ...prev,
      scaling_behavior: {
        ...prev.scaling_behavior,
        [type]: {
          ...prev.scaling_behavior[type],
          policies: prev.scaling_behavior[type].policies.map((p, i) => 
            i === idx ? { ...p, [field]: value } : p
          )
        }
      }
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
              <div className="space-y-1.5">
                <Label className="text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">Namespace</Label>
                <Select value={form.namespace} onValueChange={(v) => updateField("namespace", v)}>
                  <SelectTrigger data-testid="field-namespace" className="h-9 font-mono text-sm">
                    <SelectValue placeholder="Select namespace" />
                  </SelectTrigger>
                  <SelectContent>
                    {namespaces.length === 0 && (
                      <SelectItem value="default">default</SelectItem>
                    )}
                    {namespaces.map((ns) => (
                      <SelectItem key={ns} value={ns}>{ns}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">Target Deployment</Label>
                <Select 
                  value={form.target_deployment} 
                  onValueChange={(v) => updateField("target_deployment", v)}
                >
                  <SelectTrigger data-testid="field-target" className="h-9 font-mono text-sm">
                    <SelectValue placeholder="Select deployment" />
                  </SelectTrigger>
                  <SelectContent>
                    {deployments.length === 0 && (
                      <div className="px-2 py-1.5 text-xs text-slate-400 text-center">
                        {!form.namespace ? "Select a namespace first" : "No deployments found"}
                      </div>
                    )}
                    {form.target_deployment && !deployments.includes(form.target_deployment) && (
                      <SelectItem value={form.target_deployment}>{form.target_deployment}</SelectItem>
                    )}
                    {deployments.map((dep) => (
                      <SelectItem key={dep} value={dep}>{dep}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">Scaler Types</Label>
                <div className="flex flex-wrap gap-2 min-h-[36px] items-center border border-slate-200 rounded-md px-3 py-2 bg-slate-50">
                  {form.triggers.length > 0 ? (
                    [...new Set(form.triggers.map(t => t.type))].map((type, idx) => (
                      <Badge key={idx} variant="secondary" className="text-xs font-mono capitalize">
                        {type}
                      </Badge>
                    ))
                  ) : (
                    <span className="text-xs text-slate-400">No triggers configured</span>
                  )}
                </div>
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
          <div className="space-y-4">
            {/* Basic Scaling Parameters */}
            <div className="bg-white border border-slate-200 rounded-md p-6">
              <h3 className="text-sm font-semibold text-slate-700 mb-4">Basic Parameters</h3>
              <div className="grid grid-cols-2 gap-4">
                <NumField label="Min Replicas" value={form.min_replicas} onChange={(v) => updateField("min_replicas", v)} testId="field-min-replicas" />
                <NumField label="Max Replicas" value={form.max_replicas} onChange={(v) => updateField("max_replicas", v)} testId="field-max-replicas" />
                <NumField label="Cooldown Period (s)" value={form.cooldown_period} onChange={(v) => updateField("cooldown_period", v)} testId="field-cooldown" />
                <NumField label="Polling Interval (s)" value={form.polling_interval} onChange={(v) => updateField("polling_interval", v)} testId="field-polling" />
              </div>
            </div>

            {/* Scaling Behavior */}
            <div className="bg-white border border-slate-200 rounded-md p-6 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-semibold text-slate-700">Scaling Behavior</h3>
                  <p className="text-xs text-slate-500 mt-1">Optional advanced scaling policies</p>
                </div>
              </div>

              {/* Scale Up */}
              <div className="border border-slate-200 rounded-md p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <Label className="text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">Scale Up Behavior</Label>
                  <Button 
                    variant={form.scaling_behavior.scale_up ? "destructive" : "outline"} 
                    size="sm" 
                    onClick={() => toggleScalingBehavior("scale_up")}
                    data-testid="toggle-scale-up"
                  >
                    {form.scaling_behavior.scale_up ? "Remove" : "Add"}
                  </Button>
                </div>
                
                {form.scaling_behavior.scale_up && (
                  <div className="space-y-3 pt-2">
                    <div className="grid grid-cols-2 gap-3">
                      <NumField 
                        label="Stabilization Window (s)" 
                        value={form.scaling_behavior.scale_up.stabilization_window_seconds} 
                        onChange={(v) => updateScalingBehaviorField("scale_up", "stabilization_window_seconds", v)} 
                        testId="scale-up-stabilization"
                      />
                      <div className="space-y-1.5">
                        <Label className="text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">Select Policy</Label>
                        <Select 
                          value={form.scaling_behavior.scale_up.select_policy} 
                          onValueChange={(v) => updateScalingBehaviorField("scale_up", "select_policy", v)}
                        >
                          <SelectTrigger className="h-9" data-testid="scale-up-select-policy">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="Max">Max</SelectItem>
                            <SelectItem value="Min">Min</SelectItem>
                            <SelectItem value="Disabled">Disabled</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    </div>

                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <Label className="text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">Policies</Label>
                        <Button 
                          variant="outline" 
                          size="sm" 
                          onClick={() => addScalingPolicy("scale_up")}
                          data-testid="add-scale-up-policy"
                        >
                          <Plus className="w-3.5 h-3.5 mr-1.5" /> Add Policy
                        </Button>
                      </div>
                      {form.scaling_behavior.scale_up.policies.map((policy, idx) => (
                        <div key={idx} className="grid grid-cols-4 gap-2 items-end p-2 bg-slate-50 rounded border border-slate-200">
                          <div className="space-y-1">
                            <Label className="text-xs text-slate-500">Type</Label>
                            <Select 
                              value={policy.type} 
                              onValueChange={(v) => updateScalingPolicy("scale_up", idx, "type", v)}
                            >
                              <SelectTrigger className="h-8 text-xs">
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="Percent">Percent</SelectItem>
                                <SelectItem value="Pods">Pods</SelectItem>
                              </SelectContent>
                            </Select>
                          </div>
                          <div className="space-y-1">
                            <Label className="text-xs text-slate-500">Value</Label>
                            <Input 
                              type="number" 
                              value={policy.value} 
                              onChange={(e) => updateScalingPolicy("scale_up", idx, "value", parseInt(e.target.value) || 0)}
                              className="h-8 text-xs"
                            />
                          </div>
                          <div className="space-y-1">
                            <Label className="text-xs text-slate-500">Period (s)</Label>
                            <Input 
                              type="number" 
                              value={policy.period_seconds} 
                              onChange={(e) => updateScalingPolicy("scale_up", idx, "period_seconds", parseInt(e.target.value) || 0)}
                              className="h-8 text-xs"
                            />
                          </div>
                          <Button 
                            variant="ghost" 
                            size="icon" 
                            className="h-8 w-8 text-red-500"
                            onClick={() => removeScalingPolicy("scale_up", idx)}
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </Button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Scale Down */}
              <div className="border border-slate-200 rounded-md p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <Label className="text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">Scale Down Behavior</Label>
                  <Button 
                    variant={form.scaling_behavior.scale_down ? "destructive" : "outline"} 
                    size="sm" 
                    onClick={() => toggleScalingBehavior("scale_down")}
                    data-testid="toggle-scale-down"
                  >
                    {form.scaling_behavior.scale_down ? "Remove" : "Add"}
                  </Button>
                </div>
                
                {form.scaling_behavior.scale_down && (
                  <div className="space-y-3 pt-2">
                    <div className="grid grid-cols-2 gap-3">
                      <NumField 
                        label="Stabilization Window (s)" 
                        value={form.scaling_behavior.scale_down.stabilization_window_seconds} 
                        onChange={(v) => updateScalingBehaviorField("scale_down", "stabilization_window_seconds", v)} 
                        testId="scale-down-stabilization"
                      />
                      <div className="space-y-1.5">
                        <Label className="text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">Select Policy</Label>
                        <Select 
                          value={form.scaling_behavior.scale_down.select_policy} 
                          onValueChange={(v) => updateScalingBehaviorField("scale_down", "select_policy", v)}
                        >
                          <SelectTrigger className="h-9" data-testid="scale-down-select-policy">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="Max">Max</SelectItem>
                            <SelectItem value="Min">Min</SelectItem>
                            <SelectItem value="Disabled">Disabled</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    </div>

                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <Label className="text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">Policies</Label>
                        <Button 
                          variant="outline" 
                          size="sm" 
                          onClick={() => addScalingPolicy("scale_down")}
                          data-testid="add-scale-down-policy"
                        >
                          <Plus className="w-3.5 h-3.5 mr-1.5" /> Add Policy
                        </Button>
                      </div>
                      {form.scaling_behavior.scale_down.policies.map((policy, idx) => (
                        <div key={idx} className="grid grid-cols-4 gap-2 items-end p-2 bg-slate-50 rounded border border-slate-200">
                          <div className="space-y-1">
                            <Label className="text-xs text-slate-500">Type</Label>
                            <Select 
                              value={policy.type} 
                              onValueChange={(v) => updateScalingPolicy("scale_down", idx, "type", v)}
                            >
                              <SelectTrigger className="h-8 text-xs">
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="Percent">Percent</SelectItem>
                                <SelectItem value="Pods">Pods</SelectItem>
                              </SelectContent>
                            </Select>
                          </div>
                          <div className="space-y-1">
                            <Label className="text-xs text-slate-500">Value</Label>
                            <Input 
                              type="number" 
                              value={policy.value} 
                              onChange={(e) => updateScalingPolicy("scale_down", idx, "value", parseInt(e.target.value) || 0)}
                              className="h-8 text-xs"
                            />
                          </div>
                          <div className="space-y-1">
                            <Label className="text-xs text-slate-500">Period (s)</Label>
                            <Input 
                              type="number" 
                              value={policy.period_seconds} 
                              onChange={(e) => updateScalingPolicy("scale_down", idx, "period_seconds", parseInt(e.target.value) || 0)}
                              className="h-8 text-xs"
                            />
                          </div>
                          <Button 
                            variant="ghost" 
                            size="icon" 
                            className="h-8 w-8 text-red-500"
                            onClick={() => removeScalingPolicy("scale_down", idx)}
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </Button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </TabsContent>

        <TabsContent value="triggers">
          <div className="bg-white border border-slate-200 rounded-md p-6 space-y-4">
            <div className="flex items-center justify-between gap-3">
              <p className="text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">
                Triggers ({form.triggers.length})
              </p>
              <div className="flex items-center gap-2">
                <Select value={selectedTriggerType} onValueChange={setSelectedTriggerType}>
                  <SelectTrigger className="w-40 h-8 text-xs" data-testid="trigger-type-select">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {Object.keys(SCALER_FIELDS).map((type) => (
                      <SelectItem key={type} value={type} className="text-xs capitalize">
                        {type}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Button variant="outline" size="sm" onClick={addTrigger} data-testid="add-trigger-btn">
                  <Plus className="w-3.5 h-3.5 mr-1.5" /> Add Trigger
                </Button>
              </div>
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
