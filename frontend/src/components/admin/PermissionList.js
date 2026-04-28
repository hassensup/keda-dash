import { useState } from "react";
import api from "@/lib/api";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Trash2, Eye, Edit } from "lucide-react";

export default function PermissionList({ permissions, onPermissionDeleted }) {
  const [deleteId, setDeleteId] = useState(null);
  const [deleting, setDeleting] = useState(false);

  const handleDelete = async () => {
    if (!deleteId) return;

    setDeleting(true);
    try {
      await api.delete(`/permissions/${deleteId}`);
      toast.success("Permission deleted");
      setDeleteId(null);
      onPermissionDeleted();
    } catch (err) {
      if (err.response?.status === 403) {
        toast.error("You don't have permission to delete permissions");
      } else {
        toast.error("Failed to delete permission");
      }
    } finally {
      setDeleting(false);
    }
  };

  if (permissions.length === 0) {
    return (
      <div className="text-center py-4 text-slate-400">
        <p className="text-xs">No permissions in this namespace</p>
      </div>
    );
  }

  return (
    <>
      <div className="space-y-2">
        {permissions.map((perm) => (
          <div
            key={perm.id}
            className="flex items-center justify-between p-3 bg-slate-50 rounded-md border border-slate-200"
            data-testid={`permission-${perm.id}`}
          >
            <div className="flex items-center gap-3 flex-1 min-w-0">
              {/* Action Badge */}
              <Badge
                variant={perm.action === "write" ? "default" : "secondary"}
                className="shrink-0"
              >
                {perm.action === "read" ? (
                  <Eye className="w-3 h-3 mr-1" />
                ) : (
                  <Edit className="w-3 h-3 mr-1" />
                )}
                {perm.action}
              </Badge>

              {/* Scope Badge */}
              <Badge variant="outline" className="shrink-0 capitalize">
                {perm.scope}
              </Badge>

              {/* Object Name (if object scope) */}
              {perm.scope === "object" && perm.object_name && (
                <span className="text-sm font-mono text-slate-700 truncate">
                  {perm.object_name}
                </span>
              )}

              {/* Namespace scope indicator */}
              {perm.scope === "namespace" && (
                <span className="text-xs text-slate-500 italic">
                  All objects in namespace
                </span>
              )}
            </div>

            {/* Delete Button */}
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8 text-red-500 hover:text-red-700 hover:bg-red-50 shrink-0"
              onClick={() => setDeleteId(perm.id)}
              data-testid={`delete-permission-${perm.id}`}
            >
              <Trash2 className="w-3.5 h-3.5" />
            </Button>
          </div>
        ))}
      </div>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={!!deleteId} onOpenChange={() => setDeleteId(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Permission</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete this permission? This action cannot be undone.
              The user will immediately lose access to the associated resources.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleting}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              disabled={deleting}
              className="bg-red-600 hover:bg-red-700"
            >
              {deleting ? "Deleting..." : "Delete"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
