"""
DuckDB Sandbox API Routes for SQL Learning Platform
=================================================
Provides endpoints for managing DuckDB sandbox environments only.
PostgreSQL sandboxes have been removed.
"""

import asyncio
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .database import get_db
from .auth import get_current_user
from .models import User, TestCase, ExecutionResult, ExecutionStatus
from .schemas import (
    ExecutionResultCreate, 
    ExecutionResultResponse,
    TestCaseResponse
)
from .duckdb_sandbox import DuckDBSandbox, sandbox_manager as duckdb_sandbox_manager

# Create router
sandbox_router = APIRouter(prefix="/api/sandbox", tags=["sandbox"])

# ============================================================================
# DUCKDB-BASED SANDBOX ENDPOINTS
# ============================================================================

@sandbox_router.post("/duckdb/{problem_id}/create", response_model=Dict[str, Any])
async def create_duckdb_sandbox(
    problem_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new DuckDB sandbox for a problem with S3 data"""
    try:
        # Verify problem exists
        from .models import Problem
        problem = db.query(Problem).filter(Problem.id == problem_id).first()
        if not problem:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Problem not found"
            )
        
        # Create DuckDB sandbox
        sandbox = await duckdb_sandbox_manager.create_sandbox(current_user.id, problem_id)
        
        # Setup problem data using S3 datasets only
        s3_datasets = problem.s3_datasets if hasattr(problem, 's3_datasets') and problem.s3_datasets else None
        
        setup_result = await sandbox.setup_problem_data(problem_id, s3_datasets)
        
        if not setup_result["success"]:
            sandbox.cleanup()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=setup_result["error"]
            )
        
        # Get table info for user
        table_info = sandbox.get_table_info()
        
        response_data = {
            "success": True,
            "problem_id": problem_id,
            "sandbox_type": "duckdb",
            "data_source": setup_result.get("data_source"),
            "data_info": {
                "row_count": setup_result.get("row_count", 0),
                "schema": setup_result.get("schema", []),
                "tables": table_info.get("tables", [])
            },
            "message": "DuckDB sandbox created successfully"
        }
        
        # Sanitize result to prevent JSON serialization errors
        from .secure_execution import sanitize_json_data
        return sanitize_json_data(response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create DuckDB sandbox: {str(e)}"
        )

@sandbox_router.post("/duckdb/{problem_id}/execute", response_model=Dict[str, Any])
async def execute_duckdb_query(
    problem_id: str,
    query_data: Dict[str, str],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Execute SQL query in DuckDB sandbox against S3 data"""
    try:
        # Verify problem exists
        from .models import Problem
        problem = db.query(Problem).filter(Problem.id == problem_id).first()
        if not problem:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Problem not found"
            )
        
        # Get or create sandbox
        sandbox = duckdb_sandbox_manager.get_sandbox(current_user.id, problem_id)
        if not sandbox:
            sandbox = await duckdb_sandbox_manager.create_sandbox(current_user.id, problem_id)
            # Get S3 datasets for the problem
            s3_datasets = problem.s3_datasets if hasattr(problem, 's3_datasets') and problem.s3_datasets else None
            
            setup_result = await sandbox.setup_problem_data(problem_id, s3_datasets)
            if not setup_result["success"]:
                sandbox.cleanup()
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=setup_result["error"]
                )
        
        # Execute query
        query = query_data.get("query", "").strip()
        if not query:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Query is required"
            )
        
        result = sandbox.execute_query(query)
        
        response_data = {
            "problem_id": problem_id,
            "query": query,
            "sandbox_type": "duckdb",
            **result
        }
        
        # Sanitize result to prevent JSON serialization errors
        from .secure_execution import sanitize_json_data
        return sanitize_json_data(response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute DuckDB query: {str(e)}"
        )

@sandbox_router.get("/duckdb/{problem_id}/schema", response_model=Dict[str, Any])
async def get_duckdb_schema(
    problem_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get schema information for DuckDB sandbox"""
    try:
        # Get existing sandbox
        sandbox = duckdb_sandbox_manager.get_sandbox(current_user.id, problem_id)
        if not sandbox:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sandbox not found. Create a sandbox first."
            )
        
        # Get table information
        table_info = sandbox.get_table_info()
        
        response_data = {
            "problem_id": problem_id,
            "sandbox_type": "duckdb",
            **table_info
        }
        
        # Sanitize result to prevent JSON serialization errors
        from .secure_execution import sanitize_json_data
        return sanitize_json_data(response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get DuckDB schema: {str(e)}"
        )

@sandbox_router.delete("/duckdb/{problem_id}/cleanup")
async def cleanup_duckdb_sandbox(
    problem_id: str,
    current_user: User = Depends(get_current_user)
):
    """Clean up DuckDB sandbox for a specific problem"""
    try:
        duckdb_sandbox_manager.cleanup_sandbox(current_user.id, problem_id)
        
        response_data = {
            "message": f"DuckDB sandbox for problem {problem_id} cleaned up successfully",
            "problem_id": problem_id,
            "sandbox_type": "duckdb"
        }
        
        # Sanitize result to prevent JSON serialization errors
        from .secure_execution import sanitize_json_data
        return sanitize_json_data(response_data)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cleanup DuckDB sandbox: {str(e)}"
        )

@sandbox_router.get("/duckdb/{problem_id}/capabilities", response_model=Dict[str, Any])
async def get_duckdb_capabilities(
    problem_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get DuckDB sandbox capabilities information"""
    try:
        # Create temporary sandbox to get capabilities
        with DuckDBSandbox() as temp_sandbox:
            capabilities = temp_sandbox.get_sandbox_capabilities()
            return {
                "success": True,
                "problem_id": problem_id,
                "sandbox_type": "duckdb",
                **capabilities
            }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get DuckDB capabilities: {str(e)}"
        )

@sandbox_router.post("/duckdb/{problem_id}/test", response_model=Dict[str, Any])
async def test_duckdb_connection(
    problem_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Test DuckDB connection and S3 data accessibility"""
    try:
        # Verify problem exists
        from .models import Problem
        problem = db.query(Problem).filter(Problem.id == problem_id).first()
        if not problem:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Problem not found"
            )
        
        # Create temporary sandbox to test connection
        with DuckDBSandbox() as test_sandbox:
            # Get S3 datasets for testing
            s3_datasets = problem.s3_datasets if hasattr(problem, 's3_datasets') and problem.s3_datasets else None
            
            if not s3_datasets:
                return {
                    "success": False,
                    "message": "No S3 datasets configured for this problem",
                    "problem_id": problem_id,
                    "sandbox_type": "duckdb"
                }
            
            # Test data setup
            test_result = await test_sandbox.setup_problem_data(problem_id, s3_datasets)
            
            return {
                "success": test_result["success"],
                "message": test_result.get("message", "Connection test completed"),
                "problem_id": problem_id,
                "sandbox_type": "duckdb",
                "data_source": test_result.get("data_source"),
                "error": test_result.get("error") if not test_result["success"] else None
            }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to test DuckDB connection: {str(e)}"
        )

