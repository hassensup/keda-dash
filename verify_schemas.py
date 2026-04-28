#!/usr/bin/env python3
"""
Simple verification script for Permission Pydantic schemas
"""
import sys
from pathlib import Path
from datetime import datetime

# Add backend to path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

try:
    from server import (
        PermissionAction,
        PermissionScope,
        Permission,
        PermissionCreate,
        UserProfile,
        UserWithPermissions
    )
    print("✓ Successfully imported all Permission schemas")
    
    # Test PermissionAction enum
    assert PermissionAction.READ == "read"
    assert PermissionAction.WRITE == "write"
    print("✓ PermissionAction enum values correct")
    
    # Test PermissionScope enum
    assert PermissionScope.NAMESPACE == "namespace"
    assert PermissionScope.OBJECT == "object"
    print("✓ PermissionScope enum values correct")
    
    # Test Permission schema
    perm = Permission(
        id="perm-123",
        user_id="user-456",
        action=PermissionAction.READ,
        scope=PermissionScope.NAMESPACE,
        namespace="production",
        created_at=datetime.now()
    )
    assert perm.action == PermissionAction.READ
    print("✓ Permission schema works")
    
    # Test PermissionCreate with namespace scope (valid)
    perm_create = PermissionCreate(
        user_id="user-123",
        action=PermissionAction.READ,
        scope=PermissionScope.NAMESPACE,
        namespace="production"
    )
    assert perm_create.object_name is None
    print("✓ PermissionCreate with namespace scope works")
    
    # Test PermissionCreate with object scope (valid)
    perm_create_obj = PermissionCreate(
        user_id="user-123",
        action=PermissionAction.WRITE,
        scope=PermissionScope.OBJECT,
        namespace="production",
        object_name="my-scaler"
    )
    assert perm_create_obj.object_name == "my-scaler"
    print("✓ PermissionCreate with object scope works")
    
    # Test PermissionCreate validation - object scope without object_name (should fail)
    try:
        invalid_perm = PermissionCreate(
            user_id="user-123",
            action=PermissionAction.WRITE,
            scope=PermissionScope.OBJECT,
            namespace="production"
        )
        print("✗ PermissionCreate validation failed - should have raised error for object scope without object_name")
        sys.exit(1)
    except Exception as e:
        if "object_name required for object scope" in str(e):
            print("✓ PermissionCreate validation works - object scope requires object_name")
        else:
            print(f"✗ Unexpected error: {e}")
            sys.exit(1)
    
    # Test PermissionCreate validation - namespace scope with object_name (should fail)
    try:
        invalid_perm2 = PermissionCreate(
            user_id="user-123",
            action=PermissionAction.READ,
            scope=PermissionScope.NAMESPACE,
            namespace="production",
            object_name="my-scaler"
        )
        print("✗ PermissionCreate validation failed - should have raised error for namespace scope with object_name")
        sys.exit(1)
    except Exception as e:
        if "object_name must be null for namespace scope" in str(e):
            print("✓ PermissionCreate validation works - namespace scope cannot have object_name")
        else:
            print(f"✗ Unexpected error: {e}")
            sys.exit(1)
    
    # Test UserProfile schema
    user = UserProfile(
        id="user-456",
        email="user@example.com",
        name="Test User",
        role="user",
        auth_provider="local",
        permissions=[perm]
    )
    assert len(user.permissions) == 1
    print("✓ UserProfile schema works")
    
    # Test UserWithPermissions schema
    user_with_perms = UserWithPermissions(
        user=user,
        permissions=[perm]
    )
    assert user_with_perms.user.id == "user-456"
    print("✓ UserWithPermissions schema works")
    
    print("\n✅ All Permission schemas verified successfully!")
    sys.exit(0)
    
except ImportError as e:
    print(f"✗ Failed to import schemas: {e}")
    sys.exit(1)
except Exception as e:
    print(f"✗ Verification failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
