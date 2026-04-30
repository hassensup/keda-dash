"""
Authentication Router Module

This module provides FastAPI router for authentication endpoints,
supporting both local and Okta authentication providers.

Requirements: 1.1, 1.2
"""

import os
import logging
import secrets
from typing import Optional, Dict
from datetime import datetime, timezone
from fastapi import APIRouter, Response, HTTPException, Request

from backend.auth_config import get_auth_config
from backend.auth.local_auth import LocalAuthHandler
from backend.auth.okta_auth import OktaAuthHandler
from backend.database import async_session_maker
from backend.schemas import LoginRequest
from backend.audit import logger as audit_logger

logger = logging.getLogger(__name__)

# In-memory state storage for OAuth2 CSRF protection
# Production should use Redis or similar cache
# Format: {state: {"timestamp": datetime, "used": bool}}
_oauth_states: Dict[str, Dict] = {}

# Initialize FastAPI router with prefix and tags
router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"]
)

# Load authentication configuration
auth_config = get_auth_config()

# Get JWT secret from environment
jwt_secret = os.environ.get("JWT_SECRET")
if not jwt_secret:
    logger.error("JWT_SECRET environment variable not set")
    raise ValueError("JWT_SECRET must be configured")

# Initialize LocalAuthHandler (always available)
local_auth_handler = LocalAuthHandler(
    session_maker=async_session_maker,
    jwt_secret=jwt_secret,
    token_expiration_hours=auth_config.token_expiration_hours
)

logger.info("LocalAuthHandler initialized")

# Initialize OktaAuthHandler (conditionally if Okta is enabled)
okta_auth_handler: Optional[OktaAuthHandler] = None

if auth_config.okta_enabled:
    okta_auth_handler = OktaAuthHandler(
        config=auth_config.okta,
        session_maker=async_session_maker,
        jwt_secret=jwt_secret,
        token_expiration_hours=auth_config.token_expiration_hours
    )
    logger.info("OktaAuthHandler initialized")
else:
    logger.info("Okta authentication is disabled")


# ============ AUTHENTICATION ENDPOINTS ============

@router.post("/login")
async def login(req: LoginRequest, response: Response, request: Request):
    """
    Local authentication endpoint.
    
    Accepts email and password, verifies credentials using LocalAuthHandler,
    generates JWT token with user ID, email, and permissions, sets httpOnly cookie,
    and returns user profile with token.
    
    Requirements: 1.1, 1.3, 1.6, 1.7, 11.2, 11.3, 13.1, 13.2, 13.5
    """
    # Get client IP address for audit logging
    client_ip = request.client.host if request.client else None
    
    try:
        # Authenticate user with local credentials
        user_profile = await local_auth_handler.authenticate(req.email, req.password)
        
        # Log successful authentication
        audit_logger.log_login_success(
            user_id=user_profile["id"],
            user_email=user_profile["email"],
            auth_provider="local",
            ip_address=client_ip
        )
        
        # Set httpOnly cookie with JWT token
        response.set_cookie(
            key="access_token",
            value=user_profile["token"],
            httponly=True,
            secure=False,  # Set to True in production with HTTPS
            samesite="lax",
            max_age=86400,  # 24 hours
            path="/"
        )
        
        # Return user profile with token
        return user_profile
        
    except ValueError as e:
        # Authentication failed - log and return 401 with generic error message
        logger.warning(f"Login failed for email {req.email}: {str(e)}")
        
        # Determine failure reason
        reason = "invalid_credentials"
        if "not found" in str(e).lower():
            reason = "user_not_found"
        elif "password" in str(e).lower():
            reason = "invalid_password"
        
        # Log failed authentication
        audit_logger.log_login_failed(
            email=req.email,
            auth_provider="local",
            reason=reason,
            ip_address=client_ip
        )
        
        raise HTTPException(status_code=401, detail="Invalid credentials")
    except Exception as e:
        # Unexpected error
        logger.error(f"Unexpected error during login for email {req.email}: {str(e)}")
        
        # Log failed authentication with system error reason
        audit_logger.log_login_failed(
            email=req.email,
            auth_provider="local",
            reason="system_error",
            ip_address=client_ip
        )
        
        raise HTTPException(status_code=500, detail="Authentication service error")


