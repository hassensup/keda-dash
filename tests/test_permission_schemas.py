"""
Unit tests for Permission Pydantic schemas
"""
import pytest
from datetime import datetime
from pydantic import ValidationError
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from server import (
    PermissionAction,
    PermissionScope,
    Permission,
    PermissionCreate,
    UserProfile,
    UserWithPermissions
)


class TestPermissionEnums:
    """Test Permission enums"""
    
    def test_permission_action_values(self):
        """Test PermissionAction enum has correct values"""
        assert PermissionAction.READ == "read"
        assert PermissionAction.WRITE == "write"
    
    def test_permission_scope_values(self):
        """Test PermissionScope enum has correct values"""
        assert PermissionScope.NAMESPACE == "namespace"
        assert PermissionScope.OBJECT == "object"


class TestPermissionSchema:
    """Test Permission schema"""
    
    def test_permission_with_object_name(self):
        """Test Permission schema with object_name"""
        perm = Permission(
            id="perm-123",
            user_id="user-456",
            action=PermissionAction.READ,
            scope=PermissionScope.OBJECT,
            namespace="production",
            object_name="my-scaler",
            created_at=datetime.now(),
            created_by="admin-789"
        )
        assert perm.id == "perm-123"
        assert perm.action == PermissionAction.READ
        assert perm.scope == PermissionScope.OBJECT
        assert perm.namespace == "production"
        assert perm.object_name == "my-scaler"
    
    def test_permission_without_object_name(self):
        """Test Permission schema without object_name (namespace scope)"""
        perm = Permission(
            id="perm-123",
            user_id="user-456",
            action=PermissionAction.WRITE,
            scope=PermissionScope.NAMESPACE,
            namespace="staging",
            created_at=datetime.now()
        )
        assert perm.object_name is None
        assert perm.created_by is None


class TestPermissionCreateSchema:
    """Test PermissionCreate schema with validation"""
    
    def test_namespace_scope_without_object_name(self):
        """Test PermissionCreate with namespace scope and no object_name"""
        perm = PermissionCreate(
            user_id="user-123",
            action=PermissionAction.READ,
            scope=PermissionScope.NAMESPACE,
            namespace="production"
        )
        assert perm.object_name is None
    
    def test_object_scope_with_object_name(self):
        """Test PermissionCreate with object scope and object_name"""
        perm = PermissionCreate(
            user_id="user-123",
            action=PermissionAction.WRITE,
            scope=PermissionScope.OBJECT,
            namespace="production",
            object_name="my-scaler"
        )
        assert perm.object_name == "my-scaler"
    
    def test_object_scope_without_object_name_fails(self):
        """Test PermissionCreate with object scope but no object_name raises error"""
        with pytest.raises(ValidationError) as exc_info:
            PermissionCreate(
                user_id="user-123",
                action=PermissionAction.WRITE,
                scope=PermissionScope.OBJECT,
                namespace="production"
            )
        assert "object_name required for object scope" in str(exc_info.value)
    
    def test_namespace_scope_with_object_name_fails(self):
        """Test PermissionCreate with namespace scope but with object_name raises error"""
        with pytest.raises(ValidationError) as exc_info:
            PermissionCreate(
                user_id="user-123",
                action=PermissionAction.READ,
                scope=PermissionScope.NAMESPACE,
                namespace="production",
                object_name="my-scaler"
            )
        assert "object_name must be null for namespace scope" in str(exc_info.value)


class TestUserProfileSchema:
    """Test UserProfile schema"""
    
    def test_user_profile_with_permissions(self):
        """Test UserProfile with permissions list"""
        perm = Permission(
            id="perm-123",
            user_id="user-456",
            action=PermissionAction.READ,
            scope=PermissionScope.NAMESPACE,
            namespace="production",
            created_at=datetime.now()
        )
        
        user = UserProfile(
            id="user-456",
            email="user@example.com",
            name="Test User",
            role="user",
            auth_provider="local",
            permissions=[perm]
        )
        
        assert user.id == "user-456"
        assert user.email == "user@example.com"
        assert len(user.permissions) == 1
        assert user.permissions[0].action == PermissionAction.READ
    
    def test_user_profile_without_permissions(self):
        """Test UserProfile with empty permissions list"""
        user = UserProfile(
            id="user-456",
            email="user@example.com",
            name="Test User",
            role="user",
            auth_provider="okta"
        )
        
        assert user.permissions == []


class TestUserWithPermissionsSchema:
    """Test UserWithPermissions schema"""
    
    def test_user_with_permissions(self):
        """Test UserWithPermissions schema"""
        user = UserProfile(
            id="user-456",
            email="user@example.com",
            name="Test User",
            role="user",
            auth_provider="local",
            permissions=[]
        )
        
        perm = Permission(
            id="perm-123",
            user_id="user-456",
            action=PermissionAction.WRITE,
            scope=PermissionScope.OBJECT,
            namespace="production",
            object_name="my-scaler",
            created_at=datetime.now()
        )
        
        user_with_perms = UserWithPermissions(
            user=user,
            permissions=[perm]
        )
        
        assert user_with_perms.user.id == "user-456"
        assert len(user_with_perms.permissions) == 1
        assert user_with_perms.permissions[0].scope == PermissionScope.OBJECT
