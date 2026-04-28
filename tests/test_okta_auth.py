"""
Unit tests for Okta authentication handler.

Tests OAuth2 flow, token validation, and user profile synchronization.
"""

import os
import sys
import pytest
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch, Mock
import jwt as pyjwt

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from auth.okta_auth import OktaAuthHandler
from auth_config import OktaConfig


@pytest.fixture
def okta_config():
    """Create a test Okta configuration."""
    return OktaConfig(
        domain="test.okta.com",
        client_id="test-client-id",
        client_secret="test-client-secret",
        redirect_uri="http://localhost:8000/api/auth/okta/callback",
        scopes="openid profile email"
    )


@pytest.fixture
def mock_session_maker():
    """Create a mock session maker."""
    session = AsyncMock()
    session_maker = MagicMock()
    session_maker.return_value.__aenter__.return_value = session
    session_maker.return_value.__aexit__.return_value = None
    return session_maker


@pytest.fixture
def okta_handler(okta_config, mock_session_maker):
    """Create an OktaAuthHandler instance for testing."""
    return OktaAuthHandler(
        config=okta_config,
        session_maker=mock_session_maker,
        jwt_secret="test-secret",
        jwt_algorithm="HS256",
        token_expiration_hours=24
    )


class TestOktaAuthHandlerInit:
    """Test OktaAuthHandler initialization."""
    
    def test_init_with_valid_config(self, okta_config, mock_session_maker):
        """Test handler initialization with valid configuration."""
        handler = OktaAuthHandler(
            config=okta_config,
            session_maker=mock_session_maker,
            jwt_secret="test-secret"
        )
        
        assert handler.config == okta_config
        assert handler.session_maker == mock_session_maker
        assert handler.jwt_secret == "test-secret"
        assert handler.jwt_algorithm == "HS256"
        assert handler.token_expiration_hours == 24
        assert handler._jwks_cache is None
        assert handler._jwks_cache_time is None
    
    def test_init_with_custom_parameters(self, okta_config, mock_session_maker):
        """Test handler initialization with custom parameters."""
        handler = OktaAuthHandler(
            config=okta_config,
            session_maker=mock_session_maker,
            jwt_secret="custom-secret",
            jwt_algorithm="HS512",
            token_expiration_hours=48
        )
        
        assert handler.jwt_secret == "custom-secret"
        assert handler.jwt_algorithm == "HS512"
        assert handler.token_expiration_hours == 48


class TestGetAuthorizationUrl:
    """Test get_authorization_url method."""
    
    def test_get_authorization_url(self, okta_handler):
        """Test authorization URL generation."""
        state = "random-state-value"
        url = okta_handler.get_authorization_url(state)
        
        assert url.startswith("https://test.okta.com/oauth2/v1/authorize?")
        assert "client_id=test-client-id" in url
        assert "response_type=code" in url
        assert "scope=openid+profile+email" in url
        assert "redirect_uri=http%3A%2F%2Flocalhost%3A8000%2Fapi%2Fauth%2Fokta%2Fcallback" in url
        assert f"state={state}" in url
    
    def test_get_authorization_url_with_different_state(self, okta_handler):
        """Test authorization URL with different state values."""
        state1 = "state-1"
        state2 = "state-2"
        
        url1 = okta_handler.get_authorization_url(state1)
        url2 = okta_handler.get_authorization_url(state2)
        
        assert f"state={state1}" in url1
        assert f"state={state2}" in url2
        assert url1 != url2


class TestExchangeCodeForTokens:
    """Test exchange_code_for_tokens method."""
    
    @pytest.mark.asyncio
    async def test_exchange_code_success(self, okta_handler):
        """Test successful token exchange."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "test-access-token",
            "id_token": "test-id-token",
            "refresh_token": "test-refresh-token",
            "token_type": "Bearer",
            "expires_in": 3600
        }
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            tokens = await okta_handler.exchange_code_for_tokens("test-code")
            
            assert tokens["access_token"] == "test-access-token"
            assert tokens["id_token"] == "test-id-token"
            assert tokens["refresh_token"] == "test-refresh-token"
    
    @pytest.mark.asyncio
    async def test_exchange_code_failure(self, okta_handler):
        """Test token exchange failure."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "invalid_grant"
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            with pytest.raises(ValueError, match="Token exchange failed"):
                await okta_handler.exchange_code_for_tokens("invalid-code")
    
    @pytest.mark.asyncio
    async def test_exchange_code_http_error(self, okta_handler):
        """Test token exchange with HTTP error."""
        import httpx
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=httpx.HTTPError("Connection error")
            )
            
            with pytest.raises(ValueError, match="Token exchange failed"):
                await okta_handler.exchange_code_for_tokens("test-code")


