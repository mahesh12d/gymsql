"""
FastAPI application - converted from Express.js backend
"""
import os
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, case, and_, desc, Boolean, Integer
from datetime import timedelta
import random

from .database import get_db, create_tables
from .models import User, Problem, Submission, CommunityPost, PostLike, PostComment, Solution
from .schemas import (UserCreate, UserResponse, UserLogin, LoginResponse,
                      RegisterResponse, ProblemResponse, SubmissionCreate,
                      SubmissionResponse, CommunityPostCreate,
                      CommunityPostResponse, PostCommentCreate,
                      PostCommentResponse, SolutionResponse, QuestionData)
from .auth import (get_password_hash, verify_password, create_access_token,
                   get_current_user, get_current_user_optional)
from .secure_execution import secure_executor
from .sandbox_routes import sandbox_router
from .admin_routes import admin_router

# Create FastAPI app
app = FastAPI(title="SQLGym API",
              description="A gamified SQL learning platform API",
              version="1.0.0")

# Add CORS middleware
frontend_origins = [
    "http://localhost:5000", "https://*.replit.dev", "https://*.replit.app",
    "https://*.replit.co"
]

# In production, use environment variable or specific domain
if os.getenv("REPL_ID"):
    repl_id = os.getenv("REPL_ID")
    username = os.getenv("REPL_OWNER", "user")
    frontend_origins.extend([
        f"https://{repl_id}--{username}.replit.app",
        f"https://{repl_id}.{username}.replit.dev"
    ])

app.add_middleware(
    CORSMiddleware,
    allow_origins=frontend_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["*"],
)

# Include routers
app.include_router(sandbox_router)
app.include_router(admin_router)


def format_console_output(execution_result):
    """Create lightweight console output for errors and metadata"""
    if not execution_result.get('success'):
        error_msg = execution_result.get('error', 'Unknown error')
        return f"ERROR: {error_msg}"
    
    # Extract results from query_result structure returned by secure_executor
    query_result = execution_result.get('query_result', {})
    results = query_result.get('result', []) if query_result else []
    exec_time = query_result.get('execution_time_ms', 0) if query_result else 0
    
    if not results:
        return f"Query executed successfully.\n0 rows returned.\nExecution time: {exec_time}ms"
    
    return f"Query executed successfully.\n{len(results)} rows returned.\nExecution time: {exec_time}ms"


# Create tables on startup
# @app.on_event("startup")  
# def startup_event():
#     try:
#         print("🚀 Starting database initialization...")
#         create_tables()  # Just create basic tables first
#         print("✅ Database initialization completed")
#     except Exception as e:
#         print(f"⚠️ Database initialization failed, continuing anyway: {e}")
#         # Continue startup even if database fails


# Development/fallback root endpoint
# Health check endpoint
@app.get("/api/health")
def health_check():
    return {"status": "healthy", "service": "SQLGym API", "version": "1.0.0"}


# Database initialization endpoint (admin-only, authenticated)
@app.post("/api/admin/init-db")
def initialize_database(current_user: User = Depends(get_current_user)):
    """Initialize database tables and schema. Admin-only endpoint for safe database setup."""
    # Check if user is admin
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required for database initialization"
        )
    
    try:
        print("🚀 Starting database initialization...")
        
        # Just create tables - skip complex migrations for now
        create_tables()
        print("✅ Database tables created")
        
        return {
            "success": True,
            "message": "Database initialized successfully",
            "operations": ["table_creation"]
        }
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database initialization failed: {str(e)}"
        )


# Root endpoint and SPA fallback
@app.get("/")
def read_root():
    if os.path.exists("dist/public/index.html"):
        return FileResponse("dist/public/index.html")
    return {
        "message": "SQLGym FastAPI Backend - Please run 'npm run build' first"
    }


# SPA fallback route will be defined at the very end of the file after all API routes


# Mount static assets for production
if os.path.exists("dist/public/assets"):
    app.mount("/assets",
              StaticFiles(directory="dist/public/assets"),
              name="assets")


