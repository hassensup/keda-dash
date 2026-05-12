# Environment Variables

This document describes all environment variables used by the KEDA Dashboard application.

## Authentication Configuration

### JWT Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `JWT_SECRET` | **Yes** | None | Secret key for signing JWT tokens. Must be a long, random string. **CRITICAL**: Change this in production! |
| `TOKEN_EXPIRATION_HOURS` | No | `24` | JWT token expiration time in hours |

**Security Note**: The `JWT_SECRET` is critical for security. Use a cryptographically secure random string of at least 32 characters. If this value is compromised, all JWT tokens can be forged.

### Local Authentication

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LOCAL_AUTH_ENABLED` | No | `true` | Enable/disable local username/password authentication |
| `ADMIN_EMAIL` | No | `admin@example.com` | Default admin user email (created on first startup) |
| `ADMIN_PASSWORD` | No | `admin123` | Default admin user password. **CRITICAL**: Change this in production! |

**Migration Note**: Existing deployments have local authentication enabled by default. Disabling local auth (`LOCAL_AUTH_ENABLED=false`) requires Okta to be configured and enabled.

### Okta SSO Authentication

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OKTA_ENABLED` | No | `false` | Enable/disable Okta SSO authentication |
| `OKTA_DOMAIN` | Conditional* | None | Your Okta organization domain (e.g., `dev-12345.okta.com`) |
| `OKTA_CLIENT_ID` | Conditional* | None | Okta application client ID |
| `OKTA_CLIENT_SECRET` | Conditional* | None | Okta application client secret |
| `OKTA_REDIRECT_URI` | Conditional* | None | OAuth2 redirect URI (e.g., `https://your-domain.com/api/auth/okta/callback`) |
| `OKTA_SCOPES` | No | `openid profile email` | OAuth2 scopes to request from Okta |

**\*Conditional**: These variables are **required** when `OKTA_ENABLED=true`. The application will fail to start if Okta is enabled but these variables are not set.

**Setup Guide**: See [Okta Setup Guide](docs/OKTA_SETUP.md) for instructions on creating an Okta application and obtaining these values.

## Database Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | **Yes** | None | Database connection string (PostgreSQL or SQLite) |

**Format Examples**:
- PostgreSQL: `postgresql://user:password@host:5432/database`
- SQLite: `sqlite:///./keda_dashboard.db`

**Production Recommendation**: Use PostgreSQL for production deployments. SQLite is suitable for development and testing only.

## Application Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CORS_ORIGINS` | No | `*` | Comma-separated list of allowed CORS origins |
| `K8S_MODE` | No | `in-cluster` | Kubernetes client mode: `in-cluster` or `local` |

## Kubernetes Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `K8S_MODE` | No | `in-cluster` | How to connect to Kubernetes API: `in-cluster` (uses service account) or `local` (uses kubeconfig) |

## Configuration Examples

### Development (Local Auth Only)

```bash
# Required
JWT_SECRET=dev-secret-change-in-production
DATABASE_URL=sqlite:///./keda_dashboard.db

# Optional (defaults shown)
LOCAL_AUTH_ENABLED=true
OKTA_ENABLED=false
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=admin123
TOKEN_EXPIRATION_HOURS=24
CORS_ORIGINS=*
K8S_MODE=local
```

### Production (Local Auth + Okta SSO)

```bash
# Required
JWT_SECRET=<generate-secure-random-string-32-chars-minimum>
DATABASE_URL=postgresql://keda:secure-password@postgres:5432/keda_dashboard

# Authentication
LOCAL_AUTH_ENABLED=true
OKTA_ENABLED=true
OKTA_DOMAIN=your-org.okta.com
OKTA_CLIENT_ID=0oa1234567890abcdef
OKTA_CLIENT_SECRET=<okta-client-secret>
OKTA_REDIRECT_URI=https://keda-dashboard.your-domain.com/api/auth/okta/callback

# Admin user (change password!)
ADMIN_EMAIL=admin@your-domain.com
ADMIN_PASSWORD=<generate-secure-password>

# Optional
TOKEN_EXPIRATION_HOURS=24
CORS_ORIGINS=https://keda-dashboard.your-domain.com
K8S_MODE=in-cluster
```

