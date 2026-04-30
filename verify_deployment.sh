#!/bin/bash

# Script de vérification du déploiement de l'authentification
# Usage: ./verify_deployment.sh

set -e

NAMESPACE="test"
EXPECTED_COMMIT="60c77ce"

echo "🔍 Vérification du déploiement de l'authentification..."
echo ""

# 1. Vérifier l'image déployée
echo "1️⃣ Vérification de l'image déployée..."
CURRENT_IMAGE=$(kubectl get pod -n $NAMESPACE -l app.kubernetes.io/component=backend -o jsonpath='{.items[0].spec.containers[0].image}' 2>/dev/null || echo "")

if [ -z "$CURRENT_IMAGE" ]; then
    echo "❌ Aucun pod backend trouvé dans le namespace $NAMESPACE"
    exit 1
fi

echo "   Image actuelle: $CURRENT_IMAGE"

if echo "$CURRENT_IMAGE" | grep -q "$EXPECTED_COMMIT"; then
    echo "   ✅ Image correcte (commit $EXPECTED_COMMIT)"
else
    echo "   ⚠️  Image ne contient pas le commit $EXPECTED_COMMIT"
    echo "   Attendez que ArgoCD déploie la nouvelle version..."
fi

echo ""

# 2. Vérifier l'état du pod
echo "2️⃣ Vérification de l'état du pod..."
POD_STATUS=$(kubectl get pod -n $NAMESPACE -l app.kubernetes.io/component=backend -o jsonpath='{.items[0].status.phase}' 2>/dev/null || echo "")

if [ "$POD_STATUS" = "Running" ]; then
    echo "   ✅ Pod en cours d'exécution"
else
    echo "   ❌ Pod status: $POD_STATUS"
    exit 1
fi

echo ""

# 3. Vérifier les logs récents
echo "3️⃣ Vérification des logs récents..."
echo "   Recherche d'erreurs dans les 50 dernières lignes..."

ERROR_COUNT=$(kubectl logs -n $NAMESPACE -l app.kubernetes.io/component=backend --tail=50 2>/dev/null | grep -c "ERROR" || echo "0")

if [ "$ERROR_COUNT" -eq 0 ]; then
    echo "   ✅ Aucune erreur trouvée"
else
    echo "   ⚠️  $ERROR_COUNT erreur(s) trouvée(s)"
    echo "   Affichage des erreurs:"
    kubectl logs -n $NAMESPACE -l app.kubernetes.io/component=backend --tail=50 | grep "ERROR" || true
fi

echo ""

# 4. Vérifier les erreurs spécifiques
echo "4️⃣ Vérification des erreurs spécifiques..."

GREENLET_ERROR=$(kubectl logs -n $NAMESPACE -l app.kubernetes.io/component=backend --tail=100 2>/dev/null | grep -c "greenlet_spawn" || echo "0")
MAPPER_ERROR=$(kubectl logs -n $NAMESPACE -l app.kubernetes.io/component=backend --tail=100 2>/dev/null | grep -c "mapper" || echo "0")
TABLE_ERROR=$(kubectl logs -n $NAMESPACE -l app.kubernetes.io/component=backend --tail=100 2>/dev/null | grep -c "already defined" || echo "0")

if [ "$GREENLET_ERROR" -eq 0 ] && [ "$MAPPER_ERROR" -eq 0 ] && [ "$TABLE_ERROR" -eq 0 ]; then
    echo "   ✅ Aucune erreur SQLAlchemy détectée"
else
    echo "   ❌ Erreurs SQLAlchemy détectées:"
    [ "$GREENLET_ERROR" -gt 0 ] && echo "      - greenlet_spawn: $GREENLET_ERROR"
    [ "$MAPPER_ERROR" -gt 0 ] && echo "      - mapper: $MAPPER_ERROR"
    [ "$TABLE_ERROR" -gt 0 ] && echo "      - table already defined: $TABLE_ERROR"
fi

echo ""

# 5. Tester l'endpoint de configuration
echo "5️⃣ Test de l'endpoint de configuration..."

POD_NAME=$(kubectl get pod -n $NAMESPACE -l app.kubernetes.io/component=backend -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")

if [ -n "$POD_NAME" ]; then
    CONFIG_RESPONSE=$(kubectl exec -n $NAMESPACE $POD_NAME -- curl -s http://localhost:8001/api/auth/config 2>/dev/null || echo "")
    
    if echo "$CONFIG_RESPONSE" | grep -q "local_auth_enabled"; then
        echo "   ✅ Endpoint /api/auth/config répond correctement"
        echo "   Réponse: $CONFIG_RESPONSE"
    else
        echo "   ❌ Endpoint /api/auth/config ne répond pas correctement"
    fi
else
    echo "   ⚠️  Impossible de trouver le pod pour tester l'endpoint"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Résumé final
if echo "$CURRENT_IMAGE" | grep -q "$EXPECTED_COMMIT" && [ "$POD_STATUS" = "Running" ] && [ "$GREENLET_ERROR" -eq 0 ]; then
    echo "🎉 SUCCÈS ! Le déploiement semble correct."
    echo ""
    echo "📝 Prochaines étapes:"
    echo "   1. Testez l'authentification via l'interface web"
    echo "   2. Email: admin@example.com"
    echo "   3. Password: admin123"
    echo ""
else
    echo "⚠️  Le déploiement n'est pas encore complet ou présente des erreurs."
    echo ""
    echo "📝 Actions recommandées:"
    
    if ! echo "$CURRENT_IMAGE" | grep -q "$EXPECTED_COMMIT"; then
        echo "   - Attendez que ArgoCD déploie l'image avec le commit $EXPECTED_COMMIT"
        echo "   - Vérifiez le statut ArgoCD: kubectl get app -n argocd"
    fi
    
    if [ "$GREENLET_ERROR" -gt 0 ]; then
        echo "   - Des erreurs greenlet persistent, vérifiez les logs complets"
        echo "   - Commande: kubectl logs -n $NAMESPACE -l app.kubernetes.io/component=backend --tail=200"
    fi
    
    echo ""
fi
