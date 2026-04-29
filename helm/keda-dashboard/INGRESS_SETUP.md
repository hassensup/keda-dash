# Guide de Configuration Ingress

Ce guide explique comment exposer KEDA Dashboard publiquement via un Ingress Kubernetes.

## Prérequis

1. **Ingress Controller installé** dans votre cluster :
   - NGINX Ingress Controller
   - AWS ALB Ingress Controller
   - Traefik
   - Autre

2. **Nom de domaine** pointant vers votre cluster (ou LoadBalancer IP)

3. **(Optionnel) Cert-manager** pour les certificats TLS automatiques

## Configuration Rapide

### 1. NGINX Ingress Controller

```bash
helm upgrade --install keda-dash ./helm/keda-dashboard \
  --namespace test \
  --create-namespace \
  --set ingress.enabled=true \
  --set ingress.className=nginx \
  --set ingress.hosts[0].host=keda-dashboard.example.com \
  --set ingress.hosts[0].paths[0].path=/ \
  --set ingress.hosts[0].paths[0].pathType=Prefix \
  --set auth.okta.redirectUri=https://keda-dashboard.example.com/api/auth/okta/callback
```

### 2. AWS ALB Ingress Controller

```bash
helm upgrade --install keda-dash ./helm/keda-dashboard \
  --namespace test \
  --create-namespace \
  -f examples/values-ingress-alb.yaml
```

**Important :** Modifiez `examples/values-ingress-alb.yaml` pour :
- Remplacer `certificate-arn` par votre ARN de certificat ACM
- Remplacer `keda-dashboard.example.com` par votre domaine

### 3. Traefik Ingress Controller

```bash
helm upgrade --install keda-dash ./helm/keda-dashboard \
  --namespace test \
  --create-namespace \
  -f examples/values-ingress-traefik.yaml
```

## Configuration Détaillée

### Fichier values.yaml

```yaml
ingress:
  enabled: true
  className: "nginx"  # ou "alb", "traefik", etc.
  
  annotations:
    # Pour NGINX avec cert-manager
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

# Configuration Okta avec l'URL publique
auth:
  okta:
    enabled: true
    domain: "your-org.okta.com"
    clientId: "your-client-id"
    clientSecret: "your-client-secret"
    redirectUri: "https://keda-dashboard.example.com/api/auth/okta/callback"

# CORS pour l'URL publique
backend:
  config:
    corsOrigins: "https://keda-dashboard.example.com"
```

## Configuration TLS/HTTPS

### Option 1 : Cert-manager (Recommandé)

1. **Installer cert-manager** :
```bash
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml
```

2. **Créer un ClusterIssuer** :
```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: your-email@example.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
```

3. **Appliquer** :
```bash
kubectl apply -f cluster-issuer.yaml
```

4. **Déployer avec cert-manager** :
```yaml
ingress:
  enabled: true
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
  tls:
    - secretName: keda-dashboard-tls
      hosts:
        - keda-dashboard.example.com
```

### Option 2 : Certificat Existant

1. **Créer un Secret TLS** :
```bash
kubectl create secret tls keda-dashboard-tls \
  --cert=path/to/tls.crt \
  --key=path/to/tls.key \
  --namespace test
```

2. **Référencer le Secret** :
```yaml
ingress:
  tls:
    - secretName: keda-dashboard-tls
      hosts:
        - keda-dashboard.example.com
```

### Option 3 : AWS ACM (pour ALB)

```yaml
ingress:
  className: "alb"
  annotations:
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:region:account:certificate/xxx
```

## Configuration DNS

### Pour NGINX/Traefik

1. **Obtenir l'IP du LoadBalancer** :
```bash
kubectl get svc -n ingress-nginx ingress-nginx-controller
```

2. **Créer un enregistrement DNS A** :
```
keda-dashboard.example.com  →  <EXTERNAL-IP>
```

### Pour AWS ALB

1. **Obtenir le DNS du ALB** :
```bash
kubectl get ingress -n test keda-dash-keda-dashboard
```

2. **Créer un enregistrement DNS CNAME** :
```
keda-dashboard.example.com  →  <ALB-DNS-NAME>
```