### Production (Okta SSO Only)

```bash
# Required
JWT_SECRET=<generate-secure-random-string-32-chars-minimum>
DATABASE_URL=postgresql://keda:secure-password@postgres:5432/keda_dashboard

# Authentication (Okta only)
LOCAL_AUTH_ENABLED=false
OKTA_ENABLED=true
OKTA_DOMAIN=your-org.okta.com
OKTA_CLIENT_ID=0oa1234567890abcdef
OKTA_CLIENT_SECRET=<okta-client-secret>
OKTA_REDIRECT_URI=https://keda-dashboard.your-domain.com/api/auth/okta/callback

# Optional
TOKEN_EXPIRATION_HOURS=24
CORS_ORIGINS=https://keda-dashboard.your-domain.com
K8S_MODE=in-cluster
```

## Security Best Practices

1. **JWT_SECRET**: Generate using a cryptographically secure random generator:
   ```bash
   # Linux/Mac
   openssl rand -base64 32
   
   # Python
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

2. **ADMIN_PASSWORD**: Change the default admin password immediately after first login.

3. **OKTA_CLIENT_SECRET**: Store securely using Kubernetes secrets or a secret management system. Never commit to version control.

4. **DATABASE_URL**: Use strong passwords for database connections. Store credentials in Kubernetes secrets.

5. **CORS_ORIGINS**: In production, set to specific allowed origins instead of `*`.

## Helm Chart Configuration

When deploying with Helm, these environment variables are configured through `values.yaml`. See [Helm Chart Documentation](helm/keda-dashboard/README.md) for details.

Example Helm values:

```yaml
auth:
  jwt:
    secret: "<generate-secure-random-string>"
    expirationHours: 24
  local:
    enabled: true
  okta:
    enabled: true
    domain: "your-org.okta.com"
    clientId: "0oa1234567890abcdef"
    clientSecret: "<okta-client-secret>"
    redirectUri: "https://keda-dashboard.your-domain.com/api/auth/okta/callback"

backend:
  config:
    adminEmail: "admin@your-domain.com"
    adminPassword: "<generate-secure-password>"
```

## Validation

To verify your configuration is correct:

1. **Check auth configuration endpoint**:
   ```bash
   curl http://localhost:8001/api/auth/config
   ```
   
   Expected response:
   ```json
   {
     "okta_enabled": true,
     "local_auth_enabled": true
   }
   ```

2. **Check application logs** for configuration errors on startup.

3. **Test authentication flows**:
   - Local: POST to `/api/auth/login` with email/password
   - Okta: GET `/api/auth/okta/login` to initiate OAuth2 flow

## Troubleshooting

### "JWT_SECRET not configured"

**Cause**: `JWT_SECRET` environment variable is not set.

**Solution**: Set `JWT_SECRET` to a secure random string.

### "Okta authentication not configured"

**Cause**: `OKTA_ENABLED=true` but one or more Okta variables are missing.

**Solution**: Set all required Okta variables: `OKTA_DOMAIN`, `OKTA_CLIENT_ID`, `OKTA_CLIENT_SECRET`, `OKTA_REDIRECT_URI`.

### "Invalid Okta token"

**Cause**: Okta ID token validation failed.

**Possible reasons**:
- Incorrect `OKTA_DOMAIN`
- Incorrect `OKTA_CLIENT_ID`
- Token expired
- Token issued by different Okta org

**Solution**: Verify Okta configuration matches your Okta application settings.

### "Database connection failed"

**Cause**: Invalid `DATABASE_URL` or database not accessible.

**Solution**: Verify database connection string and ensure database is running and accessible.

## Migration from Previous Versions

If upgrading from a version without Okta support:

1. **No action required**: Okta is disabled by default (`OKTA_ENABLED=false`)
2. **Existing users continue to work**: Local authentication remains enabled
3. **Database migrations run automatically**: New columns and tables are created on startup
4. **To enable Okta**: Set Okta environment variables and set `OKTA_ENABLED=true`

See [Migration Guide](helm/keda-dashboard/MIGRATION_GUIDE.md) for detailed upgrade instructions.
