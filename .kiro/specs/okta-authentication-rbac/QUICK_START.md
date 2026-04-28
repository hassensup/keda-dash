# Guide de Démarrage Rapide - Session 2

## 🚀 Commande de Reprise Immédiate

Copiez-collez cette commande dans Kiro pour reprendre l'exécution automatique :

```
Continue l'implémentation automatique du spec okta-authentication-rbac. 
Commence par la tâche 4.1 (Create authentication router module) et exécute toutes les tâches restantes en mode fast-track.
Spec path: .kiro/specs/okta-authentication-rbac/
```

## 📊 État Actuel

- ✅ **8 tâches complétées** sur 95 (8.4%)
- 🔄 **87 tâches restantes**
- 📁 **20 fichiers créés**
- ✅ **Base de données** : Migrations et modèles prêts
- ✅ **Authentification** : LocalAuthHandler + OktaAuthHandler implémentés
- ⏭️ **Prochaine étape** : Backend Authentication Router

## 🎯 Objectifs Session 2

### Phase 1 : Backend Authentication Router (Tâches 4.1-4.7)
Créer les endpoints d'authentification :
- POST `/api/auth/login` - Login local
- GET `/api/auth/okta/login` - Initier OAuth2 Okta
- GET `/api/auth/okta/callback` - Callback OAuth2
- GET `/api/auth/config` - Configuration auth
- GET `/api/auth/me` - Profil utilisateur (mis à jour)

### Phase 2 : Backend RBAC Engine (Tâches 6.1-8.5)
Implémenter le contrôle d'accès :
- RBACEngine avec check_permission
- Permission middleware
- Mise à jour des endpoints ScaledObject

**Durée estimée** : 2-3 heures
**Livrable** : API d'authentification complète avec RBAC fonctionnel

## 📁 Fichiers Déjà Créés (À Utiliser)

### Backend
```
backend/
├── auth_config.py          ✅ Configuration Okta/Local
├── auth/
│   ├── local_auth.py       ✅ LocalAuthHandler
│   └── okta_auth.py        ✅ OktaAuthHandler
├── server.py               ✅ UserModel + PermissionModel
└── migrations/
    ├── 002_add_auth_fields.sql      ✅
    └── 003_create_permissions_table.sql ✅
```

### À Créer dans Session 2
```
backend/
├── auth/
│   └── auth_router.py      🔄 Nouveau - Router d'authentification
├── rbac/
│   ├── __init__.py         🔄 Nouveau
│   ├── engine.py           🔄 Nouveau - RBACEngine
│   └── middleware.py       🔄 Nouveau - Permission middleware
└── server.py               🔄 Mise à jour - Intégrer les routers
```

## 🔧 Contexte Technique Important

### Authentification
- **LocalAuthHandler** : `backend/auth/local_auth.py`
  - Méthode `authenticate(email, password)` retourne user + token
  - Méthode `create_access_token()` génère JWT avec permissions
  
- **OktaAuthHandler** : `backend/auth/okta_auth.py`
  - Méthode `get_authorization_url(state)` pour OAuth2
  - Méthode `exchange_code_for_tokens(code)` pour callback
  - Méthode `sync_user_profile(claims)` pour créer/màj user

### Configuration
- **AuthConfig** : `backend/auth_config.py`
  - `get_auth_config()` retourne config globale
  - `config.okta_enabled` et `config.local_auth_enabled`
  - `config.okta.get_authorization_endpoint()` etc.

### Base de Données
- **UserModel** : `backend/server.py`
  - Champs: id, email, password_hash, name, role, auth_provider, okta_subject
  - Relation: `user.permissions` (liste de PermissionModel)
  
- **PermissionModel** : `backend/server.py`
  - Champs: id, user_id, action, scope, namespace, object_name
  - Actions: "read" ou "write"
  - Scopes: "namespace" ou "object"

### Session Maker
```python
from backend.server import async_session_maker
# Utilisé par les handlers pour accéder à la DB
```

### JWT Secret
```python
import os
jwt_secret = os.environ["JWT_SECRET"]
# Utilisé pour signer les tokens
```

## 📝 Exemples de Code pour Session 2

### Exemple : Router d'Authentification
```python
# backend/auth/auth_router.py
from fastapi import APIRouter, HTTPException, Response, Depends
from backend.auth_config import get_auth_config
from backend.auth.local_auth import LocalAuthHandler
from backend.auth.okta_auth import OktaAuthHandler
from backend.server import async_session_maker
import os

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

# Initialize handlers
config = get_auth_config()
jwt_secret = os.environ["JWT_SECRET"]

local_handler = LocalAuthHandler(
    session_maker=async_session_maker,
    jwt_secret=jwt_secret,
    token_expiration_hours=config.token_expiration_hours
)

okta_handler = None
if config.okta_enabled:
    okta_handler = OktaAuthHandler(
        config=config.okta,
        session_maker=async_session_maker,
        jwt_secret=jwt_secret,
        token_expiration_hours=config.token_expiration_hours
    )

@router.post("/login")
async def login(req: LoginRequest, response: Response):
    # Utiliser local_handler.authenticate()
    pass

@router.get("/okta/login")
async def okta_login():
    # Utiliser okta_handler.get_authorization_url()
    pass

# ... autres endpoints
```

