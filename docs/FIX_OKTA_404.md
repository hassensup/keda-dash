# Correction Erreur 404 Okta

## 🔴 Problème

Vous obtenez une erreur 404 d'Okta lors de la redirection pour l'authentification.

## 🔍 Diagnostic

L'erreur 404 signifie que l'URL d'autorisation Okta est incorrecte. Il y a deux types de serveurs d'autorisation Okta:

### 1. Org Authorization Server (par défaut)
- **Format domaine**: `groupecanalplus.okta.com`
- **URL générée**: `https://groupecanalplus.okta.com/oauth2/default/v1/authorize`
- **Issuer**: `https://groupecanalplus.okta.com/oauth2/default`

### 2. Custom Authorization Server
- **Format domaine**: `groupecanalplus.okta.com/oauth2/ausbk7e6q48W7VUZr417`
- **URL générée**: `https://groupecanalplus.okta.com/oauth2/ausbk7e6q48W7VUZr417/v1/authorize`
- **Issuer**: `https://groupecanalplus.okta.com/oauth2/ausbk7e6q48W7VUZr417`

## ✅ Solution

### Étape 1: Identifier Votre Type de Serveur

Dans la console Okta (https://groupecanalplus-admin.okta.com):

1. Aller dans **Security** → **API**
2. Vous verrez la liste des Authorization Servers:
   - **default** (Org Authorization Server)
   - **Serveurs personnalisés** (Custom Authorization Servers)

3. Cliquer sur votre Authorization Server
4. Copier l'**Issuer URI** (exemple: `https://groupecanalplus.okta.com/oauth2/ausbk7e6q48W7VUZr417`)

### Étape 2: Configurer le Domaine Correctement

#### Option A: Custom Authorization Server (Recommandé)

Si votre Issuer URI est `https://groupecanalplus.okta.com/oauth2/ausbk7e6q48W7VUZr417`:

```yaml
# values-okta.yaml
auth:
  okta:
    enabled: true
    # ✅ Inclure le chemin complet /oauth2/ausXXX
    domain: "groupecanalplus.okta.com/oauth2/ausbk7e6q48W7VUZr417"
    clientId: "0oabk7991366IOzXr417"
    clientSecret: "VOTRE_SECRET"
    redirectUri: "https://VOTRE_INGRESS/api/auth/okta/callback"
```

#### Option B: Org Authorization Server (Default)

Si votre Issuer URI est `https://groupecanalplus.okta.com/oauth2/default`:

```yaml
# values-okta.yaml
auth:
  okta:
    enabled: true
    # ✅ Juste le domaine, sans /oauth2/default
    domain: "groupecanalplus.okta.com"
    clientId: "0oabk7991366IOzXr417"
    clientSecret: "VOTRE_SECRET"
    redirectUri: "https://VOTRE_INGRESS/api/auth/okta/callback"
```

### Étape 3: Redéployer

```bash
# Mettre à jour avec Helm
helm upgrade keda-dashboard ./helm/keda-dashboard \
  -n test \
  -f values-okta.yaml

# Attendre que le pod redémarre
kubectl rollout status deployment/keda-dashboard-backend -n test
```

### Étape 4: Vérifier la Configuration

```bash
# Exécuter le script de diagnostic
./diagnose_okta_config.sh test

# Devrait afficher:
# ✅ OKTA_DOMAIN configuré: groupecanalplus.okta.com/oauth2/ausbk7e6q48W7VUZr417
# ✅ Endpoint de découverte accessible
```

### Étape 5: Tester

```bash
# Tester l'endpoint de découverte manuellement
# Pour Custom Authorization Server:
curl https://groupecanalplus.okta.com/oauth2/ausbk7e6q48W7VUZr417/.well-known/openid-configuration

# Pour Org Authorization Server:
curl https://groupecanalplus.okta.com/oauth2/default/.well-known/openid-configuration

# Devrait retourner un JSON avec les endpoints
```

## 🔧 Correction du Code (Déjà Appliquée)

J'ai modifié le code pour supporter automatiquement les deux types de serveurs:

### `backend/auth_config.py`

```python
def _get_base_url(self) -> str:
    """
    Get base URL for Okta endpoints.
    
    Handles both:
    - Org Authorization Server: domain.okta.com
    - Custom Authorization Server: domain.okta.com/oauth2/ausXXX
    """
    if not self.domain:
        raise ValueError("Okta domain not configured")
    
    # If domain already contains /oauth2/, it's a custom authorization server
    if "/oauth2/" in self.domain:
        # Domain format: groupecanalplus.okta.com/oauth2/ausbk7e6q48W7VUZr417
        return f"https://{self.domain}"
    else:
        # Domain format: groupecanalplus.okta.com (default org server)
        return f"https://{self.domain}/oauth2/default"
```

## 📋 Checklist de Vérification

- [ ] Identifier le type de serveur d'autorisation dans Okta
- [ ] Copier l'Issuer URI depuis la console Okta
- [ ] Configurer `auth.okta.domain` correctement dans values.yaml
- [ ] Redéployer avec Helm
- [ ] Exécuter `./diagnose_okta_config.sh test`
- [ ] Vérifier que l'endpoint de découverte est accessible
- [ ] Tester la connexion Okta dans le navigateur

## 🧪 Tests de Validation

### Test 1: Endpoint de Découverte

```bash
# Remplacer par votre configuration
OKTA_DOMAIN="groupecanalplus.okta.com/oauth2/ausbk7e6q48W7VUZr417"

# Tester
curl -s "https://$OKTA_DOMAIN/.well-known/openid-configuration" | jq .

# Devrait afficher:
# {
#   "issuer": "https://groupecanalplus.okta.com/oauth2/ausbk7e6q48W7VUZr417",
#   "authorization_endpoint": "https://groupecanalplus.okta.com/oauth2/ausbk7e6q48W7VUZr417/v1/authorize",
#   "token_endpoint": "https://groupecanalplus.okta.com/oauth2/ausbk7e6q48W7VUZr417/v1/token",
#   ...
# }
```

### Test 2: Configuration Backend

```bash
kubectl get configmap keda-dashboard-config -n test -o yaml | grep OKTA_DOMAIN

# Devrait afficher:
# OKTA_DOMAIN: "groupecanalplus.okta.com/oauth2/ausbk7e6q48W7VUZr417"
```

### Test 3: Logs Backend

```bash
kubectl logs -n test -l app=keda-dashboard-backend --tail=50 | grep -i okta

# Devrait afficher:
# "OktaAuthHandler initialized"
# "Okta authentication is enabled"
# "Redirecting to Okta login with state=..."
```

### Test 4: Redirection dans le Navigateur

1. Ouvrir: `https://VOTRE_INGRESS/`
2. Cliquer sur "Sign in with Okta"
3. Vérifier l'URL de redirection dans la barre d'adresse:
   - ✅ Devrait être: `https://groupecanalplus.okta.com/oauth2/ausbk7e6q48W7VUZr417/v1/authorize?...`
   - ❌ Si 404: L'URL est incorrecte

## 🔍 Exemples de Configuration

### Exemple 1: Custom Authorization Server

```yaml
# values-okta.yaml
auth:
  okta:
    enabled: true
    domain: "groupecanalplus.okta.com/oauth2/ausbk7e6q48W7VUZr417"
    clientId: "0oabk7991366IOzXr417"
    clientSecret: "xxx"
    redirectUri: "https://keda.example.com/api/auth/okta/callback"
```

**URLs générées**:
- Authorization: `https://groupecanalplus.okta.com/oauth2/ausbk7e6q48W7VUZr417/v1/authorize`
- Token: `https://groupecanalplus.okta.com/oauth2/ausbk7e6q48W7VUZr417/v1/token`
- Issuer: `https://groupecanalplus.okta.com/oauth2/ausbk7e6q48W7VUZr417`

### Exemple 2: Org Authorization Server (Default)

```yaml
# values-okta.yaml
auth:
  okta:
    enabled: true
    domain: "groupecanalplus.okta.com"
    clientId: "0oabk7991366IOzXr417"
    clientSecret: "xxx"
    redirectUri: "https://keda.example.com/api/auth/okta/callback"
```

**URLs générées**:
- Authorization: `https://groupecanalplus.okta.com/oauth2/default/v1/authorize`
- Token: `https://groupecanalplus.okta.com/oauth2/default/v1/token`
- Issuer: `https://groupecanalplus.okta.com/oauth2/default`

## 🚀 Déploiement de la Correction

```bash
# 1. Commit et push
git add -A
git commit -m "fix: Support Custom Authorization Server in Okta config"
git push origin feature/okta-auth-rbac

# 2. Attendre le build CI/CD (~10 minutes)

# 3. Vérifier le déploiement
kubectl get pods -n test -w

# 4. Tester
./diagnose_okta_config.sh test
```

## 📞 Support

Si l'erreur 404 persiste:

1. **Exécuter le diagnostic**:
   ```bash
   ./diagnose_okta_config.sh test > okta-diagnostic.txt
   ```

2. **Vérifier dans Okta**:
   - Security → API → Authorization Servers
   - Copier l'Issuer URI exact
   - Vérifier que le serveur est actif

3. **Vérifier la configuration de l'application Okta**:
   - Applications → Votre App → General
   - Vérifier que les Redirect URIs correspondent

4. **Logs détaillés**:
   ```bash
   kubectl logs -n test -l app=keda-dashboard-backend --tail=200 > backend-logs.txt
   ```

---

**Commit**: À venir (correction du support Custom Authorization Server)
**Fichiers modifiés**: `backend/auth_config.py`, `backend/auth/okta_auth.py`
**Impact**: Support automatique des deux types de serveurs d'autorisation Okta
