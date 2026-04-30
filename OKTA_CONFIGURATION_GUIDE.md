# Guide de Configuration Okta

## Problème Actuel

Okta est configuré dans le ConfigMap mais **désactivé automatiquement** car `OKTA_REDIRECT_URI` est vide.

```yaml
OKTA_ENABLED: "true"
OKTA_REDIRECT_URI: ""  # ❌ VIDE - Okta sera désactivé
```

## Configuration Actuelle

```yaml
OKTA_ENABLED: "true"
OKTA_CLIENT_ID: 0oabk7991366IOzXB417
OKTA_DOMAIN: https://groupecanalplus.okta.com/oauth2/ausbk7e6q48W7VUZr417
OKTA_REDIRECT_URI: ""  # ❌ À CONFIGURER
OKTA_SCOPES: openid profile email
```

## Solution

### Étape 1 : Déterminer l'URL de votre application

Vous devez d'abord savoir comment vous accédez à l'application. Voici les options :

#### Option A : Port-Forward (développement/test)
```bash
kubectl port-forward -n test svc/keda-dash-keda-dashboard-backend 8001:8001
```
**URL de callback :** `http://localhost:8001/api/auth/okta/callback`

#### Option B : Ingress (production)
Si vous avez un Ingress configuré (ex: `https://keda-dashboard.example.com`):
**URL de callback :** `https://keda-dashboard.example.com/api/auth/okta/callback`

#### Option C : LoadBalancer
Si vous exposez le service via un LoadBalancer:
**URL de callback :** `http://<EXTERNAL-IP>:8001/api/auth/okta/callback`

### Étape 2 : Configurer Okta Application

1. **Connectez-vous à Okta Admin Console** : https://groupecanalplus.okta.com/admin
2. **Allez dans Applications > Applications**
3. **Trouvez votre application** (Client ID: `0oabk7991366IOzXB417`)
4. **Ajoutez l'URL de callback** dans "Sign-in redirect URIs" :
   - Exemple : `http://localhost:8001/api/auth/okta/callback`
   - Ou : `https://keda-dashboard.example.com/api/auth/okta/callback`
5. **Sauvegardez**

### Étape 3 : Mettre à jour le Helm Chart

Modifiez votre fichier `values.yaml` ou les valeurs Helm :

```yaml
auth:
  okta:
    enabled: true
    domain: "groupecanalplus.okta.com/oauth2/ausbk7e6q48W7VUZr417"
    clientId: "0oabk7991366IOzXB417"
    clientSecret: "<votre-secret>"  # Doit être dans le Secret
    redirectUri: "http://localhost:8001/api/auth/okta/callback"  # ✅ À ADAPTER
    scopes: "openid profile email"
```

### Étape 4 : Redéployer

#### Via Helm directement
```bash
helm upgrade keda-dash ./helm/keda-dashboard \
  --namespace test \
  --set auth.okta.redirectUri="http://localhost:8001/api/auth/okta/callback"
```

#### Via ArgoCD
1. Mettez à jour votre fichier de valeurs dans Git
2. ArgoCD synchronisera automatiquement

### Étape 5 : Vérifier la Configuration

```bash
# 1. Vérifier le ConfigMap
kubectl get configmap -n test keda-dash-keda-dashboard-config -o yaml | grep OKTA

# 2. Redémarrer le pod backend
kubectl delete pod -n test -l app.kubernetes.io/component=backend

# 3. Vérifier les logs
kubectl logs -n test -l app.kubernetes.io/component=backend --tail=50 | grep -i okta

# 4. Tester l'endpoint de configuration
POD_NAME=$(kubectl get pod -n test -l app.kubernetes.io/component=backend -o jsonpath='{.items[0].metadata.name}')
kubectl exec -n test $POD_NAME -- curl -s http://localhost:8001/api/auth/config
```

**Résultat attendu :**
```json
{
  "okta_enabled": true,
  "local_auth_enabled": true
}
```

## Frontend - Affichage du Bouton Okta

Une fois Okta activé, le frontend affichera automatiquement le bouton "Sign in with Okta" sur la page de login.

Le frontend appelle `/api/auth/config` au chargement et affiche les options d'authentification disponibles.

### Vérification Frontend

1. **Ouvrez la console du navigateur** (F12)
2. **Allez sur la page de login**
3. **Vérifiez la requête** à `/api/auth/config`
4. **Vérifiez la réponse** : `okta_enabled` doit être `true`

## Dépannage

### Okta toujours désactivé après configuration

**Vérifiez que toutes les variables sont définies :**
```bash
kubectl exec -n test <pod-name> -- env | grep OKTA
```

Doit afficher :
```
OKTA_ENABLED=true
OKTA_DOMAIN=groupecanalplus.okta.com/oauth2/ausbk7e6q48W7VUZr417
OKTA_CLIENT_ID=0oabk7991366IOzXB417
OKTA_CLIENT_SECRET=<secret>
OKTA_REDIRECT_URI=http://localhost:8001/api/auth/okta/callback
OKTA_SCOPES=openid profile email
```

### Le bouton Okta n'apparaît pas dans le GUI

1. **Vérifiez `/api/auth/config`** retourne `okta_enabled: true`
2. **Videz le cache du navigateur** (Ctrl+Shift+R)
3. **Vérifiez la console du navigateur** pour des erreurs JavaScript

### Erreur "Invalid redirect URI" lors de la connexion Okta

L'URL de callback configurée dans Helm ne correspond pas à celle configurée dans Okta.

**Solution :**
- Assurez-vous que l'URL dans Okta Admin Console correspond exactement à `OKTA_REDIRECT_URI`
- Incluez le protocole (`http://` ou `https://`)
- Incluez le port si nécessaire (`:8001`)
- Le chemin doit être `/api/auth/okta/callback`

## Configuration Recommandée par Environnement

### Développement Local
```yaml
auth:
  okta:
    redirectUri: "http://localhost:8001/api/auth/okta/callback"
```

### Staging
```yaml
auth:
  okta:
    redirectUri: "https://keda-dashboard-staging.example.com/api/auth/okta/callback"
```

### Production
```yaml
auth:
  okta:
    redirectUri: "https://keda-dashboard.example.com/api/auth/okta/callback"
```

## Exemple Complet de Configuration Helm

```yaml
# values.yaml
auth:
  jwt:
    secret: "your-super-secret-jwt-key-change-in-production"
    expirationHours: 24
  
  local:
    enabled: true
  
  okta:
    enabled: true
    domain: "groupecanalplus.okta.com/oauth2/ausbk7e6q48W7VUZr417"
    clientId: "0oabk7991366IOzXB417"
    clientSecret: "your-okta-client-secret"
    redirectUri: "http://localhost:8001/api/auth/okta/callback"
    scopes: "openid profile email"
```

## Prochaines Étapes

1. ✅ Déterminez l'URL d'accès à votre application
2. ✅ Configurez l'URL de callback dans Okta Admin Console
3. ✅ Mettez à jour `OKTA_REDIRECT_URI` dans Helm
4. ✅ Redéployez l'application
5. ✅ Vérifiez que le bouton Okta apparaît dans le GUI
6. ✅ Testez la connexion Okta

---

**Besoin d'aide ?** Partagez :
- L'URL d'accès à votre application
- Les logs du pod backend après redéploiement
- La réponse de `/api/auth/config`