### Exemple : RBAC Engine
```python
# backend/rbac/engine.py
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy import select

class RBACEngine:
    def __init__(self, session_maker: async_sessionmaker):
        self.session_maker = session_maker
    
    async def check_permission(
        self, 
        user_id: str, 
        action: str,  # "read" or "write"
        namespace: str,
        object_name: str = None
    ) -> bool:
        # 1. Check if user is admin (bypass)
        # 2. Check object-scoped permission
        # 3. Check namespace-scoped permission
        # 4. Default deny
        pass
    
    async def filter_objects_by_permission(
        self,
        user_id: str,
        objects: list,
        action: str
    ) -> list:
        # Filter objects based on user permissions
        pass
```

## ⚠️ Points d'Attention

### 1. Intégration avec server.py
Le nouveau router doit être ajouté à l'application FastAPI :
```python
# Dans backend/server.py
from backend.auth.auth_router import router as auth_router
app.include_router(auth_router)
```

### 2. Gestion des États OAuth2
Pour Okta callback, stocker le state parameter :
- Option 1 : Session/cache (Redis)
- Option 2 : Cookie signé
- Option 3 : In-memory dict (dev only)

### 3. Admin Bypass
Dans RBACEngine, les users avec `role="admin"` doivent bypasser toutes les vérifications de permissions.

### 4. Backward Compatibility
Les endpoints existants doivent continuer à fonctionner. Ajouter les vérifications de permissions sans casser l'existant.

## 🧪 Tests de Validation

### Tester l'Authentification Locale
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"admin123"}'
```

### Tester la Configuration Auth
```bash
curl http://localhost:8000/api/auth/config
# Devrait retourner: {"okta_enabled": false, "local_auth_enabled": true}
```

### Tester le Profil Utilisateur
```bash
curl http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer <token>"
```

## 📚 Documentation de Référence

### Fichiers à Consulter
1. **Design Document** : `.kiro/specs/okta-authentication-rbac/design.md`
   - Section "Components and Interfaces" pour les signatures de méthodes
   - Section "Architecture" pour les diagrammes de flux
   
2. **Requirements** : `.kiro/specs/okta-authentication-rbac/requirements.md`
   - Exigences 1.1-1.7 pour l'authentification
   - Exigences 6.1-7.7 pour le RBAC
   
3. **Tasks** : `.kiro/specs/okta-authentication-rbac/tasks.md`
   - Détails de chaque tâche avec critères d'acceptation

### Summaries Existants
- `backend/TASK_3.1_SUMMARY.md` - auth_config
- `backend/TASK_3.2_SUMMARY.md` - LocalAuthHandler
- `backend/TASK_3.4_SUMMARY.md` - OktaAuthHandler

## 🎬 Commandes Alternatives

### Exécution Phase par Phase
Si vous préférez contrôler chaque phase :

#### Phase 1 Seulement (Auth Router)
```
Exécute les tâches 4.1 à 4.7 du spec okta-authentication-rbac.
Crée le router d'authentification avec tous les endpoints.
```

#### Phase 2 Seulement (RBAC Engine)
```
Exécute les tâches 6.1 à 8.5 du spec okta-authentication-rbac.
Crée le RBACEngine et met à jour les endpoints ScaledObject.
```

### Exécution Tâche par Tâche
Pour un contrôle maximum :
```
Exécute la tâche 4.1 du spec okta-authentication-rbac : Create authentication router module
```

## 🔍 Vérification Avant de Commencer

Avant de lancer la session 2, vérifiez que :

- [x] Les fichiers de session 1 existent
- [x] `backend/auth_config.py` est présent
- [x] `backend/auth/local_auth.py` est présent
- [x] `backend/auth/okta_auth.py` est présent
- [x] Les migrations sont dans `backend/migrations/`
- [x] `backend/server.py` a UserModel et PermissionModel mis à jour

Si un fichier manque, consultez `PROGRESS.md` pour voir ce qui a été créé.

## 💡 Conseils pour Session 2

1. **Commencer Simple** : Implémenter d'abord le login local, puis Okta
2. **Tester au Fur et à Mesure** : Tester chaque endpoint après création
3. **Logs Abondants** : Ajouter des logs pour faciliter le debugging
4. **Erreurs Claires** : Messages d'erreur explicites pour l'utilisateur
5. **Admin First** : Implémenter le bypass admin en premier dans RBAC

## 📞 Support

Si vous rencontrez des problèmes :

1. **Consulter PROGRESS.md** : État détaillé de la progression
2. **Consulter CONTINUATION_SCRIPT.md** : Instructions complètes
3. **Lire les Summaries** : TASK_X.X_SUMMARY.md pour comprendre l'existant
4. **Vérifier les Tests** : Les tests montrent comment utiliser le code

---

**Prêt à Commencer ?** 

Copiez la commande du début de ce document et lancez la session 2 ! 🚀

**Bonne chance !** 🎯
