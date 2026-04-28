import { useState, useEffect } from "react";
import api from "@/lib/api";
import { toast } from "sonner";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { AlertCircle } from "lucide-react";
import PermissionList from "./PermissionList";
import PermissionForm from "./PermissionForm";

export default function UserPermissionDetail({ userId, onPermissionChange }) {
  const [permissions, setPermissions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchPermissions();
  }, [userId]);

  const fetchPermissions = async () => {
    setLoading(true);
    setError(null);
    try {
      const { data } = await api.get(`/permissions/users/${userId}`);
      setPermissions(data.permissions || []);
    } catch (err) {
      if (err.response?.status === 403) {
        setError("You don't have permission to view user permissions");
      } else {
        setError("Failed to load permissions");
      }
    } finally {
      setLoading(false);
    }
  };

  const handlePermissionAdded = () => {
    fetchPermissions();
    onPermissionChange();
  };

  const handlePermissionDeleted = () => {
    fetchPermissions();
    onPermissionChange();
  };

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>{error}</AlertDescription>
      </Alert>
    );
  }

  if (loading) {
    return (
      <div className="text-center py-8 text-slate-400">
        <p className="text-sm">Loading permissions...</p>
      </div>
    );
  }

  // Group permissions by namespace
  const groupedPermissions = permissions.reduce((acc, perm) => {
    if (!acc[perm.namespace]) {
      acc[perm.namespace] = [];
    }
    acc[perm.namespace].push(perm);
    return acc;
  }, {});

  return (
    <Tabs defaultValue="permissions" className="space-y-4">
      <TabsList>
        <TabsTrigger value="permissions" data-testid="tab-permissions">
          Current Permissions ({permissions.length})
        </TabsTrigger>
        <TabsTrigger value="add" data-testid="tab-add">
          Add Permission
        </TabsTrigger>
      </TabsList>

      <TabsContent value="permissions">
        {permissions.length === 0 ? (
          <div className="text-center py-12 text-slate-400">
            <p className="text-sm">No permissions assigned</p>
            <p className="text-xs mt-1">Use the "Add Permission" tab to grant access</p>
          </div>
        ) : (
          <div className="space-y-4">
            {Object.entries(groupedPermissions).map(([namespace, perms]) => (
              <div key={namespace} className="border border-slate-200 rounded-md p-4">
                <h3 className="text-sm font-semibold text-slate-700 mb-3 font-mono">
                  {namespace}
                </h3>
                <PermissionList
                  permissions={perms}
                  onPermissionDeleted={handlePermissionDeleted}
                />
              </div>
            ))}
          </div>
        )}
      </TabsContent>

      <TabsContent value="add">
        <PermissionForm
          userId={userId}
          onPermissionAdded={handlePermissionAdded}
        />
      </TabsContent>
    </Tabs>
  );
}
