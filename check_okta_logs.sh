#!/bin/bash
NAMESPACE="${1:-test}"
echo "Derniers logs du callback Okta:"
echo "================================"
kubectl logs -n $NAMESPACE -l app=keda-dashboard-backend --tail=100 | grep -A 5 -B 5 "Okta authentication successful"
