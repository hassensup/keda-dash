# Debug Guide: Scaling Behavior Not Persisting

## Symptômes
- Le scaling behavior est configuré dans l'interface
- Après sauvegarde et rechargement, le scaling behavior n'apparaît pas
- Le scaling behavior n'est pas visible dans le cluster Kubernetes

## Étapes de débogage

### 1. Vérifier les logs du navigateur (Frontend)

Ouvrir la console du navigateur (F12) et chercher :

```
Saving ScaledObject with data: ...
```

**Vérifier :**
- Le champ `scaling_behavior` est-il présent dans les données ?
- Les valeurs `scale_up` et `scale_down` sont-elles correctes ?
- Y a-t-il des erreurs dans la console ?

**Exemple de données attendues :**
```json
{
  "name": "test-scaler",
  "namespace": "default",
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
    "scale_down": null
  }
}
```

### 2. Vérifier les logs du backend

Consulter les logs du pod backend :

```bash
kubectl logs -f <backend-pod-name> -n <namespace>
```

**Chercher :**
```
Creating ScaledObject with data: ...
ou
Updating ScaledObject <id> with data: ...
```

**Vérifier :**
- Le champ `scaling_behavior` est-il reçu par le backend ?
- Y a-t-il des erreurs lors de la sauvegarde ?

### 3. Vérifier la base de données

#### Pour PostgreSQL :
```bash
kubectl exec -it <postgresql-pod> -n <namespace> -- psql -U <user> -d <database>
```

```sql
-- Vérifier que la colonne existe
\d scaled_objects

-- Vérifier les données
SELECT id, name, scaling_behavior_json FROM scaled_objects WHERE name = 'test-scaler';
```

#### Pour SQLite (local) :
```bash
sqlite3 backend/keda_dashboard.db
```

```sql
-- Vérifier que la colonne existe
.schema scaled_objects

-- Vérifier les données
SELECT id, name, scaling_behavior_json FROM scaled_objects WHERE name = 'test-scaler';
```

**Attendu :**
- La colonne `scaling_behavior_json` doit exister
- La valeur doit être un JSON valide ou NULL

### 4. Vérifier le ScaledObject Kubernetes

```bash
kubectl get scaledobject <name> -n <namespace> -o yaml
```

**Chercher la section `spec.behavior` :**
```yaml
spec:
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 300
      selectPolicy: Max
      policies:
        - type: Percent
          value: 100
          periodSeconds: 15
```

### 5. Vérifier le mode K8s

Vérifier la variable d'environnement `K8S_MODE` :

```bash
kubectl get deployment <backend-deployment> -n <namespace> -o yaml | grep K8S_MODE
```

**Valeurs possibles :**
- `mock` : Utilise la base de données SQLite/PostgreSQL (pas de cluster K8s)
- `in-cluster` : Utilise l'API Kubernetes réelle

### 6. Tests manuels

#### Test 1 : Créer un ScaledObject avec scaling behavior via API

```bash
curl -X POST http://localhost:8001/api/scaled-objects \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "name": "test-scaling-behavior",
    "namespace": "default",
    "scaler_type": "cron",
    "target_deployment": "test-app",
    "min_replicas": 1,
    "max_replicas": 10,
    "triggers": [],
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
      }
    }
  }'
```

#### Test 2 : Récupérer le ScaledObject

```bash
curl http://localhost:8001/api/scaled-objects/<id> \
  -H "Authorization: Bearer <token>"
```

**Vérifier que `scaling_behavior` est présent dans la réponse.**

## Solutions possibles

### Problème 1 : Colonne manquante dans la base de données

**Solution :**
```sql
-- PostgreSQL
ALTER TABLE scaled_objects ADD COLUMN scaling_behavior_json TEXT;

-- SQLite
ALTER TABLE scaled_objects ADD COLUMN scaling_behavior_json TEXT;
```

Ou redémarrer le pod pour que la migration automatique s'exécute.

### Problème 2 : Mode mock vs in-cluster

Si vous êtes en mode `mock`, les données sont dans la base de données mais pas dans Kubernetes.
Si vous êtes en mode `in-cluster`, vérifiez que le RealK8sService fonctionne correctement.

### Problème 3 : Données non envoyées depuis le frontend

Vérifier que le bouton "Add" pour scale-up/scale-down a bien été cliqué avant de sauvegarder.

### Problème 4 : Conversion de format incorrecte

Vérifier les logs pour voir si la conversion API ↔ CRD fonctionne correctement.

## Checklist de vérification

- [ ] La colonne `scaling_behavior_json` existe dans la base de données
- [ ] Les logs frontend montrent que `scaling_behavior` est envoyé
- [ ] Les logs backend montrent que `scaling_behavior` est reçu
- [ ] La base de données contient les données JSON
- [ ] Le mode K8s est correct (mock ou in-cluster)
- [ ] Le ScaledObject Kubernetes contient `spec.behavior` (si mode in-cluster)
- [ ] Pas d'erreurs dans les logs

## Contact

Si le problème persiste après ces vérifications, fournir :
1. Les logs du navigateur (console)
2. Les logs du backend
3. Le résultat de la requête SQL
4. Le YAML du ScaledObject Kubernetes (si applicable)
