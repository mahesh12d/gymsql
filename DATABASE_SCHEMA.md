# SQLGym Database Schema Documentation

> Complete PostgreSQL database structure for SQLGym - A gamified SQL learning platform
> 
> **Version:** 1.0
> **Database Type:** PostgreSQL 14+
> **Generated:** October 2025

---

## Table of Contents

1. [Overview](#overview)
2. [Custom ENUM Types](#custom-enum-types)
3. [Tables](#tables)
4. [Indexes](#indexes)
5. [Complete SQL DDL](#complete-sql-ddl)

---

## Overview

SQLGym uses a PostgreSQL database with 22 tables organized into the following functional areas:

- **User Management** (3 tables): `users`, `followers`, `helpful_links`
- **Learning Content** (4 tables): `problems`, `topics`, `test_cases`, `problem_schemas`
- **User Progress** (5 tables): `submissions`, `problem_submissions`, `problem_sessions`, `execution_results`, `user_progress`
- **Gamification** (2 tables): `badges`, `user_badges`
- **Community** (4 tables): `community_posts`, `post_likes`, `post_comments`, `problem_interactions`
- **System** (3 tables): `cache_entries`, `fallback_submissions`, `solutions`

**Total Tables:** 22
**Total Indexes:** 56+
**Foreign Key Relationships:** 25+

---

## Custom ENUM Types

PostgreSQL custom ENUM types used across the schema:

### 1. `difficultylevel`
```sql
CREATE TYPE difficultylevel AS ENUM ('BEGINNER', 'EASY', 'MEDIUM', 'HARD', 'EXPERT');
```

### 2. `execution_status`
```sql
CREATE TYPE execution_status AS ENUM ('SUCCESS', 'ERROR', 'TIMEOUT', 'MEMORY_LIMIT');
```

### 3. `sandbox_status`
```sql
CREATE TYPE sandbox_status AS ENUM ('ACTIVE', 'EXPIRED', 'CLEANUP_PENDING');
```

---

## Tables

### 1. users
**Purpose:** Core user accounts and authentication

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | VARCHAR | PRIMARY KEY | Unique user identifier (UUID) |
| username | VARCHAR(50) | UNIQUE, NOT NULL | Unique username |
| email | VARCHAR(255) | UNIQUE, NOT NULL | User email address |
| password_hash | TEXT | NULL | Bcrypt hashed password (null for OAuth users) |
| first_name | VARCHAR(50) | NULL | User's first name |
| last_name | VARCHAR(50) | NULL | User's last name |
| company_name | VARCHAR(100) | NULL | User's company/organization |
| linkedin_url | TEXT | NULL | LinkedIn profile URL |
| profile_image_url | TEXT | NULL | Profile picture URL (S3 or OAuth) |
| google_id | VARCHAR(255) | UNIQUE, NULL | Google OAuth ID |
| auth_provider | VARCHAR(20) | NOT NULL, DEFAULT 'email' | Authentication method (email, google, github) |
| problems_solved | INTEGER | NOT NULL, DEFAULT 0 | Total problems solved count |
| premium | BOOLEAN | NOT NULL, DEFAULT false | Premium subscription status |
| is_admin | BOOLEAN | NOT NULL, DEFAULT false | Admin access flag |
| email_verified | BOOLEAN | NOT NULL, DEFAULT false | Email verification status |
| verification_token | VARCHAR(255) | NULL | Email verification token |
| verification_token_expires | TIMESTAMP | NULL | Token expiration timestamp |
| created_at | TIMESTAMP | NOT NULL, DEFAULT now() | Account creation timestamp |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT now() | Last update timestamp |

**Indexes:**
- `users_pkey` (PRIMARY KEY on `id`)
- `users_username_key` (UNIQUE on `username`)
- `users_email_key` (UNIQUE on `email`)

---

### 2. followers
**Purpose:** User follower relationships (social graph)

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | VARCHAR | PRIMARY KEY | Relationship ID (UUID) |
| follower_id | VARCHAR | FOREIGN KEY (users.id), NOT NULL | User who is following |
| following_id | VARCHAR | FOREIGN KEY (users.id), NOT NULL | User being followed |
| created_at | TIMESTAMP | NOT NULL, DEFAULT now() | Follow timestamp |

**Constraints:**
- `UNIQUE (follower_id, following_id)` - Prevent duplicate follows
- `ON DELETE CASCADE` on both foreign keys

**Indexes:**
- `followers_pkey` (PRIMARY KEY on `id`)
- `idx_followers_follower_id` (on `follower_id`)
- `idx_followers_following_id` (on `following_id`)
- `uq_follower_following` (UNIQUE on `follower_id, following_id`)

---

### 3. helpful_links
**Purpose:** User-shared educational resources

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | VARCHAR | PRIMARY KEY | Link ID (UUID) |
| user_id | VARCHAR | FOREIGN KEY (users.id), NOT NULL | User who shared the link |
| title | VARCHAR(200) | NOT NULL | Link title/description |
| url | TEXT | NOT NULL | Resource URL |
| created_at | TIMESTAMP | NOT NULL, DEFAULT now() | Share timestamp |

**Indexes:**
- `helpful_links_pkey` (PRIMARY KEY on `id`)
- `idx_helpful_links_user_id` (on `user_id`)
- `idx_helpful_links_created_at` (on `created_at`)

---

### 4. topics
**Purpose:** SQL topic/category hierarchy

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | VARCHAR | PRIMARY KEY | Topic ID (UUID) |
| name | VARCHAR(100) | UNIQUE, NOT NULL | Topic name (e.g., "JOINs") |
| description | TEXT | NULL | Topic description |
| difficulty_level | difficultylevel | NOT NULL | Difficulty tier |
| order_index | INTEGER | NULL | Display order |
| parent_topic_id | VARCHAR | FOREIGN KEY (topics.id), NULL | Parent topic for hierarchy |
| created_at | TIMESTAMP | NOT NULL, DEFAULT now() | Creation timestamp |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT now() | Update timestamp |

**Indexes:**
- `topics_pkey` (PRIMARY KEY on `id`)
- `topics_name_key` (UNIQUE on `name`)

---

### 5. problems
**Purpose:** SQL coding problems/challenges

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | VARCHAR | PRIMARY KEY | Problem ID (UUID) |
| title | VARCHAR(200) | NOT NULL | Problem title |
| question | JSONB | NOT NULL | Problem description and requirements |
| difficulty | VARCHAR(20) | NOT NULL, DEFAULT 'Medium' | Difficulty level |
| tags | JSON | NOT NULL | Category tags (array) |
| hints | JSON | NOT NULL | Hint text array |
| company | VARCHAR(100) | NULL | Associated company (e.g., "Netflix") |
| topic_id | VARCHAR | FOREIGN KEY (topics.id), NULL | Related topic |
| premium | BOOLEAN | NULL | Premium-only flag |
| s3_data_source | JSONB | NULL | S3 dataset configuration |
| master_solution | JSONB | NULL | Official solution query |
| expected_display | JSONB | NULL | Expected output format |
| s3_datasets | JSONB | NULL | Multiple S3 dataset configs |
| expected_hash | VARCHAR(255) | NULL | Result hash for validation |
| created_at | TIMESTAMP | NOT NULL, DEFAULT now() | Creation timestamp |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT now() | Update timestamp |

**Indexes:**
- `problems_pkey` (PRIMARY KEY on `id`)
- `idx_problems_difficulty` (on `difficulty`)
- `idx_problems_company` (on `company`)
- `idx_problems_topic_id` (on `topic_id`)
- `idx_problems_created_at` (on `created_at`)

---

### 6. problem_schemas
**Purpose:** Database schemas for problem sandboxes

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | VARCHAR | PRIMARY KEY | Schema ID (UUID) |
| problem_id | VARCHAR | FOREIGN KEY (problems.id), NOT NULL | Associated problem |
| table_name | VARCHAR(100) | NOT NULL | Table name in sandbox |
| schema_definition | JSONB | NOT NULL | Column definitions |
| sample_data | JSONB | NULL | Sample rows for table |
| indexes | JSON | NULL | Index definitions |
| constraints | JSON | NULL | Constraint definitions |
| created_at | TIMESTAMP | NOT NULL, DEFAULT now() | Creation timestamp |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT now() | Update timestamp |

**Constraints:**
- `UNIQUE (problem_id, table_name)` - One schema per table per problem

**Indexes:**
- `problem_schemas_pkey` (PRIMARY KEY on `id`)
- `uq_problem_schemas_problem_table` (UNIQUE on `problem_id, table_name`)

---

### 7. test_cases
**Purpose:** Test cases for problem validation

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | VARCHAR | PRIMARY KEY | Test case ID (UUID) |
| problem_id | VARCHAR | FOREIGN KEY (problems.id), NOT NULL | Associated problem |
| name | VARCHAR(200) | NOT NULL | Test case name |
| description | TEXT | NULL | Test case description |
| input_data | JSONB | NOT NULL | Input dataset |
| expected_output | JSONB | NOT NULL | Expected query result |
| expected_output_source | JSONB | NULL | S3 source for expected output |
| preview_expected_output | JSONB | NULL | Preview subset of output |
| validation_rules | JSONB | NULL | Custom validation logic |
| is_hidden | BOOLEAN | NULL | Hidden test case flag |
| order_index | INTEGER | NULL | Display order |
| timeout_seconds | INTEGER | NULL | Execution timeout |
| memory_limit_mb | INTEGER | NULL | Memory limit |
| display_limit | INTEGER | NULL, DEFAULT 10 | Result preview row limit |
| created_at | TIMESTAMP | NOT NULL, DEFAULT now() | Creation timestamp |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT now() | Update timestamp |

**Constraints:**
- `UNIQUE (problem_id, name)` - Unique test case names per problem

**Indexes:**
- `test_cases_pkey` (PRIMARY KEY on `id`)
- `uq_test_cases_problem_name` (UNIQUE on `problem_id, name`)

---

### 8. submissions
**Purpose:** User SQL query submissions (main submission log)

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | VARCHAR | PRIMARY KEY | Submission ID (UUID) |
| user_id | VARCHAR | FOREIGN KEY (users.id), NOT NULL | Submitting user |
| problem_id | VARCHAR | FOREIGN KEY (problems.id), NOT NULL | Problem attempted |
| query | TEXT | NOT NULL | SQL query submitted |
| is_correct | BOOLEAN | NOT NULL | Pass/fail result |
| execution_time | INTEGER | NULL | Execution time (ms) |
| submitted_at | TIMESTAMP | NOT NULL, DEFAULT now() | Submission timestamp |

**Indexes:**
- `submissions_pkey` (PRIMARY KEY on `id`)
- `idx_submissions_user_id` (on `user_id`)
- `idx_submissions_problem_id` (on `problem_id`)
- `idx_submissions_is_correct` (on `is_correct`)
- `idx_submissions_submitted_at` (on `submitted_at`)

---

### 9. problem_submissions
**Purpose:** Detailed submission tracking with async job processing

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | VARCHAR | PRIMARY KEY | Submission ID (UUID) |
| user_id | VARCHAR | FOREIGN KEY (users.id), NOT NULL | Submitting user |
| problem_id | VARCHAR | FOREIGN KEY (problems.id), NOT NULL | Problem attempted |
| sql_query | TEXT | NOT NULL | SQL query submitted |
| status | VARCHAR(20) | NOT NULL | Processing status (pending/completed/failed) |
| rows_returned | INTEGER | NULL | Number of result rows |
| execution_time_ms | INTEGER | NULL | Execution time (ms) |
| error_message | TEXT | NULL | Error message if failed |
| result_data | JSONB | NULL | Query result data |
| created_at | TIMESTAMP | NOT NULL, DEFAULT now() | Submission timestamp |
| completed_at | TIMESTAMP | NULL | Completion timestamp |

**Indexes:**
- `problem_submissions_pkey` (PRIMARY KEY on `id`)
- `idx_problem_submissions_user_id` (on `user_id`)
- `idx_problem_submissions_problem_id` (on `problem_id`)
- `idx_problem_submissions_status` (on `status`)
- `idx_problem_submissions_created_at` (on `created_at`)
- `idx_problem_submissions_completed_at` (on `completed_at`)

---

### 10. problem_sessions
**Purpose:** Track time spent on each problem

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | VARCHAR | PRIMARY KEY, DEFAULT gen_random_uuid() | Session ID (UUID) |
| user_id | VARCHAR | FOREIGN KEY (users.id), NOT NULL | User session |
| problem_id | VARCHAR | FOREIGN KEY (problems.id), NOT NULL | Problem being worked on |
| first_query_at | TIMESTAMPTZ | NULL | First submission timestamp |
| completed_at | TIMESTAMPTZ | NULL | Completion timestamp |
| total_time_spent_seconds | INTEGER | NULL | Total time spent (seconds) |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Session start |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Last activity |

**Indexes:**
- `problem_sessions_pkey` (PRIMARY KEY on `id`)
- `idx_problem_sessions_user_problem` (on `user_id, problem_id`)
- `idx_problem_sessions_completed_at` (on `completed_at`)

---

### 11. execution_results
**Purpose:** Detailed execution results per test case

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | VARCHAR | PRIMARY KEY | Result ID (UUID) |
| submission_id | VARCHAR | FOREIGN KEY (submissions.id), NOT NULL | Associated submission |
| test_case_id | VARCHAR | FOREIGN KEY (test_cases.id), NOT NULL | Test case executed |
| status | execution_status | NOT NULL | Execution status |
| execution_time_ms | INTEGER | NULL | Execution time (ms) |
| memory_used_mb | FLOAT | NULL | Memory consumed (MB) |
| rows_affected | INTEGER | NULL | Number of rows affected |
| query_result | JSONB | NULL | Query output data |
| error_message | TEXT | NULL | Error message if failed |
| is_correct | BOOLEAN | NOT NULL | Pass/fail for this test case |
| validation_details | JSONB | NULL | Detailed validation info |
| created_at | TIMESTAMP | NOT NULL, DEFAULT now() | Result timestamp |

**Indexes:**
- `execution_results_pkey` (PRIMARY KEY on `id`)

---

### 12. user_progress
**Purpose:** Aggregate user statistics per topic

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | VARCHAR | PRIMARY KEY | Progress record ID (UUID) |
| user_id | VARCHAR | FOREIGN KEY (users.id), NOT NULL | User |
| topic_id | VARCHAR | FOREIGN KEY (topics.id), NOT NULL | Topic being tracked |
| problems_attempted | INTEGER | NULL | Total attempts |
| problems_solved | INTEGER | NULL | Total solved |
| total_submissions | INTEGER | NULL | Total submissions |
| successful_submissions | INTEGER | NULL | Successful submissions |
| average_execution_time_ms | FLOAT | NULL | Average execution time |
| best_execution_time_ms | FLOAT | NULL | Best execution time |
| total_time_spent_minutes | INTEGER | NULL | Total time spent |
| current_difficulty | difficultylevel | NULL | Current difficulty level |
| highest_difficulty_solved | difficultylevel | NULL | Highest difficulty completed |
| hint_usage_count | INTEGER | NULL | Number of hints used |
| average_attempts_per_problem | FLOAT | NULL | Average attempts per problem |
| streak_count | INTEGER | NULL | Current streak |
| max_streak_count | INTEGER | NULL | Best streak |
| experience_points | INTEGER | NULL | XP earned |
| first_attempt_at | TIMESTAMP | NULL | First attempt timestamp |
| last_activity_at | TIMESTAMP | NULL | Last activity timestamp |
| created_at | TIMESTAMP | NOT NULL, DEFAULT now() | Record creation |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT now() | Last update |

**Constraints:**
- `UNIQUE (user_id, topic_id)` - One progress record per user per topic

**Indexes:**
- `user_progress_pkey` (PRIMARY KEY on `id`)
- `uq_user_progress_user_topic` (UNIQUE on `user_id, topic_id`)

---

### 13. badges
**Purpose:** Achievement badge definitions

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | VARCHAR | PRIMARY KEY | Badge ID (UUID) |
| name | VARCHAR(100) | UNIQUE, NOT NULL | Badge name |
| description | TEXT | NOT NULL | Badge description |
| icon_url | TEXT | NULL | Badge icon URL |
| criteria | JSONB | NOT NULL | Earning criteria logic |
| points_reward | INTEGER | NULL | XP reward for earning |
| rarity | VARCHAR(20) | NULL | Rarity tier (common/rare/epic/legendary) |
| created_at | TIMESTAMP | NOT NULL, DEFAULT now() | Badge creation timestamp |

**Indexes:**
- `badges_pkey` (PRIMARY KEY on `id`)
- `badges_name_key` (UNIQUE on `name`)

---

### 14. user_badges
**Purpose:** User badge inventory

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | VARCHAR | PRIMARY KEY | Record ID (UUID) |
| user_id | VARCHAR | FOREIGN KEY (users.id), NOT NULL | User who earned badge |
| badge_id | VARCHAR | FOREIGN KEY (badges.id), NOT NULL | Badge earned |
| earned_at | TIMESTAMP | NOT NULL, DEFAULT now() | Earn timestamp |

**Constraints:**
- `UNIQUE (user_id, badge_id)` - One badge instance per user

**Indexes:**
- `user_badges_pkey` (PRIMARY KEY on `id`)
- `uq_user_badges_user_badge` (UNIQUE on `user_id, badge_id`)

---

### 15. community_posts
**Purpose:** User-generated community posts

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | VARCHAR | PRIMARY KEY | Post ID (UUID) |
| user_id | VARCHAR | FOREIGN KEY (users.id), NOT NULL | Post author |
| problem_id | VARCHAR | FOREIGN KEY (problems.id), NULL | Related problem (optional) |
| content | TEXT | NOT NULL | Post content (Markdown) |
| code_snippet | TEXT | NULL | Code snippet (syntax highlighted) |
| likes | INTEGER | NOT NULL, DEFAULT 0 | Like count |
| comments | INTEGER | NOT NULL, DEFAULT 0 | Comment count |
| created_at | TIMESTAMP | NOT NULL, DEFAULT now() | Post timestamp |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT now() | Last edit timestamp |

**Indexes:**
- `community_posts_pkey` (PRIMARY KEY on `id`)

---

### 16. post_likes
**Purpose:** User likes on community posts

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | VARCHAR | PRIMARY KEY | Like ID (UUID) |
| user_id | VARCHAR | FOREIGN KEY (users.id), NOT NULL | User who liked |
| post_id | VARCHAR | FOREIGN KEY (community_posts.id), NOT NULL | Post being liked |
| created_at | TIMESTAMP | NOT NULL, DEFAULT now() | Like timestamp |

**Constraints:**
- `UNIQUE (user_id, post_id)` - One like per user per post

**Indexes:**
- `post_likes_pkey` (PRIMARY KEY on `id`)
- `uq_post_likes_user_post` (UNIQUE on `user_id, post_id`)

---

### 17. post_comments
**Purpose:** Comments on community posts

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | VARCHAR | PRIMARY KEY | Comment ID (UUID) |
| user_id | VARCHAR | FOREIGN KEY (users.id), NOT NULL | Comment author |
| post_id | VARCHAR | FOREIGN KEY (community_posts.id), NOT NULL | Post being commented on |
| parent_id | VARCHAR | FOREIGN KEY (post_comments.id), NULL | Parent comment for threading |
| content | TEXT | NOT NULL | Comment content |
| created_at | TIMESTAMP | NOT NULL, DEFAULT now() | Comment timestamp |

**Indexes:**
- `post_comments_pkey` (PRIMARY KEY on `id`)

---

### 18. problem_interactions
**Purpose:** User bookmarks and votes on problems

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | VARCHAR | PRIMARY KEY | Interaction ID (UUID) |
| user_id | VARCHAR | FOREIGN KEY (users.id), NOT NULL | User |
| problem_id | VARCHAR | FOREIGN KEY (problems.id), NOT NULL | Problem |
| bookmark | BOOLEAN | NOT NULL, DEFAULT false | Bookmarked flag |
| upvote | BOOLEAN | NOT NULL, DEFAULT false | Upvote flag |
| downvote | BOOLEAN | NOT NULL, DEFAULT false | Downvote flag |
| created_at | TIMESTAMP | NOT NULL, DEFAULT now() | Interaction timestamp |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT now() | Last update |

**Constraints:**
- `UNIQUE (user_id, problem_id)` - One interaction record per user per problem

**Indexes:**
- `problem_interactions_pkey` (PRIMARY KEY on `id`)
- `uq_problem_interactions_user_problem` (UNIQUE on `user_id, problem_id`)

---

### 19. solutions
**Purpose:** User-submitted and official solutions

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | VARCHAR | PRIMARY KEY | Solution ID (UUID) |
| problem_id | VARCHAR | FOREIGN KEY (problems.id), NOT NULL | Associated problem |
| created_by | VARCHAR | FOREIGN KEY (users.id), NOT NULL | Solution author |
| title | VARCHAR(200) | NOT NULL | Solution title |
| content | TEXT | NOT NULL | Explanation (Markdown) |
| sql_code | TEXT | NOT NULL | SQL code |
| is_official | BOOLEAN | NOT NULL, DEFAULT false | Official solution flag |
| created_at | TIMESTAMP | NOT NULL, DEFAULT now() | Creation timestamp |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT now() | Update timestamp |

**Indexes:**
- `solutions_pkey` (PRIMARY KEY on `id`)
- `idx_solutions_problem_id` (on `problem_id`)
- `idx_solutions_created_by` (on `created_by`)
- `idx_solutions_created_at` (on `created_at`)

---

### 20. cache_entries
**Purpose:** PostgreSQL fallback cache when Redis is unavailable

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | VARCHAR | PRIMARY KEY | Cache entry ID (UUID) |
| cache_key | VARCHAR(500) | NOT NULL | Cache key |
| namespace | VARCHAR(100) | NOT NULL | Cache namespace |
| data | JSONB | NOT NULL | Cached data (JSON) |
| expires_at | TIMESTAMP | NOT NULL | Expiration timestamp |
| created_at | TIMESTAMP | NOT NULL, DEFAULT now() | Creation timestamp |

**Constraints:**
- `UNIQUE (cache_key, namespace)` - Unique key per namespace

**Indexes:**
- `cache_entries_pkey` (PRIMARY KEY on `id`)
- `uq_cache_key_namespace` (UNIQUE on `cache_key, namespace`)
- `idx_cache_key_namespace` (on `cache_key, namespace`)
- `idx_cache_expires_at` (on `expires_at`)

---

### 21. fallback_submissions
**Purpose:** Queue fallback for when Redis is unavailable

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | VARCHAR | PRIMARY KEY | Record ID (UUID) |
| job_id | VARCHAR(100) | UNIQUE, NOT NULL | Job identifier |
| data | JSONB | NOT NULL | Job payload |
| status | VARCHAR(20) | NOT NULL | Processing status |
| created_at | TIMESTAMP | NOT NULL, DEFAULT now() | Creation timestamp |
| processed_at | TIMESTAMP | NULL | Processing completion timestamp |

**Indexes:**
- `fallback_submissions_pkey` (PRIMARY KEY on `id`)
- `fallback_submissions_job_id_key` (UNIQUE on `job_id`)
- `idx_fallback_status` (on `status`)
- `idx_fallback_created_at` (on `created_at`)

---

## Indexes

### Performance Optimization Indexes

**High-Traffic Query Indexes:**
- User lookups: `users_username_key`, `users_email_key`
- Submission queries: `idx_submissions_user_id`, `idx_submissions_problem_id`, `idx_submissions_submitted_at`
- Problem filtering: `idx_problems_difficulty`, `idx_problems_company`, `idx_problems_topic_id`
- Social features: `idx_followers_follower_id`, `idx_followers_following_id`

**Composite Indexes:**
- `uq_follower_following` (follower_id, following_id)
- `uq_user_progress_user_topic` (user_id, topic_id)
- `idx_problem_sessions_user_problem` (user_id, problem_id)
- `idx_cache_key_namespace` (cache_key, namespace)

**Time-Based Indexes:**
- `idx_submissions_submitted_at` - Chronological submission queries
- `idx_problem_submissions_created_at` - Job processing queue
- `idx_helpful_links_created_at` - Resource timeline
- `idx_cache_expires_at` - Cache expiration cleanup

---

## Complete SQL DDL

### Step 1: Create ENUM Types

```sql
-- Create custom ENUM types
CREATE TYPE difficultylevel AS ENUM (
    'BEGINNER', 
    'EASY', 
    'MEDIUM', 
    'HARD', 
    'EXPERT'
);

CREATE TYPE execution_status AS ENUM (
    'SUCCESS', 
    'ERROR', 
    'TIMEOUT', 
    'MEMORY_LIMIT'
);

CREATE TYPE sandbox_status AS ENUM (
    'ACTIVE', 
    'EXPIRED', 
    'CLEANUP_PENDING'
);
```

### Step 2: Create Tables

```sql
-- =============================================
-- USER MANAGEMENT TABLES
-- =============================================

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
    premium BOOLEAN NOT NULL DEFAULT false,
    is_admin BOOLEAN NOT NULL DEFAULT false,
    email_verified BOOLEAN NOT NULL DEFAULT false,
    verification_token VARCHAR(255),
    verification_token_expires TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    updated_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE followers (
    id VARCHAR PRIMARY KEY,
    follower_id VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    following_id VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    UNIQUE (follower_id, following_id)
);

CREATE TABLE helpful_links (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    url TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT now()
);

-- =============================================
-- LEARNING CONTENT TABLES
-- =============================================

CREATE TABLE topics (
    id VARCHAR PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    difficulty_level difficultylevel NOT NULL,
    order_index INTEGER,
    parent_topic_id VARCHAR REFERENCES topics(id),
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    updated_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE problems (
    id VARCHAR PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    question JSONB NOT NULL,
    difficulty VARCHAR(20) NOT NULL DEFAULT 'Medium',
    tags JSON NOT NULL,
    hints JSON NOT NULL,
    company VARCHAR(100),
    topic_id VARCHAR REFERENCES topics(id),
    premium BOOLEAN,
    s3_data_source JSONB,
    master_solution JSONB,
    expected_display JSONB,
    s3_datasets JSONB,
    expected_hash VARCHAR(255),
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    updated_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE problem_schemas (
    id VARCHAR PRIMARY KEY,
    problem_id VARCHAR NOT NULL REFERENCES problems(id) ON DELETE CASCADE,
    table_name VARCHAR(100) NOT NULL,
    schema_definition JSONB NOT NULL,
    sample_data JSONB,
    indexes JSON,
    constraints JSON,
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    updated_at TIMESTAMP NOT NULL DEFAULT now(),
    UNIQUE (problem_id, table_name)
);

CREATE TABLE test_cases (
    id VARCHAR PRIMARY KEY,
    problem_id VARCHAR NOT NULL REFERENCES problems(id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    input_data JSONB NOT NULL,
    expected_output JSONB NOT NULL,
    expected_output_source JSONB,
    preview_expected_output JSONB,
    validation_rules JSONB,
    is_hidden BOOLEAN,
    order_index INTEGER,
    timeout_seconds INTEGER,
    memory_limit_mb INTEGER,
    display_limit INTEGER DEFAULT 10,
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    updated_at TIMESTAMP NOT NULL DEFAULT now(),
    UNIQUE (problem_id, name)
);

-- =============================================
-- USER PROGRESS TABLES
-- =============================================

CREATE TABLE submissions (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    problem_id VARCHAR NOT NULL REFERENCES problems(id) ON DELETE CASCADE,
    query TEXT NOT NULL,
    is_correct BOOLEAN NOT NULL,
    execution_time INTEGER,
    submitted_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE problem_submissions (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    problem_id VARCHAR NOT NULL REFERENCES problems(id) ON DELETE CASCADE,
    sql_query TEXT NOT NULL,
    status VARCHAR(20) NOT NULL,
    rows_returned INTEGER,
    execution_time_ms INTEGER,
    error_message TEXT,
    result_data JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    completed_at TIMESTAMP
);

CREATE TABLE problem_sessions (
    id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid()::text,
    user_id VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    problem_id VARCHAR NOT NULL REFERENCES problems(id) ON DELETE CASCADE,
    first_query_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    total_time_spent_seconds INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE execution_results (
    id VARCHAR PRIMARY KEY,
    submission_id VARCHAR NOT NULL REFERENCES submissions(id) ON DELETE CASCADE,
    test_case_id VARCHAR NOT NULL REFERENCES test_cases(id) ON DELETE CASCADE,
    status execution_status NOT NULL,
    execution_time_ms INTEGER,
    memory_used_mb DOUBLE PRECISION,
    rows_affected INTEGER,
    query_result JSONB,
    error_message TEXT,
    is_correct BOOLEAN NOT NULL,
    validation_details JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE user_progress (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    topic_id VARCHAR NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
    problems_attempted INTEGER,
    problems_solved INTEGER,
    total_submissions INTEGER,
    successful_submissions INTEGER,
    average_execution_time_ms DOUBLE PRECISION,
    best_execution_time_ms DOUBLE PRECISION,
    total_time_spent_minutes INTEGER,
    current_difficulty difficultylevel,
    highest_difficulty_solved difficultylevel,
    hint_usage_count INTEGER,
    average_attempts_per_problem DOUBLE PRECISION,
    streak_count INTEGER,
    max_streak_count INTEGER,
    experience_points INTEGER,
    first_attempt_at TIMESTAMP,
    last_activity_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    updated_at TIMESTAMP NOT NULL DEFAULT now(),
    UNIQUE (user_id, topic_id)
);

-- =============================================
-- GAMIFICATION TABLES
-- =============================================

CREATE TABLE badges (
    id VARCHAR PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT NOT NULL,
    icon_url TEXT,
    criteria JSONB NOT NULL,
    points_reward INTEGER,
    rarity VARCHAR(20),
    created_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE user_badges (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    badge_id VARCHAR NOT NULL REFERENCES badges(id) ON DELETE CASCADE,
    earned_at TIMESTAMP NOT NULL DEFAULT now(),
    UNIQUE (user_id, badge_id)
);

-- =============================================
-- COMMUNITY TABLES
-- =============================================

CREATE TABLE community_posts (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    problem_id VARCHAR REFERENCES problems(id),
    content TEXT NOT NULL,
    code_snippet TEXT,
    likes INTEGER NOT NULL DEFAULT 0,
    comments INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    updated_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE post_likes (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    post_id VARCHAR NOT NULL REFERENCES community_posts(id) ON DELETE CASCADE,
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    UNIQUE (user_id, post_id)
);

CREATE TABLE post_comments (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    post_id VARCHAR NOT NULL REFERENCES community_posts(id) ON DELETE CASCADE,
    parent_id VARCHAR REFERENCES post_comments(id),
    content TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE problem_interactions (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    problem_id VARCHAR NOT NULL REFERENCES problems(id) ON DELETE CASCADE,
    bookmark BOOLEAN NOT NULL DEFAULT false,
    upvote BOOLEAN NOT NULL DEFAULT false,
    downvote BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    updated_at TIMESTAMP NOT NULL DEFAULT now(),
    UNIQUE (user_id, problem_id)
);

-- =============================================
-- SYSTEM TABLES
-- =============================================

CREATE TABLE cache_entries (
    id VARCHAR PRIMARY KEY,
    cache_key VARCHAR(500) NOT NULL,
    namespace VARCHAR(100) NOT NULL,
    data JSONB NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    UNIQUE (cache_key, namespace)
);

CREATE TABLE fallback_submissions (
    id VARCHAR PRIMARY KEY,
    job_id VARCHAR(100) UNIQUE NOT NULL,
    data JSONB NOT NULL,
    status VARCHAR(20) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    processed_at TIMESTAMP
);

CREATE TABLE solutions (
    id VARCHAR PRIMARY KEY,
    problem_id VARCHAR NOT NULL REFERENCES problems(id) ON DELETE CASCADE,
    created_by VARCHAR NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    sql_code TEXT NOT NULL,
    is_official BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    updated_at TIMESTAMP NOT NULL DEFAULT now()
);
```

### Step 3: Create Indexes

```sql
-- =============================================
-- PERFORMANCE INDEXES
-- =============================================

-- Followers
CREATE INDEX idx_followers_follower_id ON followers(follower_id);
CREATE INDEX idx_followers_following_id ON followers(following_id);

-- Helpful Links
CREATE INDEX idx_helpful_links_user_id ON helpful_links(user_id);
CREATE INDEX idx_helpful_links_created_at ON helpful_links(created_at);

-- Problems
CREATE INDEX idx_problems_difficulty ON problems(difficulty);
CREATE INDEX idx_problems_company ON problems(company);
CREATE INDEX idx_problems_topic_id ON problems(topic_id);
CREATE INDEX idx_problems_created_at ON problems(created_at);

-- Submissions
CREATE INDEX idx_submissions_user_id ON submissions(user_id);
CREATE INDEX idx_submissions_problem_id ON submissions(problem_id);
CREATE INDEX idx_submissions_is_correct ON submissions(is_correct);
CREATE INDEX idx_submissions_submitted_at ON submissions(submitted_at);

-- Problem Submissions
CREATE INDEX idx_problem_submissions_user_id ON problem_submissions(user_id);
CREATE INDEX idx_problem_submissions_problem_id ON problem_submissions(problem_id);
CREATE INDEX idx_problem_submissions_status ON problem_submissions(status);
CREATE INDEX idx_problem_submissions_created_at ON problem_submissions(created_at);
CREATE INDEX idx_problem_submissions_completed_at ON problem_submissions(completed_at);

-- Problem Sessions
CREATE INDEX idx_problem_sessions_user_problem ON problem_sessions(user_id, problem_id);
CREATE INDEX idx_problem_sessions_completed_at ON problem_sessions(completed_at);

-- Solutions
CREATE INDEX idx_solutions_problem_id ON solutions(problem_id);
CREATE INDEX idx_solutions_created_by ON solutions(created_by);
CREATE INDEX idx_solutions_created_at ON solutions(created_at);

-- Cache Entries
CREATE INDEX idx_cache_key_namespace ON cache_entries(cache_key, namespace);
CREATE INDEX idx_cache_expires_at ON cache_entries(expires_at);

-- Fallback Submissions
CREATE INDEX idx_fallback_status ON fallback_submissions(status);
CREATE INDEX idx_fallback_created_at ON fallback_submissions(created_at);
```

---

## Usage Instructions

### Importing into New PostgreSQL Database

```bash
# 1. Create a new PostgreSQL database
createdb sqlgym_new

# 2. Connect to the database
psql -d sqlgym_new

# 3. Execute the DDL in order:

-- First, create ENUM types
\i create_enums.sql

-- Then, create all tables
\i create_tables.sql

-- Finally, create indexes
\i create_indexes.sql

# 4. Verify the schema
\dt
\di
\dT
```

### Data Migration

```bash
# Export data from Neon
pg_dump --data-only --no-owner --no-acl -h <neon-host> -U <user> -d <db> > data_export.sql

# Import data into new database
psql -d sqlgym_new -f data_export.sql
```

### Backup Script

```bash
#!/bin/bash
# Full backup of SQLGym database
pg_dump -h <host> -U <user> -d sqlgym \
  --create \
  --clean \
  --if-exists \
  --verbose \
  --file=sqlgym_backup_$(date +%Y%m%d_%H%M%S).sql
```

---

## Schema Diagram (ER Notation)

```
┌──────────┐       ┌─────────────┐       ┌──────────┐
│  users   │───┬───│ submissions │───────│ problems │
└──────────┘   │   └─────────────┘       └──────────┘
    │          │                              │
    │          └───┐                          │
    │              │                          │
    ├──────────────┼──────────────────────────┤
    │              │                          │
┌──────────┐  ┌─────────────┐        ┌──────────────┐
│followers │  │user_progress│        │problem_schemas│
└──────────┘  └─────────────┘        └──────────────┘
    │
    │         ┌────────────────┐
    └─────────│ community_posts│
              └────────────────┘
                  │          │
            ┌─────┴──┐  ┌────┴─────┐
            │post_   │  │post_     │
            │likes   │  │comments  │
            └────────┘  └──────────┘
```

---

## Notes

1. **UUID Generation:** All `id` fields use VARCHAR with UUID values generated via `uuid.uuid4()` in Python or `gen_random_uuid()` in PostgreSQL
2. **Timestamps:** All timestamps use `TIMESTAMP` (without timezone) except `problem_sessions` which uses `TIMESTAMPTZ`
3. **JSONB vs JSON:** Most JSON fields use `JSONB` for better performance and querying, except arrays like `tags` and `hints` which use `JSON`
4. **Cascade Deletes:** Most foreign keys use `ON DELETE CASCADE` to automatically clean up related records
5. **Data Retention:** The `execution_results` table should have a 6-month retention policy to prevent unbounded growth

---

## Change Log

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | Oct 2025 | Initial schema documentation |

---

**Generated for:** SQLGym Database Migration
**PostgreSQL Version:** 14+
**Contact:** See project documentation

