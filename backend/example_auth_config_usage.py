"""
Example usage of the authentication configuration module.

This script demonstrates how to use the auth_config module in the application.
"""

import os
from auth_config import get_auth_config, OktaConfig, AuthConfig

def main():
    """Demonstrate auth_config usage."""
    
    print("=" * 60)
    print("Authentication Configuration Module - Usage Examples")
    print("=" * 60)
    
    # Example 1: Get current configuration
    print("\n1. Getting current configuration:")
    print("-" * 60)
    config = get_auth_config()
    print(f"   Okta enabled: {config.okta_enabled}")
    print(f"   Local auth enabled: {config.local_auth_enabled}")
    print(f"   Token expiration: {config.token_expiration_hours} hours")
    
    if config.okta_enabled:
        print(f"   Okta domain: {config.okta.domain}")
        print(f"   Okta scopes: {config.okta.scopes}")
    
    # Example 2: Check if Okta is configured
    print("\n2. Checking Okta configuration status:")
    print("-" * 60)
    if config.okta.is_configured():
        print("   ✓ Okta is fully configured")
        print(f"   Authorization endpoint: {config.okta.get_authorization_endpoint()}")
        print(f"   Token endpoint: {config.okta.get_token_endpoint()}")
        print(f"   Userinfo endpoint: {config.okta.get_userinfo_endpoint()}")
        print(f"   JWKS URI: {config.okta.get_jwks_uri()}")
    else:
        print("   ✗ Okta is not fully configured")
        print("   Missing required configuration:")
        if not config.okta.domain:
            print("     - OKTA_DOMAIN")
        if not config.okta.client_id:
            print("     - OKTA_CLIENT_ID")
        if not config.okta.client_secret:
            print("     - OKTA_CLIENT_SECRET")
        if not config.okta.redirect_uri:
            print("     - OKTA_REDIRECT_URI")
    
    # Example 3: Determine which authentication methods are available
    print("\n3. Available authentication methods:")
    print("-" * 60)
    methods = []
    if config.local_auth_enabled:
        methods.append("Local (username/password)")
    if config.okta_enabled:
        methods.append("Okta SSO")
    
    if methods:
        print(f"   Available: {', '.join(methods)}")
    else:
        print("   ⚠ WARNING: No authentication methods enabled!")
    
    # Example 4: Configuration for API endpoint
    print("\n4. Configuration for /api/auth/config endpoint:")
    print("-" * 60)
    api_config = {
        "okta_enabled": config.okta_enabled,
        "local_auth_enabled": config.local_auth_enabled
    }
    print(f"   Response: {api_config}")
    
    # Example 5: Environment variables reference
    print("\n5. Environment variables reference:")
    print("-" * 60)
    print("   Required for Okta:")
    print("     OKTA_ENABLED=true")
    print("     OKTA_DOMAIN=your-org.okta.com")
    print("     OKTA_CLIENT_ID=your-client-id")
    print("     OKTA_CLIENT_SECRET=your-client-secret")
    print("     OKTA_REDIRECT_URI=http://localhost:8000/api/auth/okta/callback")
    print("\n   Optional:")
    print("     OKTA_SCOPES=openid profile email (default)")
    print("     LOCAL_AUTH_ENABLED=true (default)")
    print("     TOKEN_EXPIRATION_HOURS=24 (default)")
    
    print("\n" + "=" * 60)
    print("Configuration loaded successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
