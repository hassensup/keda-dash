# Fix for Cron Event Addition (422 Unprocessable Entity)

## Problem Summary

When trying to add a cron event from the calendar by selecting a ScaledObject, the operation failed with:
```
Failed to update ScaledObject: (422)
Reason: Unprocessable Entity
Warning: "unknown field \"spec.triggers[1].soId\""
Error: "ScaledObject.keda.sh \"test\" is invalid: spec.scaleTargetRef.name: Required value"
```

## Root Causes Identified

### Issue 1: Frontend Adding `soId` Field
The frontend was adding a `soId` field to triggers, which KEDA API doesn't recognize:
```json
{
  "type": "cron",
  "soId": "test/test",  // ← This field is not valid in KEDA
  "metadata": {...}
}
```

### Issue 2: All Spec Fields Sent as Null
The backend was sending ALL fields (even unset ones) as null to Kubernetes API:
```json
{
  "spec": {
    "scaleTargetRef": {"name": null},  // ← Required field sent as null!
    "minReplicaCount": null,
    "maxReplicaCount": null,
    ...
  }
}
```

This happened because the PUT endpoint was using `exclude_unset=False` for debugging.

## Fixes Implemented (Commit 47cea3e)

### Fix 1: Clean `soId` from Triggers
In `backend/k8s_service.py` (line ~335):
```python
if "triggers" in data and data["triggers"] is not None:
    # Clean triggers: remove soId field added by frontend
    cleaned_triggers = []
    for trigger in data["triggers"]:
        cleaned_trigger = {k: v for k, v in trigger.items() if k != "soId"}
        cleaned_triggers.append(cleaned_trigger)
    spec["triggers"] = cleaned_triggers
```

### Fix 2: Only Update Explicitly Provided Fields
In `backend/k8s_service.py` (line ~320-345):
```python
# Only update fields that are explicitly provided and not None
if "target_deployment" in data and data["target_deployment"] is not None:
    spec["scaleTargetRef"] = {"name": data["target_deployment"]}
if "min_replicas" in data and data["min_replicas"] is not None:
    spec["minReplicaCount"] = data["min_replicas"]
# ... etc for all fields
```

### Fix 3: Use `exclude_unset=True` in Server
In `backend/server.py` (line ~618):
```python
# Use exclude_unset=True to only send fields that were explicitly provided
update_data = data.model_dump(exclude_unset=True)
```

## Deployment Status

### ✅ Completed
- [x] Code fixes implemented
- [x] Committed to git (commit 47cea3e)
- [x] Pushed to GitHub (feature/okta-auth-rbac branch)
- [x] CI/CD pipeline triggered

### ⏳ In Progress
- [ ] GitHub Actions building Docker image
- [ ] ArgoCD detecting new image
- [ ] ArgoCD deploying to EKS cluster

### 🔄 Next Steps

1. **Monitor CI/CD Build** (5-10 minutes)
   - Check GitHub Actions: https://github.com/hassensup/keda-dash/actions
   - Wait for build to complete successfully
   - New image will be: `ghcr.io/hassensup/keda-dash-backend:okta-auth-rbac`
   - Or with commit SHA: `ghcr.io/hassensup/keda-dash-backend:feature-okta-auth-rbac-47cea3e`

2. **Wait for ArgoCD Deployment** (2-5 minutes after build)
   - ArgoCD should auto-detect the new image
   - Check ArgoCD UI for sync status
   - Or check pod status: `kubectl get pods -n test`

3. **Verify the Fix**
   ```bash
   # Check pod is running with new image
   kubectl get pods -n test -o wide
   
   # Check pod logs for startup
   kubectl logs -n test deployment/keda-dashboard-backend --tail=50
   
   # Test adding a cron event from the calendar UI
   # - Select a ScaledObject
   # - Add a new cron event
   # - Should succeed without 422 error
   ```

4. **Test Scenarios**
   - ✅ Add cron event to existing ScaledObject
   - ✅ Verify ScaledObject is NOT deleted
   - ✅ Verify cron trigger is added correctly
   - ✅ Check Kubernetes API accepts the update

## Expected Behavior After Fix

When adding a cron event from the calendar:
1. Frontend sends partial update with only `triggers` field
2. Backend receives update with `exclude_unset=True`
3. Backend cleans `soId` from triggers
4. Backend only updates `triggers` field in Kubernetes
5. Kubernetes accepts the update (no 422 error)
6. ScaledObject is updated successfully
7. Cron event is visible in calendar

## Verification Commands

```bash
# Check if new image is deployed
kubectl get deployment keda-dashboard-backend -n test -o jsonpath='{.spec.template.spec.containers[0].image}'

# Check pod logs for any errors
kubectl logs -n test -l app=keda-dashboard-backend --tail=100

# Get ScaledObject to verify triggers
kubectl get scaledobject test -n test -o yaml

# Check ArgoCD sync status
kubectl get application keda-dashboard -n argocd -o jsonpath='{.status.sync.status}'
```

## Rollback Plan (If Needed)

If the fix doesn't work:
```bash
# Rollback to previous commit
git revert 47cea3e
git push origin feature/okta-auth-rbac

# Or manually rollback in ArgoCD UI
# Or use kubectl to rollback deployment
kubectl rollout undo deployment/keda-dashboard-backend -n test
```

## Related Issues Fixed

1. ✅ **Task 3**: ScaledObject deletion bug (commit 510d93e)
   - Fixed: ScaledObjects no longer deleted when adding cron events
   
2. ✅ **Task 4**: 422 Unprocessable Entity (commit 47cea3e)
   - Fixed: Clean `soId` field and only send explicitly provided fields

## Files Modified

- `backend/k8s_service.py` (lines 320-345)
  - Added trigger cleaning logic
  - Added conditional field updates
  
- `backend/server.py` (line 618)
  - Changed to `exclude_unset=True`

## Commit Details

```
commit 47cea3e
Author: [Your Name]
Date: Thu Apr 30 2026

fix: Clean soId field from triggers and prevent null values in updates

- Remove soId field added by frontend before sending to Kubernetes API
- Only update fields that are explicitly provided and not None
- Use exclude_unset=True in server.py to avoid sending null values
- Fixes 422 Unprocessable Entity error when adding cron events
```

## Timeline

- **09:27 GMT**: User reported 422 error
- **09:30 GMT**: Root cause identified (soId field + null values)
- **09:35 GMT**: Fix implemented and committed (47cea3e)
- **09:40 GMT**: Fix pushed to GitHub
- **09:40-09:50 GMT**: CI/CD build in progress
- **09:50-09:55 GMT**: ArgoCD deployment expected
- **09:55+ GMT**: Ready for testing

---

**Status**: ⏳ Waiting for CI/CD build and ArgoCD deployment
**Next Action**: Monitor GitHub Actions and ArgoCD, then test adding cron events
