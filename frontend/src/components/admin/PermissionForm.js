import { useState, useEffect } from "react";
import api from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Plus, AlertCircle } from "lucide-react";

export default function PermissionForm({ userId, onPermissionAdded }) {
  const [action, setAction] = useState("read");
  const [scope, setScope] = useState("namespace");
  const [namespace, setNamespace] = useState("");
  const [objectName, setObjectName] = useState("");
  const [namespaces, setNamespaces] = useState([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchNamespaces();
  }, []);

  const fetchNamespaces = async () => {
    try {
      const { data } = await api.get("/namespaces");
      setNamespaces(data);
      if (data.length > 0 && !namespace) {
        setNamespace(data[0]);
      }
    } catch (err) {
      console.error("Failed to fetch namespaces:", err);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    // Validation
    if (!namespace) {
      setError("Namespace is required");
      return;
    }

    if (scope === "object" && !objectName) {
      setError("Object name is required for object-scoped permissions");
      return;
    }

    if (scope === "namespace" && objectName) {
      setError("Object name must be empty for namespace-scoped permissions");
      return;
    }

    setSubmitting(true);
    try {
      await api.post("/permissions", {
        user_id: userId,
        action,
        scope,
        namespace,
        object_name: scope === "object" ? objectName : null,
      });
      toast.success("Permission added successfully");
      
      // Reset form
      setAction("read");
      setScope("namespace");
      setObjectName("");
      
      onPermissionAdded();
    } catch (err) {
      const detail = err.response?.data?.detail;
      if (err.response?.status === 403) {
        setError("You don't have permission to add permissions");
      } else if (typeof detail === "string") {
        setError(detail);
      } else {
        setError("Failed to add permission");
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4" data-testid="permission-form">
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <div className="grid grid-cols-2 gap-4">
        {/* Action */}
        <div className="space-y-1.5">
          <Label className="text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">
            Action
          </Label>
          <Select value={action} onValueChange={setAction}>
            <SelectTrigger data-testid="permission-action" className="h-9">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="read">Read</SelectItem>
              <SelectItem value="write">Write</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Scope */}
        <div className="space-y-1.5">
          <Label className="text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">
            Scope
          </Label>
          <Select value={scope} onValueChange={(v) => {
            setScope(v);
            if (v === "namespace") {
              setObjectName("");
            }
          }}>
            <SelectTrigger data-testid="permission-scope" className="h-9">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="namespace">Namespace</SelectItem>
              <SelectItem value="object">Object</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Namespace */}
        <div className="space-y-1.5">
          <Label className="text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">
            Namespace
          </Label>
          <Select value={namespace} onValueChange={setNamespace}>
            <SelectTrigger data-testid="permission-namespace" className="h-9 font-mono text-sm">
              <SelectValue placeholder="Select namespace" />
            </SelectTrigger>
            <SelectContent>
              {namespaces.map((ns) => (
                <SelectItem key={ns} value={ns} className="font-mono text-sm">
                  {ns}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Object Name (conditional) */}
        <div className="space-y-1.5">
          <Label className="text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">
            Object Name {scope === "object" && <span className="text-red-500">*</span>}
          </Label>
          <Input
            value={objectName}
            onChange={(e) => setObjectName(e.target.value)}
            placeholder={scope === "object" ? "my-scaledobject" : "Leave empty for namespace scope"}
            disabled={scope === "namespace"}
            data-testid="permission-object-name"
            className="h-9 font-mono text-sm"
          />
        </div>
      </div>

      <div className="flex items-center justify-between pt-2">
        <p className="text-xs text-slate-500">
          {scope === "namespace" 
            ? `Grant ${action} access to all ScaledObjects in ${namespace || "selected namespace"}`
            : `Grant ${action} access to specific ScaledObject: ${objectName || "..."} in ${namespace || "selected namespace"}`
          }
        </p>
        <Button
          type="submit"
          disabled={submitting}
          data-testid="add-permission-btn"
          className="bg-slate-900 hover:bg-slate-800"
        >
          <Plus className="w-4 h-4 mr-2" />
          {submitting ? "Adding..." : "Add Permission"}
        </Button>
      </div>
    </form>
  );
}
