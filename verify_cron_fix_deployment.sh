#!/bin/bash

# Verification script for cron event fix deployment
# This script checks if the new image has been deployed and is running

set -e

NAMESPACE="test"
DEPLOYMENT="keda-dashboard-backend"
EXPECTED_COMMIT="47cea3e"

echo "=========================================="
echo "Cron Event Fix Deployment Verification"
echo "=========================================="
echo ""

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl not found. Please install kubectl first."
    exit 1
fi

echo "1. Checking current deployment image..."
CURRENT_IMAGE=$(kubectl get deployment $DEPLOYMENT -n $NAMESPACE -o jsonpath='{.spec.template.spec.containers[0].image}' 2>/dev/null || echo "NOT_FOUND")

if [ "$CURRENT_IMAGE" = "NOT_FOUND" ]; then
    echo "❌ Deployment not found in namespace $NAMESPACE"
    exit 1
fi

echo "   Current image: $CURRENT_IMAGE"

if [[ "$CURRENT_IMAGE" == *"$EXPECTED_COMMIT"* ]] || [[ "$CURRENT_IMAGE" == *"okta-auth-rbac"* ]]; then
    echo "   ✅ Image contains expected tag"
else
    echo "   ⚠️  Image does not contain expected commit SHA or branch tag"
    echo "   Expected: commit $EXPECTED_COMMIT or tag okta-auth-rbac"
fi

echo ""
echo "2. Checking pod status..."
POD_STATUS=$(kubectl get pods -n $NAMESPACE -l app=$DEPLOYMENT -o jsonpath='{.items[0].status.phase}' 2>/dev/null || echo "NOT_FOUND")
POD_NAME=$(kubectl get pods -n $NAMESPACE -l app=$DEPLOYMENT -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "NOT_FOUND")

if [ "$POD_STATUS" = "NOT_FOUND" ]; then
    echo "   ❌ No pods found for deployment $DEPLOYMENT"
    exit 1
fi

echo "   Pod name: $POD_NAME"
echo "   Pod status: $POD_STATUS"

if [ "$POD_STATUS" = "Running" ]; then
    echo "   ✅ Pod is running"
else
    echo "   ⚠️  Pod is not running yet (status: $POD_STATUS)"
fi

echo ""
echo "3. Checking pod readiness..."
READY=$(kubectl get pods -n $NAMESPACE -l app=$DEPLOYMENT -o jsonpath='{.items[0].status.conditions[?(@.type=="Ready")].status}' 2>/dev/null || echo "Unknown")
echo "   Ready status: $READY"

if [ "$READY" = "True" ]; then
    echo "   ✅ Pod is ready"
else
    echo "   ⚠️  Pod is not ready yet"
fi

echo ""
echo "4. Checking recent pod logs..."
echo "   Last 10 lines of logs:"
echo "   ---"
kubectl logs -n $NAMESPACE $POD_NAME --tail=10 2>/dev/null || echo "   ❌ Could not fetch logs"
echo "   ---"

echo ""
echo "5. Checking for errors in logs..."
ERROR_COUNT=$(kubectl logs -n $NAMESPACE $POD_NAME --tail=100 2>/dev/null | grep -i "error\|exception\|failed" | wc -l || echo "0")
echo "   Error count in last 100 lines: $ERROR_COUNT"

if [ "$ERROR_COUNT" -eq 0 ]; then
    echo "   ✅ No errors found in recent logs"
else
    echo "   ⚠️  Found $ERROR_COUNT error lines in logs"
    echo "   Recent errors:"
    kubectl logs -n $NAMESPACE $POD_NAME --tail=100 2>/dev/null | grep -i "error\|exception\|failed" | tail -5
fi

echo ""
echo "6. Checking ScaledObject in namespace..."
SO_COUNT=$(kubectl get scaledobjects -n $NAMESPACE 2>/dev/null | grep -v NAME | wc -l || echo "0")
echo "   ScaledObjects in namespace: $SO_COUNT"

if [ "$SO_COUNT" -gt 0 ]; then
    echo "   ✅ ScaledObjects found"
    kubectl get scaledobjects -n $NAMESPACE 2>/dev/null || true
else
    echo "   ⚠️  No ScaledObjects found in namespace $NAMESPACE"
fi

echo ""
echo "=========================================="
echo "Summary"
echo "=========================================="

if [[ "$CURRENT_IMAGE" == *"$EXPECTED_COMMIT"* ]] && [ "$POD_STATUS" = "Running" ] && [ "$READY" = "True" ] && [ "$ERROR_COUNT" -eq 0 ]; then
    echo "✅ Deployment verification PASSED"
    echo ""
    echo "Next steps:"
    echo "1. Open the KEDA Dashboard UI"
    echo "2. Navigate to the calendar view"
    echo "3. Select a ScaledObject"
    echo "4. Try adding a new cron event"
    echo "5. Verify no 422 error occurs"
    echo "6. Verify the ScaledObject is not deleted"
else
    echo "⚠️  Deployment verification INCOMPLETE"
    echo ""
    echo "Possible issues:"
    if [[ "$CURRENT_IMAGE" != *"$EXPECTED_COMMIT"* ]]; then
        echo "- Image not updated yet (wait for ArgoCD sync)"
    fi
    if [ "$POD_STATUS" != "Running" ]; then
        echo "- Pod not running yet (check pod events)"
    fi
    if [ "$READY" != "True" ]; then
        echo "- Pod not ready yet (check readiness probe)"
    fi
    if [ "$ERROR_COUNT" -gt 0 ]; then
        echo "- Errors found in logs (check full logs)"
    fi
    echo ""
    echo "Wait a few minutes and run this script again."
fi

echo ""
echo "=========================================="
echo "Useful commands:"
echo "=========================================="
echo "# Watch pod status"
echo "kubectl get pods -n $NAMESPACE -l app=$DEPLOYMENT -w"
echo ""
echo "# View full logs"
echo "kubectl logs -n $NAMESPACE -l app=$DEPLOYMENT --tail=100 -f"
echo ""
echo "# Check ArgoCD sync status"
echo "kubectl get application keda-dashboard -n argocd -o jsonpath='{.status.sync.status}'"
echo ""
echo "# Force ArgoCD sync"
echo "kubectl patch application keda-dashboard -n argocd --type merge -p '{\"operation\":{\"initiatedBy\":{\"username\":\"admin\"},\"sync\":{\"revision\":\"HEAD\"}}}'"
echo ""
echo "# Get ScaledObject details"
echo "kubectl get scaledobject test -n $NAMESPACE -o yaml"
echo ""
