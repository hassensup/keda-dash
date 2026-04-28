"""
Unit tests for authentication configuration module.

Tests configuration loading, validation, and error handling.
"""

import os
import pytest
from unittest.mock import patch
from pydantic import ValidationError

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from auth_config import (
    OktaConfig,
    AuthConfig,
    load_auth_config,
    get_auth_config,
    reload_auth_config
)


class TestOktaConfig:
    """Test OktaConfig model."""
    
    def test_okta_config_defaults(self):
        """Test OktaConfig with default values."""
        config = OktaConfig()
        assert config.domain is None
        assert config.client_id is None
        assert config.client_secret is None
        assert config.redirect_uri is None
        assert config.scopes == "openid profile email"
        assert not config.is_configured()
    
    def test_okta_config_fully_configured(self):
        """Test OktaConfig with all required fields."""
        config = OktaConfig(
            domain="test.okta.com",
            client_id="test-client-id",
            client_secret="test-client-secret",
            redirect_uri="http://localhost:8000/callback"
        )
        assert config.is_configured()
        assert config.domain == "test.okta.com"
        assert config.client_id == "test-client-id"
        assert config.client_secret == "test-client-secret"
        assert config.redirect_uri == "http://localhost:8000/callback"
    
    def test_okta_config_partially_configured(self):
        """Test OktaConfig with missing required fields."""
        config = OktaConfig(
            domain="test.okta.com",
            client_id="test-client-id"
            # Missing client_secret and redirect_uri
        )
        assert not config.is_configured()
    
    def test_okta_config_empty_domain(self):
        """Test OktaConfig with empty domain string."""
        config = OktaConfig(domain="   ")
        assert config.domain is None
    
    def test_get_authorization_endpoint(self):
        """Test authorization endpoint URL generation."""
        config = OktaConfig(domain="test.okta.com")
        assert config.get_authorization_endpoint() == "https://test.okta.com/oauth2/v1/authorize"
    
    def test_get_token_endpoint(self):
        """Test token endpoint URL generation."""
        config = OktaConfig(domain="test.okta.com")
        assert config.get_token_endpoint() == "https://test.okta.com/oauth2/v1/token"
    
    def test_get_userinfo_endpoint(self):
        """Test userinfo endpoint URL generation."""
        config = OktaConfig(domain="test.okta.com")
        assert config.get_userinfo_endpoint() == "https://test.okta.com/oauth2/v1/userinfo"
    
    def test_get_jwks_uri(self):
        """Test JWKS URI generation."""
        config = OktaConfig(domain="test.okta.com")
        assert config.get_jwks_uri() == "https://test.okta.com/oauth2/v1/keys"
    
    def test_get_endpoints_without_domain(self):
        """Test endpoint methods raise error when domain not configured."""
        config = OktaConfig()
        with pytest.raises(ValueError, match="Okta domain not configured"):
            config.get_authorization_endpoint()
        with pytest.raises(ValueError, match="Okta domain not configured"):
            config.get_token_endpoint()
        with pytest.raises(ValueError, match="Okta domain not configured"):
            config.get_userinfo_endpoint()
        with pytest.raises(ValueError, match="Okta domain not configured"):
            config.get_jwks_uri()
    
    def test_custom_scopes(self):
        """Test OktaConfig with custom scopes."""
        config = OktaConfig(scopes="openid profile email groups")
        assert config.scopes == "openid profile email groups"


