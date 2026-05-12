#!/bin/bash

# Script de diagnostic de la configuration Okta
# Ce script aide à identifier les problèmes de configuration Okta

set -e

NAMESPACE="${1:-test}"

echo "=========================================="
echo "Diagnostic de Configuration Okta"
echo "=========================================="
echo ""

# Vérifier kubectl
if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl non trouvé"
    exit 1
fi

echo "1. Configuration Okta dans ConfigMap"
echo "---"
kubectl get configmap keda-dashboard-config -n $NAMESPACE -o yaml 2>/dev/null | grep -E "OKTA_|FRONTEND_" || echo "❌ ConfigMap non trouvé"
echo ""

echo "2. Variables d'environnement Okta extraites"
echo "---"
OKTA_ENABLED=$(kubectl get configmap keda-dashboard-config -n $NAMESPACE -o jsonpath='{.data.OKTA_ENABLED}' 2>/dev/null || echo "NOT_FOUND")
OKTA_DOMAIN=$(kubectl get configmap keda-dashboard-config -n $NAMESPACE -o jsonpath='{.data.OKTA_DOMAIN}' 2>/dev/null || echo "NOT_FOUND")
OKTA_CLIENT_ID=$(kubectl get configmap keda-dashboard-config -n $NAMESPACE -o jsonpath='{.data.OKTA_CLIENT_ID}' 2>/dev/null || echo "NOT_FOUND")
OKTA_REDIRECT_URI=$(kubectl get configmap keda-dashboard-config -n $NAMESPACE -o jsonpath='{.data.OKTA_REDIRECT_URI}' 2>/dev/null || echo "NOT_FOUND")
FRONTEND_URL=$(kubectl get configmap keda-dashboard-config -n $NAMESPACE -o jsonpath='{.data.FRONTEND_URL}' 2>/dev/null || echo "NOT_FOUND")

echo "OKTA_ENABLED: $OKTA_ENABLED"
echo "OKTA_DOMAIN: $OKTA_DOMAIN"
echo "OKTA_CLIENT_ID: $OKTA_CLIENT_ID"
echo "OKTA_REDIRECT_URI: $OKTA_REDIRECT_URI"
echo "FRONTEND_URL: $FRONTEND_URL"
echo ""

echo "3. Analyse de la configuration"
echo "---"

# Vérifier si Okta est activé
if [ "$OKTA_ENABLED" != "true" ]; then
    echo "⚠️  OKTA_ENABLED n'est pas 'true'"
else
    echo "✅ OKTA_ENABLED est activé"
fi

# Vérifier le domaine
if [ "$OKTA_DOMAIN" = "NOT_FOUND" ] || [ -z "$OKTA_DOMAIN" ]; then
    echo "❌ OKTA_DOMAIN n'est pas configuré"
else
    echo "✅ OKTA_DOMAIN configuré: $OKTA_DOMAIN"
    
    # Déterminer le type de serveur d'autorisation
    if [[ "$OKTA_DOMAIN" == *"/oauth2/"* ]]; then
        echo "   Type: Custom Authorization Server"
        # Extraire l'ID du serveur
        AUTH_SERVER_ID=$(echo "$OKTA_DOMAIN" | grep -oP '/oauth2/\K[^/]+' || echo "")
        echo "   Authorization Server ID: $AUTH_SERVER_ID"
        BASE_URL="https://$OKTA_DOMAIN"
    else
        echo "   Type: Org Authorization Server (default)"
        BASE_URL="https://$OKTA_DOMAIN/oauth2/default"
    fi
    
    echo "   Base URL: $BASE_URL"
    echo "   Authorization Endpoint: $BASE_URL/v1/authorize"
    echo "   Token Endpoint: $BASE_URL/v1/token"
    echo "   JWKS URI: $BASE_URL/v1/keys"
fi

# Vérifier le Client ID
if [ "$OKTA_CLIENT_ID" = "NOT_FOUND" ] || [ -z "$OKTA_CLIENT_ID" ]; then
    echo "❌ OKTA_CLIENT_ID n'est pas configuré"
else
    echo "✅ OKTA_CLIENT_ID configuré: $OKTA_CLIENT_ID"
fi

# Vérifier le Redirect URI
if [ "$OKTA_REDIRECT_URI" = "NOT_FOUND" ] || [ -z "$OKTA_REDIRECT_URI" ]; then
    echo "❌ OKTA_REDIRECT_URI n'est pas configuré"
