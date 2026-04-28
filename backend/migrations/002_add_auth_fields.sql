-- Migration: Add authentication provider fields to users table
-- Date: 2024-01-15
-- Description: Extends users table to support both local and Okta authentication providers
-- Requirements: 4.5, 4.6, 4.7, 11.5

-- ============================================================
-- PostgreSQL Migration
-- ============================================================

-- Add auth_provider column with default 'local'
-- For PostgreSQL, use IF NOT EXISTS to make migration idempotent
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'users' AND column_name = 'auth_provider'
    ) THEN
        ALTER TABLE users ADD COLUMN auth_provider VARCHAR(50) DEFAULT 'local' NOT NULL;
    END IF;
END $$;

-- Add okta_subject column (nullable, for Okta user linking)
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'users' AND column_name = 'okta_subject'
    ) THEN
        ALTER TABLE users ADD COLUMN okta_subject VARCHAR(255);
    END IF;
END $$;

-- Modify password_hash to be nullable (Okta users don't have passwords)
-- PostgreSQL allows this directly
ALTER TABLE users ALTER COLUMN password_hash DROP NOT NULL;

-- Add index on okta_subject for efficient lookups
CREATE INDEX IF NOT EXISTS idx_okta_subject ON users(okta_subject);

-- Backfill existing users with auth_provider='local'
UPDATE users SET auth_provider = 'local' WHERE auth_provider IS NULL;

-- ============================================================
-- SQLite Migration (for development)
-- ============================================================
-- Note: SQLite has limited ALTER TABLE support
-- If running on SQLite, use the following approach:

-- For SQLite: Add columns (SQLite doesn't support IF NOT EXISTS for columns)
-- These will fail gracefully if columns already exist when run manually
-- ALTER TABLE users ADD COLUMN auth_provider VARCHAR(50) DEFAULT 'local' NOT NULL;
-- ALTER TABLE users ADD COLUMN okta_subject VARCHAR(255);

-- SQLite doesn't support ALTER COLUMN, so we need to recreate the table
-- This is handled automatically by SQLAlchemy ORM when the model is updated
-- Manual SQLite migration (if needed):
/*
BEGIN TRANSACTION;

-- Create new table with updated schema
CREATE TABLE users_new (
    id VARCHAR(36) PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),  -- Now nullable
    name VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'user',
    auth_provider VARCHAR(50) DEFAULT 'local' NOT NULL,
    okta_subject VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Copy data from old table
INSERT INTO users_new (id, email, password_hash, name, role, auth_provider, created_at, updated_at)
SELECT id, email, password_hash, name, role, 'local', created_at, updated_at
FROM users;

-- Drop old table
DROP TABLE users;

-- Rename new table
ALTER TABLE users_new RENAME TO users;

-- Recreate indexes
CREATE INDEX idx_email ON users(email);
CREATE INDEX idx_okta_subject ON users(okta_subject);

COMMIT;
*/

-- Verify migration (PostgreSQL)
-- SELECT column_name, data_type, is_nullable, column_default 
-- FROM information_schema.columns 
-- WHERE table_name = 'users' 
-- ORDER BY ordinal_position;
