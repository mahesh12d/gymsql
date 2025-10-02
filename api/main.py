"""
FastAPI application - converted from Express.js backend
"""
import os
import json
import asyncio
from typing import List, Optional, Dict
from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, case, and_, desc, Boolean, Integer
from datetime import timedelta, datetime
import random

from .database import get_db, create_tables
from .models import (User, Problem, Submission, CommunityPost, PostLike, PostComment, Solution,
                     ProblemInteraction, ProblemSession, UserBadge, Badge, Base)
from .schemas import (UserCreate, UserResponse, UserLogin, LoginResponse,
                      RegisterResponse, ProblemResponse, SubmissionCreate,
                      SubmissionResponse, DetailedSubmissionResponse, CommunityPostCreate,
                      CommunityPostResponse, PostCommentCreate,
                      PostCommentResponse, SolutionResponse, QuestionData)
from .auth import (get_password_hash, verify_password, create_access_token,
                   get_current_user, get_current_user_optional)
from .secure_execution import secure_executor
from .sandbox_routes import sandbox_router
from .admin_routes import admin_router
from .models import ProblemSubmissionQueue
from .redis_service import redis_service
import hashlib

# Helper function for time tracking
def track_first_query(user_id: str, problem_id: str, db: Session):
    """Track when user first runs a query on a problem"""
    # Check if session already exists
    session = db.query(ProblemSession).filter(
        ProblemSession.user_id == user_id,
        ProblemSession.problem_id == problem_id
    ).first()
    
    if not session:
        # Create new session
        session = ProblemSession(
            user_id=user_id,
            problem_id=problem_id,
            first_query_at=func.now()
        )
        db.add(session)
        db.commit()
    elif session.first_query_at is None:
        # Update existing session with first query time
        session.first_query_at = func.now()
        db.commit()

def track_successful_submission(user_id: str, problem_id: str, db: Session):
    """Track when user successfully submits a solution and calculate total time"""
    session = db.query(ProblemSession).filter(
        ProblemSession.user_id == user_id,
        ProblemSession.problem_id == problem_id
    ).first()
    
    from datetime import datetime
    now = datetime.now()
    
    is_first_solve = False
    
    if not session:
        # Create new session for direct submissions (no prior testing)
        session = ProblemSession(
            user_id=user_id,
            problem_id=problem_id,
            first_query_at=now,  # Backfill with submission time
            completed_at=now,
            total_time_spent_seconds=0  # Immediate submission
        )
        db.add(session)
        db.commit()
        is_first_solve = True
    elif session.completed_at is None:
        # Update existing session with completion
        session.completed_at = now
        
        # Calculate total time spent if first_query_at exists
        if session.first_query_at:
            time_diff = session.completed_at - session.first_query_at
            session.total_time_spent_seconds = int(time_diff.total_seconds())
        else:
            # Backfill missing first_query_at
            session.first_query_at = now
            session.total_time_spent_seconds = 0
        
        session.updated_at = func.now()
        db.commit()
        is_first_solve = True
    
    # Increment Redis leaderboard on first solve
    if is_first_solve:
        # Get problem details for topic-based leaderboard
        problem = db.query(Problem).filter(Problem.id == problem_id).first()
        topic = problem.tags[0] if problem and problem.tags else None
        
        redis_service.increment_leaderboard(user_id, problem_id, score=1, topic=topic)

# Create FastAPI app
app = FastAPI(title="SQLGym API",
              description="A gamified SQL learning platform API",
              version="1.0.0")

# Add CORS middleware - Updated for Railway + Vercel/Netlify deployment
frontend_origins = [
    "http://localhost:5000", 
    "http://localhost:3000",  # Local React development
    "https://*.replit.dev", 
    "https://*.replit.app",
    "https://*.replit.co",
    "https://*.vercel.app",   # Vercel deployments
    "https://*.netlify.app",  # Netlify deployments
    "https://*.netlify.com"   # Netlify custom domains
]

# Add production frontend domains from environment variables
if os.getenv("FRONTEND_URL"):
    frontend_origins.append(os.getenv("FRONTEND_URL"))

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

# Global exception handler for UTF-8 encoding issues
from fastapi.responses import JSONResponse
@app.exception_handler(UnicodeDecodeError)
async def unicode_decode_error_handler(request, exc: UnicodeDecodeError):
    """Handle UTF-8 encoding errors by returning sanitized JSON response"""
    from .secure_execution import sanitize_json_data
    error_data = {
        "error": "Encoding error occurred",
        "detail": "The response contains non-UTF-8 data that has been sanitized",
        "status_code": 500
    }
    return JSONResponse(
        status_code=500,
        content=sanitize_json_data(error_data),
        headers={"Content-Type": "application/json; charset=utf-8"}
    )


# Include routers
app.include_router(sandbox_router)
app.include_router(admin_router)

# Include additional routers
from .user_routes import user_router

app.include_router(user_router)



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


@app.on_event("startup")  
async def startup_event():
    try:
        print("🚀 Starting database initialization...")
        create_tables()  # Create all tables
        print("✅ Database initialization completed")
        
    except Exception as e:
        print(f"⚠️ Startup initialization failed, continuing anyway: {e}")
        # Continue startup even if initialization fails


# Development/fallback root endpoint
# Health check endpoint
@app.get("/api/health")
def health_check():
    return {"status": "healthy", "service": "SQLGym API", "version": "1.0.0"}


# Root API endpoint to handle HEAD/GET requests to /api
@app.get("/api")
@app.head("/api")
def api_root():
    return {"message": "SQLGym API", "version": "1.0.0", "status": "running"}


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


