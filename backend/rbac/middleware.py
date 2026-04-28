"""
Permission middleware for RBAC enforcement.

This module provides FastAPI dependencies for extracting and validating
user authentication tokens and loading user permissions.
"""

import os
import jwt as pyjwt
from typing import Optional, Callable
from fastapi import Request, HTTPException, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


# JWT Configuration
JWT_ALGORITHM = "HS256"

# Global references to be set by server.py
_async_session_maker = None
_user_model = None
_permission_model = None


def initialize_middleware(async_session_maker, user_model, permission_model):
    """
    Initialize the middleware with database session maker and ORM models.
    
    This should be called once at application startup from server.py.
    
    Args:
        async_session_maker: SQLAlchemy async session maker
        user_model: UserModel ORM class
        permission_model: PermissionModel ORM class
    """
    global _async_session_maker, _user_model, _permission_model
    _async_session_maker = async_session_maker
    _user_model = user_model
    _permission_model = permission_model


def get_jwt_secret():
    """Get JWT secret from environment variable."""
    return os.environ["JWT_SECRET"]


async def get_current_user_with_permissions(request: Request) -> dict:
    """
    FastAPI dependency to extract and validate JWT token and load user permissions.
    
    This dependency:
    1. Extracts JWT token from cookie ("access_token") or Authorization header ("Bearer <token>")
    2. Decodes and validates the JWT token
    3. Loads user permissions from the database
    4. Returns user dict with: id, email, auth_provider, permissions
    
    Args:
        request: FastAPI Request object
        
    Returns:
        dict with keys:
            - id: User ID (from JWT "sub" claim)
            - email: User email (from JWT "email" claim)
            - auth_provider: Authentication provider ("local" or "okta", from JWT "auth_provider" claim)
            - permissions: List of permission dicts (loaded from database or JWT)
            
    Raises:
        HTTPException 401: If token is missing, invalid, or expired
        
    Requirements:
        - Validates: Requirements 1.6, 1.7
    """
    # Step 1: Extract token from cookie or Authorization header
    token = request.cookies.get("access_token")
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
    
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Step 2: Decode and validate JWT token
    try:
        payload = pyjwt.decode(token, get_jwt_secret(), algorithms=[JWT_ALGORITHM])
        
        # Validate token type
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        
        # Extract user information from token
        user_id = payload.get("sub")
        email = payload.get("email")
        auth_provider = payload.get("auth_provider", "local")  # Default to "local" for backward compatibility
        
        if not user_id or not email:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        
        # Extract permissions from token (if present)
        # Permissions may be embedded in the JWT token for performance
        permissions = payload.get("permissions", [])
        
        # Return user dict with permissions
        return {
            "id": user_id,
            "email": email,
            "auth_provider": auth_provider,
            "permissions": permissions
        }
        
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except pyjwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def require_permission(
    action: str,
    resource_type: str,
    namespace_param: str,
    object_param: Optional[str] = None
) -> Callable:
    """
    Decorator to require permission for a route.
    
    This function returns a FastAPI dependency that:
    1. Gets the current user via get_current_user_with_permissions
    2. Extracts namespace and object_name from route path parameters
    3. Initializes RBACEngine
    4. Calls rbac_engine.check_permission()
    5. Raises HTTPException 403 if permission denied
    6. Returns user if permission granted
    
    Args:
        action: The action type ("read" or "write")
        resource_type: The resource type (e.g., "scaledobject")
        namespace_param: The name of the path parameter containing the namespace
        object_param: The name of the path parameter containing the object name (optional)
        
    Returns:
        FastAPI dependency function that checks permissions
        
    Example usage:
        @router.get(
            "/scaled-objects/{namespace}/{name}",
            dependencies=[Depends(require_permission("read", "scaledobject", "namespace", "name"))]
        )
        
    Requirements:
        - Validates: Requirements 6.6
    """
    async def permission_checker(
        request: Request,
        user: dict = Depends(get_current_user_with_permissions)
    ) -> dict:
        """
        Inner dependency that performs the actual permission check.
        
        Args:
            request: FastAPI Request object (to access path parameters)
            user: Current user dict from get_current_user_with_permissions
            
        Returns:
            User dict if permission granted
            
        Raises:
            HTTPException 403: If permission denied
        """
        # Check if middleware has been initialized
        if not _async_session_maker or not _user_model or not _permission_model:
            raise HTTPException(
                status_code=500,
                detail="RBAC middleware not initialized"
            )
        
        # Import RBACEngine here to avoid circular dependencies
        from backend.rbac.engine import RBACEngine
        
        # Extract namespace from path parameters
        namespace = request.path_params.get(namespace_param)
        if not namespace:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required path parameter: {namespace_param}"
            )
        
        # Extract object_name from path parameters (if specified)
        object_name = None
        if object_param:
            object_name = request.path_params.get(object_param)
            if not object_name:
                raise HTTPException(
                    status_code=400,
                    detail=f"Missing required path parameter: {object_param}"
                )
        
        # Initialize RBAC engine with global references
        rbac_engine = RBACEngine(
            async_session_maker=_async_session_maker,
            user_model=_user_model,
            permission_model=_permission_model
        )
        
        # Check permission
        has_permission = await rbac_engine.check_permission(
            user_id=user["id"],
            action=action,
            resource_type=resource_type,
            namespace=namespace,
            object_name=object_name
        )
        
        # Raise 403 if permission denied
        if not has_permission:
            raise HTTPException(
                status_code=403,
                detail={
                    "message": "Insufficient permissions",
                    "required": {
                        "action": action,
                        "resource_type": resource_type,
                        "namespace": namespace,
                        "object_name": object_name
                    }
                }
            )
        
        # Return user if permission granted
        return user
    
    return permission_checker
