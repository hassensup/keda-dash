# Database Migration Guide: Okta Authentication and RBAC

This guide provides step-by-step instructions for upgrading existing KEDA Dashboard deployments to support Okta authentication and Role-Based Access Control (RBAC).

## Overview

The Okta authentication and RBAC feature adds:
- **Dual authentication**: Support for both local (username/password) and Okta SSO authentication
- **Fine-grained permissions**: Namespace-scoped and object-scoped read/write permissions for ScaledObjects
- **Backward compatibility**: Existing users and authentication flows continue to work unchanged

## Migration Strategy

The migration is designed for **zero downtime** and follows a phased approach:

1. **Database schema changes** (automatic on startup)
2. **Backend deployment** (with Okta disabled initially)
3. **Validation** (verify existing functionality)
4. **Okta configuration** (optional, when ready)
5. **Permission assignment** (optional, as needed)

## Prerequisites

- Existing KEDA Dashboard deployment (any version)
- Database backup (recommended)
- Helm 3.x installed
- kubectl access to target cluster

## Phase 1: Backup (Recommended)

Before upgrading, create a backup of your database:

### PostgreSQL Backup

```bash
# Get database pod name
DB_POD=$(kubectl get pod -l app.kubernetes.io/name=keda-dashboard,app.kubernetes.io/component=postgresql -o jsonpath='{.items[0].metadata.name}')

# Create backup
kubectl exec $DB_POD -- pg_dump -U keda keda_dashboard > keda_dashboard_backup_$(date +%Y%m%d_%H%M%S).sql
```

### SQLite Backup

```bash
# Get backend pod name
BACKEND_POD=$(kubectl get pod -l app.kubernetes.io/name=keda-dashboard,app.kubernetes.io/component=backend -o jsonpath='{.items[0].metadata.name}')

# Copy database file
kubectl cp $BACKEND_POD:/app/keda_dashboard.db ./keda_dashboard_backup_$(date +%Y%m%d_%H%M%S).db
```

## Phase 2: Database Migrations

The application automatically applies database migrations on startup. The migrations are **idempotent** and safe to run multiple times.

### Migrations Applied

1. **002_add_auth_fields.sql**: Extends `users` table
   - Adds `auth_provider` column (default: 'local')
   - Adds `okta_subject` column (nullable, indexed)
   - Makes `password_hash` nullable (for Okta users)
   - Backfills existing users with `auth_provider='local'`

2. **003_create_permissions_table.sql**: Creates `permissions` table
   - Stores user permissions for RBAC
   - Foreign key to `users` table with CASCADE delete
   - Indexes for efficient permission lookups

### Manual Migration (Optional)

If you prefer to run migrations manually before deploying:

```bash
# Get database connection details from secret
DB_URL=$(kubectl get secret keda-dashboard-secret -o jsonpath='{.data.DATABASE_URL}' | base64 -d)

# Apply migrations (PostgreSQL)
kubectl exec -i $DB_POD -- psql $DB_URL < backend/migrations/002_add_auth_fields.sql
kubectl exec -i $DB_POD -- psql $DB_URL < backend/migrations/003_create_permissions_table.sql
```

### Verify Migrations

Check that migrations were applied successfully:

```bash
# PostgreSQL
kubectl exec $DB_POD -- psql -U keda keda_dashboard -c "\d users"
kubectl exec $DB_POD -- psql -U keda keda_dashboard -c "\d permissions"

# Expected output for users table should include:
# - auth_provider column
# - okta_subject column
# - password_hash (nullable)

# Expected output: permissions table should exist with columns:
# - id, user_id, action, scope, namespace, object_name, created_at, created_by
```

## Phase 3: Helm Chart Upgrade

### Update values.yaml

Create or update your `values.yaml` file with authentication configuration:

```yaml
# Minimal upgrade (Okta disabled, local auth only)
auth:
  jwt:
    secret: "<your-existing-jwt-secret-or-generate-new>"
    expirationHours: 24
  local:
    enabled: true
  okta:
    enabled: false

backend:
  config:
    adminEmail: "admin@example.com"
    adminPassword: "<your-admin-password>"
```

**IMPORTANT**: If you don't specify `auth.jwt.secret`, the default value will be used. For production, generate a secure random string:

```bash
openssl rand -base64 32
```

### Perform Helm Upgrade

```bash
# Upgrade with new values
helm upgrade keda-dashboard ./helm/keda-dashboard \
  --namespace keda-dashboard \
  --values values.yaml \
  --wait

# Monitor rollout
kubectl rollout status deployment/keda-dashboard-backend -n keda-dashboard
```

### Verify Deployment

1. **Check pod status**:
   ```bash
   kubectl get pods -n keda-dashboard
   ```

