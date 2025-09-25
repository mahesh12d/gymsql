"""
SQLAlchemy models for the PostgreSQL database schema
"""
from sqlalchemy import Column, String, Text, Integer, Boolean, DateTime, ForeignKey, Float, Enum, Index, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSON, JSONB, ENUM
import uuid
import enum

Base = declarative_base()

# Named Postgres enums for better type safety and performance
# Python enums for reference
class DifficultyLevel(enum.Enum):
    EASY = "Easy"
    MEDIUM = "Medium"
    HARD = "Hard"

class ExecutionStatus(enum.Enum):
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"
    TIMEOUT = "TIMEOUT"
    MEMORY_LIMIT = "MEMORY_LIMIT"

class SandboxStatus(enum.Enum):
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    CLEANUP_PENDING = "CLEANUP_PENDING"

# Create named Postgres enums
difficulty_enum = ENUM(
    'BEGINNER', 'EASY', 'MEDIUM', 'HARD', 'EXPERT',
    name='difficultylevel',
    create_type=False
)

execution_status_enum = ENUM(
    'SUCCESS', 'ERROR', 'TIMEOUT', 'MEMORY_LIMIT',
    name='execution_status',
    create_type=False
)

sandbox_status_enum = ENUM(
    'ACTIVE', 'EXPIRED', 'CLEANUP_PENDING',
    name='sandbox_status',
    create_type=False
)

class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(Text, name="password_hash")
    first_name = Column(String(50), name="first_name")
    last_name = Column(String(50), name="last_name")
    profile_image_url = Column(Text, name="profile_image_url")
    google_id = Column(String(255), unique=True, name="google_id")
    github_id = Column(String(255), unique=True, name="github_id")
    auth_provider = Column(String(20), default="email", nullable=False, name="auth_provider")
    problems_solved = Column(Integer, default=0, nullable=False, name="problems_solved")
    premium = Column(Boolean, nullable=False, default=False)  # False = free user, True = premium user
    is_admin = Column(Boolean, nullable=False, default=False)  # False = regular user, True = admin user
    created_at = Column(DateTime, default=func.now(), nullable=False, name="created_at")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False, name="updated_at")
    
    # Relationships
    submissions = relationship("Submission", back_populates="user")
    community_posts = relationship("CommunityPost", back_populates="user")
    post_likes = relationship("PostLike", back_populates="user")
    post_comments = relationship("PostComment", back_populates="user")
    progress = relationship("UserProgress", back_populates="user")
    user_badges = relationship("UserBadge", back_populates="user")

class Problem(Base):
    __tablename__ = "problems"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(200), nullable=False)
    difficulty = Column(String(20), nullable=False)  # Easy, Medium, Hard

    # Match DB schema: json (not jsonb)
    tags = Column(JSON, default=list, nullable=False)
    company = Column(String(100), nullable=True)
    hints = Column(JSON, default=list, nullable=False)

    # Match DB schema: jsonb
    question = Column(JSONB, nullable=False)  # description, schema, expected_output
    s3_data_source = Column(JSONB, nullable=True)  # bucket, key, table_name, description, etag (single table - legacy)
    s3_datasets = Column(JSONB, nullable=True)  # array of multiple dataset configs: [{'bucket': str, 'key': str, 'table_name': str, 'description': str, 'etag': str}]
    premium = Column(Boolean, nullable=True, default=None)  # null = free, True = premium
    
    # Master solution field - the definitive expected output for validation
    master_solution = Column(JSONB, nullable=True)  # Complete expected output for validation and display
    
    # Display field - what users see on the problem page (separate from validation)
    expected_display = Column(JSONB, nullable=True)  # Expected output shown to users on problem page
    
    # Hash field for fast validation
    expected_hash = Column(String, nullable=True)  # MD5 hash of sorted expected results for fast comparison

    created_at = Column(DateTime, default=func.now(), nullable=False, name="created_at")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False, name="updated_at")
    
    topic_id = Column(String, ForeignKey("topics.id", ondelete="SET NULL"))
    
    # Relationships
    submissions = relationship("Submission", back_populates="problem")
    test_cases = relationship("TestCase", back_populates="problem")
    schemas = relationship("ProblemSchema", back_populates="problem")
    community_posts = relationship("CommunityPost", back_populates="problem")
    solutions = relationship("Solution", back_populates="problem")
    topic = relationship("Topic", back_populates="problems")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_problems_difficulty', 'difficulty'),
        Index('idx_problems_company', 'company'),
        Index('idx_problems_topic_id', 'topic_id'),
        Index('idx_problems_created_at', 'created_at'),
    )

