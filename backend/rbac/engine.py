"""
RBAC Engine for permission evaluation and enforcement.

This module implements the Role-Based Access Control engine that evaluates
user permissions against requested resource actions.
"""

from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.audit import logger as audit_logger


class RBACEngine:
    """
    RBAC Engine for evaluating user permissions.
    
    Permission Evaluation Logic:
    1. Admin users (role="admin") bypass all checks - always return True
    2. Check object-scoped permissions (scope="object", matching namespace and object_name)
    3. Check namespace-scoped permissions (scope="namespace", matching namespace)
    4. Default deny - return False if no matching permission
    """
    
    def __init__(self, async_session_maker, user_model, permission_model):
        """
        Initialize the RBAC Engine.
        
        Args:
            async_session_maker: SQLAlchemy async session maker
            user_model: UserModel ORM class
            permission_model: PermissionModel ORM class
        """
        self.async_session_maker = async_session_maker
        self.UserModel = user_model
        self.PermissionModel = permission_model
    
    async def check_permission(
        self,
        user_id: str,
        action: str,  # "read" or "write"
        resource_type: str,  # "scaledobject"
        namespace: str,
        object_name: Optional[str] = None
    ) -> bool:
        """
        Check if user has permission for action on resource.
        
        Args:
            user_id: The ID of the user requesting access
            action: The action being requested ("read" or "write")
            resource_type: The type of resource (e.g., "scaledobject")
            namespace: The Kubernetes namespace of the resource
            object_name: The name of the specific object (optional)
            
        Returns:
            True if user has permission, False otherwise
            
        Permission Evaluation Order:
            1. Admin role bypass - admins have all permissions
            2. Object-scoped permissions - specific object access
            3. Namespace-scoped permissions - namespace-wide access
            4. Default deny - no matching permission found
            
        Requirements: 13.3 - Logs permission denials
        """
        async with self.async_session_maker() as session:
            # Step 1: Check if user is admin (admin bypass logic)
            user_result = await session.execute(
                select(self.UserModel).where(self.UserModel.id == user_id)
            )
            user = user_result.scalar_one_or_none()
            
            if not user:
                # User doesn't exist - deny access and log
                audit_logger.log_permission_denied(
                    user_id=user_id,
                    user_email="unknown",
                    action=action,
                    resource_type=resource_type,
                    namespace=namespace,
                    object_name=object_name
                )
                return False
            
            if user.role == "admin":
                # Admin users bypass all permission checks
                return True
            
            # Step 2: Check object-scoped permissions (if object_name provided)
            if object_name:
                object_permission_result = await session.execute(
                    select(self.PermissionModel).where(
                        self.PermissionModel.user_id == user_id,
                        self.PermissionModel.scope == "object",
                        self.PermissionModel.namespace == namespace,
                        self.PermissionModel.object_name == object_name
                    )
                )
                object_permissions = object_permission_result.scalars().all()
                
                # Check if any object-scoped permission matches the requested action
                for perm in object_permissions:
                    if perm.action == action:
                        return True
                    # Write permission implies read permission
                    if action == "read" and perm.action == "write":
                        return True
            
            # Step 3: Check namespace-scoped permissions
            namespace_permission_result = await session.execute(
                select(self.PermissionModel).where(
                    self.PermissionModel.user_id == user_id,
                    self.PermissionModel.scope == "namespace",
                    self.PermissionModel.namespace == namespace
                )
            )
            namespace_permissions = namespace_permission_result.scalars().all()
            
            # Check if any namespace-scoped permission matches the requested action
            for perm in namespace_permissions:
                if perm.action == action:
                    return True
                # Write permission implies read permission
                if action == "read" and perm.action == "write":
                    return True
            
            # Step 4: Default deny - no matching permission found
            # Log permission denial
            audit_logger.log_permission_denied(
                user_id=user.id,
                user_email=user.email,
                action=action,
                resource_type=resource_type,
                namespace=namespace,
                object_name=object_name
            )
            
            return False
    
    async def filter_objects_by_permission(
        self,
        user_id: str,
        objects: list,  # List of dicts with "namespace" and "name" keys
        action: str  # "read" or "write"
    ) -> list:
        """
        Filter objects list to only those user has permission to access.
        
        Args:
            user_id: The ID of the user requesting access
            objects: List of objects (dicts with "namespace" and "name" keys)
            action: The action being requested ("read" or "write")
            
        Returns:
            Filtered list of objects user has permission for
            
        Implementation:
            For each object, call check_permission() to evaluate access.
            Return only objects where check_permission() returns True.
        """
        filtered_objects = []
        
        for obj in objects:
            namespace = obj.get("namespace")
            object_name = obj.get("name")
            
            # Check permission for this specific object
            has_permission = await self.check_permission(
                user_id=user_id,
                action=action,
                resource_type="scaledobject",
                namespace=namespace,
                object_name=object_name
            )
            
            if has_permission:
                filtered_objects.append(obj)
        
        return filtered_objects
    
    async def get_user_permissions(self, user_id: str) -> list:
        """
        Get all permissions for a user.
        
        Args:
            user_id: The ID of the user
            
        Returns:
            List of permission dictionaries with keys: id, user_id, action, 
            scope, namespace, object_name, created_at, created_by
        """
        async with self.async_session_maker() as session:
            # Query all permissions for the user
            result = await session.execute(
                select(self.PermissionModel).where(
                    self.PermissionModel.user_id == user_id
                )
            )
            permissions = result.scalars().all()
            
            # Convert ORM objects to dictionaries
            return [
                {
                    "id": perm.id,
                    "user_id": perm.user_id,
                    "action": perm.action,
                    "scope": perm.scope,
                    "namespace": perm.namespace,
                    "object_name": perm.object_name,
                    "created_at": perm.created_at,
                    "created_by": perm.created_by
                }
                for perm in permissions
            ]
    
    async def grant_permission(
        self,
        user_id: str,
        action: str,
        scope: str,
        namespace: str,
        object_name: Optional[str] = None,
        created_by: Optional[str] = None
    ) -> dict:
        """
        Grant a permission to a user.
        
        Args:
            user_id: The ID of the user to grant permission to
            action: The action type ("read" or "write")
            scope: The scope type ("namespace" or "object")
            namespace: The Kubernetes namespace
            object_name: The object name (required for object scope, None for namespace scope)
            created_by: The ID of the admin user granting the permission (optional)
            
        Returns:
            Dictionary representation of the created permission with keys: id, user_id, 
            action, scope, namespace, object_name, created_at, created_by
        """
        async with self.async_session_maker() as session:
            # Create new permission
            new_permission = self.PermissionModel(
                user_id=user_id,
                action=action,
                scope=scope,
                namespace=namespace,
                object_name=object_name,
                created_by=created_by
            )
            
            session.add(new_permission)
            await session.commit()
            await session.refresh(new_permission)
            
            # Return as dictionary
            return {
                "id": new_permission.id,
                "user_id": new_permission.user_id,
                "action": new_permission.action,
                "scope": new_permission.scope,
                "namespace": new_permission.namespace,
                "object_name": new_permission.object_name,
                "created_at": new_permission.created_at,
                "created_by": new_permission.created_by
            }
    
    async def revoke_permission(self, permission_id: str) -> bool:
        """
        Revoke a permission.
        
        Args:
            permission_id: The ID of the permission to revoke
            
        Returns:
            True if permission was found and deleted, False if permission not found
        """
        async with self.async_session_maker() as session:
            # Query the permission
            result = await session.execute(
                select(self.PermissionModel).where(
                    self.PermissionModel.id == permission_id
                )
            )
            permission = result.scalar_one_or_none()
            
            if not permission:
                # Permission not found
                return False
            
            # Delete the permission
            await session.delete(permission)
            await session.commit()
            
            return True
