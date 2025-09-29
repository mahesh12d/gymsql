"""
Problem Queue API routes for SQL job processing with Redis backend
"""
import json
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime

from .database import get_db, SessionLocal
from .models import User, Problem, ProblemSubmissionQueue
from .auth import get_current_user
from .redis_config import queue_manager
from .secure_execution import secure_executor

# Pydantic models for requests/responses
class SubmitProblemRequest(BaseModel):
    problem_id: str
    sql_query: str

class ProblemSubmissionResponse(BaseModel):
    job_id: str
    status: str
    message: str

class JobResultResponse(BaseModel):
    job_id: str
    status: str
    success: bool = None
    result: Dict[str, Any] = None
    error_message: str = None
    execution_time_ms: int = None
    rows_returned: int = None
    completed_at: str = None

class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    submitted_at: str = None
    processing_started_at: str = None
    completed_at: str = None

# Create router
problem_queue_router = APIRouter(prefix="/api/problems", tags=["problem-queue"])

def persist_submission_to_db(job_data: Dict[str, Any]):
    """Background task to persist submission to PostgreSQL"""
    db = SessionLocal()
    try:
        submission = ProblemSubmissionQueue(
            id=job_data["job_id"],
            user_id=job_data["user_id"],
            problem_id=job_data["problem_id"],
            sql_query=job_data["sql_query"],
            status=job_data.get("status", "queued"),
            rows_returned=job_data.get("rows_returned"),
            execution_time_ms=job_data.get("execution_time_ms"),
            error_message=job_data.get("error_message"),
            result_data=job_data.get("result_data"),
            completed_at=datetime.fromisoformat(job_data["completed_at"]) if job_data.get("completed_at") else None
        )
        db.add(submission)
        db.commit()
    except Exception as e:
        print(f"Error persisting submission to database: {e}")
        db.rollback()
    finally:
        db.close()

def update_submission_in_db(job_id: str, update_data: Dict[str, Any]):
    """Background task to update submission in PostgreSQL"""
    db = SessionLocal()
    try:
        submission = db.query(ProblemSubmissionQueue).filter(
            ProblemSubmissionQueue.id == job_id
        ).first()
        
        if submission:
            for key, value in update_data.items():
                if hasattr(submission, key):
                    if key == "completed_at" and isinstance(value, str):
                        value = datetime.fromisoformat(value)
                    setattr(submission, key, value)
            db.commit()
    except Exception as e:
        print(f"Error updating submission in database: {e}")
        db.rollback()
    finally:
        db.close()

@problem_queue_router.post("/submit", response_model=ProblemSubmissionResponse)
def submit_problem(
    request: SubmitProblemRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Submit a SQL problem to the processing queue"""
    # Verify problem exists
    problem = db.query(Problem).filter(Problem.id == request.problem_id).first()
    if not problem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Problem not found"
        )
    
    # Submit to Redis queue
    job_id = queue_manager.submit_problem(
        user_id=current_user.id,
        problem_id=request.problem_id,
        sql_query=request.sql_query
    )
    
    # Schedule background persistence to PostgreSQL
    job_data = {
        "job_id": job_id,
        "user_id": current_user.id,
        "problem_id": request.problem_id,
        "sql_query": request.sql_query,
        "status": "queued"
    }
    background_tasks.add_task(persist_submission_to_db, job_data)
    
    return ProblemSubmissionResponse(
        job_id=job_id,
        status="queued",
        message="Problem submitted for processing"
    )

@problem_queue_router.get("/result/{job_id}", response_model=JobResultResponse)
def get_job_result(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get the result of a submitted job"""
    # First check Redis cache
    result = queue_manager.get_job_result(job_id)
    
    if result:
        # Check authorization - ensure user owns this job
        if result.get("user_id") != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"  # Don't reveal existence to unauthorized users
            )
        
        return JobResultResponse(
            job_id=job_id,
            status="completed",
            success=result["success"],
            result=result.get("result"),
            execution_time_ms=result.get("execution_time_ms"),
            rows_returned=result.get("rows_returned"),
            error_message=result.get("error_message"),  # Include error details from cache
            completed_at=result["completed_at"]
        )
    
    # Check if job is still processing
    status_info = queue_manager.get_job_status(job_id)
    if status_info and status_info.get("status") == "processing":
        # Check authorization for processing jobs too
        if status_info.get("user_id") != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
        
        return JobResultResponse(
            job_id=job_id,
            status="processing"
        )
    
    # Fallback to PostgreSQL for historical results
    submission = db.query(ProblemSubmissionQueue).filter(
        ProblemSubmissionQueue.id == job_id,
        ProblemSubmissionQueue.user_id == current_user.id  # Security: only user's own jobs
    ).first()
    
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    return JobResultResponse(
        job_id=job_id,
        status=submission.status,
        success=submission.status == "completed",
        result=submission.result_data,
        error_message=submission.error_message,
        execution_time_ms=submission.execution_time_ms,
        rows_returned=submission.rows_returned,
        completed_at=submission.completed_at.isoformat() if submission.completed_at else None
    )

@problem_queue_router.get("/status/{job_id}", response_model=JobStatusResponse)
def get_job_status(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get the current status of a submitted job"""
    # Check Redis first
    status_info = queue_manager.get_job_status(job_id)
    
    if status_info:
        # Check authorization
        if status_info.get("user_id") != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
        
        return JobStatusResponse(
            job_id=job_id,
            status=status_info["status"],
            submitted_at=status_info.get("submitted_at"),
            processing_started_at=status_info.get("processing_started_at"),
            completed_at=status_info.get("completed_at")
        )
    
    # Fallback to PostgreSQL
    submission = db.query(ProblemSubmissionQueue).filter(
        ProblemSubmissionQueue.id == job_id,
        ProblemSubmissionQueue.user_id == current_user.id  # Security: only user's own jobs
    ).first()
    
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    return JobStatusResponse(
        job_id=job_id,
        status=submission.status,
        submitted_at=submission.created_at.isoformat(),
        completed_at=submission.completed_at.isoformat() if submission.completed_at else None
    )

# Admin endpoint to get queue statistics
@problem_queue_router.get("/admin/queue-stats")
def get_queue_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get queue statistics (admin only)"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    try:
        # Get queue length from Redis
        queue_length = queue_manager.redis.llen("problems:queue")
        
        # Get processing jobs count
        processing_keys = queue_manager.redis.keys("problems:processing:*")
        processing_count = len(processing_keys)
        
        # Get recent submissions from DB
        recent_submissions = db.query(ProblemSubmissionQueue).order_by(
            ProblemSubmissionQueue.created_at.desc()
        ).limit(10).all()
        
        recent_stats = []
        for sub in recent_submissions:
            recent_stats.append({
                "job_id": sub.id,
                "user_id": sub.user_id,
                "problem_id": sub.problem_id,
                "status": sub.status,
                "created_at": sub.created_at.isoformat(),
                "execution_time_ms": sub.execution_time_ms
            })
        
        return {
            "queue_length": queue_length,
            "processing_count": processing_count,
            "recent_submissions": recent_stats
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting queue stats: {str(e)}"
        )