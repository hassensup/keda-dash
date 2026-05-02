#!/bin/bash

# Script to restart the keda-dashboard deployment after new image is built

echo "Restarting keda-dashboard deployment in namespace 'test'..."
kubectl rollout restart deployment -n test -l app.kubernetes.io/name=keda-dashboard

echo "Waiting for rollout to complete..."
kubectl rollout status deployment -n test -l app.kubernetes.io/name=keda-dashboard

echo "✅ Deployment restarted successfully"
echo ""
echo "Check logs with:"
echo "kubectl logs -n test -l app.kubernetes.io/name=keda-dashboard --tail=50 -f"
