#!/bin/bash

# Script pour surveiller les logs Okta en temps réel
# Usage: ./watch_okta_logs.sh [namespace]

NAMESPACE="${1:-test}"

echo "=========================================="
echo "Surveillance des Logs Okta"
echo "Namespace: $NAMESPACE"
echo "=========================================="
echo ""
echo "Appuyez sur Ctrl+C pour arrêter"
echo ""

# Suivre les logs en temps réel et filtrer les lignes Okta
kubectl logs -n $NAMESPACE -l app=keda-dashboard-backend -f --tail=0 2>/dev/null | grep --line-buffered -E "OKTA|okta|Okta|oauth2|OAuth2"
