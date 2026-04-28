-- Migration: Add scaling_behavior_json column to scaled_objects table
-- Date: 2026-04-27
-- Description: Adds optional scaling behavior configuration for scale-up and scale-down policies

-- For PostgreSQL
ALTER TABLE scaled_objects ADD COLUMN IF NOT EXISTS scaling_behavior_json TEXT;

-- For SQLite (if running manually, use this instead)
-- ALTER TABLE scaled_objects ADD COLUMN scaling_behavior_json TEXT;

-- Verify the column was added
-- SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'scaled_objects';
