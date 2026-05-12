# Configuration Rapide Okta SSO

## 🚀 Configuration en 5 Minutes

### 1. Créer un Fichier de Configuration

Créez `values-okta.yaml` avec votre configuration:

```yaml
# values-okta.yaml
auth:
  okta:
    enabled: true
    domain: "groupecanalplus.okta.com"
    clientId: "0oabk7991366IOzXr417"
    clientSecret: "VOTRE_CLIENT_SECRET_ICI"
    redirectUri: "https://VOTRE_INGRESS/api/auth/okta/callback"
    scopes: "openid profile email"

ingress:
  enabled: true
  className: "alb"  # ou nginx, traefik selon votre cluster
  hosts:
    - host: VOTRE_INGRESS
      paths:
        - path: /
          pathType: Prefix
  annotations:
    # Pour ALB
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTP": 80}, {"HTTPS": 443}]'
```

### 2. Déployer avec Helm

```bash
# Mettre à jour l'application
helm upgrade keda-dashboard ./helm/keda-dashboard \
  -n test \
  -f values-okta.yaml

# Vérifier le déploiement
kubectl get pods -n test -w
```

### 3. Vérifier la Configuration

```bash
# Vérifier que Okta est activé
kubectl get configmap keda-dashboard-config -n test -o yaml | grep OKTA

# Devrait afficher:
# OKTA_ENABLED: "true"
# OKTA_DOMAIN: "groupecanalplus.okta.com"
# OKTA_CLIENT_ID: "0oabk7991366IOzXr417"
# OKTA_REDIRECT_URI: "https://VOTRE_INGRESS/api/auth/okta/callback"
# FRONTEND_URL: "https://VOTRE_INGRESS"
```

### 4. Configurer l'Application Okta

Dans la console Okta (https://groupecanalplus-admin.okta.com):

1. **General Settings**:
   - Sign-in redirect URIs: `https://VOTRE_INGRESS/api/auth/okta/callback`
   - Sign-out redirect URIs: `https://VOTRE_INGRESS/`
   - Initiate login URI: `https://VOTRE_INGRESS/api/auth/okta/login`

2. **Trusted Origins**:
   - Origin URL: `https://VOTRE_INGRESS`
   - Type: CORS + Redirect

3. **Assignments**:
   - Assigner les utilisateurs/groupes qui peuvent accéder

### 5. Tester

1. Ouvrir `https://VOTRE_INGRESS/`
2. Cliquer sur "Sign in with Okta"
3. Devrait rediriger vers Okta
4. S'authentifier
5. Devrait revenir sur l'application connecté

## 🔧 Configuration Avancée

### Avec TLS/HTTPS

```yaml
ingress:
  enabled: true
  className: "nginx"
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
  hosts:
    - host: keda-dashboard.example.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: keda-dashboard-tls
      hosts:
        - keda-dashboard.example.com

auth:
  okta:
    enabled: true
    domain: "groupecanalplus.okta.com"
    clientId: "0oabk7991366IOzXr417"
    clientSecret: "VOTRE_SECRET"
    redirectUri: "https://keda-dashboard.example.com/api/auth/okta/callback"
```

### Avec AWS ALB

```yaml
ingress:
  enabled: true
  className: "alb"
  annotations:
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTP": 80}, {"HTTPS": 443}]'
    alb.ingress.kubernetes.io/ssl-redirect: '443'
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:region:account:certificate/xxx
  hosts:
    - host: keda-dashboard.example.com
      paths:
        - path: /
          pathType: Prefix
```

## 📝 Variables d'Environnement Générées

Le Helm chart génère automatiquement ces variables:

```bash
# Authentification
OKTA_ENABLED=true
LOCAL_AUTH_ENABLED=true
JWT_SECRET=[généré depuis values.yaml]
TOKEN_EXPIRATION_HOURS=24

# Okta
OKTA_DOMAIN=groupecanalplus.okta.com
OKTA_CLIENT_ID=0oabk7991366IOzXr417
OKTA_CLIENT_SECRET=[depuis Secret]
OKTA_REDIRECT_URI=https://VOTRE_INGRESS/api/auth/okta/callback
OKTA_SCOPES=openid profile email

# Frontend (auto-détecté depuis Ingress)
FRONTEND_URL=https://VOTRE_INGRESS

# Application
CORS_ORIGINS=*
K8S_MODE=in-cluster
```

## 🔐 Sécurité

### Stocker le Client Secret de Manière Sécurisée

Au lieu de mettre le secret dans `values-okta.yaml`:

```bash
# Créer un Secret Kubernetes
kubectl create secret generic okta-secret \
  -n test \
  --from-literal=client-secret='VOTRE_CLIENT_SECRET'

# Référencer dans values.yaml
auth:
  okta:
    enabled: true
    domain: "groupecanalplus.okta.com"
    clientId: "0oabk7991366IOzXr417"
    clientSecretRef:
      name: okta-secret
      key: client-secret
```

### Générer un JWT Secret Sécurisé

```bash
# Générer un secret aléatoire
openssl rand -base64 32

# Utiliser dans values.yaml
auth:
  jwt:
    secret: "VOTRE_SECRET_GENERE_ICI"
```

## 🧪 Tests

### Test 1: Configuration Chargée
```bash
curl https://VOTRE_INGRESS/api/auth/config
# Devrait retourner: {"okta_enabled": true, "local_auth_enabled": true}
```

### Test 2: Redirection Okta
```bash
curl -I https://VOTRE_INGRESS/api/auth/okta/login
# Devrait retourner:
# HTTP/1.1 302 Found
# Location: https://groupecanalplus.okta.com/oauth2/v1/authorize?...
```

### Test 3: Authentification Complète
1. Ouvrir navigateur: `https://VOTRE_INGRESS/`
2. Cliquer "Sign in with Okta"
3. S'authentifier sur Okta
4. Vérifier redirection vers home
5. Vérifier token dans localStorage

## 🐛 Dépannage Rapide

### Okta Désactivé
```bash
# Vérifier
kubectl get configmap keda-dashboard-config -n test -o yaml | grep OKTA_ENABLED

# Si "false", vérifier values.yaml et redéployer
helm upgrade keda-dashboard ./helm/keda-dashboard -n test -f values-okta.yaml
```

### Redirect URI Mismatch
```bash
# Vérifier l'URI configurée
kubectl get configmap keda-dashboard-config -n test -o yaml | grep OKTA_REDIRECT_URI

# Doit correspondre EXACTEMENT à celle dans Okta
# Okta: https://example.com/api/auth/okta/callback
# ConfigMap: https://example.com/api/auth/okta/callback
# ✅ Identiques
```

### Frontend URL Incorrecte
```bash
# Vérifier
kubectl get configmap keda-dashboard-config -n test -o yaml | grep FRONTEND_URL

# Devrait être l'URL publique de l'Ingress
# Si incorrect, vérifier ingress.hosts dans values.yaml
```

## 📚 Ressources

- [Guide Complet Okta](./OKTA_CONFIGURATION_GUIDE.md)
- [Configuration Ingress](./helm/keda-dashboard/INGRESS_SETUP.md)
- [Correction Redirect](./CORRECTION_OKTA_REDIRECT.md)
- [Script de Configuration](./configure_okta.sh)

---

**Temps estimé**: 5-10 minutes
**Prérequis**: Application Okta créée, Ingress configuré
**Difficulté**: Facile
