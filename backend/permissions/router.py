"""
Permission Management API Router

This module provides admin-only endpoints for managing user permissions.
All endpoints require admin role for access.
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy import select, func
from typing import List
import logging
from backend.audit import logger as audit_logger

logger = logging.getLogger(__name__)

# Create router with /api/permissions prefix
router = APIRouter(prefix="/api/permissions", tags=["Permission Management"])

# These will be set by server.py after models are defined
_async_session_maker = None
_user_model = None
_permission_model = None
_scaled_object_model = None
_permission_schema = None
_permission_create_schema = None
_get_current_user = None
_rbac_engine_class = None
_k8s_service = None


def initialize_permissions_router(
    async_session_maker,
    user_model,
    permission_model,
    scaled_object_model,
    permission_schema,
    permission_create_schema,
    get_current_user,
    rbac_engine_class,
    k8s_service
):
    """
    Initialize the permissions router with dependencies from server.py.
    
    This avoids circular imports by having server.py pass in the required
    models and functions after they are defined.
    """
    global _async_session_maker, _user_model, _permission_model, _scaled_object_model
    global _permission_schema, _permission_create_schema, _get_current_user, _rbac_engine_class
    global _require_admin, _k8s_service
    
    logger.info(f"[INIT] Initializing permissions router with k8s_service={k8s_service}, type={type(k8s_service)}")
    
    _async_session_maker = async_session_maker
    _user_model = user_model
    _permission_model = permission_model
    _scaled_object_model = scaled_object_model
    _permission_schema = permission_schema
    _permission_create_schema = permission_create_schema
    _get_current_user = get_current_user
    _rbac_engine_class = rbac_engine_class
    _k8s_service = k8s_service
    
    logger.info(f"[INIT] After assignment: _k8s_service={_k8s_service}, mode={_k8s_service.get_mode() if _k8s_service else 'None'}")
    
    # Create the require_admin dependency
    _require_admin = get_require_admin_dependency()


def get_require_admin_dependency():
    """
    Factory function to create the require_admin dependency.
    This is called after initialization to get the proper dependency.
    """
    async def require_admin(request: Request) -> dict:
        """
        Dependency to require admin role for permission management endpoints.
        
        Args:
            request: FastAPI Request object
            
        Returns:
            User dict if admin
            
        Raises:
            HTTPException 403: If user is not admin
        """
        # Get current user using the initialized function
        current_user = await _get_current_user(request)
        
        async with _async_session_maker() as session:
            result = await session.execute(
                select(_user_model).where(_user_model.id == current_user["id"])
            )
            user = result.scalar_one_or_none()
            
            if not user or user.role != "admin":
                raise HTTPException(
                    status_code=403,
                    detail="Admin role required for permission management"
                )
            
            return current_user
    
    return require_admin


# This will be set after initialization
_require_admin = None


def _get_require_admin():
    """Get the require_admin dependency (for use in route decorators)."""
    async def _dependency_wrapper(request: Request) -> dict:
        if _require_admin is None:
            raise RuntimeError("Permissions router not initialized")
        return await _require_admin(request)
    return _dependency_wrapper


# Create a callable that can be used in Depends()
class RequireAdminDependency:
    """Callable dependency that checks for admin role."""
    async def __call__(self, request: Request) -> dict:
        if _require_admin is None:
            raise RuntimeError("Permissions router not initialized")
        return await _require_admin(request)


_require_admin_dependency = RequireAdminDependency()


@router.get("/users", response_model=List[dict])
async def list_users_with_permissions(admin_user: dict = Depends(_require_admin_dependency)):
    """
    List all users with their permission counts.
    
    Returns a list of users with:
    - id: User ID
    - email: User email
    - name: User name
    - role: User role
    - auth_provider: Authentication provider
    - permission_count: Number of permissions granted to user
    
    Requirements: 8.4
    """
    async with _async_session_maker() as session:
        # Query all users with permission counts
        result = await session.execute(
            select(
                _user_model,
                func.count(_permission_model.id).label("permission_count")
            )
            .outerjoin(_permission_model, _user_model.id == _permission_model.user_id)
            .group_by(_user_model.id)
            .order_by(_user_model.email)
        )
        
        users_with_counts = result.all()
        
        return [
            {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "role": user.role,
                "auth_provider": user.auth_provider,
                "permission_count": count
            }
            for user, count in users_with_counts
        ]


@router.get("/users/{user_id}")
async def get_user_permissions(user_id: str, admin_user: dict = Depends(_require_admin_dependency)):
    """
    Get all permissions for a specific user.
    
    Args:
        user_id: The ID of the user to get permissions for
        
    Returns:
        List of Permission objects for the user
        
    Raises:
        HTTPException 404: If user not found
        
    Requirements: 8.1
    """
    async with _async_session_maker() as session:
        # Verify user exists
        user_result = await session.execute(
            select(_user_model).where(_user_model.id == user_id)
        )
        user = user_result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get all permissions for the user
        rbac_engine = _rbac_engine_class(
            async_session_maker=_async_session_maker,
            user_model=_user_model,
            permission_model=_permission_model
        )
        
        permissions = await rbac_engine.get_user_permissions(user_id)
        
        return permissions


@router.post("/", status_code=201)
async def create_permission(
    data: dict,
    admin_user: dict = Depends(_require_admin_dependency)
):
    """
    Create a new permission for a user.
    
    Validates:
    - User exists
    - Namespace exists (if applicable)
    - Object exists (for object-scoped permissions)
    - Permission doesn't already exist (unique constraint)
    
    Args:
        data: Permission creation data
        
    Returns:
        Created Permission object
        
    Raises:
        HTTPException 404: If user, namespace, or object not found
        HTTPException 400: If validation fails or permission already exists
        
    Requirements: 8.2, 8.5, 8.6
    """
    # Validate input using Pydantic schema
    try:
        validated_data = _permission_create_schema(**data)
        logger.info(f"Creating permission for user_id={validated_data.user_id}, namespace={validated_data.namespace}, scope={validated_data.scope}")
        logger.info(f"_k8s_service is: {_k8s_service}, mode: {_k8s_service.get_mode() if _k8s_service else 'None'}")
    except Exception as e:
        logger.error(f"Permission validation failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    
    async with _async_session_maker() as session:
        # Validate user exists
        user_result = await session.execute(
            select(_user_model).where(_user_model.id == validated_data.user_id)
        )
        user = user_result.scalar_one_or_none()
        
        if not user:
            logger.error(f"User not found: {validated_data.user_id}")
            raise HTTPException(status_code=404, detail=f"User not found: {validated_data.user_id}")
        
        logger.info(f"User validated: {user.email}")
        
        # Validate namespace exists
        # In in-cluster mode, check Kubernetes namespaces
        # In mock mode, check if any ScaledObject exists in this namespace
        
        logger.info(f"Checking namespace validation: _k8s_service={_k8s_service is not None}, mode={_k8s_service.get_mode() if _k8s_service else 'None'}")
        
        if _k8s_service and _k8s_service.get_mode() == "in-cluster":
            logger.info("Using in-cluster mode for namespace validation")
            # Check if namespace exists in Kubernetes
            try:
                namespaces = await _k8s_service.list_namespaces()
                logger.info(f"Available namespaces in cluster: {namespaces}")
                logger.info(f"Requested namespace: {validated_data.namespace}")
                
                if validated_data.namespace not in namespaces:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Namespace '{validated_data.namespace}' not found in Kubernetes. Available namespaces: {', '.join(namespaces)}"
                    )
                logger.info(f"Namespace '{validated_data.namespace}' validated successfully")
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Could not validate namespace in Kubernetes: {e}", exc_info=True)
                # Continue anyway - namespace might exist but we can't verify
        else:
            logger.info("Using mock mode for namespace validation (checking database)")
            # Mock mode - check database
            namespace_result = await session.execute(
                select(_scaled_object_model).where(_scaled_object_model.namespace == validated_data.namespace).limit(1)
            )
            namespace_exists = namespace_result.scalar_one_or_none() is not None
            
            if not namespace_exists:
                logger.error(f"Namespace '{validated_data.namespace}' not found in database")
                raise HTTPException(
                    status_code=404,
                    detail=f"Namespace '{validated_data.namespace}' not found"
                )
        
        # For object-scoped permissions, validate object exists
        if validated_data.scope == "object" and validated_data.object_name:
            if _k8s_service and _k8s_service.get_mode() == "in-cluster":
                # Check if ScaledObject exists in Kubernetes
                try:
                    obj_id = f"{validated_data.namespace}/{validated_data.object_name}"
                    obj = await _k8s_service.get_object(obj_id)
                    
                    if not obj:
                        raise HTTPException(
                            status_code=404,
                            detail=f"ScaledObject '{validated_data.object_name}' not found in namespace '{validated_data.namespace}'"
                        )
                except Exception as e:
                    logger.warning(f"Could not validate ScaledObject in Kubernetes: {e}")
                    # Continue anyway - object might exist but we can't verify
            else:
                # Mock mode - check database
                object_result = await session.execute(
                    select(_scaled_object_model).where(
                        _scaled_object_model.namespace == validated_data.namespace,
                        _scaled_object_model.name == validated_data.object_name
                    )
                )
                obj = object_result.scalar_one_or_none()
                
                if not obj:
                    raise HTTPException(
                        status_code=404,
                        detail=f"ScaledObject '{validated_data.object_name}' not found in namespace '{validated_data.namespace}'"
                    )
        
        # Check if permission already exists
        existing_permission_result = await session.execute(
            select(_permission_model).where(
                _permission_model.user_id == validated_data.user_id,
                _permission_model.action == validated_data.action,
                _permission_model.scope == validated_data.scope,
                _permission_model.namespace == validated_data.namespace,
                _permission_model.object_name == validated_data.object_name
            )
        )
        existing_permission = existing_permission_result.scalar_one_or_none()
        
        if existing_permission:
            raise HTTPException(
                status_code=400,
                detail="Permission already exists for this user"
            )
        
        # Create permission using RBAC engine
        rbac_engine = _rbac_engine_class(
            async_session_maker=_async_session_maker,
            user_model=_user_model,
            permission_model=_permission_model
        )
        
        permission = await rbac_engine.grant_permission(
            user_id=validated_data.user_id,
            action=validated_data.action,
            scope=validated_data.scope,
            namespace=validated_data.namespace,
            object_name=validated_data.object_name,
            created_by=admin_user.get("id") if isinstance(admin_user, dict) else admin_user.id
        )
        
        admin_email = admin_user.get("email", "unknown") if isinstance(admin_user, dict) else getattr(admin_user, "email", "unknown")
        admin_id = admin_user.get("id") if isinstance(admin_user, dict) else admin_user.id
        
        logger.info(
            f"Permission granted by admin {admin_email}: "
            f"user={user.email}, action={validated_data.action}, scope={validated_data.scope}, "
            f"namespace={validated_data.namespace}, object_name={validated_data.object_name}"
        )
        
        # Log permission grant to audit log
        audit_logger.log_permission_granted(
            admin_user_id=admin_id,
            admin_user_email=admin_email,
            target_user_id=user.id,
            target_user_email=user.email,
            action=validated_data.action,
            scope=validated_data.scope,
            namespace=validated_data.namespace,
            object_name=validated_data.object_name,
            permission_id=permission["id"]
        )
        
        return permission


@router.delete("/{permission_id}", status_code=200)
async def delete_permission(
    permission_id: str,
    admin_user: dict = Depends(_require_admin_dependency)
):
    """
    Delete a permission.
    
    Args:
        permission_id: The ID of the permission to delete
        
    Returns:
        Success message
        
    Raises:
        HTTPException 404: If permission not found
        
    Requirements: 8.3
    """
    async with _async_session_maker() as session:
        # Get permission details for logging before deletion
        permission_result = await session.execute(
            select(_permission_model).where(_permission_model.id == permission_id)
        )
        permission = permission_result.scalar_one_or_none()
        
        if not permission:
            raise HTTPException(status_code=404, detail="Permission not found")
        
        # Get user email for logging
        user_result = await session.execute(
            select(_user_model).where(_user_model.id == permission.user_id)
        )
        user = user_result.scalar_one_or_none()
        user_email = user.email if user else "unknown"
        
        # Delete permission using RBAC engine
        rbac_engine = _rbac_engine_class(
            async_session_maker=_async_session_maker,
            user_model=_user_model,
            permission_model=_permission_model
        )
        
        success = await rbac_engine.revoke_permission(permission_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Permission not found")
        
        logger.info(
            f"Permission revoked by admin {admin_user.get('email', 'unknown')}: "
            f"user={user_email}, action={permission.action}, scope={permission.scope}, "
            f"namespace={permission.namespace}, object_name={permission.object_name}"
        )
        
        # Log permission revocation to audit log
        audit_logger.log_permission_revoked(
            admin_user_id=admin_user["id"],
            admin_user_email=admin_user.get("email", "unknown"),
            target_user_id=permission.user_id,
            target_user_email=user_email,
            permission_id=permission_id,
            action=permission.action,
            scope=permission.scope,
            namespace=permission.namespace,
            object_name=permission.object_name
        )
        
        return {"message": "Permission deleted successfully"}
