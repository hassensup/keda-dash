"""
Audit Logging Module

This module provides structured JSON logging for security-relevant events
including authentication, authorization, and permission management.

Requirements: 13.1, 13.2, 13.3, 13.4, 13.5, 13.6, 13.7
"""

import logging
import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any


class AuditLogger:
    """
    Audit logger for security-relevant events.
    
    Logs events in structured JSON format with:
    - timestamp: ISO 8601 timestamp in UTC
    - event_type: Type of event (auth, rbac, permission_management)
    - event_action: Specific action (login_success, login_failed, permission_denied, etc.)
    - user_id: ID of the user (if applicable)
    - user_email: Email of the user (if applicable)
    - details: Event-specific details
    
    CRITICAL: Does NOT log sensitive data (passwords, tokens, secrets)
    """
    
    def __init__(self, logger_name: str = "audit"):
        """
        Initialize the audit logger.
        
        Args:
            logger_name: Name of the logger (default: "audit")
        """
        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(logging.INFO)
        
        # Create console handler with JSON formatter if not already configured
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setLevel(logging.INFO)
            formatter = JSONFormatter()
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def _log_event(
        self,
        event_type: str,
        event_action: str,
        user_id: Optional[str] = None,
        user_email: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Log an audit event in structured JSON format.
        
        Args:
            event_type: Type of event (auth, rbac, permission_management)
            event_action: Specific action within the event type
            user_id: ID of the user (optional)
            user_email: Email of the user (optional)
            details: Additional event-specific details (optional)
        """
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "event_action": event_action
        }
        
        if user_id:
            event["user_id"] = user_id
        
        if user_email:
            event["user_email"] = user_email
        
        if details:
            event["details"] = details
        
        # Log as INFO level with JSON structure
        self.logger.info(json.dumps(event))
    
    # ============ AUTHENTICATION EVENTS ============
    
    def log_login_success(
        self,
        user_id: str,
        user_email: str,
        auth_provider: str,
        ip_address: Optional[str] = None
    ):
        """
        Log successful authentication.
        
        Args:
            user_id: ID of the authenticated user
            user_email: Email of the authenticated user
            auth_provider: Authentication provider used (local, okta)
            ip_address: IP address of the client (optional)
            
        Requirements: 13.1, 13.5
        """
        details = {"auth_provider": auth_provider}
        if ip_address:
            details["ip_address"] = ip_address
        
        self._log_event(
            event_type="auth",
            event_action="login_success",
            user_id=user_id,
            user_email=user_email,
            details=details
        )
    
    def log_login_failed(
        self,
        email: str,
        auth_provider: str,
        reason: str,
        ip_address: Optional[str] = None
    ):
        """
        Log failed authentication attempt.
        
        Args:
            email: Email attempted for authentication
            auth_provider: Authentication provider used (local, okta)
            reason: Reason for failure (invalid_credentials, user_not_found, etc.)
            ip_address: IP address of the client (optional)
            
        Requirements: 13.2, 13.5
        """
        details = {
            "auth_provider": auth_provider,
            "reason": reason
        }
        if ip_address:
            details["ip_address"] = ip_address
        
        self._log_event(
            event_type="auth",
            event_action="login_failed",
            user_email=email,
            details=details
        )
    
    def log_token_validation_failed(
        self,
        auth_provider: str,
        reason: str,
        token_type: Optional[str] = None
    ):
        """
        Log token validation failure (Okta ID token, JWT, etc.).
        
        Args:
            auth_provider: Authentication provider (okta, local)
            reason: Reason for validation failure
            token_type: Type of token (id_token, access_token, jwt)
            
        Requirements: 13.5
        """
        details = {
            "auth_provider": auth_provider,
            "reason": reason
        }
        if token_type:
            details["token_type"] = token_type
        
        self._log_event(
            event_type="auth",
            event_action="token_validation_failed",
            details=details
        )
    
    # ============ RBAC EVENTS ============
    
    def log_permission_denied(
        self,
        user_id: str,
        user_email: str,
        action: str,
        resource_type: str,
        namespace: str,
        object_name: Optional[str] = None
    ):
        """
        Log permission denial by RBAC engine.
        
        Args:
            user_id: ID of the user denied access
            user_email: Email of the user denied access
            action: Action that was denied (read, write)
            resource_type: Type of resource (scaledobject)
            namespace: Kubernetes namespace
            object_name: Name of the specific object (optional)
            
        Requirements: 13.3
        """
        details = {
            "action": action,
            "resource_type": resource_type,
            "namespace": namespace
        }
        if object_name:
            details["object_name"] = object_name
        
        self._log_event(
            event_type="rbac",
            event_action="permission_denied",
            user_id=user_id,
            user_email=user_email,
            details=details
        )
    
    # ============ PERMISSION MANAGEMENT EVENTS ============
    
    def log_permission_granted(
        self,
        admin_user_id: str,
        admin_user_email: str,
        target_user_id: str,
        target_user_email: str,
        action: str,
        scope: str,
        namespace: str,
        object_name: Optional[str] = None,
        permission_id: Optional[str] = None
    ):
        """
        Log permission grant by admin.
        
        Args:
            admin_user_id: ID of the admin granting permission
            admin_user_email: Email of the admin granting permission
            target_user_id: ID of the user receiving permission
            target_user_email: Email of the user receiving permission
            action: Action granted (read, write)
            scope: Scope of permission (namespace, object)
            namespace: Kubernetes namespace
            object_name: Name of the specific object (optional)
            permission_id: ID of the created permission (optional)
            
        Requirements: 13.4
        """
        details = {
            "admin_user_id": admin_user_id,
            "admin_user_email": admin_user_email,
            "target_user_id": target_user_id,
            "target_user_email": target_user_email,
            "action": action,
            "scope": scope,
            "namespace": namespace
        }
        if object_name:
            details["object_name"] = object_name
        if permission_id:
            details["permission_id"] = permission_id
        
        self._log_event(
            event_type="permission_management",
            event_action="permission_granted",
            user_id=admin_user_id,
            user_email=admin_user_email,
            details=details
        )
    
    def log_permission_revoked(
        self,
        admin_user_id: str,
        admin_user_email: str,
        target_user_id: str,
        target_user_email: str,
        permission_id: str,
        action: str,
        scope: str,
        namespace: str,
        object_name: Optional[str] = None
    ):
        """
        Log permission revocation by admin.
        
        Args:
            admin_user_id: ID of the admin revoking permission
            admin_user_email: Email of the admin revoking permission
            target_user_id: ID of the user losing permission
            target_user_email: Email of the user losing permission
            permission_id: ID of the revoked permission
            action: Action revoked (read, write)
            scope: Scope of permission (namespace, object)
            namespace: Kubernetes namespace
            object_name: Name of the specific object (optional)
            
        Requirements: 13.4
        """
        details = {
            "admin_user_id": admin_user_id,
            "admin_user_email": admin_user_email,
            "target_user_id": target_user_id,
            "target_user_email": target_user_email,
            "permission_id": permission_id,
            "action": action,
            "scope": scope,
            "namespace": namespace
        }
        if object_name:
            details["object_name"] = object_name
        
        self._log_event(
            event_type="permission_management",
            event_action="permission_revoked",
            user_id=admin_user_id,
            user_email=admin_user_email,
            details=details
        )


class JSONFormatter(logging.Formatter):
    """
    Custom JSON formatter for audit logs.
    
    Formats log records as JSON strings for structured logging.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON string.
        
        Args:
            record: Log record to format
            
        Returns:
            JSON-formatted log string
        """
        # The message should already be JSON from AuditLogger._log_event
        # Just return it as-is
        return record.getMessage()


# Global audit logger instance
audit_logger = AuditLogger()


# Export convenience functions
def log_login_success(user_id: str, user_email: str, auth_provider: str, ip_address: Optional[str] = None):
    """Log successful authentication."""
    audit_logger.log_login_success(user_id, user_email, auth_provider, ip_address)


def log_login_failed(email: str, auth_provider: str, reason: str, ip_address: Optional[str] = None):
    """Log failed authentication attempt."""
    audit_logger.log_login_failed(email, auth_provider, reason, ip_address)


def log_token_validation_failed(auth_provider: str, reason: str, token_type: Optional[str] = None):
    """Log token validation failure."""
    audit_logger.log_token_validation_failed(auth_provider, reason, token_type)


def log_permission_denied(
    user_id: str,
    user_email: str,
    action: str,
    resource_type: str,
    namespace: str,
    object_name: Optional[str] = None
):
    """Log permission denial."""
    audit_logger.log_permission_denied(user_id, user_email, action, resource_type, namespace, object_name)


def log_permission_granted(
    admin_user_id: str,
    admin_user_email: str,
    target_user_id: str,
    target_user_email: str,
    action: str,
    scope: str,
    namespace: str,
    object_name: Optional[str] = None,
    permission_id: Optional[str] = None
):
    """Log permission grant."""
    audit_logger.log_permission_granted(
        admin_user_id, admin_user_email, target_user_id, target_user_email,
        action, scope, namespace, object_name, permission_id
    )


def log_permission_revoked(
    admin_user_id: str,
    admin_user_email: str,
    target_user_id: str,
    target_user_email: str,
    permission_id: str,
    action: str,
    scope: str,
    namespace: str,
    object_name: Optional[str] = None
):
    """Log permission revocation."""
    audit_logger.log_permission_revoked(
        admin_user_id, admin_user_email, target_user_id, target_user_email,
        permission_id, action, scope, namespace, object_name
    )
