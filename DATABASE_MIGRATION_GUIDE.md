# Guide de Migration de Base de Données

## 🐛 Problème Résolu

**Erreur** : `column users.auth_provider does not exist`

**Cause** : Les migrations SQL (002 et 003) n'étaient pas appliquées automatiquement au démarrage de l'application.

## ✅ Solution Implémentée

### Migrations Automatiques au Démarrage

Le code a été mis à jour pour appliquer **automatiquement** toutes les migrations SQL au démarrage de l'application.

**Fichier** : `backend/server.py` - fonction `lifespan()`

```python
async def lifespan(app):
    # 1. Créer les tables ORM
    await conn.run_sync(Base.metadata.create_all)
    
    # 2. Appliquer les migrations SQL
    await apply_sql_migrations()  # ← NOUVEAU
    
    # 3. Seed data
    await seed_data()
```

### Approche Technique

La fonction `apply_sql_migrations()` utilise SQLAlchemy avec asyncpg pour exécuter les migrations:

1. **Parse les fichiers SQL** : Lit tous les fichiers `*.sql` dans `backend/migrations/`
2. **Sépare les statements** : Divise le SQL en statements individuels, en gardant les blocs DO ensemble
3. **Exécute séquentiellement** : Chaque statement est exécuté avec `conn.execute(text(stmt))`
4. **Gestion d'erreurs** : Les erreurs "already exists" sont ignorées (migrations idempotentes)
5. **Continue en cas d'échec** : Si un statement échoue, continue avec le suivant

### Migrations Disponibles

| Fichier | Description | Statut |
|---------|-------------|--------|
| `001_add_scaling_behavior.sql` | Ajoute `scaling_behavior_json` à `scaled_objects` | ✅ Auto |
| `002_add_auth_fields.sql` | Ajoute `auth_provider`, `okta_subject` à `users` | ✅ Auto |
| `003_create_permissions_table.sql` | Crée la table `permissions` pour RBAC | ✅ Auto |

## 🚀 Déploiement

### Option 1 : Automatique (Recommandé)

Les migrations s'appliquent **automatiquement** au démarrage du pod.

```bash
# Déployer normalement
helm upgrade keda-dashboard ./helm/keda-dashboard \
  --namespace keda-dashboard

# Les migrations s'appliquent au démarrage
# Vérifier les logs
kubectl logs -l app.kubernetes.io/component=backend -n keda-dashboard --tail=50
```

**Logs attendus** :
```
INFO - Applying database migrations...
INFO - Found 3 migration files
INFO - Applying migration: 001_add_scaling_behavior.sql
INFO - ✅ Successfully applied: 001_add_scaling_behavior.sql
INFO - Applying migration: 002_add_auth_fields.sql
INFO - ✅ Successfully applied: 002_add_auth_fields.sql
INFO - Applying migration: 003_create_permissions_table.sql
INFO - ✅ Successfully applied: 003_create_permissions_table.sql
INFO - ✅ All migrations processed
```

### Option 2 : Manuelle (Avant Déploiement)

Si vous préférez appliquer les migrations **avant** le déploiement :

#### A. Avec le Script Python

```bash
# Dans le pod ou localement avec accès à la DB
python backend/apply_migrations.py
```

**Avantages** :
- ✅ Vérifie le schéma après application
- ✅ Logs détaillés
- ✅ Gestion d'erreurs

#### B. Avec psql (PostgreSQL)

```bash
# Connexion à PostgreSQL
export PGPASSWORD='your-password'

# Appliquer les migrations
psql -h <host> -U <user> -d <database> -f backend/migrations/002_add_auth_fields.sql
psql -h <host> -U <user> -d <database> -f backend/migrations/003_create_permissions_table.sql
```

#### C. Via Port-Forward Kubernetes

```bash
# Port-forward vers PostgreSQL
kubectl port-forward svc/postgresql 5432:5432 -n keda-dashboard

# Appliquer les migrations
psql -h localhost -U keda_user -d keda_dashboard -f backend/migrations/002_add_auth_fields.sql
psql -h localhost -U keda_user -d keda_dashboard -f backend/migrations/003_create_permissions_table.sql
```

## 🔍 Vérification

### 1. Vérifier les Colonnes de la Table Users

```sql
SELECT column_name, data_type, is_nullable, column_default 
FROM information_schema.columns 
WHERE table_name = 'users' 
ORDER BY ordinal_position;
```

**Colonnes attendues** :
- `id` (varchar)
- `email` (varchar)
- `password_hash` (varchar, **nullable**)
- `name` (varchar)
- `role` (varchar)
- `auth_provider` (varchar, default 'local') ← **NOUVEAU**
- `okta_subject` (varchar, nullable) ← **NOUVEAU**
- `created_at` (timestamp)
- `updated_at` (timestamp)

