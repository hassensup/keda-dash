import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { User, Crown } from "lucide-react";

export default function UserList({ users, selectedUserId, onUserSelect, loading }) {
  if (loading) {
    return (
      <div className="text-center py-8 text-slate-400">
        <p className="text-sm">Loading users...</p>
      </div>
    );
  }

  if (users.length === 0) {
    return (
      <div className="text-center py-8 text-slate-400">
        <User className="w-8 h-8 mx-auto mb-2 opacity-20" />
        <p className="text-sm">No users found</p>
      </div>
    );
  }

  return (
    <ScrollArea className="h-[500px] pr-4">
      <div className="space-y-2">
        {users.map((user) => (
          <Button
            key={user.id}
            variant={selectedUserId === user.id ? "secondary" : "ghost"}
            className="w-full justify-start h-auto py-3 px-3"
            onClick={() => onUserSelect(user.id)}
            data-testid={`user-item-${user.id}`}
          >
            <div className="flex items-start gap-3 w-full">
              <div className="w-8 h-8 rounded-full bg-slate-100 flex items-center justify-center shrink-0 mt-0.5">
                {user.role === "admin" ? (
                  <Crown className="w-4 h-4 text-amber-600" />
                ) : (
                  <User className="w-4 h-4 text-slate-600" />
                )}
              </div>
              <div className="flex-1 text-left min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <p className="font-medium text-sm text-slate-900 truncate">
                    {user.name}
                  </p>
                  {user.role === "admin" && (
                    <Badge variant="outline" className="text-xs bg-amber-50 text-amber-700 border-amber-200">
                      Admin
                    </Badge>
                  )}
                </div>
                <p className="text-xs text-slate-500 truncate mb-1">{user.email}</p>
                <div className="flex items-center gap-2">
                  <Badge variant="secondary" className="text-xs">
                    {user.auth_provider}
                  </Badge>
                  <span className="text-xs text-slate-400">
                    {user.permission_count} {user.permission_count === 1 ? "permission" : "permissions"}
                  </span>
                </div>
              </div>
            </div>
          </Button>
        ))}
      </div>
    </ScrollArea>
  );
}