2. **Check application logs**:
   ```bash
   kubectl logs -l app.kubernetes.io/component=backend -n keda-dashboard --tail=50
   ```
   
   Look for:
   - ✅ "Applying database migrations..."
   - ✅ "Migration 002_add_auth_fields.sql applied successfully"
   - ✅ "Migration 003_create_permissions_table.sql applied successfully"
   - ✅ "Application startup complete"

3. **Check auth configuration**:
   ```bash
   kubectl port-forward svc/keda-dashboard-backend 8001:8001 -n keda-dashboard
   curl http://localhost:8001/api/auth/config
   ```
   
   Expected response:
   ```json
   {
     "okta_enabled": false,
     "local_auth_enabled": true
   }
   ```

## Phase 4: Validation

### Test Existing Functionality

1. **Test local login**:
   ```bash
   curl -X POST http://localhost:8001/api/auth/login \
     -H "Content-Type: application/json" \
     -d '{"email":"admin@example.com","password":"admin123"}'
   ```
   
   Expected: JWT token returned

2. **Test API access**:
   ```bash
   # Get token from login response
   TOKEN="<jwt-token>"
   
   curl http://localhost:8001/api/scaled-objects \
     -H "Authorization: Bearer $TOKEN"
   ```
   
   Expected: List of ScaledObjects (admin users see all objects)

3. **Test frontend**:
   - Navigate to dashboard URL
   - Login with existing credentials
   - Verify dashboard loads correctly
   - Verify ScaledObjects list displays

### Verify Backward Compatibility

- ✅ Existing users can log in with their passwords
- ✅ Existing API calls work unchanged
- ✅ Admin users have full access to all resources
- ✅ No 403 Forbidden errors for admin users

## Phase 5: Enable Okta (Optional)

Once you've verified the upgrade is successful, you can optionally enable Okta SSO.

### Prerequisites

1. **Create Okta Application**:
   - Application type: Web
   - Grant type: Authorization Code
   - Sign-in redirect URI: `https://your-domain.com/api/auth/okta/callback`
   - Assign users/groups in Okta

2. **Obtain Okta Credentials**:
   - Okta domain (e.g., `dev-12345.okta.com`)
   - Client ID
   - Client secret

### Update Helm Values

Update your `values.yaml`:

```yaml
auth:
  jwt:
    secret: "<your-jwt-secret>"
    expirationHours: 24
  local:
    enabled: true  # Keep local auth enabled during testing
  okta:
    enabled: true
    domain: "your-org.okta.com"
    clientId: "0oa1234567890abcdef"
    clientSecret: "<okta-client-secret>"
    redirectUri: "https://keda-dashboard.your-domain.com/api/auth/okta/callback"
    scopes: "openid profile email"
```

### Upgrade Helm Release

```bash
helm upgrade keda-dashboard ./helm/keda-dashboard \
  --namespace keda-dashboard \
  --values values.yaml \
  --wait
```

### Test Okta Authentication

1. **Check auth configuration**:
   ```bash
   curl http://localhost:8001/api/auth/config
   ```
   
   Expected:
   ```json
   {
     "okta_enabled": true,
     "local_auth_enabled": true
   }
   ```

2. **Test Okta login flow**:
   - Navigate to dashboard login page
   - Click "Sign in with Okta" button
   - Complete Okta authentication
   - Verify redirect back to dashboard
   - Verify user profile created in database

3. **Verify Okta user in database**:
   ```bash
   kubectl exec $DB_POD -- psql -U keda keda_dashboard -c \
     "SELECT email, name, auth_provider, okta_subject FROM users WHERE auth_provider='okta';"
   ```

## Phase 6: Permission Assignment (Optional)

By default, all users have **no permissions** (except admin users who bypass permission checks). You can grant permissions as needed.

### Grant Permissions via API

```bash
# Get admin token
ADMIN_TOKEN=$(curl -X POST http://localhost:8001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"admin123"}' \
  | jq -r '.token')

# Grant namespace read permission
curl -X POST http://localhost:8001/api/permissions \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "<user-uuid>",
    "action": "read",
    "scope": "namespace",
    "namespace": "production"
  }'

# Grant object write permission
curl -X POST http://localhost:8001/api/permissions \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "<user-uuid>",
    "action": "write",
    "scope": "object",
    "namespace": "staging",
    "object_name": "my-scaledobject"
  }'
```

### Grant Permissions via Database

```bash
# Get user ID
kubectl exec $DB_POD -- psql -U keda keda_dashboard -c \
  "SELECT id, email FROM users WHERE email='user@example.com';"

# Grant permission (replace UUIDs)
kubectl exec $DB_POD -- psql -U keda keda_dashboard -c \
  "INSERT INTO permissions (id, user_id, action, scope, namespace, object_name) 
   VALUES (
     gen_random_uuid(), 
     '<user-uuid>', 
     'read', 
     'namespace', 
     'production', 
     NULL
   );"
```

### Permission Examples