# Redis leaderboard sync endpoint (admin-only)
@app.post("/api/admin/sync-leaderboard")
def sync_leaderboard(current_user: User = Depends(get_current_user), 
                     db: Session = Depends(get_db)):
    """Sync Redis leaderboard from PostgreSQL database (global + topics)"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    if not redis_service.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis service unavailable"
        )
    
    try:
        # Sync global leaderboard
        users = db.query(User).filter(User.problems_solved > 0).all()
        user_scores = [
            {"user_id": str(user.id), "score": user.problems_solved}
            for user in users
        ]
        redis_service.sync_leaderboard_from_db(user_scores)
        
        # Sync solved problems sets for idempotency
        successful_submissions = db.query(Submission).filter(
            Submission.is_correct == True
        ).all()
        
        solved_data = [
            {"user_id": str(sub.user_id), "problem_id": str(sub.problem_id)}
            for sub in successful_submissions
        ]
        redis_service.sync_solved_sets(solved_data)
        
        return {
            "success": True,
            "message": f"Leaderboard synced: {len(user_scores)} users, {len(successful_submissions)} solved problems",
            "users_synced": len(user_scores),
            "solved_problems_synced": len(successful_submissions)
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Leaderboard sync failed: {str(e)}"
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
        # Handle JSON parsing for question field if it's a string
        import json
        if isinstance(problem.question, str):
            try:
                problem.question = json.loads(problem.question)
            except (json.JSONDecodeError, TypeError):
                # If parsing fails, create a default QuestionData structure
                problem.question = {
                    "description": "Error loading problem description",
                    "tables": [],
                    "expectedOutput": []
                }
        
        problem_data = ProblemResponse.from_orm(problem)
        problem_data.solved_count = int(solved_count)
        problem_data.is_user_solved = bool(
            is_user_solved) if current_user else False
        
        # Add bookmark and like status for authenticated users
        if current_user:
            # Check if user has interactions with this problem
            interaction = db.query(ProblemInteraction).filter(
                ProblemInteraction.user_id == current_user.id,
                ProblemInteraction.problem_id == problem.id
            ).first()
            
            problem_data.is_bookmarked = interaction.bookmark if interaction else False
            problem_data.is_liked = interaction.upvote if interaction else False
        else:
            problem_data.is_bookmarked = False
            problem_data.is_liked = False
        
        # Get total likes count for this problem
        likes_count = db.query(ProblemInteraction).filter(
            ProblemInteraction.problem_id == problem.id,
            ProblemInteraction.upvote == True
        ).count()
        problem_data.likes_count = likes_count
        
        # Use expected_display for user-facing expected output (separate from validation)
        if hasattr(problem, 'expected_display') and problem.expected_display is not None:
            problem_data.expected_output = problem.expected_display
        elif hasattr(problem, 'expected_output') and problem.expected_output is not None:
            # Fallback to legacy expected_output field for backward compatibility
            problem_data.expected_output = problem.expected_output
        else:
            # No expected output available for display
            problem_data.expected_output = []
            
        # Clear master_solution from user response - this should only be used during submission validation
        problem_data.master_solution = None
        
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


# Migration endpoint (temporary - for migrating to unified interactions)
@app.post("/api/admin/migrate-interactions")
def migrate_to_unified_interactions(db: Session = Depends(get_db)):
    """Admin endpoint to migrate bookmark and like data to unified ProblemInteraction table"""
    try:
        # Create the new table if it doesn't exist
        Base.metadata.create_all(bind=db.bind)
        
        # Get all existing bookmarks and likes (legacy tables may not exist)
        try:
            # Try to import old models if they still exist in database
            from sqlalchemy import text
            bookmarks = []
            likes = []
            
            # Check if old tables still exist before querying
            result = db.execute(text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'problem_bookmarks')"))
            if result.scalar():
                bookmarks = db.execute(text("SELECT user_id, problem_id, created_at FROM problem_bookmarks")).fetchall()
            
            result = db.execute(text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'problem_likes')"))
            if result.scalar():
                likes = db.execute(text("SELECT user_id, problem_id, created_at FROM problem_likes")).fetchall()
                
        except Exception as e:
            print(f"Legacy tables not found or error accessing them: {e}")
            bookmarks = []
            likes = []
        
        # Create a dictionary to track user-problem combinations
        interactions = {}
        
        # Process bookmarks
        for bookmark in bookmarks:
            key = (bookmark.user_id, bookmark.problem_id)
            if key not in interactions:
                interactions[key] = {
                    'user_id': bookmark.user_id,
                    'problem_id': bookmark.problem_id,
                    'bookmark': True,
                    'upvote': False,
                    'downvote': False,
                    'created_at': bookmark.created_at
                }
            else:
                interactions[key]['bookmark'] = True
                if bookmark.created_at < interactions[key]['created_at']:
                    interactions[key]['created_at'] = bookmark.created_at
        
        # Process likes (convert to upvotes)
        for like in likes:
            key = (like.user_id, like.problem_id)
            if key not in interactions:
                interactions[key] = {
                    'user_id': like.user_id,
                    'problem_id': like.problem_id,
                    'bookmark': False,
                    'upvote': True,
                    'downvote': False,
                    'created_at': like.created_at
                }
            else:
                interactions[key]['upvote'] = True
                if like.created_at < interactions[key]['created_at']:
                    interactions[key]['created_at'] = like.created_at
        
        # Insert into ProblemInteraction table
        migrated_count = 0
        for interaction_data in interactions.values():
            # Check if this interaction already exists
            existing = db.query(ProblemInteraction).filter(
                ProblemInteraction.user_id == interaction_data['user_id'],
                ProblemInteraction.problem_id == interaction_data['problem_id']
            ).first()
            
            if not existing:
                new_interaction = ProblemInteraction(
                    user_id=interaction_data['user_id'],
                    problem_id=interaction_data['problem_id'],
                    bookmark=interaction_data['bookmark'],
                    upvote=interaction_data['upvote'],
                    downvote=interaction_data['downvote'],
                    created_at=interaction_data['created_at']
                )
                db.add(new_interaction)
                migrated_count += 1
        
        db.commit()
        
        # Verify migration
        total_interactions = db.query(ProblemInteraction).count()
        bookmark_count = db.query(ProblemInteraction).filter(ProblemInteraction.bookmark == True).count()
        upvote_count = db.query(ProblemInteraction).filter(ProblemInteraction.upvote == True).count()
        
        return {
            "success": True,
            "message": f"Successfully migrated {migrated_count} interactions",
            "stats": {
                "total_interactions": total_interactions,
                "with_bookmarks": bookmark_count,
                "with_upvotes": upvote_count,
                "original_bookmarks": len(bookmarks),
                "original_likes": len(likes)
            }
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                          detail=f"Migration failed: {str(e)}")

# Unified Problem Interaction endpoints (bookmark, upvote, downvote)
@app.post("/api/problems/{problem_id}/bookmark")
def toggle_bookmark(problem_id: str,
                   current_user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    """Toggle bookmark status for a problem"""
    # Check if problem exists
    problem = db.query(Problem).filter(Problem.id == problem_id).first()
    if not problem:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Problem not found")
    
    # Get or create interaction record
    interaction = db.query(ProblemInteraction).filter(
        ProblemInteraction.user_id == current_user.id,
        ProblemInteraction.problem_id == problem_id
    ).first()
    
    if not interaction:
        # Create new interaction with bookmark
        interaction = ProblemInteraction(
            user_id=current_user.id,
            problem_id=problem_id,
            bookmark=True,
            upvote=False,
            downvote=False
        )
        db.add(interaction)
        bookmarked = True
        message = "Problem bookmarked"
    else:
        # Toggle bookmark status
        interaction.bookmark = not interaction.bookmark
        bookmarked = interaction.bookmark
        message = "Problem bookmarked" if bookmarked else "Bookmark removed"
        
        # If no interactions left, delete the record
        if not interaction.bookmark and not interaction.upvote and not interaction.downvote:
            db.delete(interaction)
    
    db.commit()
    return {"bookmarked": bookmarked, "message": message}

@app.post("/api/problems/{problem_id}/upvote")
def toggle_upvote(problem_id: str,
                 current_user: User = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    """Toggle upvote status for a problem"""
    # Check if problem exists
    problem = db.query(Problem).filter(Problem.id == problem_id).first()
    if not problem:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Problem not found")
    
    # Get or create interaction record
    interaction = db.query(ProblemInteraction).filter(
        ProblemInteraction.user_id == current_user.id,
        ProblemInteraction.problem_id == problem_id
    ).first()
    
    if not interaction:
        # Create new interaction with upvote
        interaction = ProblemInteraction(
            user_id=current_user.id,
            problem_id=problem_id,
            bookmark=False,
            upvote=True,
            downvote=False
        )
        db.add(interaction)
        upvoted = True
        message = "Problem upvoted"
    else:
        # Toggle upvote status and ensure mutual exclusion with downvote
        if interaction.upvote:
            # Remove upvote
            interaction.upvote = False
            upvoted = False
            message = "Upvote removed"
        else:
            # Add upvote and remove downvote if present
            interaction.upvote = True
            interaction.downvote = False
            upvoted = True
            message = "Problem upvoted"
        
        # If no interactions left, delete the record
        if not interaction.bookmark and not interaction.upvote and not interaction.downvote:
            db.delete(interaction)
    
    db.commit()
    
    # Get current upvote count
    upvote_count = db.query(ProblemInteraction).filter(
        ProblemInteraction.problem_id == problem_id,
        ProblemInteraction.upvote == True
    ).count()
    
    return {"upvoted": upvoted, "upvote_count": upvote_count, "message": message}

@app.post("/api/problems/{problem_id}/downvote")
def toggle_downvote(problem_id: str,
                   current_user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    """Toggle downvote status for a problem"""
    # Check if problem exists
    problem = db.query(Problem).filter(Problem.id == problem_id).first()
    if not problem:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Problem not found")
    
    # Get or create interaction record
    interaction = db.query(ProblemInteraction).filter(
        ProblemInteraction.user_id == current_user.id,
        ProblemInteraction.problem_id == problem_id
    ).first()
    
    if not interaction:
        # Create new interaction with downvote
        interaction = ProblemInteraction(
            user_id=current_user.id,
            problem_id=problem_id,
            bookmark=False,
            upvote=False,
            downvote=True
        )
        db.add(interaction)
        downvoted = True
        message = "Problem downvoted"
    else:
        # Toggle downvote status and ensure mutual exclusion with upvote
        if interaction.downvote:
            # Remove downvote
            interaction.downvote = False
            downvoted = False
            message = "Downvote removed"
        else:
            # Add downvote and remove upvote if present
            interaction.downvote = True
            interaction.upvote = False
            downvoted = True
            message = "Problem downvoted"
        
        # If no interactions left, delete the record
        if not interaction.bookmark and not interaction.upvote and not interaction.downvote:
            db.delete(interaction)
    
    db.commit()
    return {"downvoted": downvoted, "message": message}

# Legacy endpoints (maintain compatibility during transition)
@app.post("/api/problems/{problem_id}/like")
def toggle_like_legacy(problem_id: str,
                      current_user: User = Depends(get_current_user),
                      db: Session = Depends(get_db)):
    """Legacy like endpoint - redirects to upvote"""
    return toggle_upvote(problem_id, current_user, db)


@app.get("/api/problems/{problem_id}",
         response_model=ProblemResponse,
         response_model_by_alias=True)
def get_problem(problem_id: str, 
                current_user: Optional[User] = Depends(get_current_user_optional),
                db: Session = Depends(get_db)):
    from .s3_service import s3_service
    import logging
    
    logger = logging.getLogger(__name__)
    
    problem = db.query(Problem).filter(Problem.id == problem_id).first()
    if not problem:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Problem not found")
    
    # Handle JSON parsing for question field if it's a string
    import json
    if isinstance(problem.question, str):
        try:
            problem.question = json.loads(problem.question)
        except (json.JSONDecodeError, TypeError):
            # If parsing fails, create a default QuestionData structure
            problem.question = {
                "description": "Error loading problem description",
                "tables": [],
                "expectedOutput": []
            }
    
    # Premium access is handled at frontend level - no backend modification needed
    
    # Create response from ORM
    problem_data = ProblemResponse.from_orm(problem)
    
    # Add interaction status for authenticated users
    if current_user:
        # Check user's interaction with this problem
        interaction = db.query(ProblemInteraction).filter(
            ProblemInteraction.user_id == current_user.id,
            ProblemInteraction.problem_id == problem_id
        ).first()
        
        if interaction:
            problem_data.is_bookmarked = interaction.bookmark
            problem_data.is_upvoted = interaction.upvote
            problem_data.is_downvoted = interaction.downvote
        else:
            problem_data.is_bookmarked = False
            problem_data.is_upvoted = False
            problem_data.is_downvoted = False
        
        # For backward compatibility, set is_liked = is_upvoted
        problem_data.is_liked = problem_data.is_upvoted
    else:
        problem_data.is_bookmarked = False
        problem_data.is_upvoted = False
        problem_data.is_downvoted = False
        problem_data.is_liked = False
    
    # Get total upvotes count for this problem
    upvotes_count = db.query(ProblemInteraction).filter(
        ProblemInteraction.problem_id == problem_id,
        ProblemInteraction.upvote == True
    ).count()
    problem_data.upvotes_count = upvotes_count
    
    # For backward compatibility, set likes_count = upvotes_count
    problem_data.likes_count = upvotes_count
    
    # Use expected_display for user-facing expected output (separate from validation)
    if hasattr(problem, 'expected_display') and problem.expected_display is not None:
        problem_data.expected_output = problem.expected_display
        logger.info(f"Using expected_display with {len(problem.expected_display)} rows for user display")
    elif hasattr(problem, 'expected_output') and problem.expected_output is not None:
        # Fallback to legacy expected_output field for backward compatibility
        problem_data.expected_output = problem.expected_output
        logger.info(f"Using legacy expected_output field with {len(problem.expected_output)} rows")
    else:
        # No expected output available for display
        problem_data.expected_output = []
        logger.warning(f"No expected display output found for problem {problem_id}")
        
    # Clear master_solution from user response - this should only be used during submission validation
    problem_data.master_solution = None
    
    return problem_data


# New secure execution endpoints with job queue for burst protection
@app.post("/api/problems/{problem_id}/submit")
async def submit_solution(problem_id: str,
                          query_data: dict,
                          current_user: User = Depends(get_current_user),
                          db: Session = Depends(get_db)):
    """Submit SQL query to job queue for asynchronous evaluation (protects DB from bursts)"""
    # Rate limiting: Check per-user submission rate (10 submissions per minute)
    rate_limit = redis_service.check_rate_limit(
        user_id=current_user.id,
        action="submit",
        limit=10,
        window_seconds=60
    )
    
    if not rate_limit["allowed"]:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Please wait {rate_limit['retry_after']} seconds before submitting again.",
            headers={"Retry-After": str(rate_limit["retry_after"])}
        )
    
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

    # Check if Redis is available for job queue
    if not redis_service.is_available():
        # Fallback to direct execution if Redis is unavailable
        result = await secure_executor.submit_solution(current_user.id, problem_id,
                                                       query, db)

        if not result['success']:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail=result.get('feedback',
                                                  ['Submission failed'])[0])

        # Track successful submission for recommendation system
        if result['success']:
            track_successful_submission(current_user.id, problem_id, db)

        # Add console output to submission response
        result['console_output'] = format_console_output(result)
        
        # Sanitize result to prevent JSON serialization errors
        from .secure_execution import sanitize_json_data
        return sanitize_json_data(result)
    
    # Enqueue submission to Redis job queue
    try:
        job_id = redis_service.enqueue_submission(
            user_id=current_user.id,
            problem_id=problem_id,
            sql_query=query
        )
        
        return {
            "success": True,
            "job_id": job_id,
            "status": "queued",
            "message": "Submission queued for processing. Poll /api/jobs/{job_id}/status for results."
        }
        
    except Exception as e:
        # Fallback to direct execution on queue error
        result = await secure_executor.submit_solution(current_user.id, problem_id,
                                                       query, db)
        if result['success']:
            track_successful_submission(current_user.id, problem_id, db)
        result['console_output'] = format_console_output(result)
        from .secure_execution import sanitize_json_data
        return sanitize_json_data(result)


# PostgreSQL sandbox functionality removed - using DuckDB only
# Redirect to DuckDB sandbox endpoints in /api/sandbox/duckdb/


@app.post("/api/problems/{problem_id}/test")
async def test_query(problem_id: str,
                     query_data: dict,
                     current_user: User = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    """Test query without submitting (practice mode) - with Redis caching"""
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

    # Create cache key using query hash for exact match caching
    query_hash = hashlib.md5(query.encode()).hexdigest()[:12]
    cache_key = f"{current_user.id}:{problem_id}:{query_hash}"
    
    # Check Redis cache first (10 min TTL for test queries)
    cached_result = redis_service.get_cached_result(cache_key, "query")
    
    if cached_result:
        # Return cached result immediately
        print(f"✅ Cache HIT for query hash {query_hash}")
        return cached_result

    # Track first query time for recommendation system
    track_first_query(current_user.id, problem_id, db)

    # Cache MISS - execute query
    print(f"⚠️  Cache MISS - executing query")
    result = await secure_executor.test_query(current_user.id, problem_id,
                                              query, db, include_hidden)

    # Extract results from nested query_result structure
    query_result = result.get('query_result', {})
    results_data = query_result.get('result', []) if query_result else []
    execution_time = query_result.get('execution_time_ms', 0) if query_result else 0
    
    response_data = {
        "success": result['success'],
        "results": results_data,  # Raw data for table
        "execution_time_ms": execution_time,
        "rows_affected": len(results_data),
        "console_info": format_console_output(result),  # Just metadata
        "feedback": result.get('feedback', []),
        "test_results": result.get('test_results', []),
        "error": result.get('error')
    }
    
    # Cache successful test results (10 minutes TTL)
    if result['success']:
        redis_service.cache_result(
            cache_key,
            "query",
            response_data,
            ttl_seconds=600
        )
    
    # Sanitize result to prevent JSON serialization errors
    from .secure_execution import sanitize_json_data
    return sanitize_json_data(response_data)


@app.get("/api/user/progress")
async def get_user_progress(current_user: User = Depends(get_current_user),
                            db: Session = Depends(get_db)):
    """Get comprehensive user progress statistics"""
    result = await secure_executor.get_user_progress(current_user.id, db)

    if not result['success']:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=result.get('error',
                                              'Progress data not found'))

    # Sanitize result to prevent JSON serialization errors
    from .secure_execution import sanitize_json_data
    return sanitize_json_data(result)


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
         response_model=List[DetailedSubmissionResponse],
         response_model_by_alias=True)
def get_problem_submissions(problem_id: str,
                           current_user: User = Depends(get_current_user),
                           db: Session = Depends(get_db)):
    """Get user's submissions for a specific problem"""
    from sqlalchemy.orm import joinedload
    
    submissions = db.query(Submission).options(
        joinedload(Submission.execution_results)
    ).filter(
        Submission.user_id == current_user.id,
        Submission.problem_id == problem_id
    ).order_by(desc(Submission.submitted_at)).all()

    return [DetailedSubmissionResponse.from_orm(sub) for sub in submissions]


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
    """Get the official solution for a specific problem - uses admin-configured source"""
    from .s3_service import s3_service
    import logging
    from pathlib import Path
    
    logger = logging.getLogger(__name__)
    
    # First get the problem to check admin's solution source choice
    problem = db.query(Problem).filter(Problem.id == problem_id).first()
    if not problem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Problem not found"
        )
    
    # Check if problem has solution_source attribute (legacy support)
    solution_source = getattr(problem, 'solution_source', None)
    s3_solution_source = getattr(problem, 's3_solution_source', None)
    
    logger.info(f"Problem {problem_id} solution_source: {solution_source}")
    
    # Admin-controlled hybrid logic: check the solution_source field
    if solution_source == 's3' and s3_solution_source:
        logger.info(f"Using S3 solution source for problem {problem_id}")
        
        try:
            # Extract S3 solution source info configured by admin
            s3_solution_data = s3_solution_source
            bucket = s3_solution_data.get('bucket')
            solution_key = s3_solution_data.get('key')
            
            if not bucket or not solution_key:
                logger.warning(f"Invalid S3 solution source configuration for problem {problem_id}")
                # Fall through to database solution
            else:
                logger.info(f"Looking for solution at s3://{bucket}/{solution_key}")
                
                # Validate and get info about the solution parquet file
                try:
                    validation_result = s3_service.validate_dataset_file(bucket, solution_key, 'solution')
                    if validation_result and validation_result.get('success'):
                        solution_row_count = validation_result.get('row_count', 0)
                        sample_data = validation_result.get('sample_data', [])
                        
                        # Create a synthetic user for S3-based solutions
                        synthetic_creator = UserResponse(
                            id="system",
                            username="system",
                            email="system@platform.com",
                            firstName="System",
                            lastName="Generated",
                            profileImageUrl=None
                        )
                        
                        # Create solution content showing the expected results
                        content_parts = [
                            f"This problem uses S3-based validation against expected results with {solution_row_count} rows.",
                            f"\nSolution data source: s3://{bucket}/{solution_key}",
                            "\nExpected results structure (sample):"
                        ]
                        
                        if sample_data:
                            for i, row in enumerate(sample_data[:3]):  # Show first 3 rows
                                content_parts.append(f"Row {i+1}: {row}")
                        
                        content = "\n".join(content_parts)
                        
                        solution_response = SolutionResponse(
                            id=f"s3_{problem_id}",
                            problemId=problem_id,
                            createdBy="system",
                            title="Official Solution (S3 Source)",
                            content=content,
                            sqlCode="-- This problem is validated against S3 parquet data\n-- Write your query to match the expected results structure shown above",
                            isOfficial=True,
                            createdAt=problem.created_at,
                            updatedAt=problem.updated_at,
                            creator=synthetic_creator
                        )
                        
                        logger.info(f"Successfully created solution response from S3 source for problem {problem_id}")
                        return solution_response
                        
                except Exception as e:
                    logger.warning(f"Failed to validate S3 solution source for problem {problem_id}: {e}")
                    # Fall through to database solution
                    
        except Exception as e:
            logger.warning(f"Failed to process S3 solution source for problem {problem_id}: {e}")
            # Fall through to database solution
            
    # Use database-based solution (either by admin choice or fallback)
    logger.info(f"Using database-based solution lookup for problem {problem_id}")
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


