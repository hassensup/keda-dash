"""
Unit tests for UserModel with new authentication fields
Tests Requirements 4.5, 4.6, 4.7
"""
import pytest
import sys
import os
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from server import Base, UserModel, PermissionModel
import uuid


@pytest.fixture
def db_session():
    """Create an in-memory SQLite database for testing"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_user_model_has_auth_provider_field(db_session):
    """Test that UserModel has auth_provider field with default 'local'"""
    user = UserModel(
        email="test@example.com",
        name="Test User",
        password_hash="hashed_password"
    )
    db_session.add(user)
    db_session.commit()
    
    assert user.auth_provider == "local"
    assert user.id is not None


def test_user_model_has_okta_subject_field(db_session):
    """Test that UserModel has okta_subject field (nullable)"""
    user = UserModel(
        email="okta@example.com",
        name="Okta User",
        auth_provider="okta",
        okta_subject="00u1234567890abcdef"
    )
    db_session.add(user)
    db_session.commit()
    
    assert user.okta_subject == "00u1234567890abcdef"
    assert user.auth_provider == "okta"


def test_user_model_password_hash_nullable(db_session):
    """Test that password_hash can be NULL for Okta users"""
    user = UserModel(
        email="okta_no_pass@example.com",
        name="Okta User No Password",
        auth_provider="okta",
        okta_subject="00u9876543210fedcba",
        password_hash=None  # Okta users don't have passwords
    )
    db_session.add(user)
    db_session.commit()
    
    assert user.password_hash is None
    assert user.auth_provider == "okta"


def test_user_model_has_permissions_relationship(db_session):
    """Test that UserModel has permissions relationship to PermissionModel"""
    user = UserModel(
        email="user_with_perms@example.com",
        name="User With Permissions",
        password_hash="hashed_password"
    )
    db_session.add(user)
    db_session.commit()
    
    # Add a permission
    permission = PermissionModel(
        user_id=user.id,
        action="read",
        scope="namespace",
        namespace="production"
    )
    db_session.add(permission)
    db_session.commit()
    
    # Refresh user to load relationship
    db_session.refresh(user)
    
    assert len(user.permissions) == 1
    assert user.permissions[0].action == "read"
    assert user.permissions[0].namespace == "production"


def test_permission_model_fields(db_session):
    """Test that PermissionModel has all required fields"""
    user = UserModel(
        email="perm_test@example.com",
        name="Permission Test User",
        password_hash="hashed_password"
    )
    db_session.add(user)
    db_session.commit()
    
    permission = PermissionModel(
        user_id=user.id,
        action="write",
        scope="object",
        namespace="staging",
        object_name="my-scaler",
        created_by="admin_user_id"
    )
    db_session.add(permission)
    db_session.commit()
    
    assert permission.id is not None
    assert permission.user_id == user.id
    assert permission.action == "write"
    assert permission.scope == "object"
    assert permission.namespace == "staging"
    assert permission.object_name == "my-scaler"
    assert permission.created_by == "admin_user_id"
    assert permission.created_at is not None


def test_permission_cascade_delete(db_session):
    """Test that permissions are deleted when user is deleted (cascade)"""
    user = UserModel(
        email="cascade_test@example.com",
        name="Cascade Test User",
        password_hash="hashed_password"
    )
    db_session.add(user)
    db_session.commit()
    
    permission = PermissionModel(
        user_id=user.id,
        action="read",
        scope="namespace",
        namespace="default"
    )
    db_session.add(permission)
    db_session.commit()
    
    permission_id = permission.id
    
    # Delete user
    db_session.delete(user)
    db_session.commit()
    
    # Check that permission was also deleted
    deleted_permission = db_session.query(PermissionModel).filter_by(id=permission_id).first()
    assert deleted_permission is None


def test_local_user_with_password(db_session):
    """Test creating a local user with password hash"""
    user = UserModel(
        email="local@example.com",
        name="Local User",
        password_hash="bcrypt_hashed_password",
        auth_provider="local"
    )
    db_session.add(user)
    db_session.commit()
    
    assert user.password_hash == "bcrypt_hashed_password"
    assert user.auth_provider == "local"
    assert user.okta_subject is None


def test_okta_user_without_password(db_session):
    """Test creating an Okta user without password hash"""
    user = UserModel(
        email="okta_user@example.com",
        name="Okta User",
        auth_provider="okta",
        okta_subject="00uABCDEF123456789",
        password_hash=None
    )
    db_session.add(user)
    db_session.commit()
    
    assert user.password_hash is None
    assert user.auth_provider == "okta"
    assert user.okta_subject == "00uABCDEF123456789"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