class Submission(Base):
    __tablename__ = "submissions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, name="user_id")
    problem_id = Column(String, ForeignKey("problems.id", ondelete="CASCADE"), nullable=False, name="problem_id")
    query = Column(Text, nullable=False)
    is_correct = Column(Boolean, nullable=False, name="is_correct")
    execution_time = Column(Integer, name="execution_time")  # in milliseconds
    submitted_at = Column(DateTime, default=func.now(), nullable=False, name="submitted_at")
    
    # Relationships
    user = relationship("User", back_populates="submissions")
    problem = relationship("Problem", back_populates="submissions")
    execution_results = relationship("ExecutionResult", back_populates="submission")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_submissions_user_id', 'user_id'),
        Index('idx_submissions_problem_id', 'problem_id'),
        Index('idx_submissions_submitted_at', 'submitted_at'),
        Index('idx_submissions_is_correct', 'is_correct'),
    )

class CommunityPost(Base):
    __tablename__ = "community_posts"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, name="user_id")
    problem_id = Column(String, ForeignKey("problems.id", ondelete="CASCADE"), nullable=True, name="problem_id")  # For problem-specific discussions
    content = Column(Text, nullable=False)
    code_snippet = Column(Text, name="code_snippet")
    likes = Column(Integer, default=0, nullable=False)
    comments = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False, name="created_at")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False, name="updated_at")
    
    # Relationships
    user = relationship("User", back_populates="community_posts")
    problem = relationship("Problem", back_populates="community_posts")
    post_likes = relationship("PostLike", back_populates="post")
    post_comments = relationship("PostComment", back_populates="post")

class PostLike(Base):
    __tablename__ = "post_likes"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, name="user_id")
    post_id = Column(String, ForeignKey("community_posts.id", ondelete="CASCADE"), nullable=False, name="post_id")
    created_at = Column(DateTime, default=func.now(), nullable=False, name="created_at")
    
    # Relationships
    user = relationship("User", back_populates="post_likes")
    post = relationship("CommunityPost", back_populates="post_likes")
    
    # Unique constraint: one like per user per post
    __table_args__ = (UniqueConstraint('user_id', 'post_id', name='uq_post_likes_user_post'),)

class PostComment(Base):
    __tablename__ = "post_comments"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, name="user_id")
    post_id = Column(String, ForeignKey("community_posts.id", ondelete="CASCADE"), nullable=False, name="post_id")
    parent_id = Column(String, ForeignKey("post_comments.id", ondelete="CASCADE"), nullable=True, name="parent_id")  # For nested replies
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False, name="created_at")
    
    # Relationships
    user = relationship("User", back_populates="post_comments")
    post = relationship("CommunityPost", back_populates="post_comments")
    parent = relationship("PostComment", remote_side=[id], backref="replies")

# New Tables for Enhanced SQL Learning Platform

class Topic(Base):
    """Topics/Categories to organize problems by SQL concepts"""
    __tablename__ = "topics"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    difficulty_level = Column(difficulty_enum, nullable=False)
    order_index = Column(Integer, default=0)  # For ordering topics
    parent_topic_id = Column(String, ForeignKey("topics.id", ondelete="SET NULL"))  # For subtopics
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    parent_topic = relationship("Topic", remote_side=[id])
    problems = relationship("Problem", back_populates="topic")
    user_progress = relationship("UserProgress", back_populates="topic")