class TestAuthConfig:
    """Test AuthConfig model."""
    
    def test_auth_config_defaults(self):
        """Test AuthConfig with default values."""
        config = AuthConfig()
        assert not config.okta_enabled
        assert config.local_auth_enabled
        assert config.token_expiration_hours == 24
        assert isinstance(config.okta, OktaConfig)
    
    def test_auth_config_local_only(self):
        """Test AuthConfig with only local auth enabled."""
        config = AuthConfig(
            okta_enabled=False,
            local_auth_enabled=True
        )
        assert not config.okta_enabled
        assert config.local_auth_enabled
    
    def test_auth_config_okta_enabled_but_not_configured(self):
        """Test AuthConfig with Okta enabled but missing configuration."""
        # Should auto-disable Okta and log warning
        config = AuthConfig(
            okta_enabled=True,
            local_auth_enabled=True,
            okta=OktaConfig()  # Not configured
        )
        # Okta should be auto-disabled due to missing config
        assert not config.okta_enabled
        assert config.local_auth_enabled
    
    def test_auth_config_okta_fully_configured(self):
        """Test AuthConfig with Okta enabled and fully configured."""
        okta_config = OktaConfig(
            domain="test.okta.com",
            client_id="test-client-id",
            client_secret="test-client-secret",
            redirect_uri="http://localhost:8000/callback"
        )
        config = AuthConfig(
            okta_enabled=True,
            local_auth_enabled=True,
            okta=okta_config
        )
        assert config.okta_enabled
        assert config.local_auth_enabled
        assert config.okta.is_configured()
    
    def test_auth_config_no_auth_methods(self):
        """Test AuthConfig fails when no auth methods enabled."""
        with pytest.raises(ValueError, match="At least one authentication method must be enabled"):
            AuthConfig(
                okta_enabled=False,
                local_auth_enabled=False
            )
    
    def test_auth_config_custom_token_expiration(self):
        """Test AuthConfig with custom token expiration."""
        config = AuthConfig(token_expiration_hours=48)
        assert config.token_expiration_hours == 48
    
    def test_auth_config_token_expiration_bounds(self):
        """Test AuthConfig token expiration validation."""
        # Valid range: 1-168 hours
        config = AuthConfig(token_expiration_hours=1)
        assert config.token_expiration_hours == 1
        
        config = AuthConfig(token_expiration_hours=168)
        assert config.token_expiration_hours == 168
        
        # Invalid: less than 1
        with pytest.raises(ValidationError):
            AuthConfig(token_expiration_hours=0)
        
        # Invalid: more than 168
        with pytest.raises(ValidationError):
            AuthConfig(token_expiration_hours=169)


class TestLoadAuthConfig:
    """Test load_auth_config function."""
    
    def test_load_default_config(self):
        """Test loading config with default environment variables."""
        with patch.dict(os.environ, {}, clear=True):
            config = load_auth_config()
            assert not config.okta_enabled
            assert config.local_auth_enabled
            assert config.token_expiration_hours == 24
    
    def test_load_okta_enabled_without_config(self):
        """Test loading config with Okta enabled but missing configuration."""
        with patch.dict(os.environ, {
            "OKTA_ENABLED": "true",
            "LOCAL_AUTH_ENABLED": "true"
        }, clear=True):
            config = load_auth_config()
            # Okta should be auto-disabled
            assert not config.okta_enabled
            assert config.local_auth_enabled
    
    def test_load_okta_fully_configured(self):
        """Test loading config with Okta fully configured."""
        with patch.dict(os.environ, {
            "OKTA_ENABLED": "true",
            "LOCAL_AUTH_ENABLED": "true",
            "OKTA_DOMAIN": "test.okta.com",
            "OKTA_CLIENT_ID": "test-client-id",
            "OKTA_CLIENT_SECRET": "test-client-secret",
            "OKTA_REDIRECT_URI": "http://localhost:8000/callback"
        }, clear=True):
            config = load_auth_config()
            assert config.okta_enabled
            assert config.local_auth_enabled
            assert config.okta.domain == "test.okta.com"
            assert config.okta.client_id == "test-client-id"
            assert config.okta.client_secret == "test-client-secret"
            assert config.okta.redirect_uri == "http://localhost:8000/callback"
    
    def test_load_custom_scopes(self):
        """Test loading config with custom Okta scopes."""
        with patch.dict(os.environ, {
            "OKTA_ENABLED": "true",
            "OKTA_DOMAIN": "test.okta.com",
            "OKTA_CLIENT_ID": "test-client-id",
            "OKTA_CLIENT_SECRET": "test-client-secret",
            "OKTA_REDIRECT_URI": "http://localhost:8000/callback",
            "OKTA_SCOPES": "openid profile email groups"
        }, clear=True):
            config = load_auth_config()
            assert config.okta.scopes == "openid profile email groups"
    
    def test_load_custom_token_expiration(self):
        """Test loading config with custom token expiration."""
        with patch.dict(os.environ, {
            "TOKEN_EXPIRATION_HOURS": "48"
        }, clear=True):
            config = load_auth_config()
            assert config.token_expiration_hours == 48
    
    def test_load_invalid_token_expiration(self):
        """Test loading config with invalid token expiration falls back to default."""
        with patch.dict(os.environ, {
            "TOKEN_EXPIRATION_HOURS": "invalid"
        }, clear=True):
            config = load_auth_config()
            assert config.token_expiration_hours == 24  # Default
    
    def test_load_boolean_variations(self):
        """Test loading config with various boolean string formats."""
        # Test "true"
        with patch.dict(os.environ, {"OKTA_ENABLED": "true"}, clear=True):
            config = load_auth_config()
            assert not config.okta_enabled  # Disabled due to missing config
        
        # Test "1"
        with patch.dict(os.environ, {"LOCAL_AUTH_ENABLED": "1"}, clear=True):
            config = load_auth_config()
            assert config.local_auth_enabled
        
        # Test "yes"
        with patch.dict(os.environ, {"LOCAL_AUTH_ENABLED": "yes"}, clear=True):
            config = load_auth_config()
            assert config.local_auth_enabled
        
        # Test "false"
        with patch.dict(os.environ, {"LOCAL_AUTH_ENABLED": "false"}, clear=True):
            # This should fail because no auth methods would be enabled
            with pytest.raises(ValueError):
                load_auth_config()
        
        # Test "0"
        with patch.dict(os.environ, {"OKTA_ENABLED": "0"}, clear=True):
            config = load_auth_config()
            assert not config.okta_enabled
    
    def test_load_local_auth_disabled_okta_enabled(self):
        """Test loading config with local auth disabled and Okta enabled."""
        with patch.dict(os.environ, {
            "OKTA_ENABLED": "true",
            "LOCAL_AUTH_ENABLED": "false",
            "OKTA_DOMAIN": "test.okta.com",
            "OKTA_CLIENT_ID": "test-client-id",
            "OKTA_CLIENT_SECRET": "test-client-secret",
            "OKTA_REDIRECT_URI": "http://localhost:8000/callback"
        }, clear=True):
            config = load_auth_config()
            assert config.okta_enabled
            assert not config.local_auth_enabled


