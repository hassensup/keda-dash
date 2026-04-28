"""
Integration tests for authentication configuration module.

Tests real-world usage scenarios and integration with the application.
"""

import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from auth_config import get_auth_config, reload_auth_config


def test_production_like_config():
    """Test configuration that mimics production setup."""
    with patch.dict(os.environ, {
        "OKTA_ENABLED": "true",
        "LOCAL_AUTH_ENABLED": "true",
        "OKTA_DOMAIN": "mycompany.okta.com",
        "OKTA_CLIENT_ID": "0oa1234567890abcdef",
        "OKTA_CLIENT_SECRET": "super-secret-client-secret-xyz",
        "OKTA_REDIRECT_URI": "https://keda-dashboard.example.com/api/auth/okta/callback",
        "OKTA_SCOPES": "openid profile email groups",
        "TOKEN_EXPIRATION_HOURS": "12",
        "JWT_SECRET": "production-jwt-secret-key"
    }, clear=True):
        # Reset global config
        import auth_config
        auth_config._auth_config = None
        
        config = get_auth_config()
        
        # Verify dual authentication is enabled
        assert config.okta_enabled
        assert config.local_auth_enabled
        
        # Verify Okta configuration
        assert config.okta.domain == "mycompany.okta.com"
        assert config.okta.client_id == "0oa1234567890abcdef"
        assert config.okta.client_secret == "super-secret-client-secret-xyz"
        assert config.okta.redirect_uri == "https://keda-dashboard.example.com/api/auth/okta/callback"
        assert config.okta.scopes == "openid profile email groups"
        
        # Verify Okta endpoints
        assert config.okta.get_authorization_endpoint() == "https://mycompany.okta.com/oauth2/v1/authorize"
        assert config.okta.get_token_endpoint() == "https://mycompany.okta.com/oauth2/v1/token"
        assert config.okta.get_userinfo_endpoint() == "https://mycompany.okta.com/oauth2/v1/userinfo"
        assert config.okta.get_jwks_uri() == "https://mycompany.okta.com/oauth2/v1/keys"
        
        # Verify token expiration
        assert config.token_expiration_hours == 12


def test_local_only_config():
    """Test configuration with only local authentication."""
    with patch.dict(os.environ, {
        "OKTA_ENABLED": "false",
        "LOCAL_AUTH_ENABLED": "true",
        "TOKEN_EXPIRATION_HOURS": "24"
    }, clear=True):
        # Reset global config
        import auth_config
        auth_config._auth_config = None
        
        config = get_auth_config()
        
        # Verify only local auth is enabled
        assert not config.okta_enabled
        assert config.local_auth_enabled
        assert config.token_expiration_hours == 24


def test_okta_only_config():
    """Test configuration with only Okta authentication."""
    with patch.dict(os.environ, {
        "OKTA_ENABLED": "true",
        "LOCAL_AUTH_ENABLED": "false",
        "OKTA_DOMAIN": "test.okta.com",
        "OKTA_CLIENT_ID": "test-client-id",
        "OKTA_CLIENT_SECRET": "test-client-secret",
        "OKTA_REDIRECT_URI": "http://localhost:8000/callback"
    }, clear=True):
        # Reset global config
        import auth_config
        auth_config._auth_config = None
        
        config = get_auth_config()
        
        # Verify only Okta auth is enabled
        assert config.okta_enabled
        assert not config.local_auth_enabled


def test_config_reload_on_change():
    """Test that configuration can be reloaded when environment changes."""
    # Start with local auth only
    with patch.dict(os.environ, {
        "OKTA_ENABLED": "false",
        "LOCAL_AUTH_ENABLED": "true"
    }, clear=True):
        # Reset global config
        import auth_config
        auth_config._auth_config = None
        
        config1 = get_auth_config()
        assert not config1.okta_enabled
        assert config1.local_auth_enabled
    
    # Change to Okta enabled
    with patch.dict(os.environ, {
        "OKTA_ENABLED": "true",
        "LOCAL_AUTH_ENABLED": "true",
        "OKTA_DOMAIN": "test.okta.com",
        "OKTA_CLIENT_ID": "test-client-id",
        "OKTA_CLIENT_SECRET": "test-client-secret",
        "OKTA_REDIRECT_URI": "http://localhost:8000/callback"
    }, clear=True):
        config2 = reload_auth_config()
        assert config2.okta_enabled
        assert config2.local_auth_enabled


def test_graceful_degradation_on_missing_okta_config():
    """Test that system gracefully handles missing Okta config."""
    with patch.dict(os.environ, {
        "OKTA_ENABLED": "true",
        "LOCAL_AUTH_ENABLED": "true",
        "OKTA_DOMAIN": "test.okta.com",
        # Missing OKTA_CLIENT_ID, OKTA_CLIENT_SECRET, OKTA_REDIRECT_URI
    }, clear=True):
        # Reset global config
        import auth_config
        auth_config._auth_config = None
        
        config = get_auth_config()
        
        # Okta should be auto-disabled, local auth should still work
        assert not config.okta_enabled
        assert config.local_auth_enabled


def test_default_development_config():
    """Test default configuration for development environment."""
    with patch.dict(os.environ, {}, clear=True):
        # Reset global config
        import auth_config
        auth_config._auth_config = None
        
        config = get_auth_config()
        
        # Should default to local auth only
        assert not config.okta_enabled
        assert config.local_auth_enabled
        assert config.token_expiration_hours == 24
        assert config.okta.scopes == "openid profile email"


if __name__ == "__main__":
    # Run integration tests
    test_production_like_config()
    print("✓ Production-like config test passed")
    
    test_local_only_config()
    print("✓ Local-only config test passed")
    
    test_okta_only_config()
    print("✓ Okta-only config test passed")
    
    test_config_reload_on_change()
    print("✓ Config reload test passed")
    
    test_graceful_degradation_on_missing_okta_config()
    print("✓ Graceful degradation test passed")
    
    test_default_development_config()
    print("✓ Default development config test passed")
    
    print("\n✅ All integration tests passed!")
