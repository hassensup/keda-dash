import { useAuth } from "@/contexts/AuthContext";

/**
 * PermissionGate component - conditionally renders children based on user permissions
 * 
 * @param {string} action - The required action: 'read' or 'write'
 * @param {string} namespace - The namespace to check permission for
 * @param {string} [objectName] - Optional object name for object-scoped permissions
 * @param {React.ReactNode} children - Content to render if permission is granted
 * @param {React.ReactNode} [fallback] - Optional content to render if permission is denied
 */
export default function PermissionGate({ 
  action, 
  namespace, 
  objectName = null, 
  children, 
  fallback = null 
}) {
  const { hasPermission } = useAuth();

  if (!hasPermission(action, namespace, objectName)) {
    return fallback;
  }

  return <>{children}</>;
}
