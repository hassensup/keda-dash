# KEDA Dashboard Helm Chart

This Helm chart deploys the KEDA Dashboard application with support for Okta SSO authentication and Role-Based Access Control (RBAC).

## Features

- **Dual Authentication**: Local username/password and Okta SSO
- **Fine-Grained RBAC**: Namespace-scoped and object-scoped permissions
- **PostgreSQL Database**: Persistent storage for users and permissions
- **Kubernetes RBAC**: ServiceAccount with appropriate permissions
- **Ingress Support**: Optional ingress configuration
- **Health Checks**: Liveness and readiness probes

## Prerequisites

- Kubernetes 1.19+
- Helm 3.x
- KEDA installed in the cluster (for ScaledObject management)

## Installation

### Quick Start (Development)

```bash
# Install with default values (local auth only, SQLite)
helm install keda-dashboard ./helm/keda-dashboard \
  --namespace keda-dashboard \
  --create-namespace
```

### Production Installation

```bash
# Create values file
cat > production-values.yaml <<EOF
auth:
  jwt:
    secret: "$(openssl rand -base64 32)"
    expirationHours: 24
  local:
    enabled: true
  okta:
    enabled: false

backend:
  image:
    repository: your-registry/keda-dashboard-backend
    tag: "v1.0.0"
  config:
    adminEmail: "admin@your-domain.com"
    adminPassword: "$(openssl rand -base64 16)"
    corsOrigins: "https://keda-dashboard.your-domain.com"

postgresql:
  enabled: true
  auth:
    password: "$(openssl rand -base64 16)"
  persistence:
    enabled: true
    size: 5Gi

ingress:
  enabled: true
  className: "nginx"
  hosts:
    - host: keda-dashboard.your-domain.com
      paths:
        - path: /api
          serviceName: backend
          port: 8001
EOF

# Install
helm install keda-dashboard ./helm/keda-dashboard \
  --namespace keda-dashboard \
  --create-namespace \
  --values production-values.yaml
```

### Production with Okta SSO

```bash
# Add Okta configuration to values file
cat > production-okta-values.yaml <<EOF
auth:
  jwt:
    secret: "$(openssl rand -base64 32)"
  local:
    enabled: true
  okta:
    enabled: true
    domain: "your-org.okta.com"
    clientId: "0oa1234567890abcdef"
    clientSecret: "<your-okta-client-secret>"
    redirectUri: "https://keda-dashboard.your-domain.com/api/auth/okta/callback"

backend:
  image:
    repository: your-registry/keda-dashboard-backend
    tag: "v1.0.0"
  config:
    adminEmail: "admin@your-domain.com"
    adminPassword: "<secure-password>"

postgresql:
  enabled: true
  auth:
    password: "<secure-password>"
  persistence:
    enabled: true
    size: 5Gi

ingress:
  enabled: true
  className: "nginx"
  hosts:
    - host: keda-dashboard.your-domain.com
      paths:
        - path: /api
          serviceName: backend
          port: 8001
EOF

# Install
helm install keda-dashboard ./helm/keda-dashboard \
  --namespace keda-dashboard \
  --create-namespace \
  --values production-okta-values.yaml
```

## Configuration

### Authentication Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `auth.jwt.secret` | **REQUIRED** JWT signing secret (change in production!) | `change-me-in-production-use-a-long-random-string` |
| `auth.jwt.expirationHours` | JWT token expiration in hours | `24` |
| `auth.local.enabled` | Enable local username/password authentication | `true` |
| `auth.okta.enabled` | Enable Okta SSO authentication | `false` |
| `auth.okta.domain` | Okta organization domain (required if okta.enabled=true) | `""` |
| `auth.okta.clientId` | Okta application client ID (required if okta.enabled=true) | `""` |
| `auth.okta.clientSecret` | Okta application client secret (required if okta.enabled=true) | `""` |
| `auth.okta.redirectUri` | OAuth2 redirect URI (required if okta.enabled=true) | `""` |
| `auth.okta.scopes` | OAuth2 scopes to request | `openid profile email` |

### Backend Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `backend.image.repository` | Backend image repository | `keda-dashboard-backend` |
| `backend.image.tag` | Backend image tag | `latest` |
| `backend.image.pullPolicy` | Image pull policy | `IfNotPresent` |
| `backend.service.port` | Backend service port | `8001` |
| `backend.resources.limits.cpu` | CPU limit | `500m` |
| `backend.resources.limits.memory` | Memory limit | `512Mi` |
| `backend.resources.requests.cpu` | CPU request | `100m` |
| `backend.resources.requests.memory` | Memory request | `128Mi` |
| `backend.config.adminEmail` | Default admin user email | `admin@example.com` |
| `backend.config.adminPassword` | Default admin user password (change in production!) | `admin123` |
| `backend.config.corsOrigins` | CORS allowed origins | `*` |
| `backend.config.k8sMode` | Kubernetes client mode (in-cluster or local) | `in-cluster` |

