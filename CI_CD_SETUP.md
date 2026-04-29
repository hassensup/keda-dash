# CI/CD Setup pour feature/okta-auth-rbac

## ✅ Modifications Effectuées

Le workflow GitHub Actions a été mis à jour pour supporter la branche `feature/okta-auth-rbac`.

### Changements dans `.github/workflows/docker-build-push.yml`

#### 1. Ajout du déclencheur pour la branche feature
```yaml
on:
  push:
    branches:
      - main
      - develop
      - feature/okta-auth-rbac  # Temporary: for testing auth feature
```

#### 2. Ajout d'un tag Docker spécifique
```yaml
tags: |
  type=ref,event=branch
  type=semver,pattern={{version}}
  type=semver,pattern={{major}}.{{minor}}
  type=sha,prefix={{branch}}-
  type=raw,value=latest,enable={{is_default_branch}}
  type=raw,value=dev,enable=${{ github.ref == 'refs/heads/develop' }}
  type=raw,value=okta-auth-rbac,enable=${{ github.ref == 'refs/heads/feature/okta-auth-rbac' }}
```

#### 3. Activation du push pour la branche feature
```yaml
push: ${{ github.event_name == 'push' && (github.ref == 'refs/heads/main' || github.ref == 'refs/heads/develop' || github.ref == 'refs/heads/feature/okta-auth-rbac') }}
```

## 🚀 Comment Tester

### 1. Pousser les changements vers GitHub
```bash
git push origin feature/okta-auth-rbac
```

### 2. Vérifier le workflow
1. Allez sur GitHub : `https://github.com/<votre-org>/<votre-repo>/actions`
2. Vous devriez voir un nouveau workflow "Build and Push Docker Image" en cours d'exécution
3. Le workflow va :
   - ✅ Construire l'image Docker backend
   - ✅ Pousser l'image vers GitHub Container Registry (ghcr.io)
   - ✅ Tagger l'image avec plusieurs tags

### 3. Tags Docker créés

Après le build, vous aurez plusieurs tags disponibles :

- `ghcr.io/<org>/<repo>-backend:feature-okta-auth-rbac` (nom de branche)
- `ghcr.io/<org>/<repo>-backend:okta-auth-rbac` (tag custom)
- `ghcr.io/<org>/<repo>-backend:feature-okta-auth-rbac-<sha>` (avec commit SHA)

## 📦 Utiliser l'Image Docker

### Option 1 : Utiliser le tag de branche
```bash
docker pull ghcr.io/<org>/<repo>-backend:feature-okta-auth-rbac
```

### Option 2 : Utiliser le tag custom
```bash
docker pull ghcr.io/<org>/<repo>-backend:okta-auth-rbac
```

### Option 3 : Utiliser avec Helm
Mettez à jour votre `values.yaml` :
```yaml
image:
  repository: ghcr.io/<org>/<repo>-backend
  tag: okta-auth-rbac
  pullPolicy: Always
```

Puis déployez :
```bash
helm upgrade --install keda-dashboard ./helm/keda-dashboard \
  --set image.tag=okta-auth-rbac \
  --set auth.jwt.secret="your-secret" \
  --namespace keda-dashboard \
  --create-namespace
```

## 🔐 Variables d'Environnement Requises

Pour tester l'authentification Okta, configurez ces variables :

### Obligatoires
```bash
JWT_SECRET=<votre-secret-jwt>
```

### Optionnelles (pour Okta)
```bash
OKTA_ENABLED=true
OKTA_DOMAIN=your-org.okta.com
OKTA_CLIENT_ID=0oa1234567890abcdef
OKTA_CLIENT_SECRET=<votre-secret-okta>
OKTA_REDIRECT_URI=https://your-domain.com/api/auth/okta/callback
```

### Optionnelles (pour auth locale)
```bash
LOCAL_AUTH_ENABLED=true
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=admin123
```

## 🧪 Tests de Validation

### 1. Vérifier que l'image démarre
```bash
docker run -p 8000:8000 \
  -e JWT_SECRET="test-secret" \
  -e LOCAL_AUTH_ENABLED=true \
  ghcr.io/<org>/<repo>-backend:okta-auth-rbac
```

### 2. Tester l'endpoint de santé
```bash
curl http://localhost:8000/api/health
# Expected: {"status":"ok"}
```

### 3. Tester la configuration auth
```bash
curl http://localhost:8000/api/auth/config
# Expected: {"okta_enabled":false,"local_auth_enabled":true}
```

### 4. Tester le login local
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"admin123"}'
# Expected: JWT token et profil utilisateur
```

## 🧹 Nettoyage Après Merge

**IMPORTANT** : Une fois la branche mergée dans `develop` ou `main`, supprimez ces lignes du workflow :

```yaml
# À SUPPRIMER après merge
- feature/okta-auth-rbac  # Temporary: for testing auth feature

# À SUPPRIMER après merge
type=raw,value=okta-auth-rbac,enable=${{ github.ref == 'refs/heads/feature/okta-auth-rbac' }}

# À SUPPRIMER après merge (dans la condition push)
|| github.ref == 'refs/heads/feature/okta-auth-rbac'
```

## 📊 Statut Actuel

- ✅ Workflow mis à jour
- ✅ Commit créé : `ci: Add feature/okta-auth-rbac branch to Docker workflow`
- ⏳ En attente de push vers GitHub
- ⏳ En attente de build CI/CD

## 🔗 Liens Utiles

- **GitHub Actions** : `https://github.com/<org>/<repo>/actions`
- **Packages** : `https://github.com/<org>/<repo>/pkgs/container/<repo>-backend`
- **Documentation Helm** : `helm/keda-dashboard/README.md`
- **Variables d'environnement** : `ENVIRONMENT_VARIABLES.md`
- **Guide de migration** : `helm/keda-dashboard/MIGRATION_GUIDE.md`

## 📝 Notes

- Le workflow se déclenche automatiquement à chaque push sur `feature/okta-auth-rbac`
- Les images sont poussées vers GitHub Container Registry (ghcr.io)
- Le cache Docker est utilisé pour accélérer les builds
- La plateforme cible est `linux/amd64`

---

**Créé le** : 2026-04-29  
**Branche** : feature/okta-auth-rbac  
**Statut** : ✅ Prêt pour test
