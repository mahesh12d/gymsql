-- ============================================================================
-- SQL Learning Platform - Complete Database Schema for Snowflake
-- ============================================================================
-- This file contains the complete data model for the SQL learning platform
-- optimized for Snowflake Data Cloud
-- ============================================================================

-- ============================================================================
-- NOTE: Snowflake Foreign Keys and Constraints
-- ============================================================================
-- Foreign keys in Snowflake are for documentation/metadata purposes only
-- They are NOT enforced. Application logic must handle referential integrity.
-- UNIQUE constraints are also informational only and not enforced.
-- ============================================================================

-- ============================================================================
-- CORE TABLES
-- ============================================================================

-- Users Table
CREATE TABLE users (
    id VARCHAR PRIMARY KEY,
    username VARCHAR UNIQUE NOT NULL,
    email VARCHAR UNIQUE NOT NULL,
    password_hash VARCHAR,
    first_name VARCHAR,
    last_name VARCHAR,
    company_name VARCHAR,
    linkedin_url VARCHAR,
    profile_image_url VARCHAR,
    google_id VARCHAR UNIQUE,
    auth_provider VARCHAR NOT NULL DEFAULT 'email',
    problems_solved INTEGER NOT NULL DEFAULT 0,
    premium BOOLEAN NOT NULL DEFAULT FALSE,
    is_admin BOOLEAN NOT NULL DEFAULT FALSE,
    email_verified BOOLEAN NOT NULL DEFAULT FALSE,
    verification_token VARCHAR,
    verification_token_expires TIMESTAMP_NTZ,
    created_at TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    -- Constraint for auth_provider values (informational)
    CONSTRAINT chk_auth_provider CHECK (auth_provider IN ('email', 'google', 'github', 'linkedin'))
);

-- Followers Table (User Relationships)
CREATE TABLE followers (
    id VARCHAR PRIMARY KEY,
    follower_id VARCHAR NOT NULL,
    following_id VARCHAR NOT NULL,
    created_at TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    -- Foreign keys (informational only in Snowflake)
    FOREIGN KEY (follower_id) REFERENCES users(id),
    FOREIGN KEY (following_id) REFERENCES users(id),
    -- Unique constraint (informational)
    CONSTRAINT uq_follower_following UNIQUE (follower_id, following_id)
);

-- Cache Entries Table
CREATE TABLE cache_entries (
    id VARCHAR PRIMARY KEY,
    cache_key VARCHAR NOT NULL,
    namespace VARCHAR NOT NULL DEFAULT 'result',
    data VARIANT NOT NULL,
    expires_at TIMESTAMP_NTZ NOT NULL,
    created_at TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    -- Unique constraint (informational)
    CONSTRAINT uq_cache_key_namespace UNIQUE (cache_key, namespace)
);

-- Fallback Submissions Table
CREATE TABLE fallback_submissions (
    id VARCHAR PRIMARY KEY,
    job_id VARCHAR UNIQUE NOT NULL,
    data VARIANT NOT NULL,
    status VARCHAR NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    processed_at TIMESTAMP_NTZ,
    -- Constraint for status values (informational)
    CONSTRAINT chk_fallback_status CHECK (status IN ('pending', 'processing', 'completed', 'failed'))
);

-- Topics Table (SQL Concepts Organization)
CREATE TABLE topics (
    id VARCHAR PRIMARY KEY,
    name VARCHAR UNIQUE NOT NULL,
    description VARCHAR,
    difficulty_level VARCHAR NOT NULL,
    order_index INTEGER DEFAULT 0,
    parent_topic_id VARCHAR,
    created_at TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    -- Foreign key (informational)
    FOREIGN KEY (parent_topic_id) REFERENCES topics(id),
    -- Constraint for difficulty_level values (informational)
    CONSTRAINT chk_difficulty_level CHECK (difficulty_level IN ('BEGINNER', 'EASY', 'MEDIUM', 'HARD', 'EXPERT'))
);

