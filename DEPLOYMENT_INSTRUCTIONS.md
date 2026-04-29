# Instructions de Déploiement - Feature Okta Auth RBAC

## Résumé des Corrections

### Problèmes Résolus

1. ✅ **Circular Import** - Séparation de `database.py` et `schemas.py`
2. ✅ **SQL Migrations** - Parser amélioré pour gérer les blocs DO PostgreSQL
3. ✅ **PostgreSQL Health Probes** - Ajout du paramètre `-d` pour spécifier la base de données

### Fichiers Modifiés

| Fichier | Changement |
|---------|-----------|
| `backend/server.py` | Fonction `apply_sql_migrations()` améliorée |
| `backend/database.py` | Nouveau module pour éviter les imports circulaires |
| `backend/schemas.py` | Nouveau module pour les schémas Pydantic |
| `helm/keda-dashboard/templates/postgresql.yaml` | Correction des health probes |
| `helm/keda-dashboard/templates/postgresql-init-configmap.yaml` | Nouveau script d'initialisation |

## Déploiement Rapide

### Option 1 : Déploiement Propre (Recommandé)

Si vous n'avez pas de données importantes à conserver :

```bash
# 1. Supprimer le déploiement existant
helm uninstall keda-dashboard -n keda-dashboard 2>/dev/null || true

# 2. Supprimer les PVC (données PostgreSQL)
kubectl delete pvc -n keda-dashboard -l app.kubernetes.io/component=postgresql 2>/dev/null || true

# 3. Attendre que tout soit supprimé
kubectl wait --for=delete pod -n keda-dashboard --all --timeout=60s 2>/dev/null || true

# 4. Déployer la nouvelle version
helm install keda-dashboard ./helm/keda-dashboard \
  --namespace keda-dashboard \
  --create-namespace \
  --set backend.image.repository=ghcr.io/$(git config user.name | tr '[:upper:]' '[:lower:]')/keda-dashboard-backend \
  --set backend.image.tag=okta-auth-rbac

# 5. Attendre que les pods soient prêts
kubectl wait --for=condition=ready pod -n keda-dashboard -l app.kubernetes.io/component=postgresql --timeout=120s
kubectl wait --for=condition=ready pod -n keda-dashboard -l app.kubernetes.io/component=backend --timeout=120s

# 6. Vérifier les logs
kubectl logs -n keda-dashboard -l app.kubernetes.io/component=backend --tail=50 | grep -A 10 "Applying database migrations"
```

### Option 2 : Mise à Jour (Si vous avez des données)

Si vous voulez conserver les données existantes :

```bash
# 1. Faire une sauvegarde de la base de données
kubectl exec -n keda-dashboard -it $(kubectl get pod -n keda-dashboard -l app.kubernetes.io/component=postgresql -o jsonpath='{.items[0].metadata.name}') -- \
  pg_dump -U keda -d keda_dashboard > backup_$(date +%Y%m%d_%H%M%S).sql

# 2. Mettre à jour le déploiement
helm upgrade keda-dashboard ./helm/keda-dashboard \
  --namespace keda-dashboard \
  --set backend.image.repository=ghcr.io/$(git config user.name | tr '[:upper:]' '[:lower:]')/keda-dashboard-backend \
  --set backend.image.tag=okta-auth-rbac

# 3. Redémarrer PostgreSQL pour appliquer les nouvelles probes
kubectl rollout restart statefulset -n keda-dashboard keda-dashboard-postgresql

# 4. Attendre que PostgreSQL soit prêt
kubectl wait --for=condition=ready pod -n keda-dashboard -l app.kubernetes.io/component=postgresql --timeout=120s

# 5. Redémarrer le backend
kubectl rollout restart deployment -n keda-dashboard keda-dashboard-backend

# 6. Vérifier les logs
kubectl logs -n keda-dashboard -l app.kubernetes.io/component=backend --tail=50 | grep -A 10 "Applying database migrations"
```

## Vérification Post-Déploiement

### 1. Vérifier que tous les pods sont en cours d'exécution

```bash
kubectl get pods -n keda-dashboard
```

**Résultat attendu** :
```
NAME                                      READY   STATUS    RESTARTS   AGE
keda-dashboard-backend-xxx                1/1     Running   0          2m
keda-dashboard-postgresql-0               1/1     Running   0          2m
```

### 2. Vérifier les logs PostgreSQL

```bash
kubectl logs -n keda-dashboard -l app.kubernetes.io/component=postgresql --tail=20
```

