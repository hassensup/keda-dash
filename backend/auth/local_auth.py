"""
Local Authentication Handler

This module provides local username/password authentication using bcrypt
for password hashing and JWT tokens for session management.

Requirements: 1.1, 1.3, 1.6, 11.1, 11.2
"""

import bcrypt
import jwt as pyjwt
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy import select

logger = logging.getLogger(__name__)


class LocalAuthHandler:
    """
    Handler for local username/password authentication.
    
    Provides methods for:
    - User authentication with email and password
    - User creation with password hashing
    - Password hashing and verification using bcrypt
    - JWT token generation with user identity and permissions
    """
    
    def __init__(
        self,
        session_maker: async_sessionmaker,
        jwt_secret: str,
        jwt_algorithm: str = "HS256",
        token_expiration_hours: int = 24
    ):
        """
        Initialize LocalAuthHandler.
        
        Args:
            session_maker: SQLAlchemy async session maker for database access
            jwt_secret: Secret key for JWT token signing
            jwt_algorithm: JWT signing algorithm (default: HS256)
            token_expiration_hours: JWT token expiration time in hours (default: 24)
        """
        self.session_maker = session_maker
        self.jwt_secret = jwt_secret
        self.jwt_algorithm = jwt_algorithm
        self.token_expiration_hours = token_expiration_hours
    
    def hash_password(self, password: str) -> str:
        """
        Hash a password using bcrypt.
        
        Args:
            password: Plain text password to hash
            
        Returns:
            str: Bcrypt hashed password (UTF-8 decoded)
            
        Requirements: 1.3
        """
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
        return hashed.decode("utf-8")
    
    def verify_password(self, plain: str, hashed: str) -> bool:
        """
        Verify a plain text password against a bcrypt hash.
        
        Args:
            plain: Plain text password to verify
            hashed: Bcrypt hashed password to compare against
            
        Returns:
            bool: True if password matches hash, False otherwise
            
        Requirements: 1.3
        """
        try:
            return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
        except Exception as e:
            logger.error(f"Password verification failed: {e}")
            return False
    
    def create_access_token(
        self,
        user_id: str,
        email: str,
        auth_provider: str = "local",
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
    
    async def authenticate(self, email: str, password: str) -> Dict[str, Any]:
        """
        Authenticate a user with email and password.
        
        Args:
            email: User's email address
            password: User's plain text password
            
        Returns:
            dict: User profile with id, email, name, role, auth_provider, and access token
            
        Raises:
            ValueError: If credentials are invalid or user not found
            
        Requirements: 1.1, 1.3, 1.6, 11.2
        """
        # Import here to avoid circular dependency
        from backend.server import UserModel
        
        async with self.session_maker() as session:
            # Query user by email
            result = await session.execute(
                select(UserModel).where(UserModel.email == email.lower())
            )
            user = result.scalar_one_or_none()
            
            # Validate user exists and has local authentication
            if not user:
                logger.warning(f"Authentication failed: User not found for email {email}")
                raise ValueError("Invalid credentials")
            
            if user.auth_provider != "local":
                logger.warning(
                    f"Authentication failed: User {email} is not a local user "
                    f"(auth_provider={user.auth_provider})"
                )
                raise ValueError("Invalid credentials")
            
            if not user.password_hash:
                logger.error(f"Authentication failed: User {email} has no password hash")
                raise ValueError("Invalid credentials")
            
            # Verify password
            if not self.verify_password(password, user.password_hash):
                logger.warning(f"Authentication failed: Invalid password for user {email}")
                raise ValueError("Invalid credentials")
            
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
            
            # Generate JWT token
            token = self.create_access_token(
                user_id=user.id,
                email=user.email,
                auth_provider="local",
                permissions=permissions
            )
            
            logger.info(f"User {email} authenticated successfully via local provider")
            
            return {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "role": user.role,
                "auth_provider": user.auth_provider,
                "permissions": permissions,
                "token": token
            }
    
    async def create_user(
        self,
        email: str,
        password: str,
        name: str,
        role: str = "user"
    ) -> Dict[str, Any]:
        """
        Create a new local user account.
        
        Args:
            email: User's email address
            password: User's plain text password
            name: User's display name
            role: User's role (default: 'user')
            
        Returns:
            dict: Created user profile with id, email, name, role, auth_provider
            
        Raises:
            ValueError: If user with email already exists
            
        Requirements: 1.1, 11.1
        """
        # Import here to avoid circular dependency
        from backend.server import UserModel
        
        async with self.session_maker() as session:
            # Check if user already exists
            result = await session.execute(
                select(UserModel).where(UserModel.email == email.lower())
            )
            existing_user = result.scalar_one_or_none()
            
            if existing_user:
                logger.warning(f"User creation failed: User with email {email} already exists")
                raise ValueError("User with this email already exists")
            
            # Hash password
            password_hash = self.hash_password(password)
            
            # Create user
            user = UserModel(
                id=str(uuid.uuid4()),
                email=email.lower(),
                password_hash=password_hash,
                name=name,
                role=role,
                auth_provider="local"
            )
            
            session.add(user)
            await session.commit()
            await session.refresh(user)
            
            logger.info(f"Created new local user: {email}")
            
            return {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "role": user.role,
                "auth_provider": user.auth_provider
            }
