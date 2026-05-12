# Correction du Flux de Redirection Okta SSO

## 🎯 Problème Identifié

Lors de la tentative d'authentification via Okta, l'utilisateur était redirigé vers `/api/auth/okta/login` avec les paramètres Okta, mais **aucune redirection vers Okta ne se produisait**.

### Cause Racine

Le backend retournait un JSON avec l'URL d'autorisation au lieu de faire une redirection HTTP:

```python
# ❌ AVANT (incorrect)
@router.get("/okta/login")
async def okta_login():
    authorization_url = okta_auth_handler.get_authorization_url(state)
    return {"authorization_url": authorization_url}  # Retourne JSON
```

Le frontend faisait une redirection directe vers l'endpoint:
```javascript
// Frontend
const loginWithOkta = () => {
    window.location.href = `${api.defaults.baseURL}/auth/okta/login`;
};
```

Résultat: L'utilisateur voyait le JSON au lieu d'être redirigé vers Okta.

## ✅ Solution Implémentée

### 1. Backend: Redirection HTTP au lieu de JSON

**Fichier**: `backend/auth/auth_router.py`

```python
# ✅ APRÈS (correct)
@router.get("/okta/login")
async def okta_login():
    from fastapi.responses import RedirectResponse
    
    state = secrets.token_urlsafe(32)
    _oauth_states[state] = {"timestamp": datetime.now(timezone.utc), "used": False}
    
    authorization_url = okta_auth_handler.get_authorization_url(state)
    
    # Redirection HTTP 302 vers Okta
    return RedirectResponse(url=authorization_url, status_code=302)
```

### 2. Backend: Redirection vers Frontend après Callback

**Fichier**: `backend/auth/auth_router.py`

```python
# ✅ Après authentification réussie
@router.get("/okta/callback")
async def okta_callback(...):
    # ... validation et génération du token ...
    
    # Redirection vers le frontend avec le token dans l'URL
    from fastapi.responses import RedirectResponse
    frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")
    redirect_url = f"{frontend_url}/?token={jwt_token}"
    
    return RedirectResponse(url=redirect_url, status_code=302)
```

### 3. Frontend: Détection du Token dans l'URL

**Fichier**: `frontend/src/pages/LoginPage.js`

```javascript
// ✅ Nouveau useEffect pour gérer le callback Okta
useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const token = urlParams.get("token");
    
    if (token) {
        // Stocker le token
        localStorage.setItem("token", token);
        // Nettoyer l'URL
        window.history.replaceState({}, document.title, "/");
        // Rediriger vers la page d'accueil
        navigate("/");
    }
}, [navigate]);
```

### 4. Helm: Configuration de FRONTEND_URL

**Fichier**: `helm/keda-dashboard/templates/configmap.yaml`

```yaml
# ✅ Ajout de FRONTEND_URL dérivée de l'Ingress
data:
  {{- if .Values.ingress.enabled }}
  {{- $host := index .Values.ingress.hosts 0 }}
  {{- if .Values.ingress.tls }}
  FRONTEND_URL: {{ printf "https://%s" $host.host | quote }}
  {{- else }}
  FRONTEND_URL: {{ printf "http://%s" $host.host | quote }}
  {{- end }}
  {{- else }}
  FRONTEND_URL: "http://localhost:3000"
  {{- end }}
```

## 🔄 Flux d'Authentification Okta (Corrigé)

```
1. Utilisateur clique sur "Sign in with Okta"
   ↓
2. Frontend: window.location.href = "/api/auth/okta/login"
   ↓
3. Backend: Génère state + RedirectResponse(302) vers Okta
   ↓
4. Navigateur: Redirigé automatiquement vers Okta
   ↓
5. Utilisateur: S'authentifie sur Okta
   ↓
6. Okta: Redirige vers /api/auth/okta/callback?code=xxx&state=yyy
   ↓
7. Backend: Valide code + génère JWT + RedirectResponse(302) vers frontend
   ↓
8. Frontend: Détecte token dans URL + stocke dans localStorage
   ↓
9. Frontend: Redirige vers page d'accueil
   ↓
10. ✅ Utilisateur authentifié
```

## 📦 Déploiement

