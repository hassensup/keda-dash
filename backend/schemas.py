"""
Pydantic Schemas Module

This module provides shared Pydantic schemas to avoid circular imports.
"""

from pydantic import BaseModel, validator
from typing import List, Optional
from enum import Enum
from datetime import datetime


# ============ AUTH SCHEMAS ============
class LoginRequest(BaseModel):
    email: str
    password: str


# ============ PERMISSION SCHEMAS ============
class PermissionAction(str, Enum):
    READ = "read"
    WRITE = "write"


class PermissionScope(str, Enum):
    NAMESPACE = "namespace"
    OBJECT = "object"


class Permission(BaseModel):
    id: str
    user_id: str
    action: PermissionAction
    scope: PermissionScope
    namespace: str
    object_name: Optional[str] = None
    created_at: datetime
    created_by: Optional[str] = None


class PermissionCreate(BaseModel):
    user_id: str
    action: PermissionAction
    scope: PermissionScope
    namespace: str
    object_name: Optional[str] = None
    
    @validator('object_name')
    def validate_object_name(cls, v, values):
        if values.get('scope') == PermissionScope.OBJECT and not v:
            raise ValueError('object_name required for object scope')
        if values.get('scope') == PermissionScope.NAMESPACE and v:
            raise ValueError('object_name must be null for namespace scope')
        return v


class UserProfile(BaseModel):
    id: str
    email: str
    name: str
    role: str
    auth_provider: str
    permissions: List[Permission] = []


class UserWithPermissions(BaseModel):
    user: UserProfile
    permissions: List[Permission]


# ============ SCALEDOBJECT SCHEMAS ============
class ScaledObjectCreate(BaseModel):
    name: str
    namespace: str = "default"
    scaler_type: str
    target_deployment: str
    min_replicas: int = 0
    max_replicas: int = 10
    cooldown_period: int = 300
    polling_interval: int = 30
    triggers: list = []
    scaling_behavior: Optional[dict] = None


class ScaledObjectUpdate(BaseModel):
    name: Optional[str] = None
    namespace: Optional[str] = None
    scaler_type: Optional[str] = None
    target_deployment: Optional[str] = None
    min_replicas: Optional[int] = None
    max_replicas: Optional[int] = None
    cooldown_period: Optional[int] = None
    polling_interval: Optional[int] = None
    triggers: Optional[list] = None
    scaling_behavior: Optional[dict] = None
    status: Optional[str] = None


# ============ CRON EVENT SCHEMAS ============
class CronEventCreate(BaseModel):
    scaled_object_id: str
    name: str
    timezone_str: str = "UTC"
    desired_replicas: int = 1
    event_date: str
    start_time: str = "00:00"
    end_time: str = "23:59"


class CronEventUpdate(BaseModel):
    name: Optional[str] = None
    timezone_str: Optional[str] = None
    desired_replicas: Optional[int] = None
    event_date: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    scaled_object_id: Optional[str] = None