class TestValidateIdToken:
    """Test validate_id_token method."""
    
    @pytest.mark.asyncio
    async def test_validate_id_token_success(self, okta_handler):
        """Test successful ID token validation."""
        # Create a mock ID token
        test_claims = {
            "sub": "00u1234567890",
            "email": "test@example.com",
            "name": "Test User",
            "iss": "https://test.okta.com/oauth2/v1",
            "aud": "test-client-id",
            "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp())
        }
        
        # Mock JWKS fetch
        mock_jwks = {
            "keys": [
                {
                    "kid": "test-key-id",
                    "kty": "RSA",
                    "use": "sig",
                    "n": "test-n",
                    "e": "AQAB"
                }
            ]
        }
        
        with patch.object(okta_handler, "_fetch_jwks", return_value=mock_jwks):
            with patch("jwt.PyJWKClient") as mock_jwk_client:
                mock_signing_key = Mock()
                mock_signing_key.key = "test-key"
                mock_jwk_client.return_value.get_signing_key_from_jwt.return_value = mock_signing_key
                
                with patch("jwt.decode", return_value=test_claims):
                    claims = await okta_handler.validate_id_token("test-id-token")
                    
                    assert claims["sub"] == "00u1234567890"
                    assert claims["email"] == "test@example.com"
                    assert claims["name"] == "Test User"
    
    @pytest.mark.asyncio
    async def test_validate_id_token_expired(self, okta_handler):
        """Test ID token validation with expired token."""
        with patch("jwt.get_unverified_header", return_value={"kid": "test-key-id"}):
            with patch.object(okta_handler, "_fetch_jwks", return_value={"keys": []}):
                with patch("jwt.PyJWKClient"):
                    with patch("jwt.decode", side_effect=pyjwt.ExpiredSignatureError):
                        with pytest.raises(ValueError, match="ID token expired"):
                            await okta_handler.validate_id_token("expired-token")
    
    @pytest.mark.asyncio
    async def test_validate_id_token_invalid(self, okta_handler):
        """Test ID token validation with invalid token."""
        with patch("jwt.get_unverified_header", return_value={"kid": "test-key-id"}):
            with patch.object(okta_handler, "_fetch_jwks", return_value={"keys": []}):
                with patch("jwt.PyJWKClient"):
                    with patch("jwt.decode", side_effect=pyjwt.InvalidTokenError("Invalid")):
                        with pytest.raises(ValueError, match="Invalid ID token"):
                            await okta_handler.validate_id_token("invalid-token")
    
    @pytest.mark.asyncio
    async def test_validate_id_token_missing_kid(self, okta_handler):
        """Test ID token validation with missing key ID."""
        with patch("jwt.get_unverified_header", return_value={}):
            with pytest.raises(ValueError, match="missing key ID"):
                await okta_handler.validate_id_token("token-without-kid")


