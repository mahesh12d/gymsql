"""
Pydantic schemas for request/response validation
"""
from pydantic import BaseModel, EmailStr, ConfigDict, Field
from pydantic.alias_generators import to_camel
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

# Enums matching the SQLAlchemy enums
class DifficultyLevel(str, Enum):
    BEGINNER = "BEGINNER"
    EASY = "EASY"
    MEDIUM = "MEDIUM"
    HARD = "HARD"
    EXPERT = "EXPERT"

class ExecutionStatus(str, Enum):
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"
    TIMEOUT = "TIMEOUT"
    MEMORY_LIMIT = "MEMORY_LIMIT"

class SandboxStatus(str, Enum):
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    CLEANUP_PENDING = "CLEANUP_PENDING"

# Base model for camelCase aliasing
class CamelCaseModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True
    )

# S3 Answer Source schemas
class S3AnswerSource(BaseModel):
    """Schema for S3 answer source configuration"""
    bucket: str
    key: str  # S3 object key (file path)
    format: str  # csv, json, parquet
    etag: Optional[str] = None  # For cache validation
    last_modified: Optional[datetime] = None
    description: Optional[str] = None
    
    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True
    )

# S3 Dataset Source schemas (for problem datasets)
class S3DatasetSource(BaseModel):
    """Schema for S3 dataset source configuration"""
    bucket: str
    key: str  # S3 object key (file path) - must be .parquet
    table_name: str  # Table name for DuckDB
    description: Optional[str] = None
    etag: Optional[str] = None  # For cache validation
    
    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True
    )

class MultiTableS3Source(BaseModel):
    """Schema for multiple S3 dataset sources in a single question"""
    datasets: List[S3DatasetSource]  # List of S3 dataset configurations
    description: Optional[str] = None  # Overall description of the multi-table setup
    
    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True
    )

# User schemas
class UserBase(CamelCaseModel):
    username: str
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    profile_image_url: Optional[str] = None

class UserCreate(UserBase):
    password: Optional[str] = None
    google_id: Optional[str] = None
    github_id: Optional[str] = None
    auth_provider: str = "email"

class UserResponse(UserBase):
    id: str
    problems_solved: int
    premium: bool
    created_at: datetime

class UserLogin(CamelCaseModel):
    email: EmailStr
    password: str

# Table column definition for structured display
class TableColumn(BaseModel):
    name: str
    type: str

# Table data with columns and sample data
class TableData(BaseModel):
    name: str
    columns: List[TableColumn]
    sample_data: List[dict] = Field(..., alias="sampleData")
    
    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True
    )

# Problem question structure for JSONB field - structured format
class QuestionData(BaseModel):
    description: str
    tables: List[TableData] = []
    # Note: expected_output moved to top-level ProblemBase for better data architecture
    
    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True
    )

# Problem schemas
class ProblemBase(CamelCaseModel):
    title: str
    question: QuestionData  # JSONB field containing description, schema
    difficulty: str
    tags: List[str] = []
    company: Optional[str] = None
    hints: List[str] = []
    premium: Optional[bool] = None  # null = free, True = premium
    master_solution: Optional[List[dict]] = Field(default=None, alias="masterSolution")  # Complete expected output for validation (admin only)
    expected_display: Optional[List[dict]] = Field(default=None, alias="expectedDisplay")  # Expected output for user display
    expected_output: Optional[List[dict]] = Field(default=None, alias="expectedOutput")  # Legacy field - use master_solution instead
    parquet_data_source: Optional[Dict[str, Any]] = None  # JSONB field for DuckDB parquet data (legacy)
    s3_data_source: Optional[S3DatasetSource] = None  # S3 dataset source configuration (legacy)
    s3_datasets: Optional[List[S3DatasetSource]] = None  # Multiple S3 dataset sources configuration

class ProblemCreate(ProblemBase):
    pass

class ProblemResponse(ProblemBase):
    id: str
    created_at: datetime
    solved_count: Optional[int] = 0
    is_user_solved: Optional[bool] = False
    is_bookmarked: Optional[bool] = False
    is_liked: Optional[bool] = False  # For backward compatibility
    is_upvoted: Optional[bool] = False
    is_downvoted: Optional[bool] = False
    likes_count: Optional[int] = 0  # For backward compatibility
    upvotes_count: Optional[int] = 0

# Submission schemas
class SubmissionBase(CamelCaseModel):
    problem_id: str
    query: str

class SubmissionCreate(SubmissionBase):
    pass

class SubmissionResponse(SubmissionBase):
    id: str
    user_id: str
    is_correct: bool
    execution_time: Optional[int] = None
    submitted_at: datetime

# Community post schemas
class CommunityPostBase(CamelCaseModel):
    content: str
    code_snippet: Optional[str] = None
    problem_id: Optional[str] = None  # For problem-specific discussions

class CommunityPostCreate(CommunityPostBase):
    pass

# Simple problem schema for community posts
class CommunityProblemResponse(CamelCaseModel):
    id: str
    title: str
    company: Optional[str] = None
    difficulty: str

class CommunityPostResponse(CommunityPostBase):
    id: str
    user_id: str
    likes: int
    comments: int
    created_at: datetime
    user: UserResponse
    problem: Optional[CommunityProblemResponse] = None

# Post comment schemas
class PostCommentBase(CamelCaseModel):
    content: str
    parent_id: Optional[str] = None  # For nested replies

class PostCommentCreate(PostCommentBase):
    pass

class PostCommentResponse(PostCommentBase):
    id: str
    user_id: str
    post_id: str
    parent_id: Optional[str] = None
    created_at: datetime
    user: UserResponse
    replies: List['PostCommentResponse'] = []  # Nested replies

# Update forward references for recursive type
PostCommentResponse.model_rebuild()