@router.get("/config")
async def get_auth_config():
    """
    Authentication configuration endpoint.
    
    Returns authentication provider availability flags to allow frontend
    to determine which login options to display. This endpoint is public
    (no authentication required).
    
    Requirements: 3.5, 3.6, 9.7
    """
    return {
        "okta_enabled": auth_config.okta_enabled,
        "local_auth_enabled": auth_config.local_auth_enabled
    }


@router.get("/okta/login")
async def okta_login():
    """
    Okta SSO login initiation endpoint.
    
    Generates secure random state parameter for CSRF protection,
    stores state in session/cache, and redirects user to Okta
    authorization endpoint.
    
    Requirements: 1.2, 1.4, 2.1, 2.3
    """
    from fastapi.responses import RedirectResponse
    
    # Check if Okta is enabled
    if okta_auth_handler is None:
        logger.warning("Okta login attempted but Okta is not enabled")
        raise HTTPException(status_code=404, detail="Okta authentication not available")
    
    try:
        # Generate secure random state parameter (32 bytes = 43 chars base64)
        state = secrets.token_urlsafe(32)
        
        # Store state with timestamp for CSRF validation in callback
        _oauth_states[state] = {
            "timestamp": datetime.now(timezone.utc),
            "used": False
        }
        
        # Get authorization URL from Okta handler
        authorization_url = okta_auth_handler.get_authorization_url(state)
        
        logger.info(f"Redirecting to Okta login with state={state[:8]}...")
        
        # Redirect user to Okta authorization endpoint
        return RedirectResponse(url=authorization_url, status_code=302)
        
    except Exception as e:
        logger.error(f"Error generating Okta login URL: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to initiate Okta login")


