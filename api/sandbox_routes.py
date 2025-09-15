"""
Sandbox API Routes for SQL Learning Platform
===========================================
Provides endpoints for managing user sandbox environments.
"""

import asyncio
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session

from .database import get_db
from .auth import get_current_user
from .models import User, UserSandbox, TestCase, ExecutionResult, SandboxStatus, ExecutionStatus
from .schemas import (
    UserSandboxResponse, 
    ExecutionResultCreate, 
    ExecutionResultResponse,
    TestCaseResponse
)
from .sandbox_manager import (
    create_user_sandbox,
    execute_sandbox_query,
    sandbox_manager,
    start_cleanup_scheduler
)

# Create router
sandbox_router = APIRouter(prefix="/api/sandbox", tags=["sandbox"])

# Global cleanup task
cleanup_task = None

@sandbox_router.on_event("startup")
async def start_sandbox_cleanup():
    """Start the sandbox cleanup scheduler"""
    global cleanup_task
    if cleanup_task is None:
        cleanup_task = asyncio.create_task(start_cleanup_scheduler())

@sandbox_router.post("/create", response_model=UserSandboxResponse)
async def create_sandbox(
    problem_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new sandbox environment for a user and problem"""
    try:
        # Verify problem exists
        from .models import Problem
        problem = db.query(Problem).filter(Problem.id == problem_id).first()
        if not problem:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Problem not found"
            )
        
        # Create sandbox
        sandbox = await create_user_sandbox(current_user.id, problem_id)
        
        return UserSandboxResponse(
            id=sandbox.id,
            user_id=sandbox.user_id,
            problem_id=sandbox.problem_id,
            database_name=sandbox.database_name,
            connection_string="[HIDDEN]",  # Never expose connection string
            status=sandbox.status,
            max_execution_time_seconds=sandbox.max_execution_time_seconds,
            max_memory_mb=sandbox.max_memory_mb,
            max_connections=sandbox.max_connections,
            expires_at=sandbox.expires_at,
            created_at=sandbox.created_at,
            last_accessed_at=sandbox.last_accessed_at
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create sandbox: {str(e)}"
        )

@sandbox_router.post("/execute", response_model=Dict[str, Any])
async def execute_query(
    sandbox_id: str,
    query: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Execute a SQL query in a sandbox environment"""
    try:
        # Verify sandbox exists and belongs to user
        sandbox = db.query(UserSandbox).filter(
            UserSandbox.id == sandbox_id,
            UserSandbox.user_id == current_user.id
        ).first()
        
        if not sandbox:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sandbox not found or access denied"
            )
        
        if sandbox.status != SandboxStatus.ACTIVE.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Sandbox is {sandbox.status}, not active"
            )
        
        # Execute query with timeout
        result, execution_status = await execute_sandbox_query(
            sandbox_id, 
            query, 
            sandbox.max_execution_time_seconds
        )
        
        return {
            "sandbox_id": sandbox_id,
            "query": query,
            "execution_status": execution_status.value,
            "result": result,
            "timestamp": sandbox.last_accessed_at.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute query: {str(e)}"
        )

