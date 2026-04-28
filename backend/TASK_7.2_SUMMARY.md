# Task 7.2 Implementation Summary: Permission Decorator

## Overview
Implemented the `require_permission()` decorator in `backend/rbac/middleware.py` to enforce RBAC permissions on FastAPI routes.

## Implementation Details

### 1. Added Global State Management
- Added global variables `_async_session_maker`, `_user_model`, `_permission_model` to store references
- Created `initialize_middleware()` function to set these references at application startup
- This avoids creating new database connections on every request

### 2. Implemented `require_permission()` Function
The function signature:
```python
def require_permission(
    action: str,
    resource_type: str,
    namespace_param: str,
    object_param: Optional[str] = None
) -> Callable
```

**Parameters:**
- `action`: The action type ("read" or "write")
- `resource_type`: The resource type (e.g., "scaledobject")
- `namespace_param`: The name of the path parameter containing the namespace
- `object_param`: The name of the path parameter containing the object name (optional)

**Returns:**
- A FastAPI dependency function that checks permissions

### 3. Permission Checking Logic
The returned dependency function:
1. Gets the current user via `get_current_user_with_permissions`
2. Extracts `namespace` from `request.path_params[namespace_param]`
3. Extracts `object_name` from `request.path_params[object_param]` (if provided)
4. Initializes `RBACEngine` with the global session maker and models
5. Calls `rbac_engine.check_permission()` with user_id, action, resource_type, namespace, and object_name
6. Raises `HTTPException(403)` if permission denied with detailed error message
7. Returns user dict if permission granted

### 4. Error Handling
- **400 Bad Request**: If required path parameters are missing
- **403 Forbidden**: If user lacks required permissions (includes details about what was required)
- **500 Internal Server Error**: If middleware not initialized

### 5. Example Usage
```python
from fastapi import Depends
from backend.rbac.middleware import require_permission

@router.get(
    "/scaled-objects/{namespace}/{name}",
    dependencies=[Depends(require_permission("read", "scaledobject", "namespace", "name"))]
)
async def get_scaled_object(namespace: str, name: str):
    # Route handler code
    pass
```

## Integration Requirements

**IMPORTANT**: Before the decorator can be used, `server.py` must call `initialize_middleware()` during application startup:

```python
from backend.rbac.middleware import initialize_middleware

# After creating async_session_maker and models
initialize_middleware(
    async_session_maker=async_session_maker,
    user_model=UserModel,
    permission_model=PermissionModel
)
```

## Files Modified
- `backend/rbac/middleware.py`: Added `initialize_middleware()` and `require_permission()` functions

## Requirements Validated
- **Requirement 6.6**: Permission enforcement on ScaledObject operations

## Testing Notes
- The decorator is ready to be used on routes
- Integration with server.py is required via `initialize_middleware()`
- No tests were written per task instructions ("NO TESTS - Skip all test tasks")

## Next Steps
1. Call `initialize_middleware()` in `server.py` during application startup
2. Apply the decorator to ScaledObject routes that need permission enforcement
3. Test the decorator with various permission scenarios
