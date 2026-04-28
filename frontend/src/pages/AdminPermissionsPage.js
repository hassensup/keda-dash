import { useState, useEffect } from "react";
import api from "@/lib/api";
import { toast } from "sonner";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { AlertCircle, Shield } from "lucide-react";
import UserList from "@/components/admin/UserList";
import UserPermissionDetail from "@/components/admin/UserPermissionDetail";

export default function AdminPermissionsPage() {
  const [users, setUsers] = useState([]);
  const [selectedUserId, setSelectedUserId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [permissionError, setPermissionError] = useState(null);

  useEffect(() => {
    fetchUsers();
  }, []);

  const fetchUsers = async () => {
    setLoading(true);
    setPermissionError(null);
    try {
      const { data } = await api.get("/permissions/users");
      setUsers(data);
    } catch (err) {
      if (err.response?.status === 403) {
        setPermissionError("You don't have permission to access this page. Admin role required.");
      } else {
        toast.error("Failed to load users");
      }
    } finally {
      setLoading(false);
    }
  };

  const handleUserSelect = (userId) => {
    setSelectedUserId(userId);
  };

  const handlePermissionChange = () => {
    // Refresh users list to update permission counts
    fetchUsers();
  };

  if (permissionError) {
    return (
      <div className="p-6">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{permissionError}</AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6 animate-fade-in" data-testid="admin-permissions-page">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-md bg-slate-900 flex items-center justify-center">
          <Shield className="w-5 h-5 text-white" />
        </div>
        <div>
          <h1 className="text-2xl sm:text-3xl font-semibold text-slate-900 tracking-tight">
            Permission Management
          </h1>
          <p className="text-sm text-slate-500 mt-1">Manage user permissions for ScaledObjects</p>
        </div>
      </div>

      {/* Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* User List */}
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle className="text-lg">Users</CardTitle>
            <CardDescription>Select a user to manage permissions</CardDescription>
          </CardHeader>
          <CardContent>
            <UserList
              users={users}
              selectedUserId={selectedUserId}
              onUserSelect={handleUserSelect}
              loading={loading}
            />
          </CardContent>
        </Card>

        {/* User Permission Detail */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-lg">User Permissions</CardTitle>
            <CardDescription>
              {selectedUserId
                ? "View and manage permissions for the selected user"
                : "Select a user to view their permissions"}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {selectedUserId ? (
              <UserPermissionDetail
                userId={selectedUserId}
                onPermissionChange={handlePermissionChange}
              />
            ) : (
              <div className="text-center py-12 text-slate-400">
                <Shield className="w-12 h-12 mx-auto mb-3 opacity-20" />
                <p className="text-sm">Select a user from the list to manage their permissions</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
