# Fix PostgreSQL Database Issue

## Problème Identifié

Deux erreurs liées :

1. **PostgreSQL** : `FATAL: database "keda" does not exist`
2. **Backend** : `column users.auth_provider does not exist`

## Cause Racine

Le problème vient de la configuration PostgreSQL :
- **values.yaml** définit : `username: keda` et `database: keda_dashboard`
- **pg_isready** dans les probes essayait de se connecter sans spécifier la base de données
- Par défaut, PostgreSQL essaie de se connecter à une base du même nom que l'utilisateur (`keda`)
- La base `keda` n'existe pas, seulement `keda_dashboard`

## Solution Appliquée

### 1. Correction des Health Probes

**Fichier** : `helm/keda-dashboard/templates/postgresql.yaml`

Avant :
```yaml
livenessProbe:
  exec:
    command: ["pg_isready", "-U", "keda"]
```

Après :
```yaml
livenessProbe:
  exec:
    command: ["pg_isready", "-U", "keda", "-d", "keda_dashboard"]
```

Cela force `pg_isready` à vérifier la bonne base de données.

### 2. Script d'Initialisation (Optionnel)

**Fichier** : `helm/keda-dashboard/templates/postgresql-init-configmap.yaml`

Un ConfigMap avec un script d'initialisation a été créé pour s'assurer que la base de données existe.

## Déploiement

### Étape 1 : Supprimer le Déploiement Existant (si nécessaire)

Si vous avez un déploiement existant avec des données corrompues :

```bash
# Supprimer complètement le déploiement
helm uninstall keda-dashboard -n keda-dashboard

# Supprimer le PVC PostgreSQL (ATTENTION : cela supprime les données)
kubectl delete pvc -n keda-dashboard -l app.kubernetes.io/component=postgresql

# Optionnel : supprimer le namespace et le recréer
kubectl delete namespace keda-dashboard
kubectl create namespace keda-dashboard
```

### Étape 2 : Déployer avec la Configuration Corrigée

```bash
# Déployer le chart Helm
helm install keda-dashboard ./helm/keda-dashboard \
  --namespace keda-dashboard \
  --create-namespace \
  --set backend.image.repository=ghcr.io/VOTRE_ORG/keda-dashboard-backend \
  --set backend.image.tag=okta-auth-rbac

# Ou si vous faites une mise à jour
helm upgrade keda-dashboard ./helm/keda-dashboard \
  --namespace keda-dashboard
```

### Étape 3 : Vérifier le Déploiement

```bash
# Vérifier que PostgreSQL démarre correctement
kubectl get pods -n keda-dashboard -l app.kubernetes.io/component=postgresql
kubectl logs -n keda-dashboard -l app.kubernetes.io/component=postgresql

# Vérifier que le backend démarre correctement
kubectl get pods -n keda-dashboard -l app.kubernetes.io/component=backend
kubectl logs -n keda-dashboard -l app.kubernetes.io/component=backend --tail=100
```

### Étape 4 : Vérifier les Migrations

Dans les logs du backend, vous devriez voir :

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
```

## Vérification Manuelle de la Base de Données

Si vous voulez vérifier manuellement que la base de données est correcte :

```bash
# Port-forward vers PostgreSQL
kubectl port-forward -n keda-dashboard svc/keda-dashboard-postgresql 5432:5432

# Dans un autre terminal, connectez-vous à PostgreSQL
PGPASSWORD=keda-secret psql -h localhost -U keda -d keda_dashboard

# Vérifier les colonnes de la table users
\d users

# Vérifier que auth_provider existe
SELECT column_name, data_type, is_nullable, column_default 
FROM information_schema.columns 
WHERE table_name = 'users' 
ORDER BY ordinal_position;

# Vérifier que la table permissions existe
\dt permissions

# Quitter
\q
```

## Résultat Attendu

Après le déploiement, vous devriez avoir :

1. ✅ PostgreSQL démarre avec la base `keda_dashboard`
2. ✅ Les health probes passent (vert)
3. ✅ Le backend démarre sans erreur
4. ✅ Les migrations SQL sont appliquées automatiquement
5. ✅ La table `users` a les colonnes `auth_provider` et `okta_subject`
6. ✅ La table `permissions` existe
7. ✅ L'authentification fonctionne

## Troubleshooting

### Si PostgreSQL ne démarre toujours pas

```bash
# Vérifier les logs détaillés
kubectl logs -n keda-dashboard -l app.kubernetes.io/component=postgresql --previous

# Vérifier les events
kubectl get events -n keda-dashboard --sort-by='.lastTimestamp'

# Vérifier le PVC
kubectl get pvc -n keda-dashboard
```

### Si le Backend ne peut pas se connecter

```bash
# Vérifier que le service PostgreSQL existe
kubectl get svc -n keda-dashboard

# Vérifier la résolution DNS
kubectl run -it --rm debug --image=busybox --restart=Never -n keda-dashboard -- nslookup keda-dashboard-postgresql

# Vérifier les secrets
kubectl get secret -n keda-dashboard keda-dashboard-secret -o yaml
```

### Si les Migrations Échouent

```bash
# Appliquer manuellement les migrations
kubectl exec -it -n keda-dashboard deployment/keda-dashboard-backend -- python backend/apply_migrations.py

# Ou via psql
kubectl port-forward -n keda-dashboard svc/keda-dashboard-postgresql 5432:5432
PGPASSWORD=keda-secret psql -h localhost -U keda -d keda_dashboard -f backend/migrations/002_add_auth_fields.sql
PGPASSWORD=keda-secret psql -h localhost -U keda -d keda_dashboard -f backend/migrations/003_create_permissions_table.sql
```

---

**Date** : 2026-04-29  
**Branche** : feature/okta-auth-rbac  
**Statut** : ✅ Corrigé
