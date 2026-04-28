-- Migration: Create permissions table for RBAC
-- Date: 2024-01-15
-- Description: Creates permissions table to support fine-grained role-based access control for ScaledObjects
-- Requirements: 5.5, 5.6, 5.7, 5.8

-- ============================================================
-- PostgreSQL Migration
-- ============================================================

-- Create permissions table
CREATE TABLE IF NOT EXISTS permissions (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    action VARCHAR(20) NOT NULL,
    scope VARCHAR(20) NOT NULL,
    namespace VARCHAR(255) NOT NULL,
    object_name VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(36),
    CONSTRAINT fk_permissions_user FOREIGN KEY (user_id) 
        REFERENCES users(id) ON DELETE CASCADE
);

-- Add indexes for efficient permission lookups
CREATE INDEX IF NOT EXISTS idx_user_id ON permissions(user_id);
CREATE INDEX IF NOT EXISTS idx_namespace ON permissions(namespace);
CREATE INDEX IF NOT EXISTS idx_user_namespace ON permissions(user_id, namespace);

-- Add unique constraint to prevent duplicate permissions
-- Note: In PostgreSQL, NULL values are considered distinct in unique constraints
-- This allows multiple permissions with NULL object_name for the same user/action/scope/namespace
CREATE UNIQUE INDEX IF NOT EXISTS unique_permission 
    ON permissions(user_id, action, scope, namespace, COALESCE(object_name, ''));

-- ============================================================
-- SQLite Migration (for development)
-- ============================================================
-- Note: SQLite has different syntax for some constraints
-- If running on SQLite, the above statements work with minor differences:
-- 1. SQLite supports CREATE TABLE IF NOT EXISTS
-- 2. SQLite supports FOREIGN KEY constraints (must enable with PRAGMA foreign_keys=ON)
-- 3. SQLite supports CREATE INDEX IF NOT EXISTS
-- 4. For unique constraint with nullable columns, SQLite treats NULL as distinct by default

-- For SQLite, ensure foreign keys are enabled:
-- PRAGMA foreign_keys = ON;

-- The same CREATE TABLE statement works for SQLite:
-- CREATE TABLE IF NOT EXISTS permissions (
--     id VARCHAR(36) PRIMARY KEY,
--     user_id VARCHAR(36) NOT NULL,
--     action VARCHAR(20) NOT NULL,
--     scope VARCHAR(20) NOT NULL,
--     namespace VARCHAR(255) NOT NULL,
--     object_name VARCHAR(255),
--     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
--     created_by VARCHAR(36),
--     FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
-- );

-- Verify migration (PostgreSQL)
-- SELECT column_name, data_type, is_nullable 
-- FROM information_schema.columns 
-- WHERE table_name = 'permissions' 
-- ORDER BY ordinal_position;

-- Verify indexes (PostgreSQL)
-- SELECT indexname, indexdef 
-- FROM pg_indexes 
-- WHERE tablename = 'permissions';

-- Verify foreign key constraint (PostgreSQL)
-- SELECT conname, contype, confdeltype
-- FROM pg_constraint
-- WHERE conrelid = 'permissions'::regclass;