class TestCase(Base):
    """Test cases for problems with input data and expected outputs"""
    __tablename__ = "test_cases"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    problem_id = Column(String, ForeignKey("problems.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    input_data = Column(JSONB, nullable=False)  # Schema and sample data
    expected_output = Column(JSONB, nullable=False)  # Expected query results (backward compatibility)
    validation_rules = Column(JSONB, default=dict)  # Custom validation logic
    is_hidden = Column(Boolean, default=False)  # Hidden test cases for evaluation
    order_index = Column(Integer, default=0)
    timeout_seconds = Column(Integer, default=30)
    memory_limit_mb = Column(Integer, default=256)
    
    # S3 Answer Source Support
    expected_output_source = Column(JSONB, nullable=True)  # S3 bucket, key, format, etag for full dataset
    preview_expected_output = Column(JSONB, nullable=True)  # Limited rows for frontend display
    display_limit = Column(Integer, default=10)  # Number of rows to show in preview
    
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    problem = relationship("Problem", back_populates="test_cases")
    execution_results = relationship("ExecutionResult", back_populates="test_case")
    
    # Unique constraint: unique name per problem
    __table_args__ = (UniqueConstraint('problem_id', 'name', name='uq_test_cases_problem_name'),)

class ProblemSchema(Base):
    """Define table structures that problems will use"""
    __tablename__ = "problem_schemas"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    problem_id = Column(String, ForeignKey("problems.id", ondelete="CASCADE"), nullable=False)
    table_name = Column(String(100), nullable=False)
    schema_definition = Column(JSONB, nullable=False)  # Table structure with columns, types, constraints
    sample_data = Column(JSONB, default=list)  # Sample rows for the table
    indexes = Column(JSON, default=list)  # Index definitions
    constraints = Column(JSON, default=list)  # FK, CHECK constraints etc
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    problem = relationship("Problem", back_populates="schemas")
    
    # Unique constraint: unique table_name per problem
    __table_args__ = (UniqueConstraint('problem_id', 'table_name', name='uq_problem_schemas_problem_table'),)

class ExecutionResult(Base):
    """Track detailed query execution results"""
    __tablename__ = "execution_results"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    submission_id = Column(String, ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False)
    test_case_id = Column(String, ForeignKey("test_cases.id", ondelete="CASCADE"), nullable=False)
    # user_sandbox_id removed - PostgreSQL sandbox functionality removed
    
    # Execution details
    status = Column(execution_status_enum, nullable=False)
    execution_time_ms = Column(Integer)  # Actual execution time
    memory_used_mb = Column(Float)  # Memory consumption
    rows_affected = Column(Integer)  # For DML queries
    query_result = Column(JSONB)  # Actual query output
    error_message = Column(Text)  # Error details if any
    
    # Performance metrics (unused columns removed for database optimization)
    
    # Validation
    is_correct = Column(Boolean, nullable=False)
    validation_details = Column(JSONB)  # Detailed comparison results
    
    created_at = Column(DateTime, default=func.now(), nullable=False)
    
    # Relationships
    submission = relationship("Submission", back_populates="execution_results")
    test_case = relationship("TestCase", back_populates="execution_results")
    # user_sandbox relationship removed - PostgreSQL sandbox functionality removed


class UserProgress(Base):
    """Track user statistics and problem-solving progress"""
    __tablename__ = "user_progress"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    topic_id = Column(String, ForeignKey("topics.id", ondelete="CASCADE"), nullable=False)
    
    # Progress metrics
    problems_attempted = Column(Integer, default=0)
    problems_solved = Column(Integer, default=0)
    total_submissions = Column(Integer, default=0)
    successful_submissions = Column(Integer, default=0)
    
    # Performance metrics
    average_execution_time_ms = Column(Float)
    best_execution_time_ms = Column(Float)
    total_time_spent_minutes = Column(Integer, default=0)
    
    # Difficulty progression
    current_difficulty = Column(difficulty_enum, default="EASY")
    highest_difficulty_solved = Column(difficulty_enum, default="EASY")
    
    # Learning metrics
    hint_usage_count = Column(Integer, default=0)
    average_attempts_per_problem = Column(Float, default=1.0)
    streak_count = Column(Integer, default=0)  # Current solving streak
    max_streak_count = Column(Integer, default=0)  # Best streak ever
    
    # XP and achievements
    experience_points = Column(Integer, default=0)
    
    # Timestamps
    first_attempt_at = Column(DateTime)
    last_activity_at = Column(DateTime, default=func.now())
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="progress")
    topic = relationship("Topic", back_populates="user_progress")
    
    # Unique constraint: one progress record per user per topic
    __table_args__ = (UniqueConstraint('user_id', 'topic_id', name='uq_user_progress_user_topic'),)

class Badge(Base):
    """Achievement badges for user motivation"""
    __tablename__ = "badges"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=False)
    icon_url = Column(Text)
    criteria = Column(JSONB, nullable=False)  # Conditions to earn the badge
    points_reward = Column(Integer, default=0)
    rarity = Column(String(20), default="common")  # common, rare, epic, legendary
    created_at = Column(DateTime, default=func.now(), nullable=False)
    
    # Relationships
    user_badges = relationship("UserBadge", back_populates="badge")