class TestGetAuthConfig:
    """Test get_auth_config and reload_auth_config functions."""
    
    def test_get_auth_config_caching(self):
        """Test that get_auth_config caches the configuration."""
        with patch.dict(os.environ, {}, clear=True):
            # Reset global config
            import auth_config
            auth_config._auth_config = None
            
            config1 = get_auth_config()
            config2 = get_auth_config()
            
            # Should return the same instance
            assert config1 is config2
    
    def test_reload_auth_config(self):
        """Test that reload_auth_config reloads from environment."""
        with patch.dict(os.environ, {"TOKEN_EXPIRATION_HOURS": "24"}, clear=True):
            # Reset global config
            import auth_config
            auth_config._auth_config = None
            
            config1 = get_auth_config()
            assert config1.token_expiration_hours == 24
            
            # Change environment
            os.environ["TOKEN_EXPIRATION_HOURS"] = "48"
            
            # get_auth_config should still return cached config
            config2 = get_auth_config()
            assert config2.token_expiration_hours == 24
            
            # reload_auth_config should reload from environment
            config3 = reload_auth_config()
            assert config3.token_expiration_hours == 48
            
            # Subsequent get_auth_config should return new config
            config4 = get_auth_config()
            assert config4.token_expiration_hours == 48


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_okta_config_with_whitespace_values(self):
        """Test OktaConfig handles whitespace in values."""
        config = OktaConfig(
            domain="  test.okta.com  ",
            client_id="  test-client-id  ",
            client_secret="  test-secret  ",
            redirect_uri="  http://localhost:8000/callback  "
        )
        # Pydantic should preserve whitespace (validation happens at AuthConfig level)
        assert config.domain == "  test.okta.com  "
    
    def test_auth_config_with_empty_okta_fields(self):
        """Test AuthConfig with empty Okta fields."""
        okta_config = OktaConfig(
            domain="",
            client_id="",
            client_secret="",
            redirect_uri=""
        )
        config = AuthConfig(
            okta_enabled=True,
            okta=okta_config
        )
        # Okta should be auto-disabled
        assert not config.okta_enabled
    
    def test_load_config_with_missing_env_vars(self):
        """Test loading config when environment variables are not set."""
        with patch.dict(os.environ, {}, clear=True):
            config = load_auth_config()
            # Should use defaults
            assert not config.okta_enabled
            assert config.local_auth_enabled
            assert config.token_expiration_hours == 24
            assert config.okta.scopes == "openid profile email"