# Authentication endpoints
@app.post("/api/auth/register",
          response_model=RegisterResponse,
          response_model_by_alias=True)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    # Check if user already exists
    existing_user = db.query(User).filter(
        User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="User already exists")

    # Check if username is taken
    existing_username = db.query(User).filter(
        User.username == user_data.username).first()
    if existing_username:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Username already taken")

    # Hash password if provided
    password_hash = None
    if user_data.password is not None:
        password_hash = get_password_hash(user_data.password)

    # Create user
    user = User(username=user_data.username,
                email=user_data.email,
                password_hash=password_hash,
                first_name=user_data.first_name,
                last_name=user_data.last_name,
                profile_image_url=user_data.profile_image_url,
                google_id=user_data.google_id,
                github_id=user_data.github_id,
                auth_provider=user_data.auth_provider)

    db.add(user)
    db.commit()
    db.refresh(user)

    # Generate JWT token
    access_token = create_access_token(data={
        "userId": user.id,
        "username": user.username,
        "isAdmin": user.is_admin
    })

    return RegisterResponse(token=access_token,
                            user=UserResponse.from_orm(user))


@app.post("/api/auth/login",
          response_model=LoginResponse,
          response_model_by_alias=True)
def login(login_data: UserLogin, db: Session = Depends(get_db)):
    # Find user by email
    user = db.query(User).filter(User.email == login_data.email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid credentials")

    # Verify password
    if not user.password_hash or not verify_password(login_data.password,
                                                     user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid credentials")

    # Generate JWT token
    access_token = create_access_token(data={
        "userId": user.id,
        "username": user.username,
        "isAdmin": user.is_admin
    })

    return LoginResponse(token=access_token, user=UserResponse.from_orm(user))


@app.get("/api/auth/user",
         response_model=UserResponse,
         response_model_by_alias=True)
def get_current_user_info(current_user: User = Depends(get_current_user)):
    return UserResponse.from_orm(current_user)


# Problem endpoints
@app.get("/api/problems",
         response_model=List[ProblemResponse],
         response_model_by_alias=True)
def get_problems(
        difficulty: Optional[str] = Query(None),
        company: Optional[str] = Query(None),
        premium: Optional[str] = Query(None),
        current_user: Optional[User] = Depends(get_current_user_optional),
        db: Session = Depends(get_db)):
    # Base query with solved count
    query = db.query(
        Problem,
        func.coalesce(
            func.count(
                case((Submission.is_correct == True, Submission.user_id),
                     else_=None).distinct()),
            0).label("solved_count")).outerjoin(Submission)

    # Add user-specific solved status if authenticated
    if current_user:
        query = query.add_columns(
            func.coalesce(
                func.max(
                    case((and_(Submission.user_id == current_user.id,
                               Submission.is_correct == True), 1),
                         else_=0)), 0).label("is_user_solved"))
    else:
        query = query.add_columns(
            func.cast(0, Integer).label("is_user_solved"))

    # Apply difficulty filter
    if difficulty:
        query = query.filter(Problem.difficulty == difficulty)

    # Apply company filter
    if company:
        query = query.filter(Problem.company == company)

    # Apply premium filter
    if premium:
        if premium.lower() == "free":
            query = query.filter(Problem.premium.is_(None) | Problem.premium.is_(False))
        elif premium.lower() == "premium":
            query = query.filter(Problem.premium.is_(True))

    # Group by problem and order by title
    results = query.group_by(Problem.id).order_by(Problem.title).all()

    # Format response
    problems = []
    for problem, solved_count, is_user_solved in results:
        problem_data = ProblemResponse.from_orm(problem)
        problem_data.solved_count = int(solved_count)
        problem_data.is_user_solved = bool(
            is_user_solved) if current_user else False
        
        # For premium problems, filter content for non-premium users
        if problem.premium is True and (not current_user or not current_user.premium):
            # Create a limited question data for premium problems
            limited_question = QuestionData(
                description="🔒 Premium Problem - Subscribe to view full description",
                tables=[],
                expectedOutput=[]
            )
            problem_data.question = limited_question
        
        problems.append(problem_data)

    return problems


@app.get("/api/problems/{problem_id}",
         response_model=ProblemResponse,
         response_model_by_alias=True)
def get_problem(problem_id: str, 
                current_user: Optional[User] = Depends(get_current_user_optional),
                db: Session = Depends(get_db)):
    problem = db.query(Problem).filter(Problem.id == problem_id).first()
    if not problem:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Problem not found")
    
    # Check if problem is premium and user doesn't have premium access
    if problem.premium is True and (not current_user or not current_user.premium):
        # Return problem with premium message instead of throwing error
        problem_data = ProblemResponse.from_orm(problem)
        premium_question = QuestionData(
            description="Want to lift try Premium 🏋️‍♂️",
            tables=[],
            expectedOutput=[]
        )
        problem_data.question = premium_question
        problem_data.hints = []  # Hide hints for non-premium users
        return problem_data
    
    return ProblemResponse.from_orm(problem)


# New secure execution endpoints
@app.post("/api/problems/{problem_id}/submit")
async def submit_solution(problem_id: str,
                          query_data: dict,
                          current_user: User = Depends(get_current_user),
                          db: Session = Depends(get_db)):
    """Submit and execute SQL query for final evaluation"""
    # Check if problem exists and is accessible
    problem = db.query(Problem).filter(Problem.id == problem_id).first()
    if not problem:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Problem not found")
    
    # Check if problem is premium and user doesn't have premium access
    if problem.premium is True and not current_user.premium:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Premium subscription required to submit solutions for this problem")
    
    query = query_data.get("query", "").strip()

    if not query:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Query is required")

    result = await secure_executor.submit_solution(current_user.id, problem_id,
                                                   query, db)

    if not result['success']:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=result.get('feedback',
                                              ['Submission failed'])[0])

    # Add console output to submission response
    result['console_output'] = format_console_output(result)
    return result


@app.get("/api/problems/{problem_id}/sandbox")
async def get_or_create_sandbox(problem_id: str,
                                current_user: User = Depends(get_current_user),
                                db: Session = Depends(get_db)):
    """Get or create user sandbox for a problem"""
    from .sandbox_manager import create_user_sandbox
    from .models import UserSandbox, SandboxStatus

    # Check if problem exists and is accessible
    problem = db.query(Problem).filter(Problem.id == problem_id).first()
    if not problem:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Problem not found")
    
    # Check if problem is premium and user doesn't have premium access
    if problem.premium is True and not current_user.premium:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Premium subscription required to access sandbox for this problem")

    # Check for existing active sandbox
    existing_sandbox = db.query(UserSandbox).filter(
        UserSandbox.user_id == current_user.id,
        UserSandbox.problem_id == problem_id,
        UserSandbox.status == SandboxStatus.ACTIVE.value).first()

    if existing_sandbox:
        return {
            "sandbox_id": existing_sandbox.id,
            "status": existing_sandbox.status,
            "expires_at": existing_sandbox.expires_at.isoformat(),
            "created_at": existing_sandbox.created_at.isoformat()
        }

    # Create new sandbox
    try:
        sandbox = await create_user_sandbox(current_user.id, problem_id)
        return {
            "sandbox_id": sandbox.id,
            "status": sandbox.status,
            "expires_at": sandbox.expires_at.isoformat(),
            "created_at": sandbox.created_at.isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Failed to create sandbox: {str(e)}")


@app.post("/api/problems/{problem_id}/test")
async def test_query(problem_id: str,
                     query_data: dict,
                     current_user: User = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    """Test query without submitting (practice mode)"""
    # Check if problem exists and is accessible
    problem = db.query(Problem).filter(Problem.id == problem_id).first()
    if not problem:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Problem not found")
    
    # Check if problem is premium and user doesn't have premium access
    if problem.premium is True and not current_user.premium:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Premium subscription required to test queries for this problem")
    
    query = query_data.get("query", "").strip()
    include_hidden = query_data.get("include_hidden", False)

    if not query:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Query is required")

    result = await secure_executor.test_query(current_user.id, problem_id,
                                              query, db, include_hidden)

    # Extract results from nested query_result structure
    query_result = result.get('query_result', {})
    results_data = query_result.get('result', []) if query_result else []
    execution_time = query_result.get('execution_time_ms', 0) if query_result else 0
    
    return {
        "success": result['success'],
        "results": results_data,  # Raw data for table
        "execution_time_ms": execution_time,
        "rows_affected": len(results_data),
        "console_info": format_console_output(result),  # Just metadata
        "feedback": result.get('feedback', []),
        "test_results": result.get('test_results', []),
        "error": result.get('error')
    }


@app.get("/api/user/progress")
async def get_user_progress(current_user: User = Depends(get_current_user),
                            db: Session = Depends(get_db)):
    """Get comprehensive user progress statistics"""
    result = await secure_executor.get_user_progress(current_user.id, db)

    if not result['success']:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=result.get('error',
                                              'Progress data not found'))

    return result


# Submission endpoints
@app.post("/api/submissions",
          response_model=SubmissionResponse,
          response_model_by_alias=True)
def create_submission(submission_data: SubmissionCreate,
                      current_user: User = Depends(get_current_user),
                      db: Session = Depends(get_db)):
    # Simulate SQL query execution (simplified version)
    problem = db.query(Problem).filter(
        Problem.id == submission_data.problem_id).first()
    if not problem:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Problem not found")

    # Simple validation logic (same as Express.js version)
    is_correct = simulate_query_execution(submission_data.query, problem)
    execution_time = random.randint(50, 550)  # Random execution time

    # Create submission
    submission = Submission(user_id=current_user.id,
                            problem_id=submission_data.problem_id,
                            query=submission_data.query,
                            is_correct=is_correct,
                            execution_time=execution_time)

    db.add(submission)
    db.commit()
    db.refresh(submission)

    # If correct, update user progress (check for duplicates after commit)
    if is_correct:
        # Check if this is the first time solving this problem
        existing_correct = db.query(Submission).filter(
            Submission.user_id == current_user.id,
            Submission.problem_id == submission_data.problem_id,
            Submission.is_correct == True,
            Submission.id != submission.id  # Exclude current submission
        ).first()
        
        if not existing_correct:
            # First time solving this problem
            current_user.problems_solved = (current_user.problems_solved or 0) + 1
            db.commit()
    db.refresh(submission)

    return SubmissionResponse.from_orm(submission)


@app.get("/api/submissions/user/{user_id}",
         response_model=List[SubmissionResponse],
         response_model_by_alias=True)
def get_user_submissions(user_id: str,
                         current_user: User = Depends(get_current_user),
                         db: Session = Depends(get_db)):
    # Users can only view their own submissions
    if user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Access denied")

    submissions = db.query(Submission).filter(
        Submission.user_id == user_id).order_by(desc(
            Submission.submitted_at)).all()

    return [SubmissionResponse.from_orm(sub) for sub in submissions]


@app.get("/api/problems/{problem_id}/submissions",
         response_model=List[SubmissionResponse],
         response_model_by_alias=True)
def get_problem_submissions(problem_id: str,
                           current_user: User = Depends(get_current_user),
                           db: Session = Depends(get_db)):
    """Get user's submissions for a specific problem"""
    submissions = db.query(Submission).filter(
        Submission.user_id == current_user.id,
        Submission.problem_id == problem_id
    ).order_by(desc(Submission.submitted_at)).all()

    return [SubmissionResponse.from_orm(sub) for sub in submissions]


@app.get("/api/problems/{problem_id}/solutions",
         response_model=List[SolutionResponse],
         response_model_by_alias=True)
def get_problem_solutions(problem_id: str, db: Session = Depends(get_db)):
    """Get all official solutions for a specific problem (public access)"""
    solutions = db.query(Solution).options(joinedload(Solution.creator)).filter(
        Solution.problem_id == problem_id,
        Solution.is_official == True  # Only show official solutions
    ).order_by(Solution.created_at.desc()).all()
    
    return [SolutionResponse.from_orm(solution) for solution in solutions]


@app.get("/api/problems/{problem_id}/official-solution",
         response_model=SolutionResponse,
         response_model_by_alias=True)
def get_official_solution(problem_id: str, db: Session = Depends(get_db)):
    """Get the official solution for a specific problem (returns single solution)"""
    solution = db.query(Solution).options(joinedload(Solution.creator)).filter(
        Solution.problem_id == problem_id,
        Solution.is_official == True
    ).order_by(Solution.created_at.desc()).first()
    
    if not solution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No official solution found for this problem"
        )
    
    return SolutionResponse.from_orm(solution)


# Leaderboard endpoint
@app.get("/api/leaderboard",
         response_model=List[UserResponse],
         response_model_by_alias=True)
def get_leaderboard(limit: Optional[int] = Query(50),
                    db: Session = Depends(get_db)):
    users = db.query(User).order_by(desc(
        User.problems_solved)).limit(limit).all()

    return [UserResponse.from_orm(user) for user in users]


# Community endpoints
@app.get("/api/community/posts",
         response_model=List[CommunityPostResponse],
         response_model_by_alias=True)
def get_community_posts(db: Session = Depends(get_db)):
    posts = db.query(CommunityPost).options(
        joinedload(CommunityPost.user),
        joinedload(CommunityPost.problem)
    ).order_by(desc(CommunityPost.created_at)).all()

    return [CommunityPostResponse.from_orm(post) for post in posts]


@app.post("/api/community/posts",
          response_model=CommunityPostResponse,
          response_model_by_alias=True)
def create_community_post(post_data: CommunityPostCreate,
                          current_user: User = Depends(get_current_user),
                          db: Session = Depends(get_db)):
    post = CommunityPost(user_id=current_user.id,
                         content=post_data.content,
                         code_snippet=post_data.code_snippet,
                         problem_id=post_data.problem_id)

    db.add(post)
    db.commit()
    db.refresh(post)

    # Load user relationship
    post = db.query(CommunityPost).options(joinedload(
        CommunityPost.user)).filter(CommunityPost.id == post.id).first()

    return CommunityPostResponse.from_orm(post)


@app.post("/api/community/posts/{post_id}/like")
def like_post(post_id: str,
              current_user: User = Depends(get_current_user),
              db: Session = Depends(get_db)):
    # Check if already liked
    existing_like = db.query(PostLike).filter(
        and_(PostLike.user_id == current_user.id,
             PostLike.post_id == post_id)).first()

    if existing_like:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Post already liked")

    # Create like
    like = PostLike(user_id=current_user.id, post_id=post_id)
    db.add(like)

    # Update post likes count
    post = db.query(CommunityPost).filter(CommunityPost.id == post_id).first()
    if post:
        post.likes = (post.likes or 0) + 1

    db.commit()
    return {"message": "Post liked successfully"}


@app.delete("/api/community/posts/{post_id}/like")
def unlike_post(post_id: str,
                current_user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    # Find and delete like
    like = db.query(PostLike).filter(
        and_(PostLike.user_id == current_user.id,
             PostLike.post_id == post_id)).first()

    if not like:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Like not found")

    db.delete(like)

    # Update post likes count
    post = db.query(CommunityPost).filter(CommunityPost.id == post_id).first()
    if post:
        post.likes = max(0, (post.likes or 0) - 1)

    db.commit()
    return {"message": "Post unliked successfully"}


@app.get("/api/community/posts/{post_id}/comments",
         response_model=List[PostCommentResponse],
         response_model_by_alias=True)
def get_post_comments(post_id: str, db: Session = Depends(get_db)):
    # Get all comments for the post
    all_comments = db.query(PostComment).options(joinedload(
        PostComment.user)).filter(PostComment.post_id == post_id).order_by(
            PostComment.created_at).all()
    
    # Build nested comment structure
    comment_map = {}
    root_comments = []
    
    # First pass: create comment objects
    for comment in all_comments:
        comment_response = PostCommentResponse.from_orm(comment)
        comment_map[comment.id] = comment_response
    
    # Second pass: build tree structure
    for comment in all_comments:
        comment_response = comment_map[comment.id]
        if comment.parent_id and comment.parent_id in comment_map:
            # This is a reply, add to parent's replies
            comment_map[comment.parent_id].replies.append(comment_response)
        else:
            # This is a root comment
            root_comments.append(comment_response)
    
    return root_comments


@app.post("/api/community/posts/{post_id}/comments",
          response_model=PostCommentResponse,
          response_model_by_alias=True)
def create_post_comment(post_id: str,
                        comment_data: PostCommentCreate,
                        current_user: User = Depends(get_current_user),
                        db: Session = Depends(get_db)):
    # Validate parent comment exists if parent_id is provided
    if comment_data.parent_id:
        parent_comment = db.query(PostComment).filter(
            and_(PostComment.id == comment_data.parent_id, PostComment.post_id == post_id)
        ).first()
        if not parent_comment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parent comment not found"
            )
    
    comment = PostComment(
        user_id=current_user.id,
        post_id=post_id,
        parent_id=comment_data.parent_id,
        content=comment_data.content
    )

    db.add(comment)

    # Update post comments count
    post = db.query(CommunityPost).filter(CommunityPost.id == post_id).first()
    if post:
        post.comments = (post.comments or 0) + 1

    db.commit()
    db.refresh(comment)

    # Load user relationship
    comment = db.query(PostComment).options(joinedload(
        PostComment.user)).filter(PostComment.id == comment.id).first()

    return PostCommentResponse.from_orm(comment)


# Solution API routes (public viewing)
@app.get("/api/problems/{problem_id}/solutions", response_model=List[SolutionResponse])
def get_problem_solutions_public(
    problem_id: str,
    db: Session = Depends(get_db)
):
    """Get all official solutions for a problem (public view)"""
    solutions = db.query(Solution).options(joinedload(Solution.creator)).filter(
        and_(Solution.problem_id == problem_id, Solution.is_official == True)
    ).order_by(Solution.created_at.desc()).all()
    
    return [SolutionResponse.from_orm(solution) for solution in solutions]

# Enhanced discussion API routes for problem-specific discussions  
@app.get("/api/problems/{problem_id}/discussions", response_model=List[CommunityPostResponse])
def get_problem_discussions(
    problem_id: str,
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get discussions for a specific problem"""
    posts = db.query(CommunityPost).options(
        joinedload(CommunityPost.user)
    ).filter(
        CommunityPost.problem_id == problem_id
    ).order_by(
        desc(CommunityPost.created_at)
    ).limit(limit).all()
    
    return [CommunityPostResponse.from_orm(post) for post in posts]

@app.post("/api/problems/{problem_id}/discussions", response_model=CommunityPostResponse)
def create_problem_discussion(
    problem_id: str,
    post_data: CommunityPostCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new discussion post for a specific problem"""
    # Verify problem exists
    problem = db.query(Problem).filter(Problem.id == problem_id).first()
    if not problem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Problem not found"
        )
    
    # Create discussion post
    post = CommunityPost(
        user_id=current_user.id,
        problem_id=problem_id,  # Link to problem
        content=post_data.content,
        code_snippet=post_data.code_snippet
    )
    
    db.add(post)
    db.commit()
    db.refresh(post)
    
    # Load user relationship
    post = db.query(CommunityPost).options(joinedload(CommunityPost.user)).filter(
        CommunityPost.id == post.id
    ).first()
    
    return CommunityPostResponse.from_orm(post)

# Get all community posts with optional problem filtering
@app.get("/api/community/posts/all", response_model=List[CommunityPostResponse])
def get_all_community_posts(
    problem_id: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get all community posts with optional problem filtering"""
    query = db.query(CommunityPost).options(joinedload(CommunityPost.user))
    
    if problem_id:
        query = query.filter(CommunityPost.problem_id == problem_id)
    
    posts = query.order_by(desc(CommunityPost.created_at)).limit(limit).all()
    
    return [CommunityPostResponse.from_orm(post) for post in posts]


# Helper function for query simulation
def simulate_query_execution(query: str, problem: Problem) -> bool:
    """
    Simplified query validation (same logic as Express.js version)
    """
    normalized_query = query.lower().strip()

    # Basic checks for different problem types
    if "sum" in problem.title.lower():
        return ("select" in normalized_query and "from" in normalized_query
                and ("sum" in normalized_query or "+" in normalized_query))

    if "join" in problem.title.lower():
        return ("select" in normalized_query and "from" in normalized_query
                and "join" in normalized_query)

    # Default validation: must contain SELECT and FROM
    return "select" in normalized_query and "from" in normalized_query


# SPA fallback route - handle all non-API routes (must be last)
# SPA fallback route - handle all non-API routes (must be last)
@app.get("/{full_path:path}")
def spa_fallback(full_path: str):
    # Don't handle API routes
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="API endpoint not found")

    # Don't handle asset files
    if full_path.startswith("assets/") or "." in full_path.split("/")[-1]:
        raise HTTPException(status_code=404, detail="File not found")

    # Serve SPA for all other routes
    index_path = "dist/public/index.html"
    if os.path.exists(index_path):
        return FileResponse(index_path)

    # Fallback if no built frontend
    raise HTTPException(status_code=404, detail="Frontend not built")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    host = "0.0.0.0" if os.getenv("REPL_ID") else "127.0.0.1"
    uvicorn.run(app, host=host, port=port)
