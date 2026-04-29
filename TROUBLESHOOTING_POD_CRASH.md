# Troubleshooting: Pod Crash - ModuleNotFoundError

## 🐛 Problème Résolu

**Erreur** : `ModuleNotFoundError: No module named 'backend'`

**Symptôme** : Le pod crashe au démarrage avec une erreur d'import Python.

## 🔍 Cause Racine

Le problème avait **trois causes** :

### 1. PYTHONPATH non configuré dans Docker
Le Dockerfile ne définissait pas `PYTHONPATH=/app`, donc Python ne pouvait pas résoudre les imports `backend.*` quand le script démarrait depuis `/app/backend`.

### 2. Import incorrect dans server.py
```python
# ❌ AVANT (incorrect)
from k8s_service import create_k8s_service, K8sScaledObjectService

# ✅ APRÈS (correct)
from backend.k8s_service import create_k8s_service, K8sScaledObjectService
```

### 3. Fichier __init__.py manquant
Le fichier `backend/__init__.py` n'existait pas, empêchant Python de reconnaître `backend` comme un package.

## ✅ Solutions Appliquées

### 1. Ajout de PYTHONPATH dans Dockerfile
```dockerfile
# Set PYTHONPATH to include /app so backend.* imports work
ENV PYTHONPATH=/app
```

### 2. Correction de l'import dans server.py
```python
from backend.k8s_service import create_k8s_service, K8sScaledObjectService
```

### 3. Création de backend/__init__.py
```python
"""
KEDA Dashboard Backend Package
"""
__version__ = "0.2.0"
```

## 🚀 Vérification

### 1. Rebuild l'image Docker
```bash
# Localement
docker build -t keda-dashboard-backend:test .

# Ou attendre le build CI/CD
git push origin feature/okta-auth-rbac
```

### 2. Tester l'image localement
```bash
docker run -p 8000:8001 \
  -e JWT_SECRET="test-secret" \
  -e LOCAL_AUTH_ENABLED=true \
  keda-dashboard-backend:test
```

### 3. Vérifier les logs
```bash
# Logs Docker
docker logs <container-id>

# Logs Kubernetes
kubectl logs -l app.kubernetes.io/component=backend -n keda-dashboard --tail=100
```

### 4. Tester les endpoints
```bash
# Health check
curl http://localhost:8001/api/health
# Expected: {"status":"ok"}

# Auth config
curl http://localhost:8001/api/auth/config
# Expected: {"okta_enabled":false,"local_auth_enabled":true}
```

## 📊 Structure des Imports

Tous les imports dans le projet doivent suivre cette structure :

```
/app/
├── backend/
│   ├── __init__.py          ← REQUIS
│   ├── server.py
│   ├── k8s_service.py
│   ├── auth_config.py
│   ├── auth/
│   │   ├── __init__.py      ← REQUIS
│   │   ├── auth_router.py
│   │   ├── local_auth.py
│   │   └── okta_auth.py
│   ├── rbac/
│   │   ├── __init__.py      ← REQUIS
│   │   ├── engine.py
│   │   └── middleware.py
│   ├── permissions/
│   │   ├── __init__.py      ← REQUIS
│   │   └── router.py
│   └── audit/
│       ├── __init__.py      ← REQUIS
│       └── logger.py
└── frontend/
    └── build/
```

### Règles d'Import

✅ **CORRECT** :
```python
from backend.auth.auth_router import router
from backend.rbac.engine import RBACEngine
from backend.k8s_service import create_k8s_service
```

❌ **INCORRECT** :
```python
from auth.auth_router import router        # Manque le préfixe backend
from k8s_service import create_k8s_service # Manque le préfixe backend
from .auth_router import router            # Import relatif (éviter)
```

## 🔧 Dockerfile Configuration

### Configuration Complète
```dockerfile
FROM python:3.11-slim AS backend-final
WORKDIR /app

# Install dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ ./backend/

# Copy frontend build
COPY --from=frontend-build /app/frontend/build ./frontend/build

# ⚠️ IMPORTANT: Set PYTHONPATH
ENV PYTHONPATH=/app

# Create startup script
RUN echo '#!/bin/bash\ncd /app/backend && uvicorn server:app --host 0.0.0.0 --port 8001' > /app/start.sh && chmod +x /app/start.sh

EXPOSE 8001
CMD ["/app/start.sh"]
```

### Points Clés

1. **WORKDIR** : `/app` (racine du projet)
2. **PYTHONPATH** : `/app` (permet les imports `backend.*`)
3. **Startup** : `cd /app/backend` puis `uvicorn server:app`
4. **Structure** : Code dans `/app/backend/`, frontend dans `/app/frontend/build/`

## 🧪 Tests de Validation

### Test 1 : Vérifier PYTHONPATH
```bash
docker run --rm keda-dashboard-backend:test python -c "import sys; print(sys.path)"
# Doit contenir: '/app'
```

### Test 2 : Vérifier les imports
```bash
docker run --rm keda-dashboard-backend:test python -c "from backend.rbac.engine import RBACEngine; print('OK')"
# Expected: OK
```

### Test 3 : Démarrage du serveur
```bash
docker run -d --name test-backend \
  -e JWT_SECRET="test" \
  -e LOCAL_AUTH_ENABLED=true \
  keda-dashboard-backend:test

# Attendre 5 secondes
sleep 5

# Vérifier les logs
docker logs test-backend

# Nettoyer
docker rm -f test-backend
```

## 📝 Checklist de Déploiement

Avant de déployer en production, vérifiez :

- [ ] `backend/__init__.py` existe
- [ ] Tous les sous-dossiers ont un `__init__.py`
- [ ] Tous les imports utilisent le préfixe `backend.*`
- [ ] `PYTHONPATH=/app` est défini dans le Dockerfile
- [ ] L'image Docker build sans erreur
- [ ] Le conteneur démarre sans crash
- [ ] Les endpoints `/api/health` et `/api/auth/config` répondent
- [ ] Les logs ne montrent pas d'erreurs d'import

## 🔗 Commits Associés

- `57db213` - fix: Resolve ModuleNotFoundError for backend imports in Docker

## 📚 Ressources

- **Python Packages** : https://docs.python.org/3/tutorial/modules.html#packages
- **Docker PYTHONPATH** : https://docs.docker.com/engine/reference/builder/#env
- **FastAPI Deployment** : https://fastapi.tiangolo.com/deployment/docker/

## ⚠️ Prévention Future

Pour éviter ce problème à l'avenir :

1. **Toujours créer `__init__.py`** dans les nouveaux packages Python
2. **Utiliser des imports absolus** avec le préfixe `backend.*`
3. **Tester localement** avec Docker avant de pousser
4. **Vérifier PYTHONPATH** dans les environnements conteneurisés

---

**Résolu le** : 2026-04-29  
**Branche** : feature/okta-auth-rbac  
**Statut** : ✅ Corrigé et testé
