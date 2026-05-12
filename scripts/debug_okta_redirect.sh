#!/bin/bash

# Script de debug pour la redirection Okta
# Usage: ./debug_okta_redirect.sh [namespace]

NAMESPACE="${1:-test}"

echo "=========================================="
echo "Debug Redirection Okta"
echo "=========================================="
echo ""

echo "1. Vérification de FRONTEND_URL dans le ConfigMap"
echo "---"
FRONTEND_URL=$(kubectl get configmap keda-dashboard-config -n $NAMESPACE -o jsonpath='{.data.FRONTEND_URL}' 2>/dev/null)

if [ -z "$FRONTEND_URL" ]; then
    echo "❌ FRONTEND_URL n'est PAS défini dans le ConfigMap"
    echo ""
    echo "Solution:"
    echo "./fix_frontend_url_now.sh $NAMESPACE https://keda-dashboard.dev.middle-bo.canal.aws.io-cplus.net"
else
    echo "✅ FRONTEND_URL: $FRONTEND_URL"
fi

echo ""
echo "2. Vérification que le pod a chargé FRONTEND_URL"
echo "---"
POD_NAME=$(kubectl get pods -n $NAMESPACE -l app=keda-dashboard-backend -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)

if [ -z "$POD_NAME" ]; then
    echo "❌ Aucun pod backend trouvé"
else
    echo "Pod: $POD_NAME"
    echo ""
    echo "Variables d'environnement dans le pod:"
    kubectl exec -n $NAMESPACE $POD_NAME -- env | grep -E "FRONTEND_URL|OKTA" || echo "❌ Variables non trouvées"
fi

echo ""
echo "3. Logs récents du callback Okta"
echo "---"
echo "Recherche de 'Okta authentication successful' et 'Redirecting to frontend':"
kubectl logs -n $NAMESPACE -l app=keda-dashboard-backend --tail=200 2>/dev/null | grep -E "Okta authentication successful|Redirecting to frontend|FRONTEND_URL" | tail -10

echo ""
echo "4. Dernières erreurs"
echo "---"
kubectl logs -n $NAMESPACE -l app=keda-dashboard-backend --tail=100 2>/dev/null | grep -i error | tail -5

echo ""
echo "5. Test de l'endpoint de callback"
echo "---"
echo "URL de callback: https://keda-dashboard.dev.middle-bo.canal.aws.io-cplus.net/api/auth/okta/callback"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "https://keda-dashboard.dev.middle-bo.canal.aws.io-cplus.net/api/auth/okta/callback")
echo "Code HTTP (sans paramètres): $HTTP_CODE"

if [ "$HTTP_CODE" = "400" ]; then
    echo "✅ Endpoint existe (400 = paramètres manquants, normal)"
elif [ "$HTTP_CODE" = "404" ]; then
    echo "❌ Endpoint non trouvé (404)"
else
    echo "⚠️  Code HTTP inattendu: $HTTP_CODE"
fi

echo ""
echo "=========================================="
echo "Résumé"
echo "=========================================="

if [ -z "$FRONTEND_URL" ]; then
    echo "❌ FRONTEND_URL non configuré - Exécutez:"
    echo "   ./fix_frontend_url_now.sh $NAMESPACE https://keda-dashboard.dev.middle-bo.canal.aws.io-cplus.net"
elif [ -z "$POD_NAME" ]; then
    echo "❌ Pod backend non trouvé"
else
    echo "✅ Configuration semble correcte"
    echo ""
    echo "Si la redirection ne fonctionne toujours pas:"
    echo "1. Vérifiez dans la console du navigateur (F12)"
    echo "2. Regardez l'onglet Network pour voir la redirection"
    echo "3. Vérifiez que le token est dans l'URL après le callback"
    echo "4. Vérifiez les logs en temps réel:"
    echo "   kubectl logs -n $NAMESPACE -l app=keda-dashboard-backend -f"
fi

echo ""
