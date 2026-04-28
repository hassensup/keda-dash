# Authentication Configuration Module

## Overview

The `auth_config.py` module provides centralized configuration management for authentication settings in the KEDA Dashboard application. It supports dual authentication providers (local username/password and Okta SSO) with proper validation and error handling.

## Features

- **Dual Authentication Support**: Configure both local and Okta authentication
- **Environment-Based Configuration**: Load settings from environment variables
- **Validation**: Automatic validation of required configuration
- **Graceful Degradation**: Auto-disable Okta if configuration is incomplete
- **Type Safety**: Pydantic models for type checking and validation
- **Caching**: Configuration loaded once and cached for performance

## Requirements Addressed

This module implements the following requirements from the Okta Authentication RBAC spec:

- **3.1**: Load Okta configuration from environment variables
- **3.2**: Load feature flags (OKTA_ENABLED, LOCAL_AUTH_ENABLED)
- **3.3**: Validate required configuration when Okta is enabled
- **3.4**: Create OktaConfig Pydantic model
- **3.5**: Create AuthConfig Pydantic model
- **3.6**: Support enabling/disabling authentication providers
- **3.7**: Load configuration from environment variables
- **3.8**: Log errors and disable Okta if configuration is missing

## Usage

### Basic Usage

```python
from auth_config import get_auth_config

# Get configuration (loads and caches on first call)
config = get_auth_config()

# Check which authentication methods are enabled
if config.okta_enabled:
    print("Okta SSO is enabled")
if config.local_auth_enabled:
    print("Local authentication is enabled")

# Access Okta configuration
if config.okta.is_configured():
    auth_url = config.okta.get_authorization_endpoint()
    token_url = config.okta.get_token_endpoint()
```

### Reload Configuration

```python
from auth_config import reload_auth_config

# Reload configuration from environment (useful for testing)
config = reload_auth_config()
```

### Check Okta Configuration Status

```python
from auth_config import get_auth_config

config = get_auth_config()

if config.okta_enabled and config.okta.is_configured():
    # Okta is fully configured and ready to use
    print(f"Okta domain: {config.okta.domain}")
    print(f"Authorization endpoint: {config.okta.get_authorization_endpoint()}")
else:
    # Okta is not available
    print("Okta authentication is not available")
```

## Environment Variables

### Required for Okta

When `OKTA_ENABLED=true`, the following variables are required:

```bash
OKTA_DOMAIN=your-org.okta.com
OKTA_CLIENT_ID=your-okta-client-id
OKTA_CLIENT_SECRET=your-okta-client-secret
OKTA_REDIRECT_URI=http://localhost:8000/api/auth/okta/callback
```

### Optional Configuration

```bash
# Feature flags (defaults shown)
OKTA_ENABLED=false
LOCAL_AUTH_ENABLED=true

# Okta scopes (default: "openid profile email")
OKTA_SCOPES=openid profile email groups

# JWT token expiration in hours (default: 24, max: 168)
TOKEN_EXPIRATION_HOURS=24
```

## Configuration Models

### OktaConfig

Manages Okta OAuth2/OIDC configuration.

**Fields:**
- `domain`: Okta domain (e.g., "your-org.okta.com")
- `client_id`: Okta application client ID
- `client_secret`: Okta application client secret
- `redirect_uri`: OAuth2 callback URL
- `scopes`: OAuth2 scopes (default: "openid profile email")

**Methods:**
- `is_configured()`: Check if all required fields are present
- `get_authorization_endpoint()`: Get Okta authorization URL
- `get_token_endpoint()`: Get Okta token URL
- `get_userinfo_endpoint()`: Get Okta userinfo URL
- `get_jwks_uri()`: Get Okta JWKS URI for token validation

### AuthConfig

Manages application authentication configuration.

**Fields:**
- `okta_enabled`: Enable Okta SSO authentication
- `local_auth_enabled`: Enable local username/password authentication
- `okta`: OktaConfig instance
- `token_expiration_hours`: JWT token expiration (1-168 hours)

**Validation:**
- At least one authentication method must be enabled
- If Okta is enabled, required configuration must be present
- Token expiration must be between 1 and 168 hours

## Error Handling

### Graceful Degradation

If Okta is enabled but configuration is incomplete:
1. A warning is logged with details of missing configuration
2. Okta authentication is automatically disabled
3. Application continues with local authentication only

### Validation Errors

If no authentication methods are enabled:
- Raises `ValueError` with descriptive message
- Application startup will fail (by design)

## Examples

### Example 1: Production Configuration