# Job status endpoints for async submission queue
@app.get("/api/jobs/{job_id}/status")
async def get_job_status(job_id: str, 
                        current_user: User = Depends(get_current_user),
                        db: Session = Depends(get_db)):
    """Poll job status and retrieve results when complete"""
    if not redis_service.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Job queue service unavailable"
        )
    
    # Security: Verify user owns this job
    job_owner = redis_service.get_job_owner(job_id)
    
    if not job_owner:
        # Job doesn't exist or expired
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found or expired"
        )
    
    if str(job_owner) != str(current_user.id):
        # Return 404 to avoid revealing job existence to unauthorized users
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found or expired"
        )
    
    # Get job status
    status = redis_service.get_job_status(job_id)
    
    if not status:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found or expired"
        )
    
    response = {
        "job_id": job_id,
        "status": status
    }
    
    # If completed, get the result
    if status == "completed":
        result = redis_service.get_job_result(job_id)
        
        if result:
            # Track successful submission for recommendation system
            if result.get('success') and result.get('is_correct'):
                problem_id = result.get('problem_id') or result.get('submission', {}).get('problem_id')
                if problem_id:
                    track_successful_submission(current_user.id, problem_id, db)
            
            # Add console output
            result['console_output'] = format_console_output(result)
            
            # Sanitize and return result
            from .secure_execution import sanitize_json_data
            response["result"] = sanitize_json_data(result)
        else:
            response["result"] = {
                "success": False,
                "error": "Result expired or not found"
            }
    
    return response


