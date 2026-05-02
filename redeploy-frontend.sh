#!/bin/bash

# Script de redéploiement du frontend avec la nouvelle interface
# Usage: ./redeploy-frontend.sh

set -e

echo "🚀 Redéploiement du Frontend KEDA Dashboard"
echo "==========================================="
echo ""

# Couleurs pour les messages
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Fonction pour afficher les messages
info() {
    echo -e "${GREEN}✓${NC} $1"
}

warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

error() {
    echo -e "${RED}✗${NC} $1"
}

# Étape 1 : Vérifier que les modifications sont présentes
echo "📝 Étape 1 : Vérification du code source"
if grep -q "selectedDate" frontend/src/pages/CronCalendarPage.js; then
    info "Les modifications sont présentes dans le code source"
else
    error "Les modifications ne sont pas présentes dans le code source"
    exit 1
fi
echo ""

# Étape 2 : Nettoyer et reconstruire le frontend
echo "🧹 Étape 2 : Nettoyage et reconstruction du frontend"
cd frontend

# Nettoyer le cache
if [ -d "node_modules/.cache" ]; then
    rm -rf node_modules/.cache
    info "Cache node_modules nettoyé"
fi

if [ -d "build" ]; then
    rm -rf build
    info "Dossier build supprimé"
fi

# Reconstruire
info "Reconstruction du frontend en cours..."
if yarn build; then
    info "Build du frontend réussi"
else
    error "Échec du build du frontend"
    exit 1
fi

cd ..
echo ""

# Étape 3 : Vérifier que le build contient les nouveaux fichiers
echo "🔍 Étape 3 : Vérification du build"
BUILD_SIZE=$(du -sh frontend/build | cut -f1)
info "Taille du build : $BUILD_SIZE"

if [ -d "frontend/build/static/js" ]; then
    JS_FILES=$(ls -lh frontend/build/static/js/main.*.js 2>/dev/null | wc -l)
    if [ "$JS_FILES" -gt 0 ]; then
        info "Fichiers JavaScript générés : $JS_FILES"
    else
        warn "Aucun fichier JavaScript trouvé"
    fi
fi
echo ""

# Étape 4 : Reconstruire l'image Docker
echo "🐳 Étape 4 : Reconstruction de l'image Docker"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
IMAGE_TAG="keda-dashboard:$TIMESTAMP"

warn "Construction de l'image Docker : $IMAGE_TAG"
warn "Cela peut prendre quelques minutes..."

if docker build -t "$IMAGE_TAG" .; then
    info "Image Docker construite avec succès : $IMAGE_TAG"
else
    error "Échec de la construction de l'image Docker"
    exit 1
fi
echo ""

# Étape 5 : Instructions pour le déploiement
echo "📦 Étape 5 : Déploiement"
echo ""
echo "L'image Docker a été construite avec le tag : $IMAGE_TAG"
echo ""
echo "Pour déployer cette image :"
echo ""
echo "1. Si vous utilisez Docker Compose :"
echo "   docker-compose down"
echo "   docker-compose up -d"
echo ""
echo "2. Si vous utilisez Kubernetes :"
echo "   # Pousser l'image vers votre registry"
echo "   docker tag $IMAGE_TAG votre-registry/$IMAGE_TAG"
echo "   docker push votre-registry/$IMAGE_TAG"
echo ""
echo "   # Mettre à jour le déploiement"
echo "   kubectl set image deployment/keda-dashboard-frontend frontend=votre-registry/$IMAGE_TAG -n votre-namespace"
echo "   kubectl rollout status deployment/keda-dashboard-frontend -n votre-namespace"
echo ""
echo "3. Si vous testez en local :"
echo "   docker run -p 8001:8001 $IMAGE_TAG"
echo ""

# Étape 6 : Instructions pour le navigateur
echo "🌐 Étape 6 : Vider le cache du navigateur"
echo ""
echo "Après le déploiement, n'oubliez pas de vider le cache de votre navigateur :"
echo ""
echo "  Chrome/Edge/Firefox : Ctrl + Shift + R (Windows/Linux)"
echo "                        Cmd + Shift + R (Mac)"
echo ""
echo "  Ou ouvrir les DevTools (F12) et clic droit sur le bouton de rafraîchissement"
echo "  puis sélectionner 'Vider le cache et effectuer une actualisation forcée'"
echo ""

info "Script terminé avec succès !"
echo ""
echo "📋 Résumé :"
echo "  - Code source : ✓ Vérifié"
echo "  - Frontend build : ✓ Reconstruit"
echo "  - Image Docker : ✓ Construite ($IMAGE_TAG)"
echo "  - Prochaine étape : Déployer l'image et vider le cache du navigateur"
echo ""