class UserBadge(Base):
    """Junction table for user-earned badges"""
    __tablename__ = "user_badges"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    badge_id = Column(String, ForeignKey("badges.id", ondelete="CASCADE"), nullable=False)
    earned_at = Column(DateTime, default=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="user_badges")
    badge = relationship("Badge", back_populates="user_badges")
    
    # Unique constraint: one badge per user (prevent duplicate awards)
    __table_args__ = (UniqueConstraint('user_id', 'badge_id', name='uq_user_badges_user_badge'),)

class ProblemInteraction(Base):
    """Unified user interactions for problems (bookmark, upvote, downvote)"""
    __tablename__ = "problem_interactions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    problem_id = Column(String, ForeignKey("problems.id", ondelete="CASCADE"), nullable=False)
    
    # Interaction flags - all optional
    bookmark = Column(Boolean, default=False, nullable=False)
    upvote = Column(Boolean, default=False, nullable=False)
    downvote = Column(Boolean, default=False, nullable=False)
    
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", backref="problem_interactions")
    problem = relationship("Problem", backref="interactions")
    
    # Unique constraint: one interaction record per user per problem
    __table_args__ = (UniqueConstraint('user_id', 'problem_id', name='uq_problem_interactions_user_problem'),)

# Migration completed - old ProblemBookmark and ProblemLike models removed

class ProblemSession(Base):
    """Track user engagement timing for problems"""
    __tablename__ = "problem_sessions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    problem_id = Column(String, ForeignKey("problems.id", ondelete="CASCADE"), nullable=False)
    first_query_at = Column(DateTime, nullable=True)  # When user first runs a query
    completed_at = Column(DateTime, nullable=True)    # When user successfully submits
    total_time_spent_seconds = Column(Integer, nullable=True)  # Calculated time difference
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", backref="problem_sessions")
    problem = relationship("Problem", backref="sessions")
    
    # Index for performance
    __table_args__ = (
        Index('idx_problem_sessions_user_problem', 'user_id', 'problem_id'),
        Index('idx_problem_sessions_completed_at', 'completed_at'),
    )

class Solution(Base):
    """Official solutions for problems posted by admins"""
    __tablename__ = "solutions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    problem_id = Column(String, ForeignKey("problems.id", ondelete="CASCADE"), nullable=False, name="problem_id")
    created_by = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, name="created_by")
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)  # Solution explanation
    sql_code = Column(Text, nullable=False, name="sql_code")  # The actual SQL solution
    is_official = Column(Boolean, default=True, nullable=False, name="is_official")  # Mark as official solution
    created_at = Column(DateTime, default=func.now(), nullable=False, name="created_at")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False, name="updated_at")
    
    # Relationships
    problem = relationship("Problem", back_populates="solutions")
    creator = relationship("User", foreign_keys=[created_by])
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_solutions_problem_id', 'problem_id'),
        Index('idx_solutions_created_by', 'created_by'),
        Index('idx_solutions_created_at', 'created_at'),
    )