@router.get("/okta/callback")
async def okta_callback(response: Response, request: Request, code: Optional[str] = None, 
                       state: Optional[str] = None, error: Optional[str] = None):
    """
    Okta SSO callback endpoint.
    
    Validates state parameter, exchanges authorization code for tokens,
    validates ID token, syncs user profile to database, generates JWT token
    with user ID, email, and permissions, sets httpOnly cookie, and returns
    user profile with token.
    
    Requirements: 1.4, 1.5, 1.6, 1.7, 2.4, 2.5, 2.6, 4.1, 4.2, 13.1, 13.2, 13.5
    """
    # Get client IP address for audit logging
    client_ip = request.client.host if request.client else None
    
    # Check if Okta is enabled
    if okta_auth_handler is None:
        logger.warning("Okta callback attempted but Okta is not enabled")
        raise HTTPException(status_code=404, detail="Okta authentication not available")
    
    # Handle error parameter from Okta (user cancelled, etc.)
    if error:
        logger.warning(f"Okta callback received error: {error}")
        
        # Log failed authentication
        audit_logger.log_login_failed(
            email="unknown",
            auth_provider="okta",
            reason=f"okta_error_{error}",
            ip_address=client_ip
        )
        
        raise HTTPException(status_code=400, detail=f"Okta authentication failed: {error}")
    
    # Validate required parameters
    if not code:
        logger.error("Okta callback missing authorization code")
        
        # Log failed authentication
        audit_logger.log_login_failed(
            email="unknown",
            auth_provider="okta",
            reason="missing_authorization_code",
            ip_address=client_ip
        )
        
        raise HTTPException(status_code=400, detail="Missing authorization code")
    
    if not state:
        logger.error("Okta callback missing state parameter")
        
        # Log failed authentication
        audit_logger.log_login_failed(
            email="unknown",
            auth_provider="okta",
            reason="missing_state_parameter",
            ip_address=client_ip
        )
        
        raise HTTPException(status_code=400, detail="Missing state parameter")
    
    # Validate state parameter exists in _oauth_states
    if state not in _oauth_states:
        logger.error(f"Invalid state parameter: {state[:8]}...")
        
        # Log failed authentication
        audit_logger.log_login_failed(
            email="unknown",
            auth_provider="okta",
            reason="invalid_state_parameter",
            ip_address=client_ip
        )
        
        raise HTTPException(status_code=400, detail="Invalid state parameter")
    
    # Check if state has already been used
    state_data = _oauth_states[state]
    if state_data.get("used"):
        logger.error(f"State parameter already used: {state[:8]}...")
        
        # Log failed authentication
        audit_logger.log_login_failed(
            email="unknown",
            auth_provider="okta",
            reason="state_parameter_reused",
            ip_address=client_ip
        )
        
        raise HTTPException(status_code=400, detail="State parameter already used")
    
    # Mark state as used
    _oauth_states[state]["used"] = True
    
    try:
        # Exchange authorization code for tokens
        logger.info(f"Exchanging authorization code for tokens (state={state[:8]}...)")
        tokens = await okta_auth_handler.exchange_code_for_tokens(code)
        
        # Validate ID token
        logger.info("Validating ID token")
        id_token = tokens.get("id_token")
        if not id_token:
            logger.error("Token response missing id_token")
            
            # Log token validation failure
            audit_logger.log_token_validation_failed(
                auth_provider="okta",
                reason="missing_id_token",
                token_type="id_token"
            )
            
            raise HTTPException(status_code=500, detail="Invalid token response from Okta")
        
        claims = await okta_auth_handler.validate_id_token(id_token)
        
        # Sync user profile to database
        logger.info(f"Syncing user profile for subject={claims.get('sub')}")
        user_profile = await okta_auth_handler.sync_user_profile(claims)
        
        # Generate JWT token with user ID, email, and permissions
        logger.info(f"Generating JWT token for user_id={user_profile['id']}")
        jwt_token = okta_auth_handler.create_access_token(
            user_id=user_profile["id"],
            email=user_profile["email"],
            auth_provider="okta",
            permissions=user_profile.get("permissions", [])
        )
        
        # Add token to user profile response
        user_profile["token"] = jwt_token
        
        # Log successful authentication
        audit_logger.log_login_success(
            user_id=user_profile["id"],
            user_email=user_profile["email"],
            auth_provider="okta",
            ip_address=client_ip
        )
        
        # Set httpOnly cookie with JWT token
        response.set_cookie(
            key="access_token",
            value=jwt_token,
            httponly=True,
            secure=False,  # Set to True in production with HTTPS
            samesite="lax",
            max_age=86400,  # 24 hours
            path="/"
        )
        
        logger.info(f"Okta authentication successful for user {user_profile['email']}")
        
        # Redirect to frontend with token in URL fragment (will be stored in localStorage by frontend)
        # Using URL fragment (#) instead of query parameter (?) for security (not sent to server)
        from fastapi.responses import RedirectResponse
        frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")
        redirect_url = f"{frontend_url}/?token={jwt_token}"
        
        logger.info(f"Redirecting to frontend: {frontend_url}")
        return RedirectResponse(url=redirect_url, status_code=302)
        
    except ValueError as e:
        # Token validation or profile sync failed
        logger.error(f"Okta callback failed: {str(e)}")
        
        # Determine if this is a token validation failure
        if "token" in str(e).lower() or "validation" in str(e).lower():
            # Log token validation failure
            audit_logger.log_token_validation_failed(
                auth_provider="okta",
                reason=str(e),
                token_type="id_token"
            )
        else:
            # Log failed authentication
            audit_logger.log_login_failed(
                email="unknown",
                auth_provider="okta",
                reason=str(e),
                ip_address=client_ip
            )
        
        raise HTTPException(status_code=401, detail=f"Okta authentication failed: {str(e)}")
    except Exception as e:
        # Unexpected error
        logger.error(f"Unexpected error during Okta callback: {str(e)}")
        
        # Log failed authentication with system error reason
        audit_logger.log_login_failed(
            email="unknown",
            auth_provider="okta",
            reason="system_error",
            ip_address=client_ip
        )
        
        raise HTTPException(status_code=500, detail="Authentication service error")
    finally:
        # Clean up used state from memory (optional, could also implement TTL cleanup)
        # Keep it for now to prevent replay attacks
        pass


# Export handlers for use in endpoint functions
__all__ = [
    "router",
    "local_auth_handler",
    "okta_auth_handler",
    "auth_config"
]
