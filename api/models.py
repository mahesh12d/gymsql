"""
SQLAlchemy models for the PostgreSQL database schema
"""
from sqlalchemy import Column, String, Text, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSON, JSONB
import uuid

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(Text, name="password_hash")
    first_name = Column(String(50), name="first_name")
    last_name = Column(String(50), name="last_name")
    profile_image_url = Column(Text, name="profile_image_url")
    google_id = Column(String(255), name="google_id")
    github_id = Column(String(255), name="github_id")
    auth_provider = Column(String(20), default="email", nullable=False, name="auth_provider")
    problems_solved = Column(Integer, default=0, nullable=False, name="problems_solved")
    created_at = Column(DateTime, default=func.now(), nullable=False, name="created_at")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False, name="updated_at")
    
    # Relationships
    submissions = relationship("Submission", back_populates="user")
    community_posts = relationship("CommunityPost", back_populates="user")
    post_likes = relationship("PostLike", back_populates="user")
    post_comments = relationship("PostComment", back_populates="user")

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

    created_at = Column(DateTime, default=func.now(), nullable=False, name="created_at")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False, name="updated_at")
    
    # Relationships
    submissions = relationship("Submission", back_populates="problem")

class Submission(Base):
    __tablename__ = "submissions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, name="user_id")
    problem_id = Column(String, ForeignKey("problems.id"), nullable=False, name="problem_id")
    query = Column(Text, nullable=False)
    is_correct = Column(Boolean, nullable=False, name="is_correct")
    execution_time = Column(Integer, name="execution_time")  # in milliseconds
    submitted_at = Column(DateTime, default=func.now(), nullable=False, name="submitted_at")
    
    # Relationships
    user = relationship("User", back_populates="submissions")
    problem = relationship("Problem", back_populates="submissions")

class CommunityPost(Base):
    __tablename__ = "community_posts"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, name="user_id")
    content = Column(Text, nullable=False)
    code_snippet = Column(Text, name="code_snippet")
    likes = Column(Integer, default=0, nullable=False)
    comments = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False, name="created_at")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False, name="updated_at")
    
    # Relationships
    user = relationship("User", back_populates="community_posts")
    post_likes = relationship("PostLike", back_populates="post")
    post_comments = relationship("PostComment", back_populates="post")

class PostLike(Base):
    __tablename__ = "post_likes"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, name="user_id")
    post_id = Column(String, ForeignKey("community_posts.id"), nullable=False, name="post_id")
    created_at = Column(DateTime, default=func.now(), nullable=False, name="created_at")
    
    # Relationships
    user = relationship("User", back_populates="post_likes")
    post = relationship("CommunityPost", back_populates="post_likes")

class PostComment(Base):
    __tablename__ = "post_comments"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, name="user_id")
    post_id = Column(String, ForeignKey("community_posts.id"), nullable=False, name="post_id")
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False, name="created_at")
    
    # Relationships
    user = relationship("User", back_populates="post_comments")
    post = relationship("CommunityPost", back_populates="post_comments")