-- Problems Table
CREATE TABLE problems (
    id VARCHAR PRIMARY KEY,
    title VARCHAR NOT NULL,
    difficulty VARCHAR NOT NULL,
    tags VARIANT NOT NULL DEFAULT '[]'::VARIANT,
    company VARCHAR,
    hints VARIANT NOT NULL DEFAULT '[]'::VARIANT,
    question VARIANT NOT NULL,
    s3_data_source VARIANT,
    s3_datasets VARIANT,
    premium BOOLEAN DEFAULT NULL,
    master_solution VARIANT,
    expected_display VARIANT,
    expected_hash VARCHAR,
    created_at TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    topic_id VARCHAR,
    -- Foreign key (informational)
    FOREIGN KEY (topic_id) REFERENCES topics(id),
    -- Constraint for difficulty values (informational)
    CONSTRAINT chk_problems_difficulty CHECK (difficulty IN ('Easy', 'Medium', 'Hard'))
);

-- Test Cases Table
CREATE TABLE test_cases (
    id VARCHAR PRIMARY KEY,
    problem_id VARCHAR NOT NULL,
    name VARCHAR NOT NULL,
    description VARCHAR,
    input_data VARIANT NOT NULL,
    expected_output VARIANT NOT NULL,
    validation_rules VARIANT DEFAULT '{}'::VARIANT,
    is_hidden BOOLEAN DEFAULT FALSE,
    order_index INTEGER DEFAULT 0,
    timeout_seconds INTEGER DEFAULT 30,
    memory_limit_mb INTEGER DEFAULT 256,
    expected_output_source VARIANT,
    preview_expected_output VARIANT,
    display_limit INTEGER DEFAULT 10,
    created_at TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    -- Foreign key (informational)
    FOREIGN KEY (problem_id) REFERENCES problems(id),
    -- Unique constraint (informational)
    CONSTRAINT uq_test_cases_problem_name UNIQUE (problem_id, name)
);

-- Submissions Table
CREATE TABLE submissions (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL,
    problem_id VARCHAR NOT NULL,
    query VARCHAR NOT NULL,
    is_correct BOOLEAN NOT NULL,
    execution_time INTEGER,
    submitted_at TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    -- Foreign keys (informational)
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (problem_id) REFERENCES problems(id)
);

-- Execution Results Table
CREATE TABLE execution_results (
    id VARCHAR PRIMARY KEY,
    submission_id VARCHAR NOT NULL,
    test_case_id VARCHAR NOT NULL,
    status VARCHAR NOT NULL,
    execution_time_ms INTEGER,
    memory_used_mb FLOAT,
    rows_affected INTEGER,
    query_result VARIANT,
    error_message VARCHAR,
    is_correct BOOLEAN NOT NULL,
    validation_details VARIANT,
    created_at TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    -- Foreign keys (informational)
    FOREIGN KEY (submission_id) REFERENCES submissions(id),
    FOREIGN KEY (test_case_id) REFERENCES test_cases(id),
    -- Constraint for status values (informational)
    CONSTRAINT chk_execution_status CHECK (status IN ('SUCCESS', 'ERROR', 'TIMEOUT', 'MEMORY_LIMIT'))
);

-- ============================================================================
-- COMMUNITY & SOCIAL FEATURES
-- ============================================================================

-- Community Posts Table
CREATE TABLE community_posts (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL,
    problem_id VARCHAR,
    content VARCHAR NOT NULL,
    code_snippet VARCHAR,
    likes INTEGER NOT NULL DEFAULT 0,
    comments INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    -- Foreign keys (informational)
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (problem_id) REFERENCES problems(id)
);

-- Post Likes Table
CREATE TABLE post_likes (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL,
    post_id VARCHAR NOT NULL,
    created_at TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    -- Foreign keys (informational)
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (post_id) REFERENCES community_posts(id),
    -- Unique constraint (informational)
    CONSTRAINT uq_post_likes_user_post UNIQUE (user_id, post_id)
);