@app.get("/api/jobs/{job_id}/result")
async def get_job_result(job_id: str, 
                        current_user: User = Depends(get_current_user),
                        db: Session = Depends(get_db)):
    """Get job result directly (returns 404 if not complete)"""
    if not redis_service.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Job queue service unavailable"
        )
    
    # Security: Verify user owns this job
    job_owner = redis_service.get_job_owner(job_id)
    
    if not job_owner:
        # Job doesn't exist or expired
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found or expired"
        )
    
    if str(job_owner) != str(current_user.id):
        # Return 404 to avoid revealing job existence to unauthorized users
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found or expired"
        )
    
    result = redis_service.get_job_result(job_id)
    
    if not result:
        status = redis_service.get_job_status(job_id)
        if status == "queued" or status == "processing":
            raise HTTPException(
                status_code=status.HTTP_202_ACCEPTED,
                detail=f"Job still {status}, please wait"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job result not found or expired"
            )
    
    # Track successful submission for recommendation system
    if result.get('success') and result.get('is_correct'):
        problem_id = result.get('problem_id') or result.get('submission', {}).get('problem_id')
        if problem_id:
            track_successful_submission(current_user.id, problem_id, db)
    
    # Add console output
    result['console_output'] = format_console_output(result)
    
    # Sanitize and return result
    from .secure_execution import sanitize_json_data
    return sanitize_json_data(result)


