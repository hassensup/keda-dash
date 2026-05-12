# Problème de Synchronisation ScaledObject

## Symptôme

Erreur lors de l'ajout d'un événement dans le calendrier :
```
scaledobjects.keda.sh "test" not found
```

## Cause Racine

L'application fonctionne en mode `K8S_MODE=in-cluster` mais affiche des données de seed (exemples) qui existent uniquement dans la base de données PostgreSQL, pas dans Kubernetes.

Quand vous essayez de modifier un ScaledObject :
1. ✅ L'application le trouve dans la base de données
2. ❌ Elle essaie de le mettre à jour dans Kubernetes où il n'existe pas
3. ❌ Erreur 404 "not found"

## Vérification

```bash
# 1. Vérifier le mode K8S
kubectl exec -n test <pod-name> -- env | grep K8S_MODE
# Résultat: K8S_MODE=in-cluster

# 2. Vérifier les ScaledObjects dans Kubernetes
kubectl get scaledobjects -n test
# Résultat: No resources found

# 3. Vérifier les ScaledObjects dans la base de données
kubectl exec -n test <pod-name> -- curl -s http://localhost:8001/api/scaled-objects
# Résultat: Liste des exemples (web-app-scaler, api-gateway-scaler, etc.)
```

## Solutions

### Solution 1 : Désactiver le Seed Data en Mode In-Cluster (Recommandé)

Modifiez `backend/server.py` pour ne pas créer de seed data en mode in-cluster :

```python
async def seed_data():
    # Skip seed data in in-cluster mode
    k8s_mode = os.environ.get("K8S_MODE", "mock")
    if k8s_mode == "in-cluster":
        logger.info("Skipping seed data in in-cluster mode")
        # Only seed admin user
        async with async_session_maker() as session:
            admin_email = os.environ.get("ADMIN_EMAIL", "admin@example.com")
            admin_password = os.environ.get("ADMIN_PASSWORD", "admin123")
            result = await session.execute(select(UserModel).where(UserModel.email == admin_email))
            existing = result.scalar_one_or_none()
            if not existing:
                session.add(UserModel(
                    email=admin_email,
                    password_hash=hash_password(admin_password),
                    name="Admin",
                    role="admin"
                ))
            await session.commit()
        return
    
    # Continue with full seed data in mock mode
    async with async_session_maker() as session:
        # ... rest of seed data
```

### Solution 2 : Créer de Vrais ScaledObjects dans Kubernetes

Créez des ScaledObjects réels dans le namespace `test` :

```yaml
# example-scaledobject.yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: test
  namespace: test
spec:
  scaleTargetRef:
    name: keda-dash-keda-dashboard-backend
  minReplicaCount: 1
  maxReplicaCount: 5
  triggers:
    - type: cron
      metadata:
        timezone: UTC
        start: 0 8 * * 1-5
        end: 0 20 * * 1-5
        desiredReplicas: "2"
    - type: cpu
      metricType: Utilization
      metadata:
        value: "60"
```

Appliquez :
```bash
kubectl apply -f example-scaledobject.yaml
```

### Solution 3 : Utiliser le Mode Mock pour le Développement

Si vous voulez juste tester l'application sans gérer de vrais ScaledObjects :

```bash
helm upgrade keda-dash ./helm/keda-dashboard \
  --namespace test \
  --set backend.config.k8sMode=mock
```

## Solution Recommandée (Automatique)

Modifions le code pour gérer ce cas automatiquement.

### Étape 1 : Modifier seed_data()

```python
# backend/server.py

async def seed_data():
    """Seed initial data - admin user always, example ScaledObjects only in mock mode."""
    async with async_session_maker() as session:
        # Always seed admin user
        admin_email = os.environ.get("ADMIN_EMAIL", "admin@example.com")
        admin_password = os.environ.get("ADMIN_PASSWORD", "admin123")
        result = await session.execute(select(UserModel).where(UserModel.email == admin_email))
        existing = result.scalar_one_or_none()
        if not existing:
            session.add(UserModel(
                email=admin_email,
                password_hash=hash_password(admin_password),
                name="Admin",
                role="admin"
            ))
        elif not verify_password(admin_password, existing.password_hash):
            existing.password_hash = hash_password(admin_password)
        
        await session.commit()
        
        # Only seed example ScaledObjects in mock mode
        k8s_mode = os.environ.get("K8S_MODE", "mock")
        if k8s_mode != "in-cluster":
            logger.info("Seeding example ScaledObjects (mock mode)")
            result = await session.execute(select(ScaledObjectModel))
            if not result.scalars().first():
                examples = [
                    # ... example ScaledObjects
                ]
                session.add_all(examples)
                await session.commit()
        else:
            logger.info("Skipping example ScaledObjects (in-cluster mode)")
```

### Étape 2 : Ajouter un Message d'Aide dans l'Interface

Quand aucun ScaledObject n'existe en mode in-cluster, afficher un message :

```
Aucun ScaledObject trouvé dans le namespace 'test'.

Pour commencer :
1. Créez un ScaledObject via kubectl ou l'API
2. Ou changez K8S_MODE=mock pour utiliser des exemples
```

## Vérification Après Correction

```bash
# 1. Redéployer avec le code corrigé
helm upgrade keda-dash ./helm/keda-dashboard --namespace test

# 2. Vérifier les logs
kubectl logs -n test -l app.kubernetes.io/component=backend --tail=50 | grep -i seed

# 3. Vérifier l'interface
# Devrait afficher "Aucun ScaledObject" au lieu d'exemples
```

## Prévention

Pour éviter ce problème à l'avenir :

1. **Documentation claire** : Indiquer que les exemples ne sont disponibles qu'en mode mock
2. **Message d'aide** : Afficher un guide dans l'interface quand aucun ScaledObject n'existe
3. **Validation** : Vérifier que le ScaledObject existe dans Kubernetes avant de tenter une mise à jour

## Workaround Temporaire

En attendant la correction du code, vous pouvez :

1. **Créer un ScaledObject réel** :
```bash
kubectl apply -f - <<EOF
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: test
  namespace: test
spec:
  scaleTargetRef:
    name: keda-dash-keda-dashboard-backend
  minReplicaCount: 1
  maxReplicaCount: 3
  triggers:
    - type: cpu
      metricType: Utilization
      metadata:
        value: "70"
EOF
```

2. **Ou passer en mode mock** :
```bash
kubectl patch configmap -n test keda-dash-keda-dashboard-config \
  --type merge \
  -p '{"data":{"K8S_MODE":"mock"}}'

kubectl delete pod -n test -l app.kubernetes.io/component=backend
```

## Résumé

- ❌ **Problème** : Seed data créé en mode in-cluster
- ✅ **Solution** : Ne créer que l'admin user en mode in-cluster
- ✅ **Résultat** : L'interface affichera les vrais ScaledObjects de Kubernetes