@sandbox_router.get("/status/{sandbox_id}", response_model=UserSandboxResponse)
async def get_sandbox_status(
    sandbox_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get sandbox status and details"""
    try:
        sandbox = db.query(UserSandbox).filter(
            UserSandbox.id == sandbox_id,
            UserSandbox.user_id == current_user.id
        ).first()
        
        if not sandbox:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sandbox not found or access denied"
            )
        
        return UserSandboxResponse(
            id=sandbox.id,
            user_id=sandbox.user_id,
            problem_id=sandbox.problem_id,
            database_name=sandbox.database_name,
            connection_string="[HIDDEN]",  # Never expose connection string
            status=sandbox.status,
            max_execution_time_seconds=sandbox.max_execution_time_seconds,
            max_memory_mb=sandbox.max_memory_mb,
            max_connections=sandbox.max_connections,
            expires_at=sandbox.expires_at,
            created_at=sandbox.created_at,
            last_accessed_at=sandbox.last_accessed_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get sandbox status: {str(e)}"
        )

@sandbox_router.get("/list", response_model=list[UserSandboxResponse])
async def list_user_sandboxes(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all sandboxes for the current user"""
    try:
        sandboxes = db.query(UserSandbox).filter(
            UserSandbox.user_id == current_user.id
        ).order_by(UserSandbox.created_at.desc()).all()
        
        return [
            UserSandboxResponse(
                id=sandbox.id,
                user_id=sandbox.user_id,
                problem_id=sandbox.problem_id,
                database_name=sandbox.database_name,
                connection_string="[HIDDEN]",  # Never expose connection string
                status=sandbox.status,
                max_execution_time_seconds=sandbox.max_execution_time_seconds,
                max_memory_mb=sandbox.max_memory_mb,
                max_connections=sandbox.max_connections,
                expires_at=sandbox.expires_at,
                created_at=sandbox.created_at,
                last_accessed_at=sandbox.last_accessed_at
            )
            for sandbox in sandboxes
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list sandboxes: {str(e)}"
        )

@sandbox_router.delete("/cleanup/{sandbox_id}")
async def cleanup_sandbox(
    sandbox_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Manually cleanup a sandbox (mark for deletion)"""
    try:
        sandbox = db.query(UserSandbox).filter(
            UserSandbox.id == sandbox_id,
            UserSandbox.user_id == current_user.id
        ).first()
        
        if not sandbox:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sandbox not found or access denied"
            )
        
        if sandbox.status == SandboxStatus.EXPIRED.value:
            return {"message": "Sandbox already expired"}
        
        # Mark sandbox as cleanup pending
        sandbox.status = SandboxStatus.CLEANUP_PENDING.value
        sandbox.cleanup_scheduled_at = sandbox.last_accessed_at
        db.commit()
        
        # Schedule cleanup in background
        background_tasks.add_task(sandbox_manager.cleanup_expired_sandboxes)
        
        return {"message": "Sandbox cleanup scheduled"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cleanup sandbox: {str(e)}"
        )

@sandbox_router.get("/test-cases/{problem_id}", response_model=list[TestCaseResponse])
async def get_problem_test_cases(
    problem_id: str,
    include_hidden: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get test cases for a problem (excluding hidden ones by default)"""
    try:
        # Verify problem exists
        from .models import Problem
        problem = db.query(Problem).filter(Problem.id == problem_id).first()
        if not problem:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Problem not found"
            )
        
        # Get test cases
        query = db.query(TestCase).filter(TestCase.problem_id == problem_id)
        
        if not include_hidden:
            query = query.filter(TestCase.is_hidden == False)
        
        test_cases = query.order_by(TestCase.order_index).all()
        
        return [
            TestCaseResponse(
                id=tc.id,
                problem_id=tc.problem_id,
                name=tc.name,
                description=tc.description,
                input_data=tc.input_data,
                expected_output=tc.expected_output,
                validation_rules=tc.validation_rules,
                is_hidden=tc.is_hidden,
                order_index=tc.order_index,
                timeout_seconds=tc.timeout_seconds,
                memory_limit_mb=tc.memory_limit_mb,
                created_at=tc.created_at,
                updated_at=tc.updated_at
            )
            for tc in test_cases
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get test cases: {str(e)}"
        )

@sandbox_router.post("/validate/{sandbox_id}")
async def validate_submission(
    sandbox_id: str,
    query: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Validate a user's SQL submission against all test cases"""
    try:
        # Get sandbox and verify ownership
        sandbox = db.query(UserSandbox).filter(
            UserSandbox.id == sandbox_id,
            UserSandbox.user_id == current_user.id
        ).first()
        
        if not sandbox:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sandbox not found or access denied"
            )
        
        # Get all test cases for the problem
        test_cases = db.query(TestCase).filter(
            TestCase.problem_id == sandbox.problem_id
        ).order_by(TestCase.order_index).all()
        
        if not test_cases:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No test cases found for this problem"
            )
        
        validation_results = []
        passed_count = 0
        
        for test_case in test_cases:
            try:
                # Execute query
                result, execution_status = await execute_sandbox_query(
                    sandbox_id,
                    query,
                    test_case.timeout_seconds
                )
                
                # Basic validation - compare results
                is_correct = False
                validation_details = {}
                
                if execution_status == ExecutionStatus.SUCCESS:
                    expected = test_case.expected_output
                    actual = result.get('result', [])
                    
                    # Simple comparison (can be enhanced with custom validation rules)
                    is_correct = actual == expected
                    if is_correct:
                        passed_count += 1
                    
                    validation_details = {
                        "expected_rows": len(expected),
                        "actual_rows": len(actual),
                        "matches": is_correct
                    }
                else:
                    validation_details = {
                        "error": result.get('error', 'Unknown error'),
                        "status": execution_status.value
                    }
                
                validation_results.append({
                    "test_case_id": test_case.id,
                    "test_case_name": test_case.name,
                    "is_hidden": test_case.is_hidden,
                    "is_correct": is_correct,
                    "execution_status": execution_status.value,
                    "execution_time_ms": result.get('execution_time_ms', 0),
                    "validation_details": validation_details
                })
                
            except Exception as e:
                validation_results.append({
                    "test_case_id": test_case.id,
                    "test_case_name": test_case.name,
                    "is_hidden": test_case.is_hidden,
                    "is_correct": False,
                    "execution_status": "ERROR",
                    "error": str(e),
                    "validation_details": {"error": str(e)}
                })
        
        # Calculate overall score
        total_tests = len(test_cases)
        score_percentage = (passed_count / total_tests * 100) if total_tests > 0 else 0
        
        return {
            "sandbox_id": sandbox_id,
            "problem_id": sandbox.problem_id,
            "query": query,
            "total_test_cases": total_tests,
            "passed_test_cases": passed_count,
            "score_percentage": score_percentage,
            "is_solution_correct": passed_count == total_tests,
            "validation_results": validation_results,
            "timestamp": sandbox.last_accessed_at.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate submission: {str(e)}"
        )