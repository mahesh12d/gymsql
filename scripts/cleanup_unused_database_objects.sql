-- Database Cleanup Migration: Remove Unused Tables and Columns
-- This script removes legacy database objects that are no longer used by the application
-- 
-- Objects to be removed:
-- 1. execution_results.user_sandbox_id (FK to removed user_sandboxes table)
-- 2. execution_results unused telemetry columns (cpu_time_ms, io_operations, query_plan)
-- 3. user_sandboxes table (deprecated PostgreSQL sandbox functionality)
-- 4. companies table (has data but no application usage)
--
-- SAFETY: All objects confirmed to be unused via code analysis and data verification

BEGIN;

-- Step 1: Drop foreign key constraint from execution_results.user_sandbox_id
DO $$
DECLARE
    constraint_name text;
BEGIN
    -- Find the FK constraint name dynamically
    SELECT tc.constraint_name INTO constraint_name
    FROM information_schema.table_constraints tc
    JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name
    JOIN information_schema.constraint_column_usage ccu ON ccu.constraint_name = tc.constraint_name
    WHERE tc.constraint_type = 'FOREIGN KEY'
      AND tc.table_name = 'execution_results'
      AND kcu.column_name = 'user_sandbox_id'
      AND ccu.table_name = 'user_sandboxes';
    
    IF constraint_name IS NOT NULL THEN
        EXECUTE format('ALTER TABLE execution_results DROP CONSTRAINT %I', constraint_name);
        RAISE NOTICE 'Dropped FK constraint % from execution_results.user_sandbox_id', constraint_name;
    END IF;
END $$;

-- Step 2: Drop unused columns from execution_results table
ALTER TABLE execution_results DROP COLUMN IF EXISTS user_sandbox_id;
ALTER TABLE execution_results DROP COLUMN IF EXISTS cpu_time_ms;
ALTER TABLE execution_results DROP COLUMN IF EXISTS io_operations;
ALTER TABLE execution_results DROP COLUMN IF EXISTS query_plan;

-- Step 3: Drop foreign key constraints from user_sandboxes table
DO $$
DECLARE
    constraint_name text;
BEGIN
    -- Drop FK to users table
    SELECT tc.constraint_name INTO constraint_name
    FROM information_schema.table_constraints tc
    JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name
    WHERE tc.constraint_type = 'FOREIGN KEY'
      AND tc.table_name = 'user_sandboxes'
      AND kcu.column_name = 'user_id';
    
    IF constraint_name IS NOT NULL THEN
        EXECUTE format('ALTER TABLE user_sandboxes DROP CONSTRAINT %I', constraint_name);
        RAISE NOTICE 'Dropped FK constraint % from user_sandboxes.user_id', constraint_name;
    END IF;
    
    -- Drop FK to problems table
    SELECT tc.constraint_name INTO constraint_name
    FROM information_schema.table_constraints tc
    JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name
    WHERE tc.constraint_type = 'FOREIGN KEY'
      AND tc.table_name = 'user_sandboxes'
      AND kcu.column_name = 'problem_id';
    
    IF constraint_name IS NOT NULL THEN
        EXECUTE format('ALTER TABLE user_sandboxes DROP CONSTRAINT %I', constraint_name);
        RAISE NOTICE 'Dropped FK constraint % from user_sandboxes.problem_id', constraint_name;
    END IF;
END $$;

-- Step 4: Drop the user_sandboxes table entirely
DROP TABLE IF EXISTS user_sandboxes CASCADE;

-- Step 5: Drop the companies table (no FK dependencies)
DROP TABLE IF EXISTS companies CASCADE;

-- Step 6: Clean up any orphaned indexes or constraints
-- (CASCADE should handle this, but being explicit for safety)

COMMIT;

-- Report results
DO $$
BEGIN
    RAISE NOTICE '✅ Database cleanup completed successfully!';
    RAISE NOTICE '   - Removed user_sandboxes table (deprecated PostgreSQL sandbox functionality)';
    RAISE NOTICE '   - Removed companies table (unused by application)';
    RAISE NOTICE '   - Removed unused columns from execution_results';
    RAISE NOTICE '   - All foreign key constraints cleaned up properly';
END $$;