### 2. Vérifier la Table Permissions

```sql
SELECT table_name 
FROM information_schema.tables 
WHERE table_name = 'permissions';
```

**Résultat attendu** : 1 ligne (table existe)

### 3. Vérifier les Index

```sql
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE tablename = 'users' OR tablename = 'permissions';
```

**Index attendus** :
- `idx_okta_subject` sur `users(okta_subject)`
- `idx_user_id` sur `permissions(user_id)`
- `idx_namespace` sur `permissions(namespace)`
- `idx_user_namespace` sur `permissions(user_id, namespace)`

### 4. Tester l'Application

```bash
# Health check
curl http://localhost:8001/api/health
# Expected: {"status":"ok"}

# Auth config
curl http://localhost:8001/api/auth/config
# Expected: {"okta_enabled":false,"local_auth_enabled":true}

# Login (doit fonctionner sans erreur auth_provider)
curl -X POST http://localhost:8001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"admin123"}'
# Expected: JWT token et profil utilisateur
```

## 🔄 Rollback

Si vous devez annuler les migrations :

### Rollback Migration 003 (Permissions Table)

```sql
DROP TABLE IF EXISTS permissions CASCADE;
```

### Rollback Migration 002 (Auth Fields)

```sql
-- Supprimer les colonnes ajoutées
ALTER TABLE users DROP COLUMN IF EXISTS auth_provider;
ALTER TABLE users DROP COLUMN IF EXISTS okta_subject;

-- Remettre password_hash NOT NULL
ALTER TABLE users ALTER COLUMN password_hash SET NOT NULL;

-- Supprimer l'index
DROP INDEX IF EXISTS idx_okta_subject;
```

## 📊 Migrations Idempotentes

Les migrations sont **idempotentes** : elles peuvent être exécutées plusieurs fois sans erreur.

**PostgreSQL** :
```sql
DO $ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'users' AND column_name = 'auth_provider'
    ) THEN
        ALTER TABLE users ADD COLUMN auth_provider VARCHAR(50) DEFAULT 'local' NOT NULL;
    END IF;
END $;
```

**Avantages** :
- ✅ Pas d'erreur si la colonne existe déjà
- ✅ Peut être réexécuté en cas d'échec partiel
- ✅ Safe pour les redémarrages de pods

## 🐛 Troubleshooting

### Erreur : "column already exists"

**Cause** : Migration déjà appliquée partiellement

**Solution** : Les migrations sont idempotentes, l'erreur est normale et peut être ignorée.

### Erreur : "permission denied"

**Cause** : L'utilisateur DB n'a pas les droits ALTER TABLE

**Solution** :
```sql
-- Donner les droits nécessaires
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO keda_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO keda_user;
```

### Erreur : "relation does not exist"

**Cause** : La table `users` n'existe pas encore

**Solution** : Laisser l'ORM créer les tables d'abord :
```python
await conn.run_sync(Base.metadata.create_all)
```

### Pod en CrashLoopBackOff après migration

**Diagnostic** :
```bash
# Vérifier les logs
kubectl logs <pod-name> -n keda-dashboard --previous

# Vérifier le schéma DB
kubectl exec -it <pod-name> -n keda-dashboard -- \
  python -c "from backend.apply_migrations import verify_schema; import asyncio; asyncio.run(verify_schema())"
```

## 📝 Checklist de Déploiement

Avant de déployer en production :

- [ ] Backup de la base de données
- [ ] Test des migrations en staging
- [ ] Vérification du schéma après migration
- [ ] Test de l'authentification locale
- [ ] Test de l'authentification Okta (si activée)
- [ ] Vérification des permissions RBAC
- [ ] Rollback plan documenté

## 🔗 Fichiers Modifiés

| Fichier | Changement |
|---------|-----------|
| `backend/server.py` | Ajout de `apply_sql_migrations()` dans `lifespan()` |
| `backend/apply_migrations.py` | Script de migration manuel (nouveau) |
| `backend/migrations/002_add_auth_fields.sql` | Migration auth fields (existant) |
| `backend/migrations/003_create_permissions_table.sql` | Migration permissions (existant) |

## 📚 Ressources

- **SQLAlchemy Migrations** : https://docs.sqlalchemy.org/en/20/core/metadata.html
- **PostgreSQL ALTER TABLE** : https://www.postgresql.org/docs/current/sql-altertable.html
- **Idempotent Migrations** : https://en.wikipedia.org/wiki/Idempotence

---

**Créé le** : 2026-04-29  
**Branche** : feature/okta-auth-rbac  
**Statut** : ✅ Migrations automatiques activées
