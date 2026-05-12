# Permission Creation Fix - K8s Service Integration

## Problem
When admin users tried to create permissions, the system returned:
```
AttributeError: 'NoneType' object has no attribute 'get_mode'
```

This occurred because the `k8s_service` parameter was not being passed to the permissions router during initialization.

## Root Cause
1. The `initialize_permissions_router()` function was updated to accept a `k8s_service` parameter
2. However, the call to this function in `backend/server.py` was not updated to pass the parameter
3. This caused `_k8s_service` to remain `None` in the permissions router
4. When validation logic tried to call `k8s_service.get_mode()`, it failed with AttributeError

## Solution
Updated `backend/server.py` to pass `k8s_service` parameter when initializing the permissions router:

```python
initialize_permissions_router(
    async_session_maker=async_session_maker,
    user_model=UserModel,
    permission_model=PermissionModel,
    scaled_object_model=ScaledObjectModel,
    permission_schema=Permission,
    permission_create_schema=PermissionCreate,
    get_current_user=get_current_user,
    rbac_engine_class=RBACEngine,
    k8s_service=k8s_service  # ← Added this parameter
)
```

Also fixed a bug in `backend/permissions/router.py` where ScaledObject validation was using `k8s_service` instead of `_k8s_service`.

## Changes Made
- **backend/server.py**: Added `k8s_service=k8s_service` parameter to `initialize_permissions_router()` call
- **backend/permissions/router.py**: Fixed ScaledObject validation to use `_k8s_service` instead of `k8s_service`

## Validation Logic
With this fix, the permission creation endpoint now properly:
1. Validates namespaces exist in Kubernetes (in-cluster mode)
2. Validates ScaledObjects exist in Kubernetes (for object-scoped permissions)
3. Falls back to database validation in mock mode

## Testing
After deploying this fix, admin users should be able to:
1. Navigate to Admin → Permissions
2. Click "Add Permission"
3. Select a user, namespace (e.g., "test"), and permission level
4. Successfully create the permission without errors

## Commit
```
commit b9b29cb
fix: Pass k8s_service to permissions router initialization
```

## Next Steps
1. Deploy the updated backend to the cluster
2. Test permission creation with namespace "test"
3. Verify that namespace validation works correctly in in-cluster mode
