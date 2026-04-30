#!/bin/bash

# Script de configuration Okta pour KEDA Dashboard
# Usage: ./configure_okta.sh <redirect_uri>
# Exemple: ./configure_okta.sh "http://localhost:8001/api/auth/okta/callback"

set -e

NAMESPACE="test"
RELEASE_NAME="keda-dash"

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🔧 Configuration Okta pour KEDA Dashboard"
echo ""

# Vérifier les arguments
if [ $# -eq 0 ]; then
    echo -e "${RED}❌ Erreur: URL de callback manquante${NC}"
    echo ""
    echo "Usage: $0 <redirect_uri>"
    echo ""
    echo "Exemples:"
    echo "  $0 'http://localhost:8001/api/auth/okta/callback'"
    echo "  $0 'https://keda-dashboard.example.com/api/auth/okta/callback'"
    echo ""
    exit 1
fi

REDIRECT_URI="$1"

echo -e "${YELLOW}📋 Configuration:${NC}"
echo "  Namespace: $NAMESPACE"
echo "  Release: $RELEASE_NAME"
echo "  Redirect URI: $REDIRECT_URI"
echo ""

# Vérifier que le namespace existe
if ! kubectl get namespace $NAMESPACE &> /dev/null; then
    echo -e "${RED}❌ Le namespace '$NAMESPACE' n'existe pas${NC}"
    exit 1
fi

# Vérifier la configuration actuelle
echo -e "${YELLOW}🔍 Configuration actuelle:${NC}"
CURRENT_OKTA_ENABLED=$(kubectl get configmap -n $NAMESPACE ${RELEASE_NAME}-keda-dashboard-config -o jsonpath='{.data.OKTA_ENABLED}' 2>/dev/null || echo "")
CURRENT_REDIRECT_URI=$(kubectl get configmap -n $NAMESPACE ${RELEASE_NAME}-keda-dashboard-config -o jsonpath='{.data.OKTA_REDIRECT_URI}' 2>/dev/null || echo "")

echo "  OKTA_ENABLED: $CURRENT_OKTA_ENABLED"
echo "  OKTA_REDIRECT_URI: $CURRENT_REDIRECT_URI"
echo ""

# Demander confirmation
read -p "Voulez-vous mettre à jour OKTA_REDIRECT_URI ? (y/n) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Annulé."
    exit 0
fi

# Mettre à jour le ConfigMap
echo -e "${YELLOW}📝 Mise à jour du ConfigMap...${NC}"

kubectl patch configmap -n $NAMESPACE ${RELEASE_NAME}-keda-dashboard-config \
  --type merge \
  -p "{\"data\":{\"OKTA_REDIRECT_URI\":\"$REDIRECT_URI\"}}"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ ConfigMap mis à jour${NC}"
else
    echo -e "${RED}❌ Échec de la mise à jour du ConfigMap${NC}"
    exit 1
fi

echo ""

# Redémarrer le pod backend
echo -e "${YELLOW}🔄 Redémarrage du pod backend...${NC}"

kubectl delete pod -n $NAMESPACE -l app.kubernetes.io/component=backend

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Pod redémarré${NC}"
else
    echo -e "${RED}❌ Échec du redémarrage du pod${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}⏳ Attente du démarrage du nouveau pod...${NC}"
sleep 10

# Attendre que le pod soit prêt
kubectl wait --for=condition=ready pod -n $NAMESPACE -l app.kubernetes.io/component=backend --timeout=60s

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Pod prêt${NC}"
else
    echo -e "${RED}❌ Le pod n'est pas prêt après 60 secondes${NC}"
    exit 1
fi

echo ""

# Vérifier la configuration
echo -e "${YELLOW}🔍 Vérification de la configuration...${NC}"

POD_NAME=$(kubectl get pod -n $NAMESPACE -l app.kubernetes.io/component=backend -o jsonpath='{.items[0].metadata.name}')

if [ -z "$POD_NAME" ]; then
    echo -e "${RED}❌ Impossible de trouver le pod backend${NC}"
    exit 1
fi

# Vérifier les variables d'environnement
echo ""
echo "Variables d'environnement Okta:"
kubectl exec -n $NAMESPACE $POD_NAME -- env | grep OKTA || echo "  Aucune variable OKTA trouvée"

echo ""

# Tester l'endpoint de configuration
echo -e "${YELLOW}🧪 Test de l'endpoint /api/auth/config...${NC}"

CONFIG_RESPONSE=$(kubectl exec -n $NAMESPACE $POD_NAME -- curl -s http://localhost:8001/api/auth/config 2>/dev/null || echo "")

if [ -n "$CONFIG_RESPONSE" ]; then
    echo "  Réponse: $CONFIG_RESPONSE"
    
    # Vérifier si Okta est activé
    if echo "$CONFIG_RESPONSE" | grep -q '"okta_enabled":true'; then
        echo -e "${GREEN}✅ Okta est activé !${NC}"
    else
        echo -e "${RED}❌ Okta est toujours désactivé${NC}"
        echo ""
        echo "Vérifiez les logs pour plus de détails:"
        echo "  kubectl logs -n $NAMESPACE $POD_NAME | grep -i okta"
    fi
else
    echo -e "${RED}❌ Impossible de tester l'endpoint${NC}"
fi

echo ""

# Vérifier les logs
echo -e "${YELLOW}📋 Logs récents (configuration Okta):${NC}"
kubectl logs -n $NAMESPACE $POD_NAME --tail=50 | grep -i "auth.*config\|okta" || echo "  Aucun log trouvé"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo -e "${GREEN}✅ Configuration terminée !${NC}"
echo ""
echo "📝 Prochaines étapes:"
echo "  1. Vérifiez que l'URL de callback est configurée dans Okta Admin Console:"
echo "     https://groupecanalplus.okta.com/admin"
echo "     → Applications → Votre App → Sign-in redirect URIs"
echo "     → Ajoutez: $REDIRECT_URI"
echo ""
echo "  2. Accédez à l'application et vérifiez que le bouton 'Sign in with Okta' apparaît"
echo ""
echo "  3. Si le bouton n'apparaît pas, videz le cache du navigateur (Ctrl+Shift+R)"
echo ""
