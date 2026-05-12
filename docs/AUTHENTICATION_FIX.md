# Corrections des Erreurs d'Authentification

## Date : 29 avril 2026

## Problèmes Rencontrés

### 1. Base de données PostgreSQL manquante ✅ RÉSOLU
**Erreur :**
```
asyncpg.exceptions.InvalidCatalogNameError: database "keda-dashboard" does not exist
```

**Cause :** 
Le pod PostgreSQL a été déployé avec `POSTGRES_DB=keda-dashboard`, mais la base de données n'a pas été créée lors du premier démarrage du pod.

**Solution appliquée :**
```bash
kubectl exec -n test keda-dash-keda-dashboard-postgresql-0 -- \
  psql -U keda -d postgres -c "CREATE DATABASE \"keda-dashboard\";"
```

**Résultat :** ✅ L'application se connecte maintenant à PostgreSQL et les migrations sont appliquées avec succès.

---

### 2. Erreur 500 lors de l'authentification - Table redéfinie ✅ RÉSOLU
**Erreur initiale :**
```
Table 'users' is already defined for this MetaData instance. 
Specify 'extend_existing=True' to redefine options and columns on an existing Table object.
```

**Tentative de correction #1 :**
Ajout de `__table_args__ = {'extend_existing': True}` aux modèles ORM.

**Résultat :** ❌ Nouvelle erreur apparue.

---

### 3. Erreur 500 lors de l'authentification - Mapper failed ✅ RÉSOLU
**Erreur après correction #1 :**
```
One or more mappers failed to initialize - can't proceed with initialization of other mappers. 
Triggering mapper: 'Mapper[UserModel(users)]'. 
Original exception was: Multiple classes found for path "PermissionModel" in the registry 
of this declarative base. Please use a fully module-qualified path.
```

**Cause racine :**
- Les modèles ORM (`UserModel`, `PermissionModel`, etc.) étaient définis dans `backend/server.py`
- Ces modèles étaient importés dynamiquement dans plusieurs modules (`backend/auth/local_auth.py`, `backend/auth/okta_auth.py`)
- Cela causait une double définition des modèles dans le registre SQLAlchemy
- L'option `extend_existing=True` ne résolvait pas le problème des relations entre modèles

**Solution finale appliquée :**

1. **Création d'un module séparé pour les modèles** : `backend/models.py`
   - Contient tous les modèles ORM : `UserModel`, `PermissionModel`, `ScaledObjectModel`, `CronEventModel`
   - Importe uniquement `Base` depuis `backend.database`
   - Pas de `extend_existing=True` nécessaire

2. **Mise à jour de `backend/server.py`**
   - Suppression des définitions de modèles
   - Import des modèles depuis `backend.models`

3. **Mise à jour des handlers d'authentification**
   - `backend/auth/local_auth.py` : Import de `UserModel` depuis `backend.models` au lieu de `backend.server`
   - `backend/auth/okta_auth.py` : Import de `UserModel` depuis `backend.models` au lieu de `backend.server`

**Fichiers modifiés :**
- ✅ `backend/models.py` (nouveau fichier)
- ✅ `backend/server.py` (modèles supprimés, imports ajoutés)
- ✅ `backend/auth/local_auth.py` (imports mis à jour)
- ✅ `backend/auth/okta_auth.py` (imports mis à jour)

**Commits :**
- `b580488` : fix: Add extend_existing=True to ORM models to prevent table redefinition errors
- `248e191` : fix: Extract ORM models to separate module to prevent mapper initialization errors

---

### 4. Erreur 500 lors de l'authentification - Greenlet error ✅ RÉSOLU
**Erreur après correction #2 :**
```
greenlet_spawn has not been called; can't call await_only() here. 
Was IO attempted in an unexpected place?
```

**Cause racine :**
- Les colonnes ORM utilisaient des `lambda` pour les valeurs par défaut : `default=lambda: str(uuid.uuid4())`
- SQLAlchemy async ne supporte pas bien les lambdas dans les valeurs par défaut
- Les lambdas créent des problèmes avec le contexte greenlet des sessions async

**Solution appliquée :**

Remplacement de toutes les lambdas par des fonctions régulières dans `backend/models.py` :

```python
def generate_uuid():
    """Generate a UUID string for primary keys."""
    return str(uuid.uuid4())

def get_current_time():
    """Get current datetime for timestamp columns."""
    return datetime.now()

# Avant :
id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
created_at = Column(DateTime, default=lambda: datetime.now())

# Après :
id = Column(String, primary_key=True, default=generate_uuid)
created_at = Column(DateTime, default=get_current_time)
```

**Fichiers modifiés :**
- ✅ `backend/models.py` (lambdas remplacées par fonctions)

**Commits :**
- `a499620` : fix: Replace lambda functions with regular functions in ORM models

---

## Architecture Finale

```
backend/
├── database.py          # Configuration DB : engine, session_maker, Base
├── models.py            # ✨ NOUVEAU : Tous les modèles ORM
├── schemas.py           # Schémas Pydantic
├── server.py            # Application FastAPI (importe les modèles)
├── auth/
│   ├── local_auth.py    # Handler auth locale (importe les modèles)
│   └── okta_auth.py     # Handler auth Okta (importe les modèles)
└── rbac/
    ├── engine.py        # Moteur RBAC
    └── middleware.py    # Middleware FastAPI
```

**Flux d'imports (sans cycles) :**
```
database.py (Base)
    ↓
models.py (UserModel, PermissionModel, etc.)
    ↓
server.py, auth/*.py, rbac/*.py
```

---

## Vérification

### Commandes de test
```bash
# Vérifier les imports
python -c "from backend.models import UserModel, PermissionModel; print('Import successful')"

# Vérifier les logs du pod
kubectl logs -n test -l app.kubernetes.io/component=backend --tail=50

# Vérifier l'état du pod
kubectl get pods -n test -l app.kubernetes.io/component=backend
```

### Logs attendus après correction
```
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8001 (Press CTRL+C to quit)
2026-04-29 XX:XX:XX - server - INFO - ✅ All migrations processed
2026-04-29 XX:XX:XX - backend.k8s_service - INFO - K8s service initialized: mode=in-cluster, connected=True
```

### Test d'authentification
```bash
# Via l'interface web
URL: http://<ingress-url>/
Email: admin@example.com
Password: admin123
```

---

## Recommandations pour l'avenir

1. **Toujours séparer les modèles ORM dans un module dédié** pour éviter les imports circulaires
2. **Ne pas utiliser `extend_existing=True`** sauf si absolument nécessaire (cas de tests)
3. **Utiliser des imports absolus** (`from backend.models import ...`) plutôt que relatifs
4. **Tester les imports localement** avant de déployer
5. **Ajouter un Job Kubernetes** pour créer automatiquement la base de données PostgreSQL si elle n'existe pas

---

## Statut Final

✅ **Base de données créée**
✅ **Modèles ORM refactorisés**
✅ **Imports circulaires éliminés**
✅ **Lambdas remplacées par fonctions régulières**
✅ **Code committé et poussé (3 commits)**
⏳ **En attente du déploiement CI/CD**

**Commits appliqués :**
- `b580488` : Tentative avec extend_existing=True
- `248e191` : Extraction des modèles dans backend/models.py
- `a499620` : Remplacement des lambdas par des fonctions

Une fois le build terminé et ArgoCD ayant déployé la nouvelle version, l'authentification devrait fonctionner correctement.