## Vérification

### 1. Vérifier l'Ingress

```bash
kubectl get ingress -n test
kubectl describe ingress -n test keda-dash-keda-dashboard
```

### 2. Tester l'accès

```bash
# Test HTTP
curl http://keda-dashboard.example.com/api/health

# Test HTTPS
curl https://keda-dashboard.example.com/api/health
```

### 3. Vérifier la configuration Okta

```bash
curl https://keda-dashboard.example.com/api/auth/config
```

Devrait retourner :
```json
{
  "okta_enabled": true,
  "local_auth_enabled": true
}
```

## Configuration Okta

Après avoir exposé l'application publiquement :

1. **Allez dans Okta Admin Console**
2. **Applications → Votre App → General Settings**
3. **Ajoutez l'URL de callback** :
   ```
   https://keda-dashboard.example.com/api/auth/okta/callback
   ```
4. **Sauvegardez**

## Exemples de Configuration

### Production avec HTTPS

```yaml
ingress:
  enabled: true
  className: "nginx"
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/force-ssl-redirect: "true"
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
    redirectUri: "https://keda-dashboard.example.com/api/auth/okta/callback"

backend:
  config:
    corsOrigins: "https://keda-dashboard.example.com"
```

### Staging/Test sans HTTPS

```yaml
ingress:
  enabled: true
  className: "nginx"
  hosts:
    - host: keda-dashboard-staging.example.com
      paths:
        - path: /
          pathType: Prefix
  tls: []

auth:
  okta:
    enabled: true
    redirectUri: "http://keda-dashboard-staging.example.com/api/auth/okta/callback"

backend:
  config:
    corsOrigins: "http://keda-dashboard-staging.example.com"
```

### AWS EKS avec ALB

```yaml
ingress:
  enabled: true
  className: "alb"
  annotations:
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:eu-west-1:123456789012:certificate/xxx
    alb.ingress.kubernetes.io/ssl-redirect: '443'
    alb.ingress.kubernetes.io/healthcheck-path: /api/health
  hosts:
    - host: keda-dashboard.example.com
      paths:
        - path: /
          pathType: Prefix

auth:
  okta:
    enabled: true
    redirectUri: "https://keda-dashboard.example.com/api/auth/okta/callback"
```

## Dépannage

### Ingress ne crée pas de LoadBalancer

**Vérifiez que l'Ingress Controller est installé :**
```bash
kubectl get pods -n ingress-nginx
# ou
kubectl get pods -n kube-system | grep alb
```

### Certificat TLS non généré

**Vérifiez cert-manager :**
```bash
kubectl get certificate -n test
kubectl describe certificate -n test keda-dashboard-tls
```

### 502 Bad Gateway

**Vérifiez que le backend est accessible :**
```bash
kubectl get pods -n test
kubectl logs -n test -l app.kubernetes.io/component=backend
```

### Okta callback échoue

**Vérifiez que l'URL de callback correspond exactement :**
- Dans Okta Admin Console
- Dans `auth.okta.redirectUri`
- Incluez le protocole (`https://`)
- Incluez le chemin complet (`/api/auth/okta/callback`)

## Sécurité

### Recommandations

1. **Toujours utiliser HTTPS en production**
2. **Configurer des limites de taux** (rate limiting)
3. **Activer WAF** si disponible (AWS WAF, Cloudflare, etc.)
4. **Restreindre CORS** aux domaines autorisés
5. **Utiliser des secrets Kubernetes** pour les credentials sensibles

### Exemple avec Rate Limiting (NGINX)

```yaml
ingress:
  annotations:
    nginx.ingress.kubernetes.io/limit-rps: "10"
    nginx.ingress.kubernetes.io/limit-connections: "20"
```

## Support

Pour plus d'informations :
- [NGINX Ingress Controller](https://kubernetes.github.io/ingress-nginx/)
- [AWS Load Balancer Controller](https://kubernetes-sigs.github.io/aws-load-balancer-controller/)
- [Traefik](https://doc.traefik.io/traefik/providers/kubernetes-ingress/)
- [Cert-manager](https://cert-manager.io/docs/)
