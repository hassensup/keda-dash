#!/usr/bin/env python3
"""
Migration runner for KEDA Dashboard
Applies SQL migrations in order to the database
"""
import sqlite3
import os
import sys
from pathlib import Path

# Get the database path
ROOT_DIR = Path(__file__).parent
DB_PATH = ROOT_DIR / "keda_dashboard.db"
MIGRATIONS_DIR = ROOT_DIR / "migrations"

def get_migration_files():
    """Get all migration files in order"""
    migrations = []
    for file in sorted(MIGRATIONS_DIR.glob("*.sql")):
        if file.name.startswith("00") and file.name.endswith(".sql"):
            migrations.append(file)
    return migrations

def create_migrations_table(conn):
    """Create a table to track applied migrations"""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            migration_name VARCHAR(255) NOT NULL UNIQUE,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()

def get_applied_migrations(conn):
    """Get list of already applied migrations"""
    cursor = conn.execute("SELECT migration_name FROM schema_migrations")
    return {row[0] for row in cursor.fetchall()}

def apply_migration(conn, migration_file):
    """Apply a single migration file"""
    print(f"Applying migration: {migration_file.name}")
    
    with open(migration_file, 'r') as f:
        sql = f.read()
    
    # For SQLite, we need to handle the migration carefully
    # Split by semicolons and execute each statement
    statements = []
    current_statement = []
    
    for line in sql.split('\n'):
        # Skip comments and empty lines
        stripped = line.strip()
        if not stripped or stripped.startswith('--'):
            continue
        
        current_statement.append(line)
        
        # Check if this line ends a statement
        if stripped.endswith(';'):
            statement = '\n'.join(current_statement)
            statements.append(statement)
            current_statement = []
    
    # Execute each statement
    for statement in statements:
        statement = statement.strip()
        if not statement:
            continue
        
        # Skip PostgreSQL-specific statements
        if 'DO $' in statement or 'END $' in statement:
            print(f"  Skipping PostgreSQL-specific statement")
            continue
        
        # Handle ALTER TABLE statements for SQLite
        if 'ALTER TABLE users ALTER COLUMN password_hash DROP NOT NULL' in statement:
            print(f"  Skipping ALTER COLUMN (handled by table recreation)")
            continue
        
        try:
            conn.execute(statement)
            print(f"  Executed statement successfully")
        except sqlite3.OperationalError as e:
            # Check if it's a "duplicate column" error, which is OK
            if "duplicate column" in str(e).lower():
                print(f"  Column already exists, skipping: {e}")
            else:
                print(f"  Warning: {e}")
                # Continue anyway for idempotent migrations
    
    # Record the migration as applied
    conn.execute(
        "INSERT OR IGNORE INTO schema_migrations (migration_name) VALUES (?)",
        (migration_file.name,)
    )
    conn.commit()
    print(f"  Migration {migration_file.name} applied successfully")

def handle_users_table_migration(conn):
    """
    Special handling for users table migration to make password_hash nullable
    SQLite doesn't support ALTER COLUMN, so we need to recreate the table
    """
    # Check if we need to migrate
    cursor = conn.execute("PRAGMA table_info(users)")
    columns = {row[1]: row for row in cursor.fetchall()}
    
    # Check if auth_provider exists
    if 'auth_provider' in columns:
        print("Users table already migrated")
        return
    
    print("Migrating users table to support auth providers...")
    
    # Create new table with updated schema
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users_new (
            id VARCHAR NOT NULL PRIMARY KEY,
            email VARCHAR NOT NULL UNIQUE,
            password_hash VARCHAR,
            name VARCHAR NOT NULL,
            role VARCHAR DEFAULT 'user',
            auth_provider VARCHAR DEFAULT 'local' NOT NULL,
            okta_subject VARCHAR,
            created_at DATETIME,
            updated_at DATETIME
        )
    """)
    
    # Copy data from old table
    conn.execute("""
        INSERT INTO users_new (id, email, password_hash, name, role, auth_provider, created_at)
        SELECT id, email, password_hash, name, COALESCE(role, 'user'), 'local', created_at
        FROM users
    """)
    
    # Drop old table
    conn.execute("DROP TABLE users")
    
    # Rename new table
    conn.execute("ALTER TABLE users_new RENAME TO users")
    
    # Recreate indexes
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users(email)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_okta_subject ON users(okta_subject)")
    
    conn.commit()
    print("Users table migration completed")

def main():
    """Main migration runner"""
    if not DB_PATH.exists():
        print(f"Database not found at {DB_PATH}")
        print("Please start the server first to create the database")
        sys.exit(1)
    
    print(f"Connecting to database: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    
    try:
        # Create migrations tracking table
        create_migrations_table(conn)
        
        # Get applied migrations
        applied = get_applied_migrations(conn)
        print(f"Already applied migrations: {applied}")
        
        # Get all migration files
        migrations = get_migration_files()
        print(f"Found {len(migrations)} migration files")
        
        # Apply each migration
        for migration_file in migrations:
            if migration_file.name in applied:
                print(f"Skipping already applied migration: {migration_file.name}")
                continue
            
            # Special handling for users table migration
            if migration_file.name == "002_add_auth_fields.sql":
                handle_users_table_migration(conn)
                # Mark as applied
                conn.execute(
                    "INSERT OR IGNORE INTO schema_migrations (migration_name) VALUES (?)",
                    (migration_file.name,)
                )
                conn.commit()
            else:
                apply_migration(conn, migration_file)
        
        print("\nAll migrations applied successfully!")
        
        # Show current schema
        print("\n=== Current Users Table Schema ===")
        cursor = conn.execute("PRAGMA table_info(users)")
        for row in cursor.fetchall():
            print(f"  {row[1]}: {row[2]} {'NOT NULL' if row[3] else 'NULL'}")
        
        print("\n=== Current Permissions Table Schema ===")
        try:
            cursor = conn.execute("PRAGMA table_info(permissions)")
            for row in cursor.fetchall():
                print(f"  {row[1]}: {row[2]} {'NOT NULL' if row[3] else 'NULL'}")
        except sqlite3.OperationalError:
            print("  Permissions table does not exist yet")
        
    finally:
        conn.close()

if __name__ == "__main__":
    main()