**Résultat attendu** : Pas d'erreur "database does not exist"

### 3. Vérifier les logs du Backend

```bash
kubectl logs -n keda-dashboard -l app.kubernetes.io/component=backend --tail=100
```

**Résultat attendu** :
```
INFO - Applying database migrations...
INFO - Found 3 migration files
INFO - Applying migration: 001_add_scaling_behavior.sql
INFO - ✅ Successfully processed: 001_add_scaling_behavior.sql
INFO - Applying migration: 002_add_auth_fields.sql
INFO - ✅ Successfully processed: 002_add_auth_fields.sql
INFO - Applying migration: 003_create_permissions_table.sql
INFO - ✅ Successfully processed: 003_create_permissions_table.sql
INFO - ✅ All migrations processed
INFO - K8s service initialized: mode=in-cluster, connected=True
```

### 4. Tester l'API

```bash
# Port-forward vers le backend
kubectl port-forward -n keda-dashboard svc/keda-dashboard-backend 8001:8001 &

# Tester le health check
curl http://localhost:8001/api/health

# Tester la configuration d'authentification
curl http://localhost:8001/api/auth/config

# Tester le login
curl -X POST http://localhost:8001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"admin123"}'
```

### 5. Vérifier la Base de Données

```bash
# Port-forward vers PostgreSQL
kubectl port-forward -n keda-dashboard svc/keda-dashboard-postgresql 5432:5432 &

# Se connecter à PostgreSQL
PGPASSWORD=keda-secret psql -h localhost -U keda -d keda_dashboard

# Vérifier les colonnes de la table users
\d users

# Vérifier que auth_provider existe
SELECT column_name FROM information_schema.columns WHERE table_name = 'users';

# Vérifier que la table permissions existe
\dt

# Quitter
\q
```

## Troubleshooting

### Erreur : "database keda does not exist"

**Solution** : Les health probes ne sont pas à jour. Redéployez avec la nouvelle configuration :

```bash
helm upgrade keda-dashboard ./helm/keda-dashboard --namespace keda-dashboard
kubectl rollout restart statefulset -n keda-dashboard keda-dashboard-postgresql
```

### Erreur : "column users.auth_provider does not exist"

**Solution** : Les migrations ne sont pas appliquées. Vérifiez les logs du backend :

```bash
kubectl logs -n keda-dashboard -l app.kubernetes.io/component=backend | grep migration
```

Si les migrations n'apparaissent pas, appliquez-les manuellement :

```bash
kubectl exec -it -n keda-dashboard deployment/keda-dashboard-backend -- python backend/apply_migrations.py
```

### Pod Backend en CrashLoopBackOff

**Diagnostic** :

```bash
# Vérifier les logs du pod précédent
kubectl logs -n keda-dashboard -l app.kubernetes.io/component=backend --previous

# Vérifier les events
kubectl get events -n keda-dashboard --sort-by='.lastTimestamp' | grep backend
```

**Solutions courantes** :
1. PostgreSQL n'est pas prêt → Attendre que PostgreSQL soit en état Running
2. Erreur de connexion → Vérifier le secret DATABASE_URL
3. Erreur de migration → Appliquer manuellement les migrations

### PostgreSQL ne démarre pas

**Diagnostic** :

```bash
kubectl describe pod -n keda-dashboard -l app.kubernetes.io/component=postgresql
kubectl logs -n keda-dashboard -l app.kubernetes.io/component=postgresql
```

**Solutions courantes** :
1. PVC corrompu → Supprimer le PVC et redéployer
2. Problème de permissions → Vérifier les droits sur le volume
3. Ressources insuffisantes → Augmenter les limites dans values.yaml

## Rollback

Si vous devez revenir en arrière :

```bash
# Restaurer depuis la sauvegarde
kubectl exec -n keda-dashboard -it $(kubectl get pod -n keda-dashboard -l app.kubernetes.io/component=postgresql -o jsonpath='{.items[0].metadata.name}') -- \
  psql -U keda -d keda_dashboard < backup_YYYYMMDD_HHMMSS.sql

# Ou revenir à la version précédente du Helm chart
helm rollback keda-dashboard -n keda-dashboard
```

## Prochaines Étapes

Une fois le déploiement réussi :

1. ✅ Tester l'authentification locale
2. ✅ Configurer Okta (si nécessaire)
3. ✅ Tester les permissions RBAC
4. ✅ Déployer en production

---

**Date** : 2026-04-29  
**Branche** : feature/okta-auth-rbac  
**Auteur** : Kiro AI Assistant