class TestGetUserInfo:
    """Test get_user_info method."""
    
    @pytest.mark.asyncio
    async def test_get_user_info_success(self, okta_handler):
        """Test successful user info fetch."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "sub": "00u1234567890",
            "email": "test@example.com",
            "name": "Test User",
            "preferred_username": "testuser"
        }
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )
            
            user_info = await okta_handler.get_user_info("test-access-token")
            
            assert user_info["sub"] == "00u1234567890"
            assert user_info["email"] == "test@example.com"
            assert user_info["name"] == "Test User"
    
    @pytest.mark.asyncio
    async def test_get_user_info_failure(self, okta_handler):
        """Test user info fetch failure."""
        mock_response = Mock()
        mock_response.status_code = 401
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )
            
            with pytest.raises(ValueError, match="Failed to fetch user info"):
                await okta_handler.get_user_info("invalid-token")


class TestSyncUserProfile:
    """Test sync_user_profile method."""
    
    @pytest.mark.asyncio
    async def test_sync_user_profile_new_user(self, okta_handler, mock_session_maker):
        """Test creating a new user from Okta claims."""
        okta_claims = {
            "sub": "00u1234567890",
            "email": "newuser@example.com",
            "name": "New User"
        }
        
        # Mock database queries
        session = mock_session_maker.return_value.__aenter__.return_value
        
        # Mock user not found by subject
        result_by_subject = Mock()
        result_by_subject.scalar_one_or_none.return_value = None
        
        # Mock user not found by email
        result_by_email = Mock()
        result_by_email.scalar_one_or_none.return_value = None
        
        session.execute = AsyncMock(side_effect=[result_by_subject, result_by_email])
        session.commit = AsyncMock()
        
        # Mock the created user
        mock_user = Mock()
        mock_user.id = str(uuid.uuid4())
        mock_user.email = "newuser@example.com"
        mock_user.name = "New User"
        mock_user.role = "user"
        mock_user.auth_provider = "okta"
        mock_user.okta_subject = "00u1234567890"
        mock_user.permissions = []
        
        session.refresh = AsyncMock(side_effect=lambda u: setattr(u, 'permissions', []))
        
        with patch("backend.server.UserModel", return_value=mock_user):
            profile = await okta_handler.sync_user_profile(okta_claims)
            
            assert profile["email"] == "newuser@example.com"
            assert profile["name"] == "New User"
            assert profile["auth_provider"] == "okta"
            assert profile["okta_subject"] == "00u1234567890"
    
    @pytest.mark.asyncio
    async def test_sync_user_profile_existing_user(self, okta_handler, mock_session_maker):
        """Test updating an existing user from Okta claims."""
        okta_claims = {
            "sub": "00u1234567890",
            "email": "existing@example.com",
            "name": "Updated Name"
        }
        
        # Mock database queries
        session = mock_session_maker.return_value.__aenter__.return_value
        
        # Mock existing user found by subject
        mock_user = Mock()
        mock_user.id = str(uuid.uuid4())
        mock_user.email = "existing@example.com"
        mock_user.name = "Old Name"
        mock_user.role = "user"
        mock_user.auth_provider = "local"
        mock_user.okta_subject = "00u1234567890"
        mock_user.password_hash = "old-hash"
        mock_user.permissions = []
        
        result = Mock()
        result.scalar_one_or_none.return_value = mock_user
        
        session.execute = AsyncMock(return_value=result)
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        
        profile = await okta_handler.sync_user_profile(okta_claims)
        
        # Verify user was updated
        assert mock_user.name == "Updated Name"
        assert mock_user.auth_provider == "okta"
        assert mock_user.password_hash is None  # Cleared for Okta users
    
    @pytest.mark.asyncio
    async def test_sync_user_profile_missing_subject(self, okta_handler):
        """Test sync fails when Okta claims missing subject."""
        okta_claims = {
            "email": "test@example.com",
            "name": "Test User"
            # Missing 'sub'
        }
        
        with pytest.raises(ValueError, match="missing subject"):
            await okta_handler.sync_user_profile(okta_claims)
    
    @pytest.mark.asyncio
    async def test_sync_user_profile_missing_email(self, okta_handler):
        """Test sync fails when Okta claims missing email."""
        okta_claims = {
            "sub": "00u1234567890",
            "name": "Test User"
            # Missing 'email'
        }
        
        with pytest.raises(ValueError, match="missing email"):
            await okta_handler.sync_user_profile(okta_claims)
    
    @pytest.mark.asyncio
    async def test_sync_user_profile_fallback_name(self, okta_handler, mock_session_maker):
        """Test sync uses email as fallback when name is missing."""
        okta_claims = {
            "sub": "00u1234567890",
            "email": "test@example.com"
            # Missing 'name'
        }
        
        session = mock_session_maker.return_value.__aenter__.return_value
        
        # Mock user not found
        result = Mock()
        result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(side_effect=[result, result])
        session.commit = AsyncMock()
        
        mock_user = Mock()
        mock_user.id = str(uuid.uuid4())
        mock_user.email = "test@example.com"
        mock_user.name = "test@example.com"  # Should use email as fallback
        mock_user.role = "user"
        mock_user.auth_provider = "okta"
        mock_user.okta_subject = "00u1234567890"
        mock_user.permissions = []
        
        session.refresh = AsyncMock()
        
        with patch("backend.server.UserModel", return_value=mock_user):
            profile = await okta_handler.sync_user_profile(okta_claims)
            assert profile["name"] == "test@example.com"


class TestCreateAccessToken:
    """Test create_access_token method."""
    
    def test_create_access_token_basic(self, okta_handler):
        """Test creating a basic access token."""
        user_id = str(uuid.uuid4())
        email = "test@example.com"
        
        token = okta_handler.create_access_token(user_id, email)
        
        # Decode and verify token
        decoded = pyjwt.decode(
            token,
            okta_handler.jwt_secret,
            algorithms=[okta_handler.jwt_algorithm]
        )
        
        assert decoded["sub"] == user_id
        assert decoded["email"] == email
        assert decoded["auth_provider"] == "okta"
        assert decoded["type"] == "access"
        assert "exp" in decoded
    
    def test_create_access_token_with_permissions(self, okta_handler):
        """Test creating an access token with permissions."""
        user_id = str(uuid.uuid4())
        email = "test@example.com"
        permissions = [
            {"action": "read", "scope": "namespace", "namespace": "default"},
            {"action": "write", "scope": "object", "namespace": "prod", "object_name": "app"}
        ]
        
        token = okta_handler.create_access_token(user_id, email, permissions=permissions)
        
        decoded = pyjwt.decode(
            token,
            okta_handler.jwt_secret,
            algorithms=[okta_handler.jwt_algorithm]
        )
        
        assert decoded["permissions"] == permissions
    
    def test_create_access_token_expiration(self, okta_handler):
        """Test access token expiration time."""
        user_id = str(uuid.uuid4())
        email = "test@example.com"
        
        before = datetime.now(timezone.utc)
        token = okta_handler.create_access_token(user_id, email)
        after = datetime.now(timezone.utc)
        
        decoded = pyjwt.decode(
            token,
            okta_handler.jwt_secret,
            algorithms=[okta_handler.jwt_algorithm]
        )
        
        exp_time = datetime.fromtimestamp(decoded["exp"], tz=timezone.utc)
        expected_min = before + timedelta(hours=okta_handler.token_expiration_hours)
        expected_max = after + timedelta(hours=okta_handler.token_expiration_hours)
        
        assert expected_min <= exp_time <= expected_max


class TestRefreshAccessToken:
    """Test refresh_access_token method."""
    
    @pytest.mark.asyncio
    async def test_refresh_access_token_success(self, okta_handler):
        """Test successful token refresh."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new-access-token",
            "id_token": "new-id-token",
            "token_type": "Bearer",
            "expires_in": 3600
        }
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            tokens = await okta_handler.refresh_access_token("test-refresh-token")
            
            assert tokens["access_token"] == "new-access-token"
            assert tokens["id_token"] == "new-id-token"
    
    @pytest.mark.asyncio
    async def test_refresh_access_token_failure(self, okta_handler):
        """Test token refresh failure."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "invalid_grant"
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            with pytest.raises(ValueError, match="Token refresh failed"):
                await okta_handler.refresh_access_token("invalid-refresh-token")


class TestJWKSCaching:
    """Test JWKS caching behavior."""
    
    @pytest.mark.asyncio
    async def test_jwks_cache_hit(self, okta_handler):
        """Test JWKS cache is used when valid."""
        mock_jwks = {"keys": [{"kid": "test-key"}]}
        
        # Set cache
        okta_handler._jwks_cache = mock_jwks
        okta_handler._jwks_cache_time = datetime.now(timezone.utc)
        
        # Fetch should return cached value without HTTP request
        with patch("httpx.AsyncClient") as mock_client:
            jwks = await okta_handler._fetch_jwks()
            
            assert jwks == mock_jwks
            # Verify no HTTP request was made
            mock_client.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_jwks_cache_miss(self, okta_handler):
        """Test JWKS is fetched when cache is empty."""
        mock_jwks = {"keys": [{"kid": "test-key"}]}
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_jwks
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )
            
            jwks = await okta_handler._fetch_jwks()
            
            assert jwks == mock_jwks
            assert okta_handler._jwks_cache == mock_jwks
            assert okta_handler._jwks_cache_time is not None
    
    @pytest.mark.asyncio
    async def test_jwks_cache_expired(self, okta_handler):
        """Test JWKS is refetched when cache is expired."""
        old_jwks = {"keys": [{"kid": "old-key"}]}
        new_jwks = {"keys": [{"kid": "new-key"}]}
        
        # Set expired cache
        okta_handler._jwks_cache = old_jwks
        okta_handler._jwks_cache_time = datetime.now(timezone.utc) - timedelta(hours=25)
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = new_jwks
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )
            
            jwks = await okta_handler._fetch_jwks()
            
            assert jwks == new_jwks
            assert okta_handler._jwks_cache == new_jwks
