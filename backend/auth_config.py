"""
Authentication Configuration Module

This module provides configuration management for authentication settings,
including Okta SSO and local authentication providers.

Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8
"""

import os
import logging
from typing import Optional
from pydantic import BaseModel, Field, field_validator, model_validator

logger = logging.getLogger(__name__)


class OktaConfig(BaseModel):
    """
    Okta OAuth2/OIDC configuration.
    
    Validates required Okta parameters when Okta authentication is enabled.
    """
    domain: Optional[str] = Field(
        default=None,
        description="Okta domain (e.g., 'your-org.okta.com')"
    )
    client_id: Optional[str] = Field(
        default=None,
        description="Okta application client ID"
    )
    client_secret: Optional[str] = Field(
        default=None,
        description="Okta application client secret"
    )
    redirect_uri: Optional[str] = Field(
        default=None,
        description="OAuth2 callback URL for authorization code flow"
    )
    scopes: str = Field(
        default="openid profile email",
        description="OAuth2 scopes to request"
    )
    
    @field_validator('domain')
    @classmethod
    def validate_domain(cls, v: Optional[str]) -> Optional[str]:
        """Validate Okta domain format."""
        if v and not v.strip():
            return None
        return v
    
    def is_configured(self) -> bool:
        """
        Check if all required Okta configuration is present.
        
        Returns:
            bool: True if all required fields are configured, False otherwise
        """
        return all([
            self.domain,
            self.client_id,
            self.client_secret,
            self.redirect_uri
        ])
    
    def get_authorization_endpoint(self) -> str:
        """Get Okta authorization endpoint URL."""
        if not self.domain:
            raise ValueError("Okta domain not configured")
        return f"https://{self.domain}/oauth2/v1/authorize"
    
    def get_token_endpoint(self) -> str:
        """Get Okta token endpoint URL."""
        if not self.domain:
            raise ValueError("Okta domain not configured")
        return f"https://{self.domain}/oauth2/v1/token"
    
    def get_userinfo_endpoint(self) -> str:
        """Get Okta userinfo endpoint URL."""
        if not self.domain:
            raise ValueError("Okta domain not configured")
        return f"https://{self.domain}/oauth2/v1/userinfo"
    
    def get_jwks_uri(self) -> str:
        """Get Okta JWKS URI for token validation."""
        if not self.domain:
            raise ValueError("Okta domain not configured")
        return f"https://{self.domain}/oauth2/v1/keys"


class AuthConfig(BaseModel):
    """
    Application authentication configuration.
    
    Manages feature flags for authentication providers and validates
    that at least one authentication method is enabled.
    """
    okta_enabled: bool = Field(
        default=False,
        description="Enable Okta SSO authentication"
    )
    local_auth_enabled: bool = Field(
        default=True,
        description="Enable local username/password authentication"
    )
    okta: OktaConfig = Field(
        default_factory=OktaConfig,
        description="Okta configuration"
    )
    token_expiration_hours: int = Field(
        default=24,
        description="JWT token expiration time in hours",
        ge=1,
        le=168  # Max 1 week
    )
    
    @model_validator(mode='after')
    def validate_auth_config(self) -> 'AuthConfig':
        """
        Validate authentication configuration.
        
        Ensures:
        1. At least one authentication method is enabled
        2. If Okta is enabled, required configuration is present
        
        Returns:
            AuthConfig: Validated configuration
        """
        # At least one auth method must be enabled
        if not self.okta_enabled and not self.local_auth_enabled:
            logger.error("No authentication methods enabled")
            raise ValueError("At least one authentication method must be enabled")
        
        # If Okta is enabled, validate required configuration
        if self.okta_enabled:
            if not self.okta.is_configured():
                logger.error(
                    "Okta is enabled but required configuration is missing. "
                    "Required: OKTA_DOMAIN, OKTA_CLIENT_ID, OKTA_CLIENT_SECRET, OKTA_REDIRECT_URI"
                )
                # Disable Okta instead of failing
                self.okta_enabled = False
                logger.warning("Okta authentication has been disabled due to missing configuration")
        
        return self


def load_auth_config() -> AuthConfig:
    """
    Load authentication configuration from environment variables.
    
    Environment Variables:
        OKTA_ENABLED: Enable Okta SSO (default: false)
        LOCAL_AUTH_ENABLED: Enable local auth (default: true)
        OKTA_DOMAIN: Okta domain (required if Okta enabled)
        OKTA_CLIENT_ID: Okta client ID (required if Okta enabled)
        OKTA_CLIENT_SECRET: Okta client secret (required if Okta enabled)
        OKTA_REDIRECT_URI: OAuth2 callback URL (required if Okta enabled)
        OKTA_SCOPES: OAuth2 scopes (default: "openid profile email")
        TOKEN_EXPIRATION_HOURS: JWT expiration in hours (default: 24)
    
    Returns:
        AuthConfig: Loaded and validated authentication configuration
    
    Raises:
        ValueError: If configuration is invalid
    """
    # Parse boolean environment variables
    okta_enabled = os.environ.get("OKTA_ENABLED", "false").lower() in ("true", "1", "yes")
    local_auth_enabled = os.environ.get("LOCAL_AUTH_ENABLED", "true").lower() in ("true", "1", "yes")
    
    # Parse token expiration
    try:
        token_expiration_hours = int(os.environ.get("TOKEN_EXPIRATION_HOURS", "24"))
    except ValueError:
        logger.warning("Invalid TOKEN_EXPIRATION_HOURS, using default: 24")
        token_expiration_hours = 24
    
    # Load Okta configuration
    okta_config = OktaConfig(
        domain=os.environ.get("OKTA_DOMAIN"),
        client_id=os.environ.get("OKTA_CLIENT_ID"),
        client_secret=os.environ.get("OKTA_CLIENT_SECRET"),
        redirect_uri=os.environ.get("OKTA_REDIRECT_URI"),
        scopes=os.environ.get("OKTA_SCOPES", "openid profile email")
    )
    
    # Create and validate auth config
    auth_config = AuthConfig(
        okta_enabled=okta_enabled,
        local_auth_enabled=local_auth_enabled,
        okta=okta_config,
        token_expiration_hours=token_expiration_hours
    )
    
    # Log configuration status
    logger.info(f"Authentication configuration loaded:")
    logger.info(f"  - Local auth: {'enabled' if auth_config.local_auth_enabled else 'disabled'}")
    logger.info(f"  - Okta auth: {'enabled' if auth_config.okta_enabled else 'disabled'}")
    if auth_config.okta_enabled:
        logger.info(f"  - Okta domain: {auth_config.okta.domain}")
        logger.info(f"  - Okta scopes: {auth_config.okta.scopes}")
    logger.info(f"  - Token expiration: {auth_config.token_expiration_hours} hours")
    
    return auth_config


# Global configuration instance
_auth_config: Optional[AuthConfig] = None


def get_auth_config() -> AuthConfig:
    """
    Get the global authentication configuration instance.
    
    Loads configuration on first call and caches it for subsequent calls.
    
    Returns:
        AuthConfig: Global authentication configuration
    """
    global _auth_config
    if _auth_config is None:
        _auth_config = load_auth_config()
    return _auth_config


def reload_auth_config() -> AuthConfig:
    """
    Reload authentication configuration from environment variables.
    
    Useful for testing or when configuration changes at runtime.
    
    Returns:
        AuthConfig: Reloaded authentication configuration
    """
    global _auth_config
    _auth_config = load_auth_config()
    return _auth_config