### Commit et Push
```bash
# Commit: 92cf9ea
git commit -m "fix: Okta SSO redirect flow and frontend callback handling"
git push origin feature/okta-auth-rbac
```

### CI/CD
- ✅ Code poussé vers GitHub
- ⏳ Build CI/CD en cours (~10 minutes)
- ⏳ Déploiement ArgoCD en attente (~5 minutes après build)

### Images Docker
```
Backend: ghcr.io/hassensup/keda-dash-backend:okta-auth-rbac
Frontend: ghcr.io/hassensup/keda-dash-frontend:okta-auth-rbac
```

## 🧪 Test du Flux Okta

### Prérequis
1. **Okta configuré** dans l'application Helm:
   ```yaml
   auth:
     okta:
       enabled: true
       domain: "groupecanalplus.okta.com"
       clientId: "0oabk7991366IOzXr417"
       clientSecret: "[secret]"
       redirectUri: "https://[votre-ingress]/api/auth/okta/callback"
   ```

2. **Ingress configuré** pour exposer l'application:
   ```yaml
   ingress:
     enabled: true
     className: "alb"  # ou nginx, traefik
     hosts:
       - host: keda-dashboard.example.com
         paths:
           - path: /
             pathType: Prefix
   ```

3. **Application Okta configurée** avec:
   - Sign-in redirect URIs: `https://[votre-ingress]/api/auth/okta/callback`
   - Sign-out redirect URIs: `https://[votre-ingress]/`
   - Trusted Origins: `https://[votre-ingress]`

### Étapes de Test

1. **Ouvrir l'application**:
   ```
   https://[votre-ingress]/
   ```

2. **Cliquer sur "Sign in with Okta"**:
   - ✅ Devrait rediriger vers Okta (groupecanalplus.okta.com)
   - ❌ Si reste sur `/api/auth/okta/login`: Vérifier que le nouveau code est déployé

3. **S'authentifier sur Okta**:
   - Entrer identifiants Okta
   - Cliquer sur "Sign In"

4. **Vérifier la redirection**:
   - ✅ Devrait revenir sur l'application (page d'accueil)
   - ✅ Utilisateur devrait être connecté
   - ✅ Token devrait être dans localStorage

5. **Vérifier l'authentification**:
   ```javascript
   // Dans la console du navigateur
   localStorage.getItem("token")  // Devrait afficher le JWT
   ```

## 🔍 Vérification du Déploiement

### 1. Vérifier l'Image Déployée
```bash
kubectl get deployment keda-dashboard-backend -n test -o jsonpath='{.spec.template.spec.containers[0].image}'
# Devrait contenir: 92cf9ea ou okta-auth-rbac
```

### 2. Vérifier les Variables d'Environnement
```bash
kubectl get configmap keda-dashboard-config -n test -o yaml | grep -E "OKTA|FRONTEND"
# Devrait afficher:
# OKTA_ENABLED: "true"
# OKTA_DOMAIN: "groupecanalplus.okta.com"
# OKTA_CLIENT_ID: "0oabk7991366IOzXr417"
# OKTA_REDIRECT_URI: "https://[ingress]/api/auth/okta/callback"
# FRONTEND_URL: "https://[ingress]"
```

### 3. Vérifier les Logs Backend
```bash
kubectl logs -n test -l app=keda-dashboard-backend --tail=50 | grep -i okta
# Devrait afficher:
# "OktaAuthHandler initialized"
# "Okta authentication is enabled"
```

### 4. Tester l'Endpoint de Configuration
```bash
curl https://[votre-ingress]/api/auth/config
# Devrait retourner:
# {"okta_enabled": true, "local_auth_enabled": true}
```

### 5. Tester la Redirection Okta
```bash
curl -I https://[votre-ingress]/api/auth/okta/login
# Devrait retourner:
# HTTP/1.1 302 Found
# Location: https://groupecanalplus.okta.com/oauth2/v1/authorize?...
```

## 🐛 Dépannage

