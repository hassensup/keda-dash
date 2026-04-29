# Résumé - Mise à Jour Ingress du Chart Helm

## Modifications Apportées

### 1. Fichiers Modifiés

#### `helm/keda-dashboard/values.yaml`
- ✅ Configuration Ingress améliorée avec commentaires détaillés
- ✅ Support pour différents Ingress Controllers (NGINX, ALB, Traefik)
- ✅ Exemples d'annotations pour chaque type
- ✅ Configuration TLS simplifiée

#### `helm/keda-dashboard/templates/ingress.yaml`
- ✅ Correction du nom du service backend
- ✅ Correction du port (utilise `backend.service.port`)
- ✅ Support du pathType par défaut
- ✅ Template compatible avec tous les Ingress Controllers

#### `helm/keda-dashboard/README.md`
- ✅ Section Ingress mise à jour
- ✅ Référence au guide INGRESS_SETUP.md

### 2. Nouveaux Fichiers Créés

#### Exemples de Configuration
- ✅ `helm/keda-dashboard/examples/values-ingress-nginx.yaml`
- ✅ `helm/keda-dashboard/examples/values-ingress-alb.yaml`
- ✅ `helm/keda-dashboard/examples/values-ingress-traefik.yaml`

#### Documentation
- ✅ `helm/keda-dashboard/INGRESS_SETUP.md` - Guide complet de configuration Ingress

#### Scripts
- ✅ `deploy_with_ingress.sh` - Script de déploiement automatique avec Ingress

---

## Utilisation

### Option 1 : Script Automatique (Recommandé)

```bash
# Déploiement avec NGINX Ingress
./deploy_with_ingress.sh keda-dashboard.example.com nginx

# Déploiement avec AWS ALB
./deploy_with_ingress.sh keda-dashboard.example.com alb
```

Le script vous guidera à travers :
- Configuration HTTPS/HTTP
- Configuration Okta (optionnel)
- Déploiement automatique
- Vérification post-déploiement

### Option 2 : Helm avec Fichier d'Exemple

```bash
# Pour NGINX Ingress
helm upgrade --install keda-dash ./helm/keda-dashboard \
  --namespace test \
  -f helm/keda-dashboard/examples/values-ingress-nginx.yaml

# Pour AWS ALB
helm upgrade --install keda-dash ./helm/keda-dashboard \
  --namespace test \
  -f helm/keda-dashboard/examples/values-ingress-alb.yaml
```

**Important :** Modifiez les fichiers d'exemple pour :
- Remplacer `keda-dashboard.example.com` par votre domaine
- Ajouter vos credentials Okta
- Ajuster les annotations selon vos besoins

### Option 3 : Helm avec Paramètres en Ligne

```bash
helm upgrade --install keda-dash ./helm/keda-dashboard \
  --namespace test \
  --create-namespace \
  --set ingress.enabled=true \
  --set ingress.className=nginx \
  --set ingress.hosts[0].host=keda-dashboard.example.com \
  --set ingress.hosts[0].paths[0].path=/ \
  --set ingress.hosts[0].paths[0].pathType=Prefix \
  --set ingress.tls[0].secretName=keda-dashboard-tls \
  --set ingress.tls[0].hosts[0]=keda-dashboard.example.com \
  --set auth.okta.redirectUri=https://keda-dashboard.example.com/api/auth/okta/callback \
  --set backend.config.corsOrigins=https://keda-dashboard.example.com
```

---

## Configuration Ingress par Type

### NGINX Ingress Controller

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
```

### AWS ALB Ingress Controller

```yaml
ingress:
  enabled: true
  className: "alb"
  annotations:
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:region:account:certificate/xxx
    alb.ingress.kubernetes.io/ssl-redirect: '443'
    alb.ingress.kubernetes.io/healthcheck-path: /api/health
  hosts:
    - host: keda-dashboard.example.com
      paths:
        - path: /
          pathType: Prefix
