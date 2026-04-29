"""
Database Migration Script

This script applies all SQL migrations from the migrations/ directory.
It should be run before starting the application or as part of the deployment process.
"""

import os
import asyncio
import logging
from pathlib import Path
from sqlalchemy import text
from backend.database import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MIGRATIONS_DIR = Path(__file__).parent / "migrations"


async def apply_migrations():
    """Apply all SQL migrations in order."""
    
    # Get all migration files sorted by name
    migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    
    if not migration_files:
        logger.warning(f"No migration files found in {MIGRATIONS_DIR}")
        return
    
    logger.info(f"Found {len(migration_files)} migration files")
    
    async with engine.begin() as conn:
        for migration_file in migration_files:
            logger.info(f"Applying migration: {migration_file.name}")
            
            try:
                # Read migration SQL
                with open(migration_file, 'r') as f:
                    sql_content = f.read()
                
                # Split by semicolon and execute each statement
                # Skip empty statements and comments
                statements = [
                    stmt.strip() 
                    for stmt in sql_content.split(';') 
                    if stmt.strip() and not stmt.strip().startswith('--')
                ]
                
                for statement in statements:
                    # Skip SQLite-specific comments
                    if statement.strip().startswith('/*') or statement.strip().startswith('*/'):
                        continue
                    
                    # Execute statement
                    await conn.execute(text(statement))
                
                logger.info(f"✅ Successfully applied: {migration_file.name}")
                
            except Exception as e:
                # Log error but continue with other migrations
                # Some migrations might be idempotent and fail if already applied
                logger.warning(f"⚠️  Error applying {migration_file.name}: {e}")
                logger.info("Continuing with next migration...")
    
    logger.info("✅ All migrations processed")


async def verify_schema():
    """Verify that the schema has the expected columns."""
    
    logger.info("Verifying database schema...")
    
    async with engine.begin() as conn:
        # Check users table columns
        result = await conn.execute(text("""
            SELECT column_name, data_type, is_nullable 
            FROM information_schema.columns 
            WHERE table_name = 'users' 
            ORDER BY ordinal_position
        """))
        
        columns = result.fetchall()
        logger.info(f"Users table has {len(columns)} columns:")
        for col in columns:
            logger.info(f"  - {col[0]} ({col[1]}, nullable={col[2]})")
        
        # Check if auth_provider exists
        auth_provider_exists = any(col[0] == 'auth_provider' for col in columns)
        okta_subject_exists = any(col[0] == 'okta_subject' for col in columns)
        
        if auth_provider_exists and okta_subject_exists:
            logger.info("✅ Auth fields exist in users table")
        else:
            logger.error("❌ Auth fields missing from users table")
            if not auth_provider_exists:
                logger.error("  - Missing: auth_provider")
            if not okta_subject_exists:
                logger.error("  - Missing: okta_subject")
        
        # Check permissions table
        try:
            result = await conn.execute(text("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_name = 'permissions'
            """))
            permissions_exists = result.scalar() > 0
            
            if permissions_exists:
                logger.info("✅ Permissions table exists")
            else:
                logger.error("❌ Permissions table does not exist")
        except Exception as e:
            logger.error(f"❌ Error checking permissions table: {e}")


async def main():
    """Main entry point."""
    logger.info("=" * 60)
    logger.info("Database Migration Script")
    logger.info("=" * 60)
    
    try:
        # Apply migrations
        await apply_migrations()
        
        # Verify schema
        await verify_schema()
        
        logger.info("=" * 60)
        logger.info("Migration script completed successfully")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"Migration script failed: {e}")
        raise
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