# Leaderboard endpoints (Redis-powered for high performance)
@app.get("/api/leaderboard",
         response_model=List[UserResponse],
         response_model_by_alias=True)
def get_leaderboard(limit: Optional[int] = Query(50),
                    db: Session = Depends(get_db)):
    """Get global leaderboard - uses Redis sorted sets for O(log N) performance"""
    
    # Try Redis first (fast path)
    if redis_service.is_available():
        redis_leaderboard = redis_service.get_global_leaderboard(limit=limit)
        
        if redis_leaderboard:
            # Fetch user details from database
            user_ids = [entry["user_id"] for entry in redis_leaderboard]
            users = db.query(User).filter(User.id.in_(user_ids)).all()
            
            # Create user lookup for ordering
            user_map = {str(user.id): user for user in users}
            
            # Return ordered by Redis leaderboard
            ordered_users = []
            for entry in redis_leaderboard:
                user_id = entry["user_id"]
                if user_id in user_map:
                    ordered_users.append(user_map[user_id])
            
            return [UserResponse.from_orm(user) for user in ordered_users]
    
    # Fallback to PostgreSQL (if Redis unavailable)
    users = db.query(User).order_by(desc(
        User.problems_solved)).limit(limit).all()

    return [UserResponse.from_orm(user) for user in users]