else
    echo "✅ OKTA_REDIRECT_URI configuré: $OKTA_REDIRECT_URI"
fi

# Vérifier le Frontend URL
if [ "$FRONTEND_URL" = "NOT_FOUND" ] || [ -z "$FRONTEND_URL" ]; then
    echo "❌ FRONTEND_URL n'est pas configuré"
else
    echo "✅ FRONTEND_URL configuré: $FRONTEND_URL"
fi

echo ""
echo "4. Test des endpoints Okta"
echo "---"

if [ "$OKTA_DOMAIN" != "NOT_FOUND" ] && [ -n "$OKTA_DOMAIN" ]; then
    # Construire l'URL de base
    if [[ "$OKTA_DOMAIN" == *"/oauth2/"* ]]; then
        BASE_URL="https://$OKTA_DOMAIN"
    else
        BASE_URL="https://$OKTA_DOMAIN/oauth2/default"
    fi
    
    # Tester l'endpoint de découverte
    echo "Test: $BASE_URL/.well-known/openid-configuration"
    if curl -s -f -o /dev/null "$BASE_URL/.well-known/openid-configuration"; then
        echo "✅ Endpoint de découverte accessible"
        
        # Afficher les endpoints
        echo ""
        echo "Endpoints découverts:"
        curl -s "$BASE_URL/.well-known/openid-configuration" | jq -r '{
            issuer,
            authorization_endpoint,
            token_endpoint,
            userinfo_endpoint,
            jwks_uri
        }' 2>/dev/null || echo "❌ Impossible de parser la réponse"
    else
        echo "❌ Endpoint de découverte non accessible (404)"
        echo ""
        echo "Suggestions:"
        echo "1. Vérifier que le domaine Okta est correct"
        echo "2. Si vous utilisez un Custom Authorization Server:"
        echo "   - Format: groupecanalplus.okta.com/oauth2/ausbk7e6q48W7VUZr417"
        echo "3. Si vous utilisez le serveur par défaut:"
        echo "   - Format: groupecanalplus.okta.com"
        echo "   - L'URL sera: groupecanalplus.okta.com/oauth2/default"
    fi
else
    echo "⚠️  Impossible de tester (OKTA_DOMAIN non configuré)"
fi

echo ""
echo "5. Logs récents du backend"
echo "---"
kubectl logs -n $NAMESPACE -l app=keda-dashboard-backend --tail=20 2>/dev/null | grep -i okta || echo "Aucun log Okta trouvé"

echo ""
echo "=========================================="
echo "Résumé"
echo "=========================================="

ISSUES=0

if [ "$OKTA_ENABLED" != "true" ]; then
    echo "❌ Okta n'est pas activé"
    ((ISSUES++))
fi

if [ "$OKTA_DOMAIN" = "NOT_FOUND" ] || [ -z "$OKTA_DOMAIN" ]; then
    echo "❌ OKTA_DOMAIN manquant"
    ((ISSUES++))
fi

if [ "$OKTA_CLIENT_ID" = "NOT_FOUND" ] || [ -z "$OKTA_CLIENT_ID" ]; then
    echo "❌ OKTA_CLIENT_ID manquant"
    ((ISSUES++))
fi

if [ "$OKTA_REDIRECT_URI" = "NOT_FOUND" ] || [ -z "$OKTA_REDIRECT_URI" ]; then
    echo "❌ OKTA_REDIRECT_URI manquant"
    ((ISSUES++))
fi

if [ $ISSUES -eq 0 ]; then
    echo "✅ Configuration semble correcte"
    echo ""
    echo "Si vous avez toujours une erreur 404:"
    echo "1. Vérifiez le format du domaine Okta"
    echo "2. Vérifiez que l'Authorization Server existe dans Okta"
    echo "3. Consultez les logs backend pour plus de détails"
else
    echo "⚠️  $ISSUES problème(s) de configuration détecté(s)"
fi

echo ""
echo "=========================================="
echo "Commandes utiles:"
echo "=========================================="
echo "# Voir les logs backend en temps réel"
echo "kubectl logs -n $NAMESPACE -l app=keda-dashboard-backend -f"
echo ""
echo "# Mettre à jour la configuration"
echo "helm upgrade keda-dashboard ./helm/keda-dashboard -n $NAMESPACE -f values-okta.yaml"
echo ""
echo "# Redémarrer le backend"
echo "kubectl rollout restart deployment/keda-dashboard-backend -n $NAMESPACE"
echo ""