**Read-only access to production namespace**:
```json
{
  "action": "read",
  "scope": "namespace",
  "namespace": "production"
}
```

**Write access to staging namespace** (can create, edit, delete all objects):
```json
{
  "action": "write",
  "scope": "namespace",
  "namespace": "staging"
}
```

**Write access to specific object**:
```json
{
  "action": "write",
  "scope": "object",
  "namespace": "production",
  "object_name": "critical-app"
}
```

## Rollback Procedure

If issues occur, you can rollback to the previous version.

### Rollback Helm Release

```bash
# List releases
helm history keda-dashboard -n keda-dashboard

# Rollback to previous revision
helm rollback keda-dashboard -n keda-dashboard

# Or rollback to specific revision
helm rollback keda-dashboard <revision> -n keda-dashboard
```

### Rollback Database (If Needed)

The new database columns and tables do **not** break existing functionality, so database rollback is usually not necessary. However, if needed:

```bash
# Restore from backup (PostgreSQL)
kubectl exec -i $DB_POD -- psql -U keda keda_dashboard < keda_dashboard_backup.sql

# Or drop new tables/columns (PostgreSQL)
kubectl exec $DB_POD -- psql -U keda keda_dashboard -c "DROP TABLE IF EXISTS permissions;"
kubectl exec $DB_POD -- psql -U keda keda_dashboard -c "ALTER TABLE users DROP COLUMN IF EXISTS auth_provider;"
kubectl exec $DB_POD -- psql -U keda keda_dashboard -c "ALTER TABLE users DROP COLUMN IF EXISTS okta_subject;"
```

**Note**: Dropping columns will lose Okta user data. Only do this if you're certain you want to remove the feature.

## Troubleshooting

### Issue: "JWT_SECRET not configured"

**Cause**: `auth.jwt.secret` not set in values.yaml

**Solution**: Set `auth.jwt.secret` in values.yaml and upgrade:
```yaml
auth:
  jwt:
    secret: "<generate-secure-random-string>"
```

### Issue: "Okta authentication not configured"

**Cause**: `auth.okta.enabled=true` but Okta credentials missing

**Solution**: Set all required Okta fields in values.yaml:
```yaml
auth:
  okta:
    enabled: true
    domain: "your-org.okta.com"
    clientId: "<client-id>"
    clientSecret: "<client-secret>"
    redirectUri: "https://your-domain.com/api/auth/okta/callback"
```

### Issue: "Migration failed"

**Cause**: Database migration error

**Solution**:
1. Check application logs for specific error
2. Verify database connectivity
3. Check database user has sufficient permissions (CREATE TABLE, ALTER TABLE)
4. Try manual migration (see Phase 2)

### Issue: "403 Forbidden" errors after upgrade

**Cause**: User has no permissions (non-admin users)

**Solution**:
- Admin users should not see 403 errors (they bypass permission checks)
- For non-admin users, grant appropriate permissions (see Phase 6)
- Verify user role: `SELECT email, role FROM users;`

### Issue: Existing users can't log in

**Cause**: Unlikely, but check:
1. `LOCAL_AUTH_ENABLED` is set to `true`
2. Database migration completed successfully
3. `auth_provider` column was backfilled with 'local'

**Solution**:
```bash
# Verify users table
kubectl exec $DB_POD -- psql -U keda keda_dashboard -c \
  "SELECT email, auth_provider, password_hash IS NOT NULL as has_password FROM users;"

# All existing users should have:
# - auth_provider = 'local'
# - has_password = true
```

## Post-Migration Checklist

- [ ] Database backup created
- [ ] Helm upgrade completed successfully
- [ ] Pods are running and healthy
- [ ] Database migrations applied (check logs)
- [ ] Auth config endpoint returns expected values
- [ ] Existing users can log in with local credentials
- [ ] Admin users have full access to all resources
- [ ] API calls work unchanged
- [ ] Frontend dashboard loads correctly
- [ ] (Optional) Okta authentication tested and working
- [ ] (Optional) Permissions granted to non-admin users
- [ ] Documentation updated with new configuration

## Support

For issues or questions:
1. Check application logs: `kubectl logs -l app.kubernetes.io/component=backend -n keda-dashboard`
2. Check database state: `kubectl exec $DB_POD -- psql -U keda keda_dashboard`
3. Review [Environment Variables Documentation](../../ENVIRONMENT_VARIABLES.md)
4. Review [Okta Setup Guide](../../docs/OKTA_SETUP.md) (if using Okta)

## Additional Resources

- [Environment Variables Documentation](../../ENVIRONMENT_VARIABLES.md)
- [Permission Model Documentation](../../docs/PERMISSIONS.md)
- [Okta Setup Guide](../../docs/OKTA_SETUP.md)
- [API Documentation](../../docs/API.md)
- [Troubleshooting Guide](../../docs/TROUBLESHOOTING.md)
