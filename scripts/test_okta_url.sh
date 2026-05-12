#!/bin/bash

# Script pour tester l'URL d'autorisation Okta
# Usage: ./test_okta_url.sh [namespace]

NAMESPACE="${1:-test}"

echo "=========================================="
echo "Test de l'URL d'Autorisation Okta"
echo "=========================================="
echo ""

# Récupérer la configuration
echo "1. Récupération de la configuration..."
OKTA_DOMAIN=$(kubectl get configmap keda-dashboard-config -n $NAMESPACE -o jsonpath='{.data.OKTA_DOMAIN}' 2>/dev/null)
OKTA_CLIENT_ID=$(kubectl get configmap keda-dashboard-config -n $NAMESPACE -o jsonpath='{.data.OKTA_CLIENT_ID}' 2>/dev/null)
OKTA_REDIRECT_URI=$(kubectl get configmap keda-dashboard-config -n $NAMESPACE -o jsonpath='{.data.OKTA_REDIRECT_URI}' 2>/dev/null)

echo "   OKTA_DOMAIN: $OKTA_DOMAIN"
echo "   OKTA_CLIENT_ID: $OKTA_CLIENT_ID"
echo "   OKTA_REDIRECT_URI: $OKTA_REDIRECT_URI"
echo ""

# Construire l'URL de base
echo "2. Construction de l'URL de base..."
if [[ "$OKTA_DOMAIN" == *"/oauth2/"* ]]; then
    BASE_URL="https://$OKTA_DOMAIN"
    echo "   Type: Custom Authorization Server"
else
    BASE_URL="https://$OKTA_DOMAIN/oauth2/default"
    echo "   Type: Org Authorization Server (default)"
fi
echo "   Base URL: $BASE_URL"
echo ""

# Construire l'endpoint d'autorisation
AUTH_ENDPOINT="$BASE_URL/v1/authorize"
echo "3. Endpoint d'autorisation:"
echo "   $AUTH_ENDPOINT"
echo ""

# Tester l'endpoint de découverte
echo "4. Test de l'endpoint de découverte..."
DISCOVERY_URL="$BASE_URL/.well-known/openid-configuration"
echo "   URL: $DISCOVERY_URL"
echo ""

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$DISCOVERY_URL")
echo "   Code HTTP: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
    echo "   ✅ Endpoint accessible"
    echo ""
    echo "5. Détails de la configuration Okta:"
    curl -s "$DISCOVERY_URL" | jq '{
        issuer,
        authorization_endpoint,
        token_endpoint,
        userinfo_endpoint,
        jwks_uri
    }' 2>/dev/null || echo "   ❌ Impossible de parser la réponse"
elif [ "$HTTP_CODE" = "404" ]; then
    echo "   ❌ Endpoint non trouvé (404)"
    echo ""
    echo "   Problème: L'URL de découverte n'existe pas"
    echo ""
    echo "   Solutions possibles:"
    echo "   1. Vérifier le domaine Okta dans la console Okta"
    echo "   2. Aller dans Security → API → Authorization Servers"
    echo "   3. Copier l'Issuer URI exact"
    echo ""
    echo "   Exemples d'Issuer URI:"
    echo "   - Custom: https://groupecanalplus.okta.com/oauth2/ausbk7e6q48W7VUZr417"
    echo "   - Default: https://groupecanalplus.okta.com/oauth2/default"
    echo ""
    echo "   Configuration actuelle:"
    echo "   - OKTA_DOMAIN: $OKTA_DOMAIN"
    echo "   - URL générée: $BASE_URL"
else
    echo "   ⚠️  Code HTTP inattendu: $HTTP_CODE"
fi

echo ""
echo "6. Test de l'endpoint d'autorisation..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$AUTH_ENDPOINT")
echo "   URL: $AUTH_ENDPOINT"
echo "   Code HTTP: $HTTP_CODE"

if [ "$HTTP_CODE" = "400" ]; then
    echo "   ✅ Endpoint existe (400 = paramètres manquants, normal)"
elif [ "$HTTP_CODE" = "404" ]; then
    echo "   ❌ Endpoint non trouvé (404)"
else
    echo "   ⚠️  Code HTTP: $HTTP_CODE"
fi

echo ""
echo "7. URL complète qui sera générée par l'application:"
FULL_URL="$AUTH_ENDPOINT?client_id=$OKTA_CLIENT_ID&response_type=code&scope=openid+profile+email&redirect_uri=$OKTA_REDIRECT_URI&state=TEST_STATE"
echo "   $FULL_URL"
echo ""

echo "8. Test de l'URL complète..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$FULL_URL")
echo "   Code HTTP: $HTTP_CODE"

if [ "$HTTP_CODE" = "302" ]; then
    echo "   ✅ Redirection (302) - L'URL fonctionne!"
    LOCATION=$(curl -s -I "$FULL_URL" | grep -i "^location:" | cut -d' ' -f2 | tr -d '\r')
    echo "   Redirige vers: $LOCATION"
elif [ "$HTTP_CODE" = "200" ]; then
    echo "   ✅ Page de login Okta (200) - L'URL fonctionne!"
elif [ "$HTTP_CODE" = "404" ]; then
    echo "   ❌ Endpoint non trouvé (404)"
    echo ""
    echo "   Le problème est confirmé: l'URL d'autorisation est incorrecte"
else
    echo "   ⚠️  Code HTTP inattendu: $HTTP_CODE"
fi

echo ""
echo "=========================================="
echo "Résumé"
echo "=========================================="

if [ "$HTTP_CODE" = "302" ] || [ "$HTTP_CODE" = "200" ]; then
    echo "✅ Configuration Okta correcte"
    echo ""
    echo "L'URL d'autorisation fonctionne. Si vous avez toujours une erreur 404"
    echo "dans le navigateur, vérifiez:"
    echo "1. Que le nouveau code est déployé (commit 6437218)"
    echo "2. Les logs backend avec: ./watch_okta_logs.sh $NAMESPACE"
    echo "3. Que le pod a redémarré après la mise à jour de la config"
else
    echo "❌ Configuration Okta incorrecte"
    echo ""
    echo "Actions à effectuer:"
    echo "1. Vérifier le domaine Okta dans la console Okta"
    echo "2. Copier l'Issuer URI exact depuis Security → API"
    echo "3. Mettre à jour values.yaml avec le bon domaine"
    echo "4. Redéployer: helm upgrade keda-dashboard ./helm/keda-dashboard -n $NAMESPACE -f values-okta.yaml"
fi

echo ""
echo "=========================================="
echo "Commandes utiles:"
echo "=========================================="
echo "# Voir les logs Okta en temps réel"
echo "./watch_okta_logs.sh $NAMESPACE"
echo ""
echo "# Diagnostic complet"
echo "./diagnose_okta_config.sh $NAMESPACE"
echo ""
echo "# Redémarrer le backend"
echo "kubectl rollout restart deployment/keda-dashboard-backend -n $NAMESPACE"
echo ""