### PostgreSQL Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `postgresql.enabled` | Enable PostgreSQL deployment | `true` |
| `postgresql.image.repository` | PostgreSQL image repository | `postgres` |
| `postgresql.image.tag` | PostgreSQL image tag | `16-alpine` |
| `postgresql.auth.username` | PostgreSQL username | `keda` |
| `postgresql.auth.password` | PostgreSQL password (change in production!) | `keda-secret` |
| `postgresql.auth.database` | PostgreSQL database name | `keda_dashboard` |
| `postgresql.persistence.enabled` | Enable persistent storage | `true` |
| `postgresql.persistence.size` | Persistent volume size | `1Gi` |
| `postgresql.persistence.storageClass` | Storage class name | `""` (default) |
| `postgresql.resources.limits.cpu` | CPU limit | `500m` |
| `postgresql.resources.limits.memory` | Memory limit | `512Mi` |
| `postgresql.resources.requests.cpu` | CPU request | `100m` |
| `postgresql.resources.requests.memory` | Memory request | `128Mi` |

### Ingress Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `ingress.enabled` | Enable ingress | `false` |
| `ingress.className` | Ingress class name | `nginx` |
| `ingress.annotations` | Ingress annotations | `{}` |
| `ingress.hosts[0].host` | Hostname | `keda-dashboard.local` |
| `ingress.hosts[0].paths[0].path` | Path | `/api` |
| `ingress.hosts[0].paths[0].serviceName` | Service name | `backend` |
| `ingress.hosts[0].paths[0].port` | Service port | `8001` |
| `ingress.tls` | TLS configuration | `[]` |

### RBAC Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `rbac.create` | Create RBAC resources | `true` |
| `serviceAccount.create` | Create service account | `true` |
| `serviceAccount.name` | Service account name | `""` (auto-generated) |
| `serviceAccount.annotations` | Service account annotations | `{}` |

### Other Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `replicaCount` | Number of backend replicas | `1` |
| `imagePullSecrets` | Image pull secrets | `[]` |
| `nameOverride` | Override chart name | `""` |
| `fullnameOverride` | Override full name | `""` |
| `nodeSelector` | Node selector | `{}` |
| `tolerations` | Tolerations | `[]` |
| `affinity` | Affinity rules | `{}` |

## Upgrading

### From Previous Versions (Without Okta/RBAC)

See [MIGRATION_GUIDE.md](./MIGRATION_GUIDE.md) for detailed upgrade instructions.

Quick upgrade:

```bash
# Backup database first!
# Then upgrade with new values
helm upgrade keda-dashboard ./helm/keda-dashboard \
  --namespace keda-dashboard \
  --values values.yaml \
  --wait
```

Database migrations run automatically on startup.

### Changing Configuration

```bash
# Update values.yaml
# Then upgrade
helm upgrade keda-dashboard ./helm/keda-dashboard \
  --namespace keda-dashboard \
  --values values.yaml \
  --wait
```

## Uninstallation

```bash
# Uninstall release
helm uninstall keda-dashboard --namespace keda-dashboard

# Delete namespace (optional)
kubectl delete namespace keda-dashboard
```

**Note**: This will delete all data including users and permissions. Backup your database before uninstalling if you need to preserve data.

## Security Considerations

### Production Checklist

- [ ] Change `auth.jwt.secret` to a secure random string (32+ characters)
- [ ] Change `backend.config.adminPassword` to a secure password
- [ ] Change `postgresql.auth.password` to a secure password
- [ ] Set `backend.config.corsOrigins` to specific allowed origins (not `*`)
- [ ] Enable TLS for ingress
- [ ] Use a secret management system for sensitive values (e.g., Sealed Secrets, External Secrets)
- [ ] Enable PostgreSQL persistence with appropriate storage class
- [ ] Configure resource limits based on your workload
- [ ] Review and adjust RBAC permissions as needed

### Generating Secure Secrets

```bash
# JWT secret (32 characters)
openssl rand -base64 32

# Admin password (16 characters)
openssl rand -base64 16

# PostgreSQL password (16 characters)
openssl rand -base64 16
```

### Using External Secrets

Instead of storing secrets in values.yaml, use Kubernetes secrets:

```bash
# Create secret manually
kubectl create secret generic keda-dashboard-auth \
  --from-literal=jwt-secret="$(openssl rand -base64 32)" \
  --from-literal=admin-password="$(openssl rand -base64 16)" \
  --from-literal=okta-client-secret="<your-okta-secret>" \
  --namespace keda-dashboard

# Reference in values.yaml (requires chart modification)
# Or use External Secrets Operator / Sealed Secrets
```

