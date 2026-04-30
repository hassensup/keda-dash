# Déploiement Okta - Guide Rapide

## 🚀 Déploiement Immédiat

### Étape 1: Éditer la Configuration

Éditez `values-okta-complete.yaml` et remplacez:

```yaml
frontend:
  # ✅ Votre URL publique
  url: "https://keda-dashboard.dev.middle-bo.canal.aws.io-cplus.net"

auth:
  jwt:
    # ✅ Générer avec: openssl rand -base64 32
    secret: "REMPLACER_PAR_UN_SECRET_ALEATOIRE"
  
  okta:
    enabled: true
    domain: "integrator-2906309.okta.com"
    clientId: "0oa12hyd5y32AhyPN698"
    # ✅ Votre Client Secret Okta
    clientSecret: "REMPLACER_PAR_VOTRE_CLIENT_SECRET"
    redirectUri: "https://keda-dashboard.dev.middle-bo.canal.aws.io-cplus.net/api/auth/okta/callback"
```

### Étape 2: Déployer

```bash
# Déployer avec Helm
helm upgrade keda-dashboard ./helm/keda-dashboard \
  -n test \
  -f values-okta-complete.yaml

# Attendre que le pod redémarre
kubectl rollout status deployment/keda-dashboard-backend -n test
```

### Étape 3: Vérifier

```bash
# Vérifier FRONTEND_URL
kubectl get configmap keda-dashboard-config -n test -o yaml | grep FRONTEND_URL

# Devrait afficher:
# FRONTEND_URL: "https://keda-dashboard.dev.middle-bo.canal.aws.io-cplus.net"
```

### Étape 4: Tester

1. Ouvrir: `https://keda-dashboard.dev.middle-bo.canal.aws.io-cplus.net/`
2. Cliquer: "Sign in with Okta"
3. S'authentifier avec Okta
4. ✅ Devrait être redirigé vers la page d'accueil connecté

## 🔧 Alternative: Patch Rapide du ConfigMap

Si vous ne voulez pas attendre le build CI/CD, vous pouvez patcher directement le ConfigMap:

```bash
# Patcher le ConfigMap
kubectl patch configmap keda-dashboard-config -n test --type merge -p '{"data":{"FRONTEND_URL":"https://keda-dashboard.dev.middle-bo.canal.aws.io-cplus.net"}}'

# Redémarrer le backend
kubectl rollout restart deployment/keda-dashboard-backend -n test

# Attendre
kubectl rollout status deployment/keda-dashboard-backend -n test

# Tester immédiatement
```

## 📋 Checklist Complète

### Configuration Okta (Console Okta)
- [ ] Authorization Server "default" existe et est actif
- [ ] Application créée avec Client ID: `0oa12hyd5y32AhyPN698`
- [ ] Grant type "Authorization Code" activé
- [ ] Sign-in redirect URI: `https://keda-dashboard.dev.middle-bo.canal.aws.io-cplus.net/api/auth/okta/callback`
- [ ] Trusted Origin ajouté: `https://keda-dashboard.dev.middle-bo.canal.aws.io-cplus.net`
- [ ] Utilisateur assigné à l'application

### Configuration Helm
- [ ] `frontend.url` configuré
- [ ] `auth.okta.enabled: true`
- [ ] `auth.okta.domain` correct (sans -admin)
- [ ] `auth.okta.clientId` correct
- [ ] `auth.okta.clientSecret` configuré
- [ ] `auth.okta.redirectUri` correspond à Okta

### Déploiement
- [ ] Helm upgrade exécuté
- [ ] Pod backend redémarré
- [ ] ConfigMap contient FRONTEND_URL
- [ ] Logs backend sans erreur

### Test
- [ ] Page de login accessible
- [ ] Bouton "Sign in with Okta" visible
- [ ] Redirection vers Okta fonctionne
- [ ] Authentification Okta réussie
- [ ] Redirection vers frontend fonctionne
- [ ] Utilisateur connecté
- [ ] Token dans localStorage

## 🐛 Dépannage

### Pas de redirection après Okta
```bash
# Vérifier FRONTEND_URL
kubectl get configmap keda-dashboard-config -n test -o yaml | grep FRONTEND_URL

# Si vide, patcher:
kubectl patch configmap keda-dashboard-config -n test --type merge -p '{"data":{"FRONTEND_URL":"https://keda-dashboard.dev.middle-bo.canal.aws.io-cplus.net"}}'

# Redémarrer
kubectl rollout restart deployment/keda-dashboard-backend -n test
```

### Erreur 500
```bash
# Voir les logs
kubectl logs -n test -l app=keda-dashboard-backend --tail=100

# Chercher les erreurs
kubectl logs -n test -l app=keda-dashboard-backend --tail=200 | grep ERROR
```

### Token non stocké
```bash
# Vérifier dans la console du navigateur
localStorage.getItem("token")

# Si null, vérifier les logs frontend
# Ouvrir DevTools → Console
```

## 📞 Support

Si le problème persiste:

1. Exécuter les diagnostics:
   ```bash
   ./check_frontend_url.sh test
   ./diagnose_okta_config.sh test
   ./test_okta_url.sh test
   ```

2. Collecter les logs:
   ```bash
   kubectl logs -n test -l app=keda-dashboard-backend --tail=500 > backend-logs.txt
   kubectl get configmap keda-dashboard-config -n test -o yaml > configmap.yaml
   ```

3. Vérifier la configuration Okta dans la console

---

**Temps estimé**: 5 minutes
**Prérequis**: Client Secret Okta, accès kubectl
