-- ============================================================================
-- SQL Learning Platform - Complete Database Schema for Neon PostgreSQL
-- ============================================================================
-- This file contains the complete data model for the SQL learning platform
-- including all tables, enums, constraints, indexes, and relationships
-- ============================================================================

-- ============================================================================
-- ENUMS
-- ============================================================================

CREATE TYPE difficultylevel AS ENUM ('BEGINNER', 'EASY', 'MEDIUM', 'HARD', 'EXPERT');
CREATE TYPE execution_status AS ENUM ('SUCCESS', 'ERROR', 'TIMEOUT', 'MEMORY_LIMIT');
CREATE TYPE sandbox_status AS ENUM ('ACTIVE', 'EXPIRED', 'CLEANUP_PENDING');

-- ============================================================================
-- CORE TABLES
-- ============================================================================

-- Users Table
CREATE TABLE users (
    id VARCHAR PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash TEXT,
    first_name VARCHAR(50),
    last_name VARCHAR(50),
    company_name VARCHAR(100),
    linkedin_url TEXT,
    profile_image_url TEXT,
    google_id VARCHAR(255) UNIQUE,
    auth_provider VARCHAR(20) NOT NULL DEFAULT 'email',
    problems_solved INTEGER NOT NULL DEFAULT 0,
    premium BOOLEAN NOT NULL DEFAULT FALSE,
    is_admin BOOLEAN NOT NULL DEFAULT FALSE,
    email_verified BOOLEAN NOT NULL DEFAULT FALSE,
    verification_token VARCHAR(255),
    verification_token_expires TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Followers Table (User Relationships)
CREATE TABLE followers (
    id VARCHAR PRIMARY KEY,
    follower_id VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    following_id VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_follower_following UNIQUE (follower_id, following_id)
);

CREATE INDEX idx_followers_follower_id ON followers(follower_id);
CREATE INDEX idx_followers_following_id ON followers(following_id);

-- Cache Entries Table (PostgreSQL fallback cache)
CREATE TABLE cache_entries (
    id VARCHAR PRIMARY KEY,
    cache_key VARCHAR(500) NOT NULL,
    namespace VARCHAR(100) NOT NULL DEFAULT 'result',
    data JSONB NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_cache_key_namespace UNIQUE (cache_key, namespace)
);

CREATE INDEX idx_cache_key_namespace ON cache_entries(cache_key, namespace);
CREATE INDEX idx_cache_expires_at ON cache_entries(expires_at);

-- Fallback Submissions Table (PostgreSQL fallback queue)
CREATE TABLE fallback_submissions (
    id VARCHAR PRIMARY KEY,
    job_id VARCHAR(100) UNIQUE NOT NULL,
    data JSONB NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    processed_at TIMESTAMP
);

CREATE INDEX idx_fallback_status ON fallback_submissions(status);
CREATE INDEX idx_fallback_created_at ON fallback_submissions(created_at);

-- Topics Table (SQL Concepts Organization)
CREATE TABLE topics (
    id VARCHAR PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    difficulty_level difficultylevel NOT NULL,
    order_index INTEGER DEFAULT 0,
    parent_topic_id VARCHAR REFERENCES topics(id) ON DELETE SET NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Problems Table
CREATE TABLE problems (
    id VARCHAR PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    difficulty VARCHAR(20) NOT NULL,
    tags JSON NOT NULL DEFAULT '[]',
    company VARCHAR(100),
    hints JSON NOT NULL DEFAULT '[]',
    question JSONB NOT NULL,
    s3_data_source JSONB,
    s3_datasets JSONB,
    premium BOOLEAN DEFAULT NULL,
    master_solution JSONB,
    expected_display JSONB,
    expected_hash VARCHAR,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    topic_id VARCHAR REFERENCES topics(id) ON DELETE SET NULL
);

CREATE INDEX idx_problems_difficulty ON problems(difficulty);
CREATE INDEX idx_problems_company ON problems(company);
CREATE INDEX idx_problems_topic_id ON problems(topic_id);
CREATE INDEX idx_problems_created_at ON problems(created_at);

-- Test Cases Table
CREATE TABLE test_cases (
    id VARCHAR PRIMARY KEY,
    problem_id VARCHAR NOT NULL REFERENCES problems(id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    input_data JSONB NOT NULL,
    expected_output JSONB NOT NULL,
    validation_rules JSONB DEFAULT '{}',
    is_hidden BOOLEAN DEFAULT FALSE,
    order_index INTEGER DEFAULT 0,
    timeout_seconds INTEGER DEFAULT 30,
    memory_limit_mb INTEGER DEFAULT 256,
    expected_output_source JSONB,
    preview_expected_output JSONB,
    display_limit INTEGER DEFAULT 10,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_test_cases_problem_name UNIQUE (problem_id, name)
);

-- Submissions Table
CREATE TABLE submissions (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    problem_id VARCHAR NOT NULL REFERENCES problems(id) ON DELETE CASCADE,
    query TEXT NOT NULL,
    is_correct BOOLEAN NOT NULL,
    execution_time INTEGER,
    submitted_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_submissions_user_id ON submissions(user_id);
CREATE INDEX idx_submissions_problem_id ON submissions(problem_id);
CREATE INDEX idx_submissions_submitted_at ON submissions(submitted_at);
CREATE INDEX idx_submissions_is_correct ON submissions(is_correct);

-- Execution Results Table
CREATE TABLE execution_results (
    id VARCHAR PRIMARY KEY,
    submission_id VARCHAR NOT NULL REFERENCES submissions(id) ON DELETE CASCADE,
    test_case_id VARCHAR NOT NULL REFERENCES test_cases(id) ON DELETE CASCADE,
    status execution_status NOT NULL,
    execution_time_ms INTEGER,
    memory_used_mb FLOAT,
    rows_affected INTEGER,
    query_result JSONB,
    error_message TEXT,
    is_correct BOOLEAN NOT NULL,
    validation_details JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- COMMUNITY & SOCIAL FEATURES
-- ============================================================================

-- Community Posts Table
CREATE TABLE community_posts (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    problem_id VARCHAR REFERENCES problems(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    code_snippet TEXT,
    likes INTEGER NOT NULL DEFAULT 0,
    comments INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Post Likes Table
CREATE TABLE post_likes (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    post_id VARCHAR NOT NULL REFERENCES community_posts(id) ON DELETE CASCADE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_post_likes_user_post UNIQUE (user_id, post_id)
);

-- Post Comments Table
CREATE TABLE post_comments (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    post_id VARCHAR NOT NULL REFERENCES community_posts(id) ON DELETE CASCADE,
    parent_id VARCHAR REFERENCES post_comments(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Solutions Table (Official Solutions)
CREATE TABLE solutions (
    id VARCHAR PRIMARY KEY,
    problem_id VARCHAR NOT NULL REFERENCES problems(id) ON DELETE CASCADE,
    created_by VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    sql_code TEXT NOT NULL,
    is_official BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_solutions_problem_id ON solutions(problem_id);
CREATE INDEX idx_solutions_created_by ON solutions(created_by);
CREATE INDEX idx_solutions_created_at ON solutions(created_at);

-- Helpful Links Table
CREATE TABLE helpful_links (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    url TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_helpful_links_created_at ON helpful_links(created_at);
CREATE INDEX idx_helpful_links_user_id ON helpful_links(user_id);

-- ============================================================================
-- GAMIFICATION & ACHIEVEMENTS
-- ============================================================================

-- Badges Table
CREATE TABLE badges (
    id VARCHAR PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT NOT NULL,
    icon_url TEXT,
    criteria JSONB NOT NULL,
    points_reward INTEGER DEFAULT 0,
    rarity VARCHAR(20) DEFAULT 'common',
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- User Badges Table (Junction Table)
CREATE TABLE user_badges (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    badge_id VARCHAR NOT NULL REFERENCES badges(id) ON DELETE CASCADE,
    earned_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_user_badges_user_badge UNIQUE (user_id, badge_id)
);

-- ============================================================================
-- USER INTERACTIONS & TRACKING
-- ============================================================================

-- Problem Interactions Table (Bookmarks, Upvotes, Downvotes)
CREATE TABLE problem_interactions (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    problem_id VARCHAR NOT NULL REFERENCES problems(id) ON DELETE CASCADE,
    bookmark BOOLEAN NOT NULL DEFAULT FALSE,
    upvote BOOLEAN NOT NULL DEFAULT FALSE,
    downvote BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_problem_interactions_user_problem UNIQUE (user_id, problem_id)
);

-- Problem Sessions Table (Engagement Tracking)
CREATE TABLE problem_sessions (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    problem_id VARCHAR NOT NULL REFERENCES problems(id) ON DELETE CASCADE,
    first_query_at TIMESTAMP,
    completed_at TIMESTAMP,
    total_time_spent_seconds INTEGER,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_problem_sessions_user_problem ON problem_sessions(user_id, problem_id);
CREATE INDEX idx_problem_sessions_completed_at ON problem_sessions(completed_at);

-- ============================================================================
-- SAMPLE DATA INITIALIZATION (Optional)
-- ============================================================================

-- Sample Topics
INSERT INTO topics (id, name, description, difficulty_level, order_index) VALUES
    ('topic-1', 'Joins and Relationships', 'Master INNER, LEFT, RIGHT, and FULL joins', 'EASY', 1),
    ('topic-2', 'Aggregate Functions', 'COUNT, SUM, AVG, MIN, MAX and GROUP BY clauses', 'MEDIUM', 2),
    ('topic-3', 'Subqueries and CTEs', 'Complex nested queries and Common Table Expressions', 'HARD', 3)
ON CONFLICT (id) DO NOTHING;

-- Sample Badges
INSERT INTO badges (id, name, description, criteria, points_reward, rarity) VALUES
    ('badge-1', 'First Steps', 'Complete your first SQL query', '{"first_successful_submission": true}', 10, 'common'),
    ('badge-2', 'Problem Solver', 'Solve 10 problems', '{"problems_solved": 10}', 50, 'common'),
    ('badge-3', 'Speed Demon', 'Execute a query in under 100ms', '{"execution_time_ms": {"<": 100}}', 25, 'rare'),
    ('badge-4', 'Master', 'Solve 5 Hard level problems', '{"hard_problems_solved": 5}', 200, 'legendary')
ON CONFLICT (id) DO NOTHING;

-- ============================================================================
-- NOTES
-- ============================================================================
-- 1. All IDs are VARCHAR to support UUID strings
-- 2. JSONB is used for flexible data structures (questions, test cases, etc.)
-- 3. Indexes are created on commonly queried columns for performance
-- 4. Foreign keys include ON DELETE CASCADE for proper cleanup
-- 5. Unique constraints prevent duplicate entries where needed
-- 6. Default values are set for timestamps and boolean fields
-- ============================================================================