## Troubleshooting

### Check Pod Status

```bash
kubectl get pods -n keda-dashboard
kubectl logs -l app.kubernetes.io/component=backend -n keda-dashboard
```

### Check Database Migrations

```bash
# View logs for migration status
kubectl logs -l app.kubernetes.io/component=backend -n keda-dashboard | grep -i migration
```

### Test Authentication

```bash
# Port forward to backend
kubectl port-forward svc/keda-dashboard-backend 8001:8001 -n keda-dashboard

# Check auth config
curl http://localhost:8001/api/auth/config

# Test login
curl -X POST http://localhost:8001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"admin123"}'
```

### Common Issues

**Issue**: "JWT_SECRET not configured"
- **Solution**: Set `auth.jwt.secret` in values.yaml

**Issue**: "Okta authentication not configured"
- **Solution**: Set all required Okta fields when `auth.okta.enabled=true`

**Issue**: "Database connection failed"
- **Solution**: Check PostgreSQL pod status and credentials

**Issue**: "403 Forbidden" errors
- **Solution**: Check user permissions (admin users bypass permission checks)

See [MIGRATION_GUIDE.md](./MIGRATION_GUIDE.md) for more troubleshooting tips.

## Examples

### Example 1: Development Setup

```yaml
# dev-values.yaml
auth:
  jwt:
    secret: "dev-secret-not-for-production"
  local:
    enabled: true
  okta:
    enabled: false

backend:
  config:
    adminEmail: "admin@localhost"
    adminPassword: "admin"
    corsOrigins: "*"
    k8sMode: "local"

postgresql:
  enabled: false  # Use SQLite for development
```

### Example 2: Production with Local Auth Only

```yaml
# prod-local-values.yaml
auth:
  jwt:
    secret: "<generate-secure-random-string>"
  local:
    enabled: true
  okta:
    enabled: false

backend:
  image:
    repository: your-registry/keda-dashboard-backend
    tag: "v1.0.0"
  config:
    adminEmail: "admin@your-domain.com"
    adminPassword: "<secure-password>"
    corsOrigins: "https://keda-dashboard.your-domain.com"

postgresql:
  enabled: true
  auth:
    password: "<secure-password>"
  persistence:
    enabled: true
    size: 5Gi
    storageClass: "fast-ssd"

ingress:
  enabled: true
  className: "nginx"
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
  hosts:
    - host: keda-dashboard.your-domain.com
      paths:
        - path: /api
          serviceName: backend
          port: 8001
  tls:
    - secretName: keda-dashboard-tls
      hosts:
        - keda-dashboard.your-domain.com
```

### Example 3: Production with Okta SSO

```yaml
# prod-okta-values.yaml
auth:
  jwt:
    secret: "<generate-secure-random-string>"
  local:
    enabled: true  # Keep local auth as backup
  okta:
    enabled: true
    domain: "your-org.okta.com"
    clientId: "0oa1234567890abcdef"
    clientSecret: "<okta-client-secret>"
    redirectUri: "https://keda-dashboard.your-domain.com/api/auth/okta/callback"

backend:
  image:
    repository: your-registry/keda-dashboard-backend
    tag: "v1.0.0"
  config:
    adminEmail: "admin@your-domain.com"
    adminPassword: "<secure-password>"
    corsOrigins: "https://keda-dashboard.your-domain.com"

postgresql:
  enabled: true
  auth:
    password: "<secure-password>"
  persistence:
    enabled: true
    size: 10Gi
    storageClass: "fast-ssd"

ingress:
  enabled: true
  className: "nginx"
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
  hosts:
    - host: keda-dashboard.your-domain.com
      paths:
        - path: /api
          serviceName: backend
          port: 8001
  tls:
    - secretName: keda-dashboard-tls
      hosts:
        - keda-dashboard.your-domain.com
```

## Additional Resources

- [Migration Guide](./MIGRATION_GUIDE.md) - Upgrading from previous versions
- [Environment Variables](../../ENVIRONMENT_VARIABLES.md) - Complete environment variable reference
- [Okta Setup Guide](../../docs/OKTA_SETUP.md) - Setting up Okta application
- [Permission Model](../../docs/PERMISSIONS.md) - Understanding RBAC permissions
- [API Documentation](../../docs/API.md) - API endpoint reference

## Support

For issues or questions:
1. Check application logs
2. Review troubleshooting section above
3. Check [Migration Guide](./MIGRATION_GUIDE.md) for upgrade issues
4. Review [Environment Variables](../../ENVIRONMENT_VARIABLES.md) documentation
