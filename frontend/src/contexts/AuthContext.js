import { createContext, useContext, useState, useEffect, useCallback } from "react";
import api from "@/lib/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [permissions, setPermissions] = useState([]);
  const [loading, setLoading] = useState(true);

  const checkAuth = useCallback(async () => {
    const token = localStorage.getItem("token");
    if (!token) {
      setUser(null);
      setPermissions([]);
      setLoading(false);
      return;
    }
    try {
      const { data } = await api.get("/auth/me");
      setUser(data);
      setPermissions(data.permissions || []);
    } catch {
      setUser(null);
      setPermissions([]);
      localStorage.removeItem("token");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  const login = async (email, password) => {
    const { data } = await api.post("/auth/login", { email, password });
    if (data.token) {
      localStorage.setItem("token", data.token);
    }
    setUser(data);
    setPermissions(data.permissions || []);
    return data;
  };

  const loginWithOkta = () => {
    // Redirect to Okta login endpoint
    window.location.href = `${api.defaults.baseURL}/auth/okta/login`;
  };

  const logout = async () => {
    try {
      await api.post("/auth/logout");
    } catch { /* ignore */ }
    localStorage.removeItem("token");
    setUser(null);
    setPermissions([]);
  };

  const hasPermission = useCallback((action, namespace, objectName = null) => {
    // Admin users have all permissions
    if (user?.role === "admin") {
      return true;
    }

    // Check for matching permissions
    return permissions.some((perm) => {
      // Action must match or permission must be write (write includes read)
      const actionMatches = perm.action === action || (perm.action === "write" && action === "read");
      
      // Namespace must match
      const namespaceMatches = perm.namespace === namespace;
      
      // For namespace-scoped permissions, no object_name check needed
      if (perm.scope === "namespace") {
        return actionMatches && namespaceMatches;
      }
      
      // For object-scoped permissions, object_name must match if provided
      if (perm.scope === "object") {
        if (objectName) {
          return actionMatches && namespaceMatches && perm.object_name === objectName;
        }
        // If no objectName provided, just check namespace (for list operations)
        return actionMatches && namespaceMatches;
      }
      
      return false;
    });
  }, [user, permissions]);

  return (
    <AuthContext.Provider value={{ 
      user, 
      permissions, 
      loading, 
      login, 
      loginWithOkta, 
      logout, 
      checkAuth, 
      hasPermission 
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
