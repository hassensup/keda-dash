# KEDA Dashboard

Dashboard de gestion et de visualisation des ScaledObjects KEDA avec authentification Okta et contrôle d'accès basé sur les rôles (RBAC).

## 📋 Table des matières

- [Vue d'ensemble](#vue-densemble)
- [Architecture](#architecture)
- [Fonctionnalités](#fonctionnalités)
- [Prérequis](#prérequis)
- [Installation](#installation)
- [Configuration](#configuration)
- [Utilisation](#utilisation)
- [Gestion des événements Cron](#gestion-des-événements-cron)
- [Permissions et RBAC](#permissions-et-rbac)
- [Développement](#développement)
- [Déploiement](#déploiement)

## 🎯 Vue d'ensemble

KEDA Dashboard est une application web permettant de gérer les ScaledObjects KEDA dans un cluster Kubernetes. Elle offre une interface intuitive pour créer, modifier et supprimer des configurations d'autoscaling, ainsi qu'un système de permissions granulaires pour contrôler l'accès aux ressources.

### Cas d'usage

- **Gestion centralisée** : Interface unique pour tous les ScaledObjects du cluster
- **Planification d'événements** : Création d'événements cron pour scaler automatiquement les applications
- **Contrôle d'accès** : Permissions au niveau namespace ou objet pour une sécurité fine
- **Authentification SSO** : Intégration Okta pour l'authentification d'entreprise
- **Audit** : Traçabilité complète des actions effectuées

## 🏗️ Architecture

### Stack technique

**Backend**
- Python 3.11 avec FastAPI
- SQLAlchemy (ORM) + asyncpg (PostgreSQL)
- Kubernetes Python Client
- JWT pour l'authentification
- Okta OAuth2/OIDC

**Frontend**
- React 18
- React Router pour la navigation
- Axios pour les appels API
- CSS moderne avec design responsive

**Infrastructure**
- PostgreSQL 16 pour la persistance
- Kubernetes (EKS) pour l'orchestration
- KEDA pour l'autoscaling
- ArgoCD pour le déploiement continu
- GitHub Actions pour CI/CD

### Architecture des composants

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (React)                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │Dashboard │  │ScaledObj │  │  Events  │  │  Admin   │   │
│  │   Page   │  │   Page   │  │   Page   │  │   Page   │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ HTTPS/REST API
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    Backend (FastAPI)                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Auth Router  │  │ API Router   │  │ Permissions  │     │
│  │ (Okta/Local) │  │ (CRUD)       │  │ Router       │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ RBAC Engine  │  │ K8s Service  │  │ Audit Logger │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                │                           │
                │                           │
                ▼                           ▼
        ┌──────────────┐          ┌──────────────────┐
        │  PostgreSQL  │          │  Kubernetes API  │
        │   Database   │          │   (KEDA CRDs)    │
        └──────────────┘          └──────────────────┘
```

### Modes de fonctionnement

Le backend peut fonctionner en deux modes :

1. **Mode In-Cluster** (Production)
   - Déployé dans Kubernetes
   - Accès direct à l'API Kubernetes
   - Gestion des vrais ScaledObjects KEDA

2. **Mode Mock** (Développement)
   - Exécution locale
   - Données simulées en base de données
   - Pas besoin d'accès Kubernetes

## ✨ Fonctionnalités

### Gestion des ScaledObjects

- ✅ Création, modification, suppression de ScaledObjects
- ✅ Support de multiples types de scalers (CPU, Memory, Prometheus, Cron, etc.)
- ✅ Configuration du comportement de scaling (scale-up/scale-down)
- ✅ Visualisation en temps réel des ScaledObjects

### Événements Cron

- ✅ Planification d'événements de scaling basés sur le temps
- ✅ Support des fuseaux horaires
- ✅ Gestion des plages horaires (start_time - end_time)
- ✅ Définition du nombre de replicas souhaité

### Authentification et Autorisation

- ✅ Authentification Okta (OAuth2/OIDC)
- ✅ Authentification locale (fallback)
- ✅ Tokens JWT avec expiration configurable
- ✅ Rôles : admin et user

### Permissions (RBAC)

- ✅ Permissions au niveau namespace (accès à tous les objets d'un namespace)
- ✅ Permissions au niveau objet (accès à un ScaledObject spécifique)
- ✅ Actions : read, write, delete
- ✅ Interface d'administration pour gérer les permissions

### Audit

- ✅ Logs structurés de toutes les actions
- ✅ Traçabilité des modifications (qui, quoi, quand)
- ✅ Logs d'authentification et d'autorisation

## 📦 Prérequis

### Pour le développement local

- Python 3.11+
- Node.js 18+
- PostgreSQL 16+
- Docker (optionnel)

### Pour le déploiement

- Cluster Kubernetes 1.24+
- KEDA 2.x installé
- Helm 3.x
- ArgoCD (optionnel, pour CD)
- Compte Okta (pour l'authentification SSO)

## 🚀 Installation

### Installation locale (développement)

#### 1. Cloner le repository

```bash
git clone https://github.com/hassensup/keda-dash.git
cd keda-dash
```

#### 2. Configuration de la base de données

```bash
# Créer une base de données PostgreSQL
createdb keda_dashboard

# Ou avec Docker
docker run -d \
  --name keda-postgres \
  -e POSTGRES_DB=keda_dashboard \
  -e POSTGRES_USER=keda \
  -e POSTGRES_PASSWORD=keda123 \
  -p 5432:5432 \
  postgres:16-alpine
```

#### 3. Configuration du backend

```bash
cd backend

# Créer un environnement virtuel
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# Installer les dépendances
pip install -r requirements.txt

# Créer le fichier .env
cat > .env << EOF
DATABASE_URL=postgresql+asyncpg://keda:keda123@localhost:5432/keda_dashboard
JWT_SECRET=your-secret-key-change-in-production
K8S_MODE=mock
AUTH_ENABLED=true
LOCAL_AUTH_ENABLED=true
OKTA_ENABLED=false
EOF

# Lancer le backend
python -m uvicorn server:app --reload --port 8001
```

#### 4. Configuration du frontend

```bash
cd frontend

# Installer les dépendances
npm install

# Lancer le frontend
npm start
```

L'application sera accessible sur http://localhost:3000

**Identifiants par défaut** :
- Email: `admin@example.com`
- Password: `admin123`

### Installation avec Docker

```bash
# Build des images
docker build -t keda-dashboard-backend:latest --target backend-final .
docker build -t keda-dashboard-frontend:latest --target frontend-final .

# Lancer avec docker-compose
docker-compose up -d
```

## ⚙️ Configuration

### Variables d'environnement

#### Backend

| Variable | Description | Défaut | Requis |
|----------|-------------|--------|--------|
| `DATABASE_URL` | URL de connexion PostgreSQL | - | ✅ |
| `JWT_SECRET` | Secret pour signer les JWT | - | ✅ |
| `JWT_EXPIRATION_HOURS` | Durée de validité des tokens | 24 | ❌ |
| `K8S_MODE` | Mode Kubernetes (`in-cluster` ou `mock`) | `mock` | ❌ |
| `AUTH_ENABLED` | Activer l'authentification | `true` | ❌ |
| `LOCAL_AUTH_ENABLED` | Activer l'auth locale | `true` | ❌ |
| `OKTA_ENABLED` | Activer l'auth Okta | `false` | ❌ |
| `OKTA_DOMAIN` | Domaine Okta | - | Si Okta activé |
| `OKTA_CLIENT_ID` | Client ID Okta | - | Si Okta activé |
| `OKTA_CLIENT_SECRET` | Client Secret Okta | - | Si Okta activé |
| `OKTA_REDIRECT_URI` | URI de callback Okta | - | Si Okta activé |
| `FRONTEND_URL` | URL du frontend | - | Si Okta activé |
| `CORS_ORIGINS` | Origines CORS autorisées | `*` | ❌ |

#### Frontend

Les variables sont configurées au build time dans le fichier `.env` :

```bash
REACT_APP_API_URL=http://localhost:8001
```

### Configuration Helm

Le déploiement Kubernetes utilise Helm. Fichier `values.yaml` :

```yaml
backend:
  image:
    repository: ghcr.io/hassensup/keda-dash-backend
    tag: "latest"
  
  env:
    K8S_MODE: "in-cluster"
    AUTH_ENABLED: "true"
    LOCAL_AUTH_ENABLED: "true"
    OKTA_ENABLED: "true"
  
  okta:
    domain: "your-domain.okta.com"
    clientId: "your-client-id"
    clientSecret: "your-client-secret"
  
  frontend:
    url: "https://keda-dashboard.example.com"

ingress:
  enabled: true
  className: "nginx"
  hosts:
    - host: keda-dashboard.example.com
      paths:
        - path: /
          pathType: Prefix

postgresql:
  enabled: true
  auth:
    username: keda
    password: keda123
    database: keda_dashboard
```

### Configuration Okta

1. **Créer une application Okta** :
   - Type : Web Application
   - Grant type : Authorization Code
   - Sign-in redirect URI : `https://your-domain.com/api/auth/okta/callback`

2. **Configurer les Trusted Origins** :
   - Origin URL : `https://your-domain.com`
   - Type : CORS + Redirect

3. **Assigner des utilisateurs** à l'application

4. **Récupérer les credentials** :
   - Domain
   - Client ID
   - Client Secret

## 📖 Utilisation

### Créer un ScaledObject

1. Naviguer vers **Dashboard** → **Create ScaledObject**
2. Remplir le formulaire :
   - **Name** : Nom unique du ScaledObject
   - **Namespace** : Namespace Kubernetes
   - **Target Deployment** : Nom du Deployment à scaler
   - **Scaler Type** : Type de scaler (CPU, Memory, Prometheus, etc.)
   - **Min/Max Replicas** : Limites de scaling
   - **Cooldown Period** : Période de refroidissement
   - **Polling Interval** : Intervalle de vérification
3. Configurer le **Scaling Behavior** (optionnel)
4. Cliquer sur **Create**

### Modifier un ScaledObject

1. Cliquer sur un ScaledObject dans la liste
2. Modifier les champs souhaités
3. Cliquer sur **Update**

### Supprimer un ScaledObject

1. Cliquer sur un ScaledObject
2. Cliquer sur **Delete**
3. Confirmer la suppression

## 📅 Gestion des événements Cron

Les événements Cron permettent de planifier des changements de scaling basés sur le temps.

### Créer un événement Cron

1. Naviguer vers **Events**
2. Cliquer sur **Add Event**
3. Remplir le formulaire :
   - **Name** : Nom descriptif de l'événement
   - **ScaledObject** : Sélectionner le ScaledObject cible
   - **Date** : Date de l'événement (format YYYY-MM-DD)
   - **Start Time** : Heure de début (format HH:MM)
   - **End Time** : Heure de fin (format HH:MM)
   - **Desired Replicas** : Nombre de replicas souhaité pendant l'événement
   - **Timezone** : Fuseau horaire (ex: Europe/Paris, UTC)
4. Cliquer sur **Create Event**

### Exemples d'événements

**Scale-up pour les heures de bureau** :
- Name : "Business Hours Scale Up"
- Date : 2026-05-03
- Start Time : 08:00
- End Time : 20:00
- Desired Replicas : 10
- Timezone : Europe/Paris

**Scale-down pour la maintenance nocturne** :
- Name : "Nightly Maintenance"
- Date : 2026-05-03
- Start Time : 02:00
- End Time : 06:00
- Desired Replicas : 2
- Timezone : Europe/Paris

### Modifier un événement

1. Cliquer sur l'événement dans la liste
2. Modifier les champs
3. Cliquer sur **Update Event**

### Supprimer un événement

1. Cliquer sur **Delete** à côté de l'événement
2. Confirmer la suppression

### Notes importantes

- Les événements sont appliqués automatiquement par KEDA
- Un événement peut couvrir plusieurs jours si nécessaire
- Les fuseaux horaires sont respectés pour l'exécution
- Les événements passés restent visibles pour l'audit

## 🔐 Permissions et RBAC

### Rôles

- **admin** : Accès complet, peut gérer les permissions
- **user** : Accès selon les permissions assignées

### Types de permissions

#### Permission Namespace

Donne accès à tous les ScaledObjects d'un namespace :

```
User: john@example.com
Action: write
Scope: namespace
Namespace: production
```

→ John peut lire et écrire tous les ScaledObjects du namespace `production`

#### Permission Object

Donne accès à un ScaledObject spécifique :

```
User: jane@example.com
Action: read
Scope: object
Namespace: production
Object: my-app-scaler
```

→ Jane peut seulement lire le ScaledObject `my-app-scaler` dans `production`

### Actions disponibles

- **read** : Visualiser les ScaledObjects et événements
- **write** : Créer et modifier (inclut read)
- **delete** : Supprimer (inclut write et read)

### Gérer les permissions (Admin uniquement)

1. Naviguer vers **Admin** → **Permissions**
2. Cliquer sur **Add Permission**
3. Sélectionner :
   - **User** : Utilisateur cible
   - **Namespace** : Namespace concerné
   - **Scope** : namespace ou object
   - **Object Name** : Si scope = object
   - **Action** : read, write, ou delete
4. Cliquer sur **Create**

### Vérifier les permissions d'un utilisateur

1. Aller dans **Admin** → **Permissions**
2. Sélectionner un utilisateur dans la liste
3. Voir toutes ses permissions

## 🛠️ Développement

### Structure du projet

```
keda-dash/
├── backend/
│   ├── auth/              # Authentification (Okta, local)
│   ├── permissions/       # Gestion des permissions
│   ├── rbac/             # Moteur RBAC
│   ├── migrations/       # Migrations SQL
│   ├── models.py         # Modèles SQLAlchemy
│   ├── server.py         # Point d'entrée FastAPI
│   ├── k8s_service.py    # Service Kubernetes
│   └── audit.py          # Logs d'audit
├── frontend/
│   ├── src/
│   │   ├── components/   # Composants React
│   │   ├── contexts/     # Contexts (Auth, etc.)
│   │   ├── pages/        # Pages de l'application
│   │   └── App.js        # Composant principal
│   └── public/
├── helm/
│   └── keda-dashboard/   # Chart Helm
├── .github/
│   └── workflows/        # CI/CD GitHub Actions
├── Dockerfile            # Multi-stage build
└── README.md
```

### Lancer les tests

```bash
# Backend
cd backend
pytest

# Frontend
cd frontend
npm test
```

### Ajouter une migration SQL

1. Créer un fichier dans `backend/migrations/` :
   ```
   004_add_new_feature.sql
   ```

2. Écrire le SQL :
   ```sql
   -- Add new column
   ALTER TABLE scaled_objects ADD COLUMN new_field VARCHAR(255);
   ```

3. La migration sera appliquée automatiquement au démarrage

### Contribuer

1. Fork le repository
2. Créer une branche feature (`git checkout -b feature/amazing-feature`)
3. Commit les changements (`git commit -m 'Add amazing feature'`)
4. Push vers la branche (`git push origin feature/amazing-feature`)
5. Ouvrir une Pull Request

## 🚢 Déploiement

### Déploiement avec Helm

```bash
# Ajouter le repository Helm (si configuré)
helm repo add keda-dashboard https://charts.example.com
helm repo update

# Installer
helm install keda-dash keda-dashboard/keda-dashboard \
  --namespace test \
  --create-namespace \
  --values values-production.yaml

# Mettre à jour
helm upgrade keda-dash keda-dashboard/keda-dashboard \
  --namespace test \
  --values values-production.yaml
```

### Déploiement avec ArgoCD

1. Créer une Application ArgoCD :

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: keda-dashboard
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/hassensup/keda-dash.git
    targetRevision: main
    path: helm/keda-dashboard
    helm:
      valueFiles:
        - values.yaml
  destination:
    server: https://kubernetes.default.svc
    namespace: test
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

2. Appliquer :
```bash
kubectl apply -f argocd-application.yaml
```

### CI/CD avec GitHub Actions

Le workflow `.github/workflows/docker-build-push.yml` :

1. Build les images Docker
2. Push vers GitHub Container Registry
3. Tag avec le nom de branche et le commit SHA
4. ArgoCD détecte les changements et déploie automatiquement

### Vérifier le déploiement

```bash
# Vérifier les pods
kubectl get pods -n test

# Vérifier les logs
kubectl logs -n test -l app.kubernetes.io/name=keda-dashboard --tail=100

# Vérifier l'ingress
kubectl get ingress -n test

# Tester l'API
curl https://keda-dashboard.example.com/api/health
```

## 📝 Logs et Monitoring

### Logs d'audit

Les logs d'audit sont écrits dans stdout au format JSON :

```json
{
  "timestamp": "2026-05-02T10:30:00Z",
  "event_type": "scaled_object",
  "event_action": "created",
  "user_email": "admin@example.com",
  "details": {
    "object_name": "my-app-scaler",
    "namespace": "production"
  }
}
```

### Événements audités

- Authentification (login, logout, échecs)
- Création/modification/suppression de ScaledObjects
- Création/modification/suppression d'événements Cron
- Gestion des permissions
- Erreurs d'autorisation

### Collecter les logs

```bash
# Logs en temps réel
kubectl logs -n test -l app.kubernetes.io/name=keda-dashboard -f

# Filtrer les logs d'audit
kubectl logs -n test -l app.kubernetes.io/name=keda-dashboard | grep '"event_type"'

# Exporter vers un fichier
kubectl logs -n test -l app.kubernetes.io/name=keda-dashboard > logs.txt
```

## 🔧 Troubleshooting

### Le backend ne démarre pas

```bash
# Vérifier les logs
kubectl logs -n test -l app.kubernetes.io/name=keda-dashboard

# Vérifier la connexion à la base de données
kubectl exec -n test -it <pod-name> -- psql $DATABASE_URL -c "SELECT 1"

# Vérifier les variables d'environnement
kubectl exec -n test <pod-name> -- env | grep -E "DATABASE|OKTA|K8S"
```

### Erreur "Namespace not found"

Le backend ne peut pas lister les namespaces Kubernetes. Vérifier les RBAC :

```bash
# Vérifier le ClusterRole
kubectl get clusterrole keda-dash-keda-dashboard -o yaml

# Vérifier le ClusterRoleBinding
kubectl get clusterrolebinding keda-dash-keda-dashboard -o yaml

# Le ClusterRole doit avoir :
# - apiGroups: [""]
#   resources: ["namespaces"]
#   verbs: ["get", "list"]
```

### Erreur d'authentification Okta

1. Vérifier la configuration Okta :
   ```bash
   kubectl get configmap -n test keda-dash-keda-dashboard-config -o yaml
   ```

2. Vérifier les logs d'authentification :
   ```bash
   kubectl logs -n test -l app.kubernetes.io/name=keda-dashboard | grep -i okta
   ```

3. Vérifier la configuration Okta :
   - Redirect URI correcte
   - Client ID/Secret valides
   - Utilisateur assigné à l'application

### Les permissions ne fonctionnent pas

1. Vérifier que l'utilisateur a bien des permissions :
   ```bash
   # Via l'API
   curl -H "Authorization: Bearer $TOKEN" \
     https://keda-dashboard.example.com/api/permissions/users/<user-id>
   ```

2. Vérifier les logs RBAC :
   ```bash
   kubectl logs -n test -l app.kubernetes.io/name=keda-dashboard | grep -i rbac
   ```

## 📄 Licence

Ce projet est sous licence MIT. Voir le fichier `LICENSE` pour plus de détails.

## 👥 Auteurs

- Hassen Hadjamor - [@hassensup](https://github.com/hassensup)

## 🙏 Remerciements

- [KEDA](https://keda.sh/) pour l'autoscaling Kubernetes
- [FastAPI](https://fastapi.tiangolo.com/) pour le framework backend
- [React](https://react.dev/) pour le framework frontend
- La communauté open source

---

Pour toute question ou problème, ouvrir une issue sur [GitHub](https://github.com/hassensup/keda-dash/issues).