@app.get("/api/leaderboard/topic/{topic}")
def get_topic_leaderboard(topic: str,
                          limit: Optional[int] = Query(50),
                          db: Session = Depends(get_db)):
    """Get topic-specific leaderboard (e.g., 'joins', 'aggregation')"""
    
    if not redis_service.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Leaderboard service temporarily unavailable"
        )
    
    redis_leaderboard = redis_service.get_topic_leaderboard(topic, limit=limit)
    
    if not redis_leaderboard:
        return []
    
    # Fetch user details
    user_ids = [entry["user_id"] for entry in redis_leaderboard]
    users = db.query(User).filter(User.id.in_(user_ids)).all()
    
    # Create user lookup
    user_map = {str(user.id): user for user in users}
    
    # Return ordered users with scores
    result = []
    for entry in redis_leaderboard:
        user_id = entry["user_id"]
        if user_id in user_map:
            user_data = UserResponse.from_orm(user_map[user_id]).dict()
            user_data["leaderboard_score"] = entry["score"]
            result.append(user_data)
    
    return result


@app.get("/api/leaderboard/user/{user_id}")
def get_user_leaderboard_rank(user_id: str, db: Session = Depends(get_db)):
    """Get user's rank and score on global and topic leaderboards"""
    
    # Check if user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    if not redis_service.is_available():
        # Fallback to database count
        rank_data = db.query(func.count(User.id)).filter(
            User.problems_solved > user.problems_solved
        ).scalar()
        return {
            "global_rank": rank_data + 1 if rank_data else 1,
            "global_score": user.problems_solved,
            "topic_ranks": []
        }
    
    # Get global rank from Redis
    global_rank_data = redis_service.get_user_rank(user_id)
    
    # Get topic ranks (if user has solved problems in topics)
    topic_ranks = []
    # You could extend this to track which topics the user has solved
    
    return {
        "user_id": user_id,
        "username": user.username,
        "global_rank": global_rank_data["rank"] if global_rank_data else None,
        "global_score": global_rank_data["score"] if global_rank_data else 0,
        "topic_ranks": topic_ranks
    }


# Helpful Links endpoints
@app.get("/api/helpful-links",
         response_model=List,
         response_model_by_alias=True)
def get_helpful_links(db: Session = Depends(get_db)):
    """Get all helpful links - visible to all users"""
    from .models import HelpfulLink
    from .schemas import HelpfulLinkResponse
    
    links = db.query(HelpfulLink).options(
        joinedload(HelpfulLink.user)
    ).order_by(desc(HelpfulLink.created_at)).limit(10).all()
    
    return [HelpfulLinkResponse.from_orm(link) for link in links]


@app.post("/api/helpful-links",
          response_model=dict,
          response_model_by_alias=True)
def create_helpful_link(
    link_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new helpful link - premium users only"""
    from .models import HelpfulLink
    from .schemas import HelpfulLinkCreate
    
    # Check if user is premium
    if not current_user.premium:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only premium users can post helpful links"
        )
    
    # Validate input
    link_create = HelpfulLinkCreate(**link_data)
    
    # Create the link
    new_link = HelpfulLink(
        user_id=current_user.id,
        title=link_create.title,
        url=link_create.url
    )
    
    db.add(new_link)
    db.commit()
    db.refresh(new_link)
    
    return {"success": True, "id": new_link.id}


@app.delete("/api/helpful-links/{link_id}")
def delete_helpful_link(
    link_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a helpful link - only the creator or admin can delete"""
    from .models import HelpfulLink
    
    link = db.query(HelpfulLink).filter(HelpfulLink.id == link_id).first()
    
    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Link not found"
        )
    
    # Check if user is the creator or an admin
    if link.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own links"
        )
    
    db.delete(link)
    db.commit()
    
    return {"success": True}


# Community endpoints
@app.get("/api/community/posts",
         response_model=List[CommunityPostResponse],
         response_model_by_alias=True)
def get_community_posts(current_user: Optional[User] = Depends(get_current_user_optional),
                        db: Session = Depends(get_db)):
    posts = db.query(CommunityPost).options(
        joinedload(CommunityPost.user),
        joinedload(CommunityPost.problem)
    ).order_by(desc(CommunityPost.created_at)).all()

    # Filter out posts related to premium problems for non-premium users
    filtered_posts = []
    for post in posts:
        # If post is not related to any problem, include it
        if not post.problem:
            filtered_posts.append(post)
        # If post is related to a non-premium problem, include it
        elif not post.problem.premium:
            filtered_posts.append(post)
        # If post is related to a premium problem, only include it if user has premium access
        elif current_user and current_user.premium:
            filtered_posts.append(post)
        # Otherwise, exclude the post

    # Get liked posts for the current user
    liked_post_ids = set()
    if current_user:
        liked_posts = db.query(PostLike.post_id).filter(
            PostLike.user_id == current_user.id
        ).all()
        # Normalize to strings to ensure type consistency
        liked_post_ids = {str(like.post_id) for like in liked_posts}

    # Build response with liked status
    response = []
    for post in filtered_posts:
        post_response = CommunityPostResponse.from_orm(post)
        # Set the liked status directly as an attribute (compare as strings)
        post_response.liked_by_current_user = str(post.id) in liked_post_ids
        response.append(post_response)
    
    return response


