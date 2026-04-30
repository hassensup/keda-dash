"""
Okta Authentication Handler

This module provides Okta SSO authentication using OAuth2/OIDC protocol.
Implements authorization code flow, token validation, and user profile synchronization.

Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7
"""

import httpx
import jwt as pyjwt
import uuid
import logging
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from urllib.parse import urlencode
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy import select
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)


class OktaAuthHandler:
    """
    Handler for Okta SSO authentication using OAuth2/OIDC.
    
    Provides methods for:
    - OAuth2 authorization code flow
    - Token exchange and validation
    - ID token signature verification using JWKS
    - User profile synchronization from Okta claims
    - Token refresh logic
    """
    
    def __init__(
        self,
        config,  # OktaConfig from auth_config module
        session_maker: async_sessionmaker,
        jwt_secret: str,
        jwt_algorithm: str = "HS256",
        token_expiration_hours: int = 24
    ):
        """
        Initialize OktaAuthHandler.
        
        Args:
            config: OktaConfig instance with Okta domain, client_id, client_secret, etc.
            session_maker: SQLAlchemy async session maker for database access
            jwt_secret: Secret key for JWT token signing (application tokens)
            jwt_algorithm: JWT signing algorithm (default: HS256)
            token_expiration_hours: JWT token expiration time in hours (default: 24)
        """
        self.config = config
        self.session_maker = session_maker
        self.jwt_secret = jwt_secret
        self.jwt_algorithm = jwt_algorithm
        self.token_expiration_hours = token_expiration_hours
        self._jwks_cache: Optional[Dict[str, Any]] = None
        self._jwks_cache_time: Optional[datetime] = None
        self._jwks_cache_ttl = timedelta(hours=24)  # Cache JWKS for 24 hours
    
    def get_authorization_url(self, state: str) -> str:
        """
        Generate Okta authorization URL for OAuth2 flow.
        
        Args:
            state: Random state parameter for CSRF protection
            
        Returns:
            str: Full authorization URL to redirect user to
            
        Requirements: 2.1, 2.3
        """
        params = {
            "client_id": self.config.client_id,
            "response_type": "code",
            "scope": self.config.scopes,
            "redirect_uri": self.config.redirect_uri,
            "state": state,
        }
        
        auth_endpoint = self.config.get_authorization_endpoint()
        url = f"{auth_endpoint}?{urlencode(params)}"
        
        logger.info(f"[OKTA] Generated authorization URL:")
        logger.info(f"[OKTA]   Endpoint: {auth_endpoint}")
        logger.info(f"[OKTA]   Client ID: {self.config.client_id}")
        logger.info(f"[OKTA]   Redirect URI: {self.config.redirect_uri}")
        logger.info(f"[OKTA]   Scopes: {self.config.scopes}")
        logger.info(f"[OKTA]   State: {state[:8]}...")
        logger.info(f"[OKTA]   Full URL: {url}")
        
        return url
    
    async def exchange_code_for_tokens(self, code: str) -> Dict[str, Any]:
        """
        Exchange authorization code for access and ID tokens.
        
        Args:
            code: Authorization code from Okta callback
            
        Returns:
            dict: Token response containing access_token, id_token, refresh_token, etc.
            
        Raises:
            ValueError: If token exchange fails
            
        Requirements: 2.1, 2.4
        """
        token_endpoint = self.config.get_token_endpoint()
        
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.config.redirect_uri,
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    token_endpoint,
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                
                if response.status_code != 200:
                    error_detail = response.text
                    logger.error(
                        f"Token exchange failed: status={response.status_code}, "
                        f"error={error_detail}"
                    )
                    raise ValueError(f"Token exchange failed: {error_detail}")
                
                tokens = response.json()
                logger.info("Successfully exchanged authorization code for tokens")
                return tokens
                
        except httpx.HTTPError as e:
            logger.error(f"HTTP error during token exchange: {e}")
            raise ValueError(f"Token exchange failed: {str(e)}")
    
    async def _fetch_jwks(self) -> Dict[str, Any]:
        """
        Fetch Okta's JSON Web Key Set (JWKS) for token validation.
        
        Returns:
            dict: JWKS response containing public keys
            
        Raises:
            ValueError: If JWKS fetch fails
        """
        # Check cache first
        if self._jwks_cache and self._jwks_cache_time:
            age = datetime.now(timezone.utc) - self._jwks_cache_time
            if age < self._jwks_cache_ttl:
                logger.debug("Using cached JWKS")
                return self._jwks_cache
        
        # Fetch fresh JWKS
        jwks_uri = self.config.get_jwks_uri()
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(jwks_uri)
                
                if response.status_code != 200:
                    logger.error(f"JWKS fetch failed: status={response.status_code}")
                    raise ValueError("Failed to fetch JWKS")
                
                jwks = response.json()
                
                # Cache the result
                self._jwks_cache = jwks
                self._jwks_cache_time = datetime.now(timezone.utc)
                
                logger.info("Successfully fetched and cached JWKS")
                return jwks
                
        except httpx.HTTPError as e:
            logger.error(f"HTTP error during JWKS fetch: {e}")
            raise ValueError(f"JWKS fetch failed: {str(e)}")
    
    async def validate_id_token(self, id_token: str) -> Dict[str, Any]:
        """
        Validate ID token signature and claims using Okta's JWKS.
        
        Args:
            id_token: JWT ID token from Okta
            
        Returns:
            dict: Decoded and validated token claims
            
        Raises:
            ValueError: If token validation fails
            
        Requirements: 2.5, 2.6, 2.7
        """
        try:
            # Decode header to get key ID (kid)
            unverified_header = pyjwt.get_unverified_header(id_token)
            kid = unverified_header.get("kid")
            
            if not kid:
                logger.error("ID token missing 'kid' in header")
                raise ValueError("Invalid ID token: missing key ID")
            
            # Fetch JWKS
            jwks = await self._fetch_jwks()
            
            # Find matching key
            key_data = None
            for key in jwks.get("keys", []):
                if key.get("kid") == kid:
                    key_data = key
                    break
            
            if not key_data:
                logger.error(f"No matching key found for kid={kid}")
                raise ValueError("Invalid ID token: key not found")
            
            # Convert JWK to PEM format for PyJWT
            # PyJWT can handle JWK directly with PyJWKClient, but we'll use the simpler approach
            from jwt import PyJWKClient
            
            # Create a JWK client to handle the conversion
            jwks_uri = self.config.get_jwks_uri()
            jwk_client = PyJWKClient(jwks_uri)
            signing_key = jwk_client.get_signing_key_from_jwt(id_token)
            
            # Validate token
            # Get expected issuer from config
            expected_issuer = self.config._get_base_url()
            
            claims = pyjwt.decode(
                id_token,
                signing_key.key,
                algorithms=["RS256"],
                audience=self.config.client_id,
                issuer=expected_issuer,
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_aud": True,
                    "verify_iss": True,
                }
            )
            
            logger.info(f"Successfully validated ID token for subject={claims.get('sub')}")
            return claims
            
        except pyjwt.ExpiredSignatureError:
            logger.error("ID token has expired")
            raise ValueError("ID token expired")
        except pyjwt.InvalidTokenError as e:
            logger.error(f"ID token validation failed: {e}")
            raise ValueError(f"Invalid ID token: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during ID token validation: {e}")
            raise ValueError(f"Token validation failed: {str(e)}")
    
    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """
        Fetch user info from Okta userinfo endpoint.
        
        Args:
            access_token: Okta access token
            
        Returns:
            dict: User information from Okta
            
        Raises:
            ValueError: If userinfo request fails
            
        Requirements: 2.6
        """
        userinfo_endpoint = self.config.get_userinfo_endpoint()
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    userinfo_endpoint,
                    headers={"Authorization": f"Bearer {access_token}"}
                )
                
                if response.status_code != 200:
                    logger.error(f"Userinfo request failed: status={response.status_code}")
                    raise ValueError("Failed to fetch user info")
                
                user_info = response.json()
                logger.info(f"Successfully fetched user info for sub={user_info.get('sub')}")
                return user_info
                
        except httpx.HTTPError as e:
            logger.error(f"HTTP error during userinfo request: {e}")
            raise ValueError(f"Userinfo request failed: {str(e)}")
    
    async def sync_user_profile(self, okta_claims: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create or update user profile from Okta claims.
        
        Args:
            okta_claims: Claims from Okta ID token or userinfo endpoint
            
        Returns:
            dict: User profile with id, email, name, role, auth_provider
            
        Raises:
            ValueError: If required claims are missing
            
        Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7
        """
        # Import here to avoid circular dependency
        from backend.models import UserModel
        from sqlalchemy.orm import selectinload
        
        # Extract required claims
        okta_subject = okta_claims.get("sub")
        email = okta_claims.get("email")
        name = okta_claims.get("name") or okta_claims.get("preferred_username") or email
        
        if not okta_subject:
            logger.error("Okta claims missing 'sub' field")
            raise ValueError("Invalid Okta claims: missing subject")
        
        if not email:
            logger.error("Okta claims missing 'email' field")
            raise ValueError("Invalid Okta claims: missing email")
        
        async with self.session_maker() as session:
            # Try to find existing user by Okta subject with eager loading
            result = await session.execute(
                select(UserModel)
                .options(selectinload(UserModel.permissions))
                .where(UserModel.okta_subject == okta_subject)
            )
            user = result.scalar_one_or_none()
            
            # If not found by subject, try by email (for account linking)
            if not user:
                result = await session.execute(
                    select(UserModel)
                    .options(selectinload(UserModel.permissions))
                    .where(UserModel.email == email.lower())
                )
                user = result.scalar_one_or_none()
            
            if user:
                # Update existing user
                logger.info(f"Updating existing user profile for email={email}")
                user.email = email.lower()
                user.name = name
                user.auth_provider = "okta"
                user.okta_subject = okta_subject
                # Clear password hash for Okta users (account linking scenario)
                user.password_hash = None
                user.updated_at = datetime.now(timezone.utc)
            else:
                # Create new user
                logger.info(f"Creating new user profile for email={email}")
                user = UserModel(
                    id=str(uuid.uuid4()),
                    email=email.lower(),
                    password_hash=None,  # No password for Okta users
                    name=name,
                    role="user",  # Default role
                    auth_provider="okta",
                    okta_subject=okta_subject
                )
                session.add(user)
            
            await session.commit()
            
            # Refresh user with permissions eagerly loaded
            await session.refresh(user)
            result = await session.execute(
                select(UserModel)
                .options(selectinload(UserModel.permissions))
                .where(UserModel.id == user.id)
            )
            user = result.scalar_one()
            
            # Load user permissions
            permissions = []
            for perm in user.permissions:
                permissions.append({
                    "id": perm.id,
                    "action": perm.action,
                    "scope": perm.scope,
                    "namespace": perm.namespace,
                    "object_name": perm.object_name
                })
            
            logger.info(f"User profile synchronized for email={email}, id={user.id}")
            
            return {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "role": user.role,
                "auth_provider": user.auth_provider,
                "okta_subject": user.okta_subject,
                "permissions": permissions
            }
    
    def create_access_token(
        self,
        user_id: str,
        email: str,
        auth_provider: str = "okta",
        permissions: Optional[list] = None
    ) -> str:
        """
        Create a JWT access token for a user.
        
        Args:
            user_id: User's unique identifier
            email: User's email address
            auth_provider: Authentication provider ('local' or 'okta')
            permissions: List of user permissions to include in token
            
        Returns:
            str: Encoded JWT token
            
        Requirements: 1.6, 1.7
        """
        payload = {
            "sub": user_id,
            "email": email,
            "auth_provider": auth_provider,
            "exp": datetime.now(timezone.utc) + timedelta(hours=self.token_expiration_hours),
            "type": "access"
        }
        
        # Include permissions in token if provided
        if permissions:
            payload["permissions"] = permissions
        
        token = pyjwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
        return token
    
    async def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh access token using Okta refresh token.
        
        Args:
            refresh_token: Okta refresh token
            
        Returns:
            dict: New token response with access_token, id_token, etc.
            
        Raises:
            ValueError: If token refresh fails
            
        Requirements: 2.4
        """
        token_endpoint = self.config.get_token_endpoint()
        
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "scope": self.config.scopes,
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    token_endpoint,
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                
                if response.status_code != 200:
                    error_detail = response.text
                    logger.error(
                        f"Token refresh failed: status={response.status_code}, "
                        f"error={error_detail}"
                    )
                    raise ValueError(f"Token refresh failed: {error_detail}")
                
                tokens = response.json()
                logger.info("Successfully refreshed access token")
                return tokens
                
        except httpx.HTTPError as e:
            logger.error(f"HTTP error during token refresh: {e}")
            raise ValueError(f"Token refresh failed: {str(e)}")