# Authentication schemas
class Token(CamelCaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(CamelCaseModel):
    user_id: Optional[str] = None
    username: Optional[str] = None
    is_admin: Optional[bool] = None

class LoginResponse(CamelCaseModel):
    token: str
    user: UserResponse
    message: str = "Login successful"

class RegisterResponse(CamelCaseModel):
    token: str
    user: UserResponse
    message: str = "User created successfully"

# Enhanced schemas for new database models

# Topic schemas
class TopicBase(CamelCaseModel):
    name: str
    description: Optional[str] = None
    difficulty_level: DifficultyLevel
    order_index: int = 0
    parent_topic_id: Optional[str] = None

class TopicCreate(TopicBase):
    pass

class TopicResponse(TopicBase):
    id: str
    created_at: datetime
    updated_at: datetime

# Test case schemas
class TestCaseBase(CamelCaseModel):
    problem_id: str
    name: str
    description: Optional[str] = None
    input_data: Dict[str, Any]
    expected_output: List[Dict[str, Any]]  # Backward compatibility - full dataset or fallback
    validation_rules: Dict[str, Any] = {}
    is_hidden: bool = False
    order_index: int = 0
    timeout_seconds: int = 30
    memory_limit_mb: int = 256
    
    # S3 Answer Source Support
    expected_output_source: Optional[S3AnswerSource] = None  # S3 source for full dataset
    preview_expected_output: Optional[List[Dict[str, Any]]] = None  # Limited rows for frontend
    display_limit: int = 10  # Number of rows to show in preview

class TestCaseCreate(TestCaseBase):
    pass

class TestCaseResponse(TestCaseBase):
    id: str
    created_at: datetime
    updated_at: datetime

# Problem schema schemas
class ProblemSchemaBase(CamelCaseModel):
    problem_id: str
    table_name: str
    schema_definition: Dict[str, Any]
    sample_data: List[Dict[str, Any]] = []
    indexes: List[Dict[str, Any]] = []
    constraints: List[Dict[str, Any]] = []

class ProblemSchemaCreate(ProblemSchemaBase):
    pass

class ProblemSchemaResponse(ProblemSchemaBase):
    id: str
    created_at: datetime
    updated_at: datetime

# Execution result schemas
class ExecutionResultBase(CamelCaseModel):
    submission_id: str
    test_case_id: str
    # user_sandbox_id removed - PostgreSQL sandbox functionality removed
    status: ExecutionStatus
    execution_time_ms: Optional[int] = None
    memory_used_mb: Optional[float] = None
    rows_affected: Optional[int] = None
    query_result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    cpu_time_ms: Optional[int] = None
    io_operations: Optional[int] = None
    query_plan: Optional[Dict[str, Any]] = None
    is_correct: bool
    validation_details: Optional[Dict[str, Any]] = None

class ExecutionResultCreate(ExecutionResultBase):
    pass

class ExecutionResultResponse(ExecutionResultBase):
    id: str
    created_at: datetime

# User sandbox schemas removed - PostgreSQL sandbox functionality removed

# User progress schemas
class UserProgressBase(CamelCaseModel):
    user_id: str
    topic_id: str
    problems_attempted: int = 0
    problems_solved: int = 0
    total_submissions: int = 0
    successful_submissions: int = 0
    average_execution_time_ms: Optional[float] = None
    best_execution_time_ms: Optional[float] = None
    total_time_spent_minutes: int = 0
    current_difficulty: DifficultyLevel = DifficultyLevel.EASY
    highest_difficulty_solved: DifficultyLevel = DifficultyLevel.EASY
    hint_usage_count: int = 0
    average_attempts_per_problem: float = 1.0
    streak_count: int = 0
    max_streak_count: int = 0
    experience_points: int = 0
    first_attempt_at: Optional[datetime] = None
    last_activity_at: Optional[datetime] = None

class UserProgressCreate(UserProgressBase):
    pass

class UserProgressResponse(UserProgressBase):
    id: str
    created_at: datetime
    updated_at: datetime

# Badge schemas
class BadgeBase(CamelCaseModel):
    name: str
    description: str
    icon_url: Optional[str] = None
    criteria: Dict[str, Any]
    points_reward: int = 0
    rarity: str = "common"

class BadgeCreate(BadgeBase):
    pass

class BadgeResponse(BadgeBase):
    id: str
    created_at: datetime

class UserBadgeResponse(CamelCaseModel):
    id: str
    user_id: str
    badge_id: str
    earned_at: datetime
    badge: BadgeResponse

# Enhanced existing schemas
class EnhancedUserResponse(UserResponse):
    """Enhanced user response with progress data"""
    progress: Optional[List[UserProgressResponse]] = []
    badges: Optional[List[UserBadgeResponse]] = []
    current_level: Optional[str] = None
    total_xp: Optional[int] = 0

class EnhancedProblemResponse(ProblemResponse):
    """Enhanced problem response with test cases and schema"""
    test_cases: Optional[List[TestCaseResponse]] = []
    schemas: Optional[List[ProblemSchemaResponse]] = []
    topic: Optional[TopicResponse] = None

class DetailedSubmissionResponse(SubmissionResponse):
    """Detailed submission with execution results"""
    execution_results: Optional[List[ExecutionResultResponse]] = []
    overall_score: Optional[float] = None
    passed_test_cases: Optional[int] = 0
    total_test_cases: Optional[int] = 0

# Solution schemas
class SolutionBase(CamelCaseModel):
    title: str
    content: str
    sql_code: str
    is_official: bool = True  # Always true since there's only one solution per problem

class SolutionCreate(SolutionBase):
    pass

class SolutionResponse(SolutionBase):
    id: str
    problem_id: str
    created_by: str
    created_at: datetime
    updated_at: datetime
    creator: UserResponse