#!/bin/bash

NAMESPACE="${1:-test}"

echo "Vérification de FRONTEND_URL"
echo "=============================="
echo ""

FRONTEND_URL=$(kubectl get configmap keda-dashboard-config -n $NAMESPACE -o jsonpath='{.data.FRONTEND_URL}' 2>/dev/null)

echo "FRONTEND_URL dans ConfigMap: $FRONTEND_URL"
echo ""

if [ -z "$FRONTEND_URL" ] || [ "$FRONTEND_URL" = "http://localhost:3000" ]; then
    echo "❌ FRONTEND_URL n'est pas configurée correctement"
    echo ""
    echo "Solution:"
    echo "1. Vérifier ingress.hosts dans values.yaml"
    echo "2. Redéployer avec Helm"
else
    echo "✅ FRONTEND_URL configurée"
fi
