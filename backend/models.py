"""
ORM Models Module

This module contains all SQLAlchemy ORM models to avoid circular imports.
"""

from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from backend.database import Base


def generate_uuid():
    """Generate a UUID string for primary keys."""
    return str(uuid.uuid4())


def get_current_time():
    """Get current datetime for timestamp columns."""
    return datetime.now()


class UserModel(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=True)  # Changed to nullable for Okta users
    name = Column(String, nullable=False)
    role = Column(String, default="user")
    auth_provider = Column(String, default="local")  # 'local' or 'okta'
    okta_subject = Column(String, nullable=True, index=True)  # Okta 'sub' claim
    created_at = Column(DateTime, default=get_current_time)
    updated_at = Column(DateTime, default=get_current_time, onupdate=get_current_time)
    
    # Relationships
    permissions = relationship("PermissionModel", back_populates="user", cascade="all, delete-orphan")


class PermissionModel(Base):
    __tablename__ = "permissions"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    action = Column(String, nullable=False)  # 'read' or 'write'
    scope = Column(String, nullable=False)  # 'namespace' or 'object'
    namespace = Column(String, nullable=False, index=True)
    object_name = Column(String, nullable=True)
    created_at = Column(DateTime, default=get_current_time)
    created_by = Column(String, nullable=True)
    
    # Relationships
    user = relationship("UserModel", back_populates="permissions")


class ScaledObjectModel(Base):
    __tablename__ = "scaled_objects"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    namespace = Column(String, nullable=False, default="default")
    scaler_type = Column(String, nullable=False)
    target_deployment = Column(String, nullable=False)
    min_replicas = Column(Integer, default=0)
    max_replicas = Column(Integer, default=10)
    cooldown_period = Column(Integer, default=300)
    polling_interval = Column(Integer, default=30)
    triggers_json = Column(Text, default="[]")
    scaling_behavior_json = Column(Text, default=None, nullable=True)
    status = Column(String, default="Active")
    created_at = Column(DateTime, default=get_current_time)
    updated_at = Column(DateTime, default=get_current_time)
    cron_events = relationship("CronEventModel", back_populates="scaled_object", cascade="all, delete-orphan")


class CronEventModel(Base):
    __tablename__ = "cron_events"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    scaled_object_id = Column(String, ForeignKey("scaled_objects.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    timezone_str = Column(String, default="UTC")
    desired_replicas = Column(Integer, default=1)
    event_date = Column(String, nullable=False)
    start_time = Column(String, default="00:00")
    end_time = Column(String, default="23:59")
    created_at = Column(DateTime, default=get_current_time)
    updated_at = Column(DateTime, default=get_current_time)
    scaled_object = relationship("ScaledObjectModel", back_populates="cron_events")