@app.post("/api/community/posts",
          response_model=CommunityPostResponse,
          response_model_by_alias=True)
def create_community_post(post_data: CommunityPostCreate,
                          current_user: User = Depends(get_current_user),
                          db: Session = Depends(get_db)):
    # Check if user is trying to create a post about a premium problem
    if post_data.problem_id:
        problem = db.query(Problem).filter(Problem.id == post_data.problem_id).first()
        if problem and problem.premium and not current_user.premium:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Premium subscription required to create discussions for this problem"
            )

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
    # Check if post is related to a premium problem and user has access
    post = db.query(CommunityPost).options(joinedload(CommunityPost.problem)).filter(
        CommunityPost.id == post_id).first()
    
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    
    # Check premium access for posts related to premium problems
    if post.problem and post.problem.premium and not current_user.premium:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Premium subscription required to interact with this discussion"
        )

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

    # Update post likes count (we already have the post from above)
    post.likes = (post.likes or 0) + 1

    db.commit()
    return {"message": "Post liked successfully"}


@app.delete("/api/community/posts/{post_id}/like")
def unlike_post(post_id: str,
                current_user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    # Check if post is related to a premium problem and user has access
    post = db.query(CommunityPost).options(joinedload(CommunityPost.problem)).filter(
        CommunityPost.id == post_id).first()
    
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    
    # Check premium access for posts related to premium problems
    if post.problem and post.problem.premium and not current_user.premium:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Premium subscription required to interact with this discussion"
        )

    # Find and delete like
    like = db.query(PostLike).filter(
        and_(PostLike.user_id == current_user.id,
             PostLike.post_id == post_id)).first()

    if not like:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Like not found")

    db.delete(like)

    # Update post likes count (we already have the post from above)
    post.likes = max(0, (post.likes or 0) - 1)

    db.commit()
    return {"message": "Post unliked successfully"}


@app.get("/api/community/posts/{post_id}/comments",
         response_model=List[PostCommentResponse],
         response_model_by_alias=True)
def get_post_comments(post_id: str, 
                      current_user: Optional[User] = Depends(get_current_user_optional),
                      db: Session = Depends(get_db)):
    # Check if post is related to a premium problem and user has access
    post = db.query(CommunityPost).options(joinedload(CommunityPost.problem)).filter(
        CommunityPost.id == post_id).first()
    
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    
    # Check premium access for posts related to premium problems
    if post.problem and post.problem.premium and (not current_user or not current_user.premium):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Premium subscription required to view comments on this discussion"
        )

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
    # Check if post is related to a premium problem and user has access
    post = db.query(CommunityPost).options(joinedload(CommunityPost.problem)).filter(
        CommunityPost.id == post_id).first()
    
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    
    # Check premium access for posts related to premium problems
    if post.problem and post.problem.premium and not current_user.premium:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Premium subscription required to comment on this discussion"
        )

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

# User Profile API routes for comprehensive profile data
@app.get("/api/user/profile")
async def get_user_profile(current_user: User = Depends(get_current_user),
                          db: Session = Depends(get_db)):
    """Get comprehensive user profile with enhanced statistics"""
    from sqlalchemy import func, case, distinct
    from datetime import datetime, timedelta
    
    user_id = current_user.id
    
    # Basic user info
    basic_stats = {
        'user_id': user_id,
        'username': current_user.username,
        'email': current_user.email,
        'first_name': current_user.first_name,
        'last_name': current_user.last_name,
        'company_name': current_user.company_name,
        'linkedin_url': current_user.linkedin_url,
        'profile_image_url': current_user.profile_image_url,
        'problems_solved': current_user.problems_solved or 0,
        'premium': current_user.premium,
        'created_at': current_user.created_at
    }
    
    # Performance stats
    total_submissions = db.query(Submission).filter(Submission.user_id == user_id).count()
    correct_submissions = db.query(Submission).filter(
        Submission.user_id == user_id,
        Submission.is_correct == True
    ).count()
    
    accuracy = (correct_submissions / total_submissions * 100) if total_submissions > 0 else 0
    
    # Difficulty breakdown
    difficulty_stats = db.query(
        Problem.difficulty,
        func.count(distinct(Problem.id)).label('solved_count')
    ).join(Submission, Submission.problem_id == Problem.id).filter(
        Submission.user_id == user_id,
        Submission.is_correct == True
    ).group_by(Problem.difficulty).all()
    
    difficulty_breakdown = {
        'Easy': 0,
        'Medium': 0, 
        'Hard': 0
    }
    for stat in difficulty_stats:
        # Normalize difficulty to title case to match the expected format
        normalized_difficulty = stat.difficulty.capitalize() if stat.difficulty else None
        if normalized_difficulty in difficulty_breakdown:
            difficulty_breakdown[normalized_difficulty] = stat.solved_count
    
    # Topic breakdown - Get all solved problems and process tags manually
    solved_problems_with_tags = db.query(Problem.tags).join(
        Submission, Submission.problem_id == Problem.id
    ).filter(
        Submission.user_id == user_id,
        Submission.is_correct == True
    ).all()
    
    # Process tags to get topic breakdown
    topic_breakdown = {}
    for problem in solved_problems_with_tags:
        if problem.tags and isinstance(problem.tags, list):
            for tag in problem.tags:
                if tag:  # Skip empty tags
                    topic_breakdown[tag] = topic_breakdown.get(tag, 0) + 1
    
    # Recent activity (last 5 successful submissions)
    recent_activity = db.query(Submission, Problem.title, Problem.difficulty).join(
        Problem, Submission.problem_id == Problem.id
    ).filter(
        Submission.user_id == user_id,
        Submission.is_correct == True
    ).order_by(desc(Submission.submitted_at)).limit(5).all()
    
    recent_submissions = []
    for submission, title, difficulty in recent_activity:
        recent_submissions.append({
            'problem_title': title,
            'difficulty': difficulty,
            'submitted_at': submission.submitted_at,
            'execution_time': submission.execution_time
        })
    
    # Calculate streaks
    recent_submissions_all = db.query(Submission).filter(
        Submission.user_id == user_id
    ).order_by(desc(Submission.submitted_at)).limit(50).all()
    
    current_streak = 0
    longest_streak = 0
    temp_streak = 0
    
    for submission in recent_submissions_all:
        if submission.is_correct:
            temp_streak += 1
            if temp_streak > longest_streak:
                longest_streak = temp_streak
        else:
            if current_streak == 0:  # First streak we're calculating
                current_streak = temp_streak
            temp_streak = 0
    
    if current_streak == 0:  # If we haven't hit an incorrect submission yet
        current_streak = temp_streak
    
    # Performance over time (last 30 days)
    thirty_days_ago = datetime.now() - timedelta(days=30)
    daily_progress = db.query(
        func.date(Submission.submitted_at).label('date'),
        func.count(case((Submission.is_correct == True, 1))).label('solved_count')
    ).filter(
        Submission.user_id == user_id,
        Submission.submitted_at >= thirty_days_ago
    ).group_by(func.date(Submission.submitted_at)).order_by('date').all()
    
    progress_over_time = []
    for entry in daily_progress:
        progress_over_time.append({
            'date': entry.date.isoformat(),
            'solved_count': entry.solved_count
        })
    
    # User badges (if any exist)
    user_badges = db.query(UserBadge, Badge).join(
        Badge, UserBadge.badge_id == Badge.id
    ).filter(UserBadge.user_id == user_id).all()
    
    badges = []
    for user_badge, badge in user_badges:
        badges.append({
            'id': badge.id,
            'name': badge.name,
            'description': badge.description,
            'icon_url': badge.icon_url,
            'rarity': badge.rarity,
            'earned_at': user_badge.earned_at
        })
    
    # Calculate rank in leaderboard
    users_above = db.query(User).filter(
        User.problems_solved > current_user.problems_solved
    ).count()
    rank = users_above + 1
    
    # Get total user count for rank display
    total_users = db.query(User).count()
    
    return {
        'success': True,
        'basic_info': basic_stats,
        'performance_stats': {
            'total_submissions': total_submissions,
            'correct_submissions': correct_submissions,
            'accuracy_rate': round(accuracy, 1),
            'current_streak': current_streak,
            'longest_streak': longest_streak,
            'rank': rank,
            'total_users': total_users
        },
        'difficulty_breakdown': difficulty_breakdown,
        'topic_breakdown': topic_breakdown,
        'recent_activity': recent_submissions,
        'progress_over_time': progress_over_time,
        'badges': badges
    }

