# Guide d'utilisation de Swagger UI

## 🌐 Accès à l'interface Swagger

### URLs disponibles :

- **Swagger UI** (interface interactive) : `http://localhost:8001/docs`
- **ReDoc** (documentation alternative) : `http://localhost:8001/redoc`
- **OpenAPI JSON** (spécification brute) : `http://localhost:8001/openapi.json`

En production, remplacez `localhost:8001` par l'URL de votre backend.

## 🔐 Authentification

### Méthode 1 : Via l'interface Swagger

1. Ouvrez `http://localhost:8001/docs`
2. Trouvez l'endpoint `POST /api/auth/login` dans la section **Authentication**
3. Cliquez sur "Try it out"
4. Entrez les credentials :
   ```json
   {
     "email": "admin@example.com",
     "password": "admin123"
   }
   ```
5. Cliquez sur "Execute"
6. Copiez le `token` de la réponse
7. Cliquez sur le bouton **"Authorize"** 🔒 en haut à droite
8. Entrez le token dans le champ "Value" (format: `Bearer <token>`)
9. Cliquez sur "Authorize"
10. Fermez la fenêtre

Tous les endpoints sont maintenant authentifiés !

### Méthode 2 : Via curl

```bash
# 1. Obtenir le token
TOKEN=$(curl -s -X POST http://localhost:8001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "admin123"}' | jq -r '.token')

# 2. Utiliser le token
curl http://localhost:8001/api/scaled-objects \
  -H "Authorization: Bearer $TOKEN"
```

## 📚 Organisation des endpoints

Les endpoints sont organisés par catégories :

### 🔐 Authentication
- `POST /api/auth/login` - Se connecter et obtenir un token
- `GET /api/auth/me` - Obtenir les informations de l'utilisateur connecté
- `POST /api/auth/logout` - Se déconnecter

### 📦 ScaledObjects
- `GET /api/scaled-objects` - Lister tous les ScaledObjects
- `POST /api/scaled-objects` - Créer un nouveau ScaledObject
- `GET /api/scaled-objects/{obj_id}` - Obtenir un ScaledObject spécifique
- `PUT /api/scaled-objects/{obj_id}` - Mettre à jour un ScaledObject
- `DELETE /api/scaled-objects/{obj_id}` - Supprimer un ScaledObject

### 📅 Cron Events
- `GET /api/cron-events` - Lister tous les événements cron
- `POST /api/cron-events` - Créer un nouvel événement cron
- `PUT /api/cron-events/{event_id}` - Mettre à jour un événement cron
- `DELETE /api/cron-events/{event_id}` - Supprimer un événement cron

### ☸️ Kubernetes
- `GET /api/namespaces` - Lister les namespaces disponibles
- `GET /api/scaler-types` - Lister les types de scalers disponibles
- `GET /api/deployments` - Lister les deployments disponibles
- `GET /api/k8s-status` - Obtenir le statut de la connexion Kubernetes

### 🏥 Health
- `GET /api/health` - Vérifier l'état de santé de l'API

## 🧪 Exemples d'utilisation

### Créer un ScaledObject avec scaling behavior

1. Authentifiez-vous (voir section Authentification)
2. Allez sur `POST /api/scaled-objects`
3. Cliquez sur "Try it out"
4. Entrez le JSON suivant :

```json
{
  "name": "my-scaler",
  "namespace": "default",
  "scaler_type": "cron",
  "target_deployment": "my-app",
  "min_replicas": 1,
  "max_replicas": 10,
  "cooldown_period": 300,
  "polling_interval": 30,
  "triggers": [
    {
      "type": "cron",
      "metadata": {
        "timezone": "UTC",
        "start": "0 8 * * *",
        "end": "0 20 * * *",
        "desiredReplicas": "5"
      }
    }
  ],
  "scaling_behavior": {
    "scale_up": {
      "stabilization_window_seconds": 300,
      "select_policy": "Max",
      "policies": [
        {
          "type": "Percent",
          "value": 100,
          "period_seconds": 15
        }
      ]
    },
    "scale_down": {
      "stabilization_window_seconds": 600,
      "select_policy": "Min",
      "policies": [
        {
          "type": "Pods",
          "value": 1,
          "period_seconds": 30
        }
      ]
    }
  }
}
```

5. Cliquez sur "Execute"
6. Vérifiez la réponse (code 200 = succès)

### Lister les ScaledObjects d'un namespace

1. Allez sur `GET /api/scaled-objects`
2. Cliquez sur "Try it out"
3. Entrez le namespace dans le champ `namespace` (ex: "default")
4. Cliquez sur "Execute"

### Mettre à jour un ScaledObject

1. Allez sur `PUT /api/scaled-objects/{obj_id}`
2. Cliquez sur "Try it out"
3. Entrez l'ID du ScaledObject (ex: "default/my-scaler" ou UUID)
4. Entrez les champs à mettre à jour :

```json
{
  "max_replicas": 20,
  "scaling_behavior": {
    "scale_up": {
      "stabilization_window_seconds": 180,
      "select_policy": "Max",
      "policies": [
        {
          "type": "Percent",
          "value": 50,
          "period_seconds": 15
        }
      ]
    }
  }
}
```

5. Cliquez sur "Execute"

## 💡 Astuces

### Filtrer les endpoints
Utilisez la barre de recherche en haut pour filtrer les endpoints par nom.

### Télécharger la spécification OpenAPI
Cliquez sur le lien `/openapi.json` en haut de la page pour télécharger la spécification complète.

### Générer un client
Utilisez la spécification OpenAPI pour générer automatiquement un client dans votre langage préféré :
- Python : `openapi-generator-cli generate -i http://localhost:8001/openapi.json -g python`
- TypeScript : `openapi-generator-cli generate -i http://localhost:8001/openapi.json -g typescript-axios`
- Java : `openapi-generator-cli generate -i http://localhost:8001/openapi.json -g java`

### Tester en local
Pour tester l'API en local :

```bash
cd backend
uvicorn server:app --reload --host 0.0.0.0 --port 8001
```

Puis ouvrez `http://localhost:8001/docs`

## 🔍 Schémas de données

Swagger affiche automatiquement tous les schémas de données (Pydantic models) en bas de la page dans la section "Schemas". Vous pouvez les consulter pour voir la structure exacte des données attendues.

## 📝 Notes

- Tous les endpoints (sauf `/api/health`) nécessitent une authentification
- Les tokens JWT expirent après 24 heures
- Le mode K8s (mock ou in-cluster) affecte le comportement des endpoints
- En mode mock, les données sont stockées dans SQLite
- En mode in-cluster, les données sont synchronisées avec Kubernetes
