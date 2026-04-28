# Database Migrations

This directory contains SQL migration scripts for the KEDA Dashboard database.

## Automatic Migrations

The application automatically applies migrations on startup. The migration logic is in `server.py` in the `lifespan` function.

## Manual Migrations

If you need to apply migrations manually (e.g., in production before deploying), you can run the SQL scripts directly:

### PostgreSQL

```bash
psql -h <host> -U <user> -d <database> -f 001_add_scaling_behavior.sql
```

### SQLite

```bash
sqlite3 keda_dashboard.db < 001_add_scaling_behavior.sql
```

## Migration List

- **001_add_scaling_behavior.sql**: Adds `scaling_behavior_json` column to `scaled_objects` table for optional scale-up/scale-down policies configuration.
- **002_add_auth_fields.sql**: Extends `users` table to support dual authentication providers (local and Okta SSO). Adds `auth_provider` and `okta_subject` columns, makes `password_hash` nullable, and backfills existing users as 'local' provider.
- **003_create_permissions_table.sql**: Creates `permissions` table for fine-grained RBAC on ScaledObjects. Includes foreign key to users table with CASCADE delete, indexes for efficient lookups, and unique constraint to prevent duplicate permissions.

## Creating New Migrations

1. Create a new SQL file with a sequential number: `00X_description.sql`
2. Add the migration logic for both PostgreSQL and SQLite
3. Update the automatic migration logic in `server.py` if needed
4. Update this README with the migration description