```

### Traefik Ingress Controller

```yaml
ingress:
  enabled: true
  className: "traefik"
  annotations:
    traefik.ingress.kubernetes.io/router.tls: "true"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
  hosts:
    - host: keda-dashboard.example.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: keda-dashboard-tls
      hosts:
        - keda-dashboard.example.com
```

---

## Configuration Okta avec Ingress

Une fois l'Ingress configuré, mettez à jour Okta :

### 1. Dans le Chart Helm

```yaml
auth:
  okta:
    enabled: true
    domain: "your-org.okta.com"
    clientId: "your-client-id"
    clientSecret: "your-client-secret"
    redirectUri: "https://keda-dashboard.example.com/api/auth/okta/callback"
```

### 2. Dans Okta Admin Console

1. Allez sur https://your-org.okta.com/admin
2. Applications → Votre App → General Settings
3. Ajoutez l'URL de callback :
   ```
   https://keda-dashboard.example.com/api/auth/okta/callback
   ```
4. Sauvegardez

---

## Vérification

### 1. Vérifier l'Ingress

```bash
kubectl get ingress -n test
kubectl describe ingress -n test keda-dash-keda-dashboard
```

### 2. Tester l'Accès

```bash
# Health check
curl https://keda-dashboard.example.com/api/health

# Configuration auth
curl https://keda-dashboard.example.com/api/auth/config
```

### 3. Vérifier le Certificat TLS (si HTTPS)

```bash
kubectl get certificate -n test
kubectl describe certificate -n test keda-dashboard-tls
```

### 4. Vérifier les Logs

```bash
kubectl logs -n test -l app.kubernetes.io/component=backend --tail=50
```

---

## Configuration DNS

### Pour NGINX/Traefik

1. Obtenir l'IP du LoadBalancer :
```bash
kubectl get svc -n ingress-nginx ingress-nginx-controller
```

2. Créer un enregistrement DNS A :
```
keda-dashboard.example.com  →  <EXTERNAL-IP>
```

### Pour AWS ALB

1. Obtenir le DNS du ALB :
```bash
kubectl get ingress -n test keda-dash-keda-dashboard
```

2. Créer un enregistrement DNS CNAME :
```
keda-dashboard.example.com  →  <ALB-DNS-NAME>
```

---

## Dépannage

### Ingress ne crée pas de LoadBalancer

**Vérifiez que l'Ingress Controller est installé :**
```bash
# Pour NGINX
kubectl get pods -n ingress-nginx

# Pour ALB
kubectl get pods -n kube-system | grep aws-load-balancer-controller
```

### Certificat TLS non généré

**Vérifiez cert-manager :**
```bash
kubectl get certificate -n test
kubectl describe certificate -n test keda-dashboard-tls
kubectl get clusterissuer
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

---

## Ressources

### Documentation
- `helm/keda-dashboard/INGRESS_SETUP.md` - Guide complet
- `helm/keda-dashboard/README.md` - Documentation du chart
- `OKTA_CONFIGURATION_GUIDE.md` - Guide Okta

### Exemples
- `helm/keda-dashboard/examples/values-ingress-nginx.yaml`
- `helm/keda-dashboard/examples/values-ingress-alb.yaml`
- `helm/keda-dashboard/examples/values-ingress-traefik.yaml`

### Scripts
- `deploy_with_ingress.sh` - Déploiement automatique
- `configure_okta.sh` - Configuration Okta

---

## Prochaines Étapes

1. ✅ Choisissez votre Ingress Controller (NGINX, ALB, Traefik)
2. ✅ Configurez votre domaine DNS
3. ✅ Déployez avec le script ou Helm
4. ✅ Configurez Okta (si activé)
5. ✅ Testez l'accès et l'authentification

**Besoin d'aide ?** Consultez `helm/keda-dashboard/INGRESS_SETUP.md` pour plus de détails.