@app.get("/api/user/profile/recommendations")
async def get_user_recommendations(current_user: User = Depends(get_current_user),
                                 db: Session = Depends(get_db)):
    """Get personalized recommendations for user improvement"""
    user_id = current_user.id
    
    # Find topics with low performance
    solved_problems = db.query(Problem.tags).join(
        Submission, Submission.problem_id == Problem.id
    ).filter(
        Submission.user_id == user_id,
        Submission.is_correct == True
    ).all()
    
    # Count solved problems by tag
    topic_solved_count = {}
    for problem in solved_problems:
        if problem.tags:
            for tag in problem.tags:
                topic_solved_count[tag] = topic_solved_count.get(tag, 0) + 1
    
    # Find all available topics from all problems
    all_problems_with_tags = db.query(Problem.tags).all()
    all_topic_set = set()
    for problem in all_problems_with_tags:
        if problem.tags and isinstance(problem.tags, list):
            for tag in problem.tags:
                if tag:  # Skip empty tags
                    all_topic_set.add(tag)
    
    weak_topics = []
    for topic in all_topic_set:
        solved_count = topic_solved_count.get(topic, 0)
        if solved_count <= 2:  # Less than 3 problems solved in this topic
            weak_topics.append({
                'topic': topic,
                'solved_count': solved_count,
                'recommendation': f"Practice more {topic} problems to improve"
            })
    
    # Recommend next difficulty level
    current_difficulty_counts = {
        'Easy': topic_solved_count.get('Easy', 0),
        'Medium': topic_solved_count.get('Medium', 0), 
        'Hard': topic_solved_count.get('Hard', 0)
    }
    
    next_difficulty = "Easy"
    if current_difficulty_counts['Easy'] >= 5:
        next_difficulty = "Medium"
    if current_difficulty_counts['Medium'] >= 3:
        next_difficulty = "Hard"
    
    # Get recommended problems
    recommended_problems = db.query(Problem).filter(
        Problem.difficulty == next_difficulty,
        ~Problem.id.in_(
            db.query(Submission.problem_id).filter(
                Submission.user_id == user_id,
                Submission.is_correct == True
            )
        )
    ).limit(5).all()
    
    recommendations = []
    for problem in recommended_problems:
        recommendations.append({
            'id': problem.id,
            'title': problem.title,
            'difficulty': problem.difficulty,
            'tags': problem.tags,
            'company': problem.company
        })
    
    return {
        'success': True,
        'weak_topics': weak_topics[:5],  # Top 5 weak areas
        'recommended_difficulty': next_difficulty,
        'recommended_problems': recommendations,
        'learning_path': f"Focus on {next_difficulty} problems, especially in: {', '.join([wt['topic'] for wt in weak_topics[:3]])}"
    }

# Enhanced discussion API routes for problem-specific discussions  
@app.get("/api/problems/{problem_id}/discussions", response_model=List[CommunityPostResponse])
def get_problem_discussions(
    problem_id: str,
    limit: int = Query(20, ge=1, le=100),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """Get discussions for a specific problem"""
    # First check if the problem exists and if it's premium
    problem = db.query(Problem).filter(Problem.id == problem_id).first()
    if not problem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Problem not found"
        )
    
    # For premium problems with non-premium users, return empty list
    # The frontend will handle showing the locked state UI
    if problem.premium and (not current_user or not current_user.premium):
        return []
    
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
    
    # Check premium access for premium problems
    if problem.premium and not current_user.premium:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Premium subscription required to create discussions for this problem"
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



@app.get("/api/users/search")
def search_users(
    q: str = Query(..., min_length=1),
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Search for users by username"""
    users = db.query(User).filter(
        and_(
            User.username.ilike(f"%{q}%"),
            User.id != current_user.id  # Exclude current user
        )
    ).limit(limit).all()
    
    return [
        {
            "id": user.id,
            "username": user.username,
            "profileImageUrl": user.profile_image_url,
            "problemsSolved": user.problems_solved
        }
        for user in users
    ]


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

    # Don't handle WebSocket routes
    if full_path.startswith("ws/"):
        raise HTTPException(status_code=404, detail="WebSocket endpoint not found")

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
