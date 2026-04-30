#!/bin/bash

# Script pour corriger FRONTEND_URL immédiatement
# Usage: ./fix_frontend_url_now.sh [namespace] [frontend_url]

NAMESPACE="${1:-test}"
FRONTEND_URL="${2:-https://keda-dashboard.dev.middle-bo.canal.aws.io-cplus.net}"

echo "=========================================="
echo "Correction de FRONTEND_URL"
echo "=========================================="
echo ""
echo "Namespace: $NAMESPACE"
echo "Frontend URL: $FRONTEND_URL"
echo ""

# Vérifier que kubectl fonctionne
if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl non trouvé"
    exit 1
fi

# Vérifier que le ConfigMap existe
if ! kubectl get configmap keda-dashboard-config -n $NAMESPACE &> /dev/null; then
    echo "❌ ConfigMap keda-dashboard-config non trouvé dans le namespace $NAMESPACE"
    exit 1
fi

echo "1. Patch du ConfigMap..."
kubectl patch configmap keda-dashboard-config -n $NAMESPACE --type merge -p "{\"data\":{\"FRONTEND_URL\":\"$FRONTEND_URL\"}}"

if [ $? -eq 0 ]; then
    echo "✅ ConfigMap patché"
else
    echo "❌ Échec du patch"
    exit 1
fi

echo ""
echo "2. Vérification du patch..."
CURRENT_URL=$(kubectl get configmap keda-dashboard-config -n $NAMESPACE -o jsonpath='{.data.FRONTEND_URL}' 2>/dev/null)
echo "FRONTEND_URL actuel: $CURRENT_URL"

if [ "$CURRENT_URL" = "$FRONTEND_URL" ]; then
    echo "✅ Patch vérifié"
else
    echo "⚠️  La valeur ne correspond pas"
fi

echo ""
echo "3. Redémarrage du backend..."
kubectl rollout restart deployment/keda-dashboard-backend -n $NAMESPACE

if [ $? -eq 0 ]; then
    echo "✅ Redémarrage lancé"
else
    echo "❌ Échec du redémarrage"
    exit 1
fi

echo ""
echo "4. Attente du redémarrage..."
kubectl rollout status deployment/keda-dashboard-backend -n $NAMESPACE --timeout=120s

if [ $? -eq 0 ]; then
    echo "✅ Pod redémarré"
else
    echo "⚠️  Timeout - vérifier manuellement"
fi

echo ""
echo "5. Vérification des logs..."
echo "Dernières lignes des logs:"
kubectl logs -n $NAMESPACE -l app=keda-dashboard-backend --tail=5 2>/dev/null || echo "❌ Impossible de récupérer les logs"

echo ""
echo "=========================================="
echo "✅ Correction terminée"
echo "=========================================="
echo ""
echo "Testez maintenant:"
echo "1. Ouvrir: $FRONTEND_URL"
echo "2. Cliquer: 'Sign in with Okta'"
echo "3. S'authentifier"
echo "4. Devrait être redirigé vers la page d'accueil"
echo ""
echo "Pour voir les logs en temps réel:"
echo "kubectl logs -n $NAMESPACE -l app=keda-dashboard-backend -f"
echo ""
