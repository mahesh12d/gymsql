-- ROLLBACK SCRIPT: Restore Database Objects Removed by cleanup_unused_database_objects.sql
-- 
-- IMPORTANT: This rollback script recreates the table structures but CANNOT restore the original data
-- Use this only if you have a database backup to restore from
--
-- BEFORE RUNNING: Ensure you have a complete database backup from before the cleanup

BEGIN;

-- Step 1: Recreate companies table (structure only - data must be restored from backup)
CREATE TABLE IF NOT EXISTS companies (
    id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    logo_filename VARCHAR,
    website_url VARCHAR,
    industry VARCHAR,
    total_questions INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
);

-- Step 2: Recreate user_sandboxes table (structure only - data must be restored from backup)
CREATE TABLE IF NOT EXISTS user_sandboxes (
    id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id VARCHAR NOT NULL,
    problem_id VARCHAR NOT NULL,
    database_name VARCHAR NOT NULL,
    connection_string TEXT,
    status VARCHAR NOT NULL,
    max_execution_time_seconds INTEGER,
    max_memory_mb INTEGER,
    max_connections INTEGER,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    last_accessed_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    cleanup_scheduled_at TIMESTAMP WITHOUT TIME ZONE
);

-- Step 3: Add foreign key constraints to user_sandboxes
ALTER TABLE user_sandboxes ADD CONSTRAINT user_sandboxes_user_id_fkey 
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
ALTER TABLE user_sandboxes ADD CONSTRAINT user_sandboxes_problem_id_fkey 
    FOREIGN KEY (problem_id) REFERENCES problems(id) ON DELETE CASCADE;

-- Step 4: Add missing columns back to execution_results
ALTER TABLE execution_results ADD COLUMN IF NOT EXISTS user_sandbox_id VARCHAR;
ALTER TABLE execution_results ADD COLUMN IF NOT EXISTS cpu_time_ms INTEGER;
ALTER TABLE execution_results ADD COLUMN IF NOT EXISTS io_operations INTEGER;
ALTER TABLE execution_results ADD COLUMN IF NOT EXISTS query_plan JSONB;

-- Step 5: Add foreign key constraint from execution_results to user_sandboxes
ALTER TABLE execution_results ADD CONSTRAINT execution_results_user_sandbox_id_fkey 
    FOREIGN KEY (user_sandbox_id) REFERENCES user_sandboxes(id) ON DELETE CASCADE;

COMMIT;

-- IMPORTANT NOTES FOR ROLLBACK:
-- 1. This script only recreates table structures
-- 2. You must restore data from a backup taken before the cleanup
-- 3. Update api/models.py to restore the removed ExecutionResult columns
-- 4. The companies table had 3 rows of data that must be restored from backup
-- 5. Test the application thoroughly after rollback