```bash
# .env file
OKTA_ENABLED=true
LOCAL_AUTH_ENABLED=true
OKTA_DOMAIN=mycompany.okta.com
OKTA_CLIENT_ID=0oa1234567890abcdef
OKTA_CLIENT_SECRET=super-secret-client-secret
OKTA_REDIRECT_URI=https://keda-dashboard.example.com/api/auth/okta/callback
OKTA_SCOPES=openid profile email groups
TOKEN_EXPIRATION_HOURS=12
```

### Example 2: Development Configuration (Local Only)

```bash
# .env file
OKTA_ENABLED=false
LOCAL_AUTH_ENABLED=true
TOKEN_EXPIRATION_HOURS=24
```

### Example 3: Okta-Only Configuration

```bash
# .env file
OKTA_ENABLED=true
LOCAL_AUTH_ENABLED=false
OKTA_DOMAIN=test.okta.com
OKTA_CLIENT_ID=test-client-id
OKTA_CLIENT_SECRET=test-client-secret
OKTA_REDIRECT_URI=http://localhost:8000/api/auth/okta/callback
```

## Testing

### Run Unit Tests

```bash
python3 -m pytest tests/test_auth_config.py -v
```

### Run Integration Tests

```bash
python3 -m pytest tests/test_auth_config_integration.py -v
```

### Run Example Usage Script

```bash
python3 backend/example_auth_config_usage.py
```

## Integration with FastAPI

### Example: Auth Configuration Endpoint

```python
from fastapi import APIRouter
from auth_config import get_auth_config

router = APIRouter()

@router.get("/api/auth/config")
async def get_auth_configuration():
    """Get authentication configuration for frontend."""
    config = get_auth_config()
    return {
        "okta_enabled": config.okta_enabled,
        "local_auth_enabled": config.local_auth_enabled
    }
```

### Example: Conditional Okta Routes

```python
from fastapi import FastAPI
from auth_config import get_auth_config

app = FastAPI()
config = get_auth_config()

if config.okta_enabled:
    # Register Okta authentication routes
    from auth.okta_router import okta_router
    app.include_router(okta_router)

if config.local_auth_enabled:
    # Register local authentication routes
    from auth.local_router import local_router
    app.include_router(local_router)
```

## Logging

The module logs important configuration events:

- **INFO**: Configuration loaded successfully with summary
- **WARNING**: Okta auto-disabled due to missing configuration
- **ERROR**: No authentication methods enabled (before raising exception)

Example log output:

```
INFO - Authentication configuration loaded:
INFO -   - Local auth: enabled
INFO -   - Okta auth: disabled
INFO -   - Token expiration: 24 hours
```

## Security Considerations

1. **Environment Variables**: Store sensitive values (client secrets) in environment variables, never in code
2. **Validation**: Configuration is validated on load to prevent runtime errors
3. **Graceful Degradation**: Missing Okta config doesn't break the application
4. **Token Expiration**: Configurable token expiration with reasonable bounds (1-168 hours)

## Migration Guide

### Existing Applications

For applications upgrading to use this module:

1. Add new environment variables to `.env` file
2. Import and use `get_auth_config()` instead of direct `os.environ` access
3. Update authentication logic to check `config.okta_enabled` and `config.local_auth_enabled`
4. Test with both Okta enabled and disabled

### Example Migration

**Before:**
```python
okta_domain = os.environ.get("OKTA_DOMAIN")
if okta_domain:
    # Use Okta
    pass
```

**After:**
```python
from auth_config import get_auth_config

config = get_auth_config()
if config.okta_enabled:
    # Use Okta
    okta_domain = config.okta.domain
```

## Troubleshooting

### Issue: Okta is enabled but not working

**Solution**: Check that all required environment variables are set:
```bash
echo $OKTA_DOMAIN
echo $OKTA_CLIENT_ID
echo $OKTA_CLIENT_SECRET
echo $OKTA_REDIRECT_URI
```

### Issue: Configuration not updating

**Solution**: Use `reload_auth_config()` to force reload:
```python
from auth_config import reload_auth_config
config = reload_auth_config()
```

### Issue: No authentication methods available

**Solution**: Ensure at least one of `OKTA_ENABLED` or `LOCAL_AUTH_ENABLED` is true.

## API Reference

### Functions

#### `load_auth_config() -> AuthConfig`
Load authentication configuration from environment variables.

#### `get_auth_config() -> AuthConfig`
Get the global authentication configuration instance (cached).

#### `reload_auth_config() -> AuthConfig`
Reload authentication configuration from environment variables.

### Classes

#### `OktaConfig`
Okta OAuth2/OIDC configuration model.

#### `AuthConfig`
Application authentication configuration model.

## License

This module is part of the KEDA Dashboard project.
