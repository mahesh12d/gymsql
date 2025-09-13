"""
Pydantic schemas for request/response validation
"""
from pydantic import BaseModel, EmailStr, ConfigDict, Field
from pydantic.alias_generators import to_camel
from typing import Optional, List
from datetime import datetime

# Base model for camelCase aliasing
class CamelCaseModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
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
    expected_output: List[dict] = Field(..., alias="expectedOutput")
    
    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True
    )

# Problem schemas
class ProblemBase(CamelCaseModel):
    title: str
    question: QuestionData  # JSONB field containing description, schema, expectedOutput
    difficulty: str
    tags: List[str] = []
    company: Optional[str] = None
    hints: List[str] = []

class ProblemCreate(ProblemBase):
    pass

class ProblemResponse(ProblemBase):
    id: str
    created_at: datetime
    solved_count: Optional[int] = 0
    is_user_solved: Optional[bool] = False

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

class CommunityPostCreate(CommunityPostBase):
    pass

class CommunityPostResponse(CommunityPostBase):
    id: str
    user_id: str
    likes: int
    comments: int
    created_at: datetime
    user: UserResponse

# Post comment schemas
class PostCommentBase(CamelCaseModel):
    content: str

class PostCommentCreate(PostCommentBase):
    pass

class PostCommentResponse(PostCommentBase):
    id: str
    user_id: str
    post_id: str
    created_at: datetime
    user: UserResponse

# Authentication schemas
class Token(CamelCaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(CamelCaseModel):
    user_id: Optional[str] = None
    username: Optional[str] = None

class LoginResponse(CamelCaseModel):
    token: str
    user: UserResponse
    message: str = "Login successful"

class RegisterResponse(CamelCaseModel):
    token: str
    user: UserResponse
    message: str = "User created successfully"