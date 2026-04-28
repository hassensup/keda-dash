#!/usr/bin/env python3
"""
Quick test to verify audit logger produces correct JSON output.
"""

import json
import sys
import logging
from io import StringIO
from backend.audit.logger import audit_logger

# Capture logs by adding a custom handler
captured_logs = []

class ListHandler(logging.Handler):
    def emit(self, record):
        captured_logs.append(self.format(record))

# Add custom handler to audit logger
handler = ListHandler()
handler.setFormatter(audit_logger.logger.handlers[0].formatter)
audit_logger.logger.addHandler(handler)

# Test authentication events
audit_logger.log_login_success(
    user_id="test-user-123",
    user_email="test@example.com",
    auth_provider="local",
    ip_address="192.168.1.100"
)

audit_logger.log_login_failed(
    email="test@example.com",
    auth_provider="local",
    reason="invalid_password",
    ip_address="192.168.1.100"
)

audit_logger.log_token_validation_failed(
    auth_provider="okta",
    reason="Token signature verification failed",
    token_type="id_token"
)

# Test RBAC events
audit_logger.log_permission_denied(
    user_id="test-user-123",
    user_email="test@example.com",
    action="write",
    resource_type="scaledobject",
    namespace="production",
    object_name="my-app-scaler"
)

# Test permission management events
audit_logger.log_permission_granted(
    admin_user_id="admin-123",
    admin_user_email="admin@example.com",
    target_user_id="test-user-123",
    target_user_email="test@example.com",
    action="read",
    scope="namespace",
    namespace="production",
    permission_id="perm-456"
)

audit_logger.log_permission_revoked(
    admin_user_id="admin-123",
    admin_user_email="admin@example.com",
    target_user_id="test-user-123",
    target_user_email="test@example.com",
    permission_id="perm-456",
    action="read",
    scope="namespace",
    namespace="production"
)

# Parse and validate JSON output
print(f"Generated {len(captured_logs)} audit log entries\n")

for i, line in enumerate(captured_logs, 1):
    try:
        log_entry = json.loads(line)
        print(f"Entry {i}: {log_entry['event_type']}.{log_entry['event_action']}")
        
        # Verify required fields
        assert "timestamp" in log_entry, "Missing timestamp"
        assert "event_type" in log_entry, "Missing event_type"
        assert "event_action" in log_entry, "Missing event_action"
        
        # Verify no sensitive data (actual password values, not the word "password" in reasons)
        details = log_entry.get("details", {})
        assert "password_hash" not in details, "Password hash found in log!"
        assert "token" not in details or details.get("token_type"), "Token value found in log!"
        assert "secret" not in details, "Secret found in log!"
        
        print(f"  ✓ Valid JSON with required fields")
        print(f"  ✓ No sensitive data")
        
    except json.JSONDecodeError as e:
        print(f"  ✗ Invalid JSON: {e}")
        sys.exit(1)
    except AssertionError as e:
        print(f"  ✗ Validation failed: {e}")
        sys.exit(1)

print("\n✅ All audit log entries are valid!")