### Problème: Reste sur `/api/auth/okta/login`
**Cause**: Ancien code encore déployé
**Solution**:
```bash
# Vérifier l'image
kubectl get deployment keda-dashboard-backend -n test -o jsonpath='{.spec.template.spec.containers[0].image}'

# Forcer le redéploiement
kubectl rollout restart deployment/keda-dashboard-backend -n test

# Ou forcer ArgoCD à synchroniser
kubectl patch application keda-dashboard -n argocd --type merge -p '{"operation":{"sync":{}}}'
```

### Problème: Erreur "Okta authentication not available"
**Cause**: OKTA_ENABLED=false ou configuration manquante
**Solution**:
```bash
# Vérifier la configuration
kubectl get configmap keda-dashboard-config -n test -o yaml

# Vérifier que OKTA_ENABLED="true"
# Vérifier que OKTA_DOMAIN, OKTA_CLIENT_ID, OKTA_REDIRECT_URI sont définis

# Si manquant, mettre à jour values.yaml et redéployer
helm upgrade keda-dashboard ./helm/keda-dashboard -n test -f values-okta.yaml
```

### Problème: Erreur "Invalid state parameter"
**Cause**: State expiré ou déjà utilisé
**Solution**:
- Réessayer la connexion (générera un nouveau state)
- Vérifier que les cookies ne sont pas bloqués
- Vérifier que le backend n'a pas redémarré entre login et callback

### Problème: Erreur "Token exchange failed"
**Cause**: Configuration Okta incorrecte
**Solution**:
```bash
# Vérifier les logs backend
kubectl logs -n test -l app=keda-dashboard-backend --tail=100 | grep -i "token exchange"

# Vérifier la configuration Okta:
# 1. Client ID correct
# 2. Client Secret correct
# 3. Redirect URI correspond exactement à celui configuré dans Okta
# 4. Application Okta activée
```

### Problème: Redirection vers frontend mais pas de token
**Cause**: FRONTEND_URL incorrecte ou token non généré
**Solution**:
```bash
# Vérifier FRONTEND_URL
kubectl get configmap keda-dashboard-config -n test -o yaml | grep FRONTEND_URL

# Vérifier les logs pour voir si le token est généré
kubectl logs -n test -l app=keda-dashboard-backend --tail=100 | grep -i "jwt token"
```

## 📊 Résumé des Changements

| Fichier | Type | Description |
|---------|------|-------------|
| `backend/auth/auth_router.py` | Modifié | Redirection HTTP au lieu de JSON |
| `frontend/src/pages/LoginPage.js` | Modifié | Détection du token dans l'URL |
| `helm/keda-dashboard/templates/configmap.yaml` | Modifié | Ajout de FRONTEND_URL |

## ✅ Checklist de Vérification

- [ ] Build GitHub Actions terminé avec succès
- [ ] Image Docker disponible (commit 92cf9ea)
- [ ] ArgoCD a synchronisé l'application
- [ ] Pods backend et frontend en cours d'exécution
- [ ] ConfigMap contient OKTA_ENABLED="true"
- [ ] ConfigMap contient FRONTEND_URL correcte
- [ ] Endpoint `/api/auth/config` retourne `okta_enabled: true`
- [ ] Endpoint `/api/auth/okta/login` retourne 302 redirect
- [ ] Clic sur "Sign in with Okta" redirige vers Okta
- [ ] Authentification Okta réussie
- [ ] Redirection vers frontend avec token
- [ ] Token stocké dans localStorage
- [ ] Utilisateur connecté et redirigé vers home

## 🚀 Prochaines Étapes

1. **Attendre le déploiement** (~15-20 minutes)
2. **Vérifier la configuration Okta** dans le ConfigMap
3. **Tester le flux complet** d'authentification Okta
4. **Vérifier les logs** pour toute erreur
5. **Confirmer** que l'utilisateur peut se connecter via Okta

## 📞 Support

Si le problème persiste:

1. Vérifier que le nouveau code est déployé (commit 92cf9ea)
2. Vérifier la configuration Okta dans le ConfigMap
3. Vérifier les logs backend pour les erreurs
4. Tester l'endpoint `/api/auth/okta/login` avec curl
5. Vérifier la configuration de l'application Okta

---

**Dernière mise à jour**: 30 avril 2026, 10:30 GMT
**Commit**: 92cf9ea
**Branche**: feature/okta-auth-rbac
**Statut**: ⏳ En attente de déploiement