-- Post Comments Table
CREATE TABLE post_comments (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL,
    post_id VARCHAR NOT NULL,
    parent_id VARCHAR,
    content VARCHAR NOT NULL,
    created_at TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    -- Foreign keys (informational)
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (post_id) REFERENCES community_posts(id),
    FOREIGN KEY (parent_id) REFERENCES post_comments(id)
);

-- Solutions Table (Official Solutions)
CREATE TABLE solutions (
    id VARCHAR PRIMARY KEY,
    problem_id VARCHAR NOT NULL,
    created_by VARCHAR NOT NULL,
    title VARCHAR NOT NULL,
    content VARCHAR NOT NULL,
    sql_code VARCHAR NOT NULL,
    is_official BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    -- Foreign keys (informational)
    FOREIGN KEY (problem_id) REFERENCES problems(id),
    FOREIGN KEY (created_by) REFERENCES users(id)
);

-- Helpful Links Table
CREATE TABLE helpful_links (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL,
    title VARCHAR NOT NULL,
    url VARCHAR NOT NULL,
    created_at TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    -- Foreign key (informational)
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- ============================================================================
-- GAMIFICATION & ACHIEVEMENTS
-- ============================================================================

-- Badges Table
CREATE TABLE badges (
    id VARCHAR PRIMARY KEY,
    name VARCHAR UNIQUE NOT NULL,
    description VARCHAR NOT NULL,
    icon_url VARCHAR,
    criteria VARIANT NOT NULL,
    points_reward INTEGER DEFAULT 0,
    rarity VARCHAR DEFAULT 'common',
    created_at TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    -- Constraint for rarity values (informational)
    CONSTRAINT chk_badge_rarity CHECK (rarity IN ('common', 'rare', 'epic', 'legendary'))
);

-- User Badges Table (Junction Table)
CREATE TABLE user_badges (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL,
    badge_id VARCHAR NOT NULL,
    earned_at TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    -- Foreign keys (informational)
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (badge_id) REFERENCES badges(id),
    -- Unique constraint (informational)
    CONSTRAINT uq_user_badges_user_badge UNIQUE (user_id, badge_id)
);

-- ============================================================================
-- USER INTERACTIONS & TRACKING
-- ============================================================================

-- Problem Interactions Table (Bookmarks, Upvotes, Downvotes)
CREATE TABLE problem_interactions (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL,
    problem_id VARCHAR NOT NULL,
    bookmark BOOLEAN NOT NULL DEFAULT FALSE,
    upvote BOOLEAN NOT NULL DEFAULT FALSE,
    downvote BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    -- Foreign keys (informational)
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (problem_id) REFERENCES problems(id),
    -- Unique constraint (informational)
    CONSTRAINT uq_problem_interactions_user_problem UNIQUE (user_id, problem_id)
);

-- Problem Sessions Table (Engagement Tracking)
CREATE TABLE problem_sessions (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL,
    problem_id VARCHAR NOT NULL,
    first_query_at TIMESTAMP_NTZ,
    completed_at TIMESTAMP_NTZ,
    total_time_spent_seconds INTEGER,
    created_at TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP_NTZ NOT NULL DEFAULT CURRENT_TIMESTAMP(),
    -- Foreign keys (informational)
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (problem_id) REFERENCES problems(id)
);

-- ============================================================================
-- SAMPLE DATA INITIALIZATION (Optional)
-- ============================================================================

-- Sample Topics
-- Note: Snowflake doesn't support ON CONFLICT, use MERGE or conditional insert
INSERT INTO topics (id, name, description, difficulty_level, order_index)
SELECT * FROM VALUES
    ('topic-1', 'Joins and Relationships', 'Master INNER, LEFT, RIGHT, and FULL joins', 'EASY', 1),
    ('topic-2', 'Aggregate Functions', 'COUNT, SUM, AVG, MIN, MAX and GROUP BY clauses', 'MEDIUM', 2),
    ('topic-3', 'Subqueries and CTEs', 'Complex nested queries and Common Table Expressions', 'HARD', 3)
AS t(id, name, description, difficulty_level, order_index)
WHERE NOT EXISTS (SELECT 1 FROM topics WHERE topics.id = t.id);

-- Sample Badges
INSERT INTO badges (id, name, description, criteria, points_reward, rarity)
SELECT * FROM VALUES
    ('badge-1', 'First Steps', 'Complete your first SQL query', PARSE_JSON('{"first_successful_submission": true}'), 10, 'common'),
    ('badge-2', 'Problem Solver', 'Solve 10 problems', PARSE_JSON('{"problems_solved": 10}'), 50, 'common'),
    ('badge-3', 'Speed Demon', 'Execute a query in under 100ms', PARSE_JSON('{"execution_time_ms": {"<": 100}}'), 25, 'rare'),
    ('badge-4', 'Master', 'Solve 5 Hard level problems', PARSE_JSON('{"hard_problems_solved": 5}'), 200, 'legendary')
AS b(id, name, description, criteria, points_reward, rarity)
WHERE NOT EXISTS (SELECT 1 FROM badges WHERE badges.id = b.id);

-- ============================================================================
-- SNOWFLAKE-SPECIFIC OPTIMIZATIONS
-- ============================================================================

-- Create clustering keys for better query performance
ALTER TABLE submissions CLUSTER BY (user_id, submitted_at);
ALTER TABLE problems CLUSTER BY (difficulty, created_at);
ALTER TABLE execution_results CLUSTER BY (submission_id);
ALTER TABLE community_posts CLUSTER BY (user_id, created_at);

-- Enable automatic clustering
ALTER TABLE submissions RESUME RECLUSTER;
ALTER TABLE problems RESUME RECLUSTER;
ALTER TABLE execution_results RESUME RECLUSTER;
ALTER TABLE community_posts RESUME RECLUSTER;

-- ============================================================================
-- NOTES - SNOWFLAKE SPECIFIC
-- ============================================================================
-- 1. All IDs are VARCHAR (no length limit in Snowflake)
-- 2. VARIANT type is used for semi-structured data (equivalent to JSON/JSONB)
-- 3. TIMESTAMP_NTZ (without timezone) is used for all timestamps
-- 4. Foreign keys and unique constraints are INFORMATIONAL ONLY - not enforced
-- 5. Application logic must handle referential integrity and uniqueness
-- 6. CHECK constraints are also informational and not enforced
-- 7. CURRENT_TIMESTAMP() is used instead of NOW()
-- 8. Clustering keys are recommended for frequently queried columns
-- 9. No indexes needed - Snowflake uses micro-partitions and clustering
-- 10. Use MERGE statements instead of INSERT...ON CONFLICT for upserts
-- ============================================================================

-- ============================================================================
-- ADDITIONAL SNOWFLAKE RECOMMENDATIONS
-- ============================================================================
-- 1. Use TIME_TRAVEL for point-in-time queries: 
--    SELECT * FROM users AT(TIMESTAMP => '2024-01-01 00:00:00'::timestamp);
-- 
-- 2. Use STREAMS for CDC (Change Data Capture):
--    CREATE STREAM users_stream ON TABLE users;
--
-- 3. Use TASKS for scheduled data processing:
--    CREATE TASK process_submissions
--    WAREHOUSE = compute_wh
-- SCHEDULE = 'USING CRON 0 * * * * UTC'
--    AS ...;
--
-- 4. Enable SEARCH OPTIMIZATION for text columns:
--    ALTER TABLE problems ADD SEARCH OPTIMIZATION ON EQUALITY(title, company);
--
-- 5. Use MATERIALIZED VIEWS for aggregated data:
--    CREATE MATERIALIZED VIEW user_stats AS
--    SELECT user_id, COUNT(*) as total_submissions
--    FROM submissions GROUP BY user_id;
-- ============================================================================
