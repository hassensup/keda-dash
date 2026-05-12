#!/bin/bash

# Script de déploiement KEDA Dashboard avec Ingress
# Usage: ./deploy_with_ingress.sh <domain> [ingress-class]

set -e

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  KEDA Dashboard - Déploiement avec Ingress${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Vérifier les arguments
if [ $# -eq 0 ]; then
    echo -e "${RED}❌ Erreur: Domaine manquant${NC}"
    echo ""
    echo "Usage: $0 <domain> [ingress-class]"
    echo ""
    echo "Exemples:"
    echo "  $0 keda-dashboard.example.com"
    echo "  $0 keda-dashboard.example.com nginx"
    echo "  $0 keda-dashboard.example.com alb"
    echo ""
    exit 1
fi

DOMAIN="$1"
INGRESS_CLASS="${2:-nginx}"
NAMESPACE="test"
RELEASE_NAME="keda-dash"

echo -e "${YELLOW}📋 Configuration:${NC}"
echo "  Domaine: $DOMAIN"
echo "  Ingress Class: $INGRESS_CLASS"
echo "  Namespace: $NAMESPACE"
echo "  Release: $RELEASE_NAME"
echo ""

# Déterminer le protocole (HTTPS par défaut)
PROTOCOL="https"
read -p "Utiliser HTTPS ? (Y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Nn]$ ]]; then
    PROTOCOL="http"
    echo -e "${YELLOW}⚠️  Mode HTTP (non sécurisé)${NC}"
else
    echo -e "${GREEN}✅ Mode HTTPS${NC}"
fi
echo ""

# Construire l'URL de callback Okta
OKTA_REDIRECT_URI="${PROTOCOL}://${DOMAIN}/api/auth/okta/callback"

echo -e "${YELLOW}🔐 Configuration Okta:${NC}"
echo "  Redirect URI: $OKTA_REDIRECT_URI"
echo ""

# Demander les credentials Okta
read -p "Activer Okta SSO ? (y/N) " -n 1 -r
echo ""
OKTA_ENABLED="false"
OKTA_DOMAIN=""
OKTA_CLIENT_ID=""
OKTA_CLIENT_SECRET=""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    OKTA_ENABLED="true"
    
    echo ""
    echo -e "${YELLOW}Entrez les informations Okta:${NC}"
    read -p "Okta Domain (ex: your-org.okta.com): " OKTA_DOMAIN
    read -p "Okta Client ID: " OKTA_CLIENT_ID
    read -sp "Okta Client Secret: " OKTA_CLIENT_SECRET
    echo ""
    echo ""
fi

# Demander confirmation
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}Résumé de la configuration:${NC}"
echo ""
echo "  URL publique: ${PROTOCOL}://${DOMAIN}"
echo "  Ingress Class: $INGRESS_CLASS"
echo "  Okta activé: $OKTA_ENABLED"
if [ "$OKTA_ENABLED" = "true" ]; then
    echo "  Okta Domain: $OKTA_DOMAIN"
    echo "  Okta Redirect URI: $OKTA_REDIRECT_URI"
fi
echo ""
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

read -p "Continuer avec cette configuration ? (y/N) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Annulé."
    exit 0
fi

echo ""
echo -e "${BLUE}🚀 Déploiement en cours...${NC}"
echo ""

# Construire la commande Helm
HELM_CMD="helm upgrade --install $RELEASE_NAME ./helm/keda-dashboard \
  --namespace $NAMESPACE \
  --create-namespace \
  --set ingress.enabled=true \
  --set ingress.className=$INGRESS_CLASS \
  --set ingress.hosts[0].host=$DOMAIN \
  --set ingress.hosts[0].paths[0].path=/ \
  --set ingress.hosts[0].paths[0].pathType=Prefix \
  --set backend.config.corsOrigins=${PROTOCOL}://${DOMAIN}"

# Ajouter la configuration TLS si HTTPS
if [ "$PROTOCOL" = "https" ]; then
    HELM_CMD="$HELM_CMD \
  --set ingress.tls[0].secretName=keda-dashboard-tls \
  --set ingress.tls[0].hosts[0]=$DOMAIN \
  --set ingress.annotations.cert-manager\\.io/cluster-issuer=letsencrypt-prod \
  --set ingress.annotations.nginx\\.ingress\\.kubernetes\\.io/ssl-redirect=true"
fi

# Ajouter la configuration Okta si activée
if [ "$OKTA_ENABLED" = "true" ]; then
    HELM_CMD="$HELM_CMD \
  --set auth.okta.enabled=true \
  --set auth.okta.domain=$OKTA_DOMAIN \
  --set auth.okta.clientId=$OKTA_CLIENT_ID \
  --set auth.okta.clientSecret=$OKTA_CLIENT_SECRET \
  --set auth.okta.redirectUri=$OKTA_REDIRECT_URI"
fi

# Exécuter la commande Helm
echo -e "${YELLOW}Exécution de Helm...${NC}"
eval $HELM_CMD

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ Déploiement réussi !${NC}"
else
    echo ""
    echo -e "${RED}❌ Échec du déploiement${NC}"
    exit 1
fi

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}🎉 Déploiement terminé !${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Attendre que les pods soient prêts
echo -e "${YELLOW}⏳ Attente du démarrage des pods...${NC}"
kubectl wait --for=condition=ready pod -n $NAMESPACE -l app.kubernetes.io/component=backend --timeout=120s

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Pods prêts${NC}"
else
    echo -e "${YELLOW}⚠️  Timeout en attendant les pods${NC}"
fi

echo ""

# Afficher les informations de l'Ingress
echo -e "${YELLOW}📊 Informations Ingress:${NC}"
kubectl get ingress -n $NAMESPACE

echo ""

# Afficher les prochaines étapes
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}📝 Prochaines étapes:${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

echo "1. ${YELLOW}Configurer le DNS${NC}"
if [ "$INGRESS_CLASS" = "alb" ]; then
    echo "   Créez un enregistrement CNAME:"
    ALB_DNS=$(kubectl get ingress -n $NAMESPACE $RELEASE_NAME-keda-dashboard -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null || echo "<ALB-DNS>")
    echo "   $DOMAIN → $ALB_DNS"
else
    echo "   Créez un enregistrement A:"
    LB_IP=$(kubectl get svc -n ingress-nginx ingress-nginx-controller -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "<EXTERNAL-IP>")
    echo "   $DOMAIN → $LB_IP"
fi
echo ""

if [ "$OKTA_ENABLED" = "true" ]; then
    echo "2. ${YELLOW}Configurer Okta Admin Console${NC}"
    echo "   URL: https://$OKTA_DOMAIN/admin"
    echo "   → Applications → Votre App"
    echo "   → Ajoutez l'URL de callback:"
    echo "   $OKTA_REDIRECT_URI"
    echo ""
fi

echo "3. ${YELLOW}Tester l'accès${NC}"
echo "   URL: ${PROTOCOL}://${DOMAIN}"
echo "   Health check: ${PROTOCOL}://${DOMAIN}/api/health"
echo ""

echo "4. ${YELLOW}Vérifier les logs${NC}"
echo "   kubectl logs -n $NAMESPACE -l app.kubernetes.io/component=backend --tail=50"
echo ""

if [ "$PROTOCOL" = "https" ]; then
    echo "5. ${YELLOW}Vérifier le certificat TLS${NC}"
    echo "   kubectl get certificate -n $NAMESPACE"
    echo "   kubectl describe certificate -n $NAMESPACE keda-dashboard-tls"
    echo ""
fi

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
