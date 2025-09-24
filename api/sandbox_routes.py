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
        
        # Setup problem data with question tables (preferred) or S3 data sources (fallback)
        s3_data_source = problem.s3_data_source if hasattr(problem, 's3_data_source') and problem.s3_data_source else None
        s3_datasets = problem.s3_datasets if hasattr(problem, 's3_datasets') and problem.s3_datasets else None
        question_tables = None
        
        # Extract tables from question field if available
        if hasattr(problem, 'question') and problem.question:
            question_tables = problem.question.get('tables', [])
        
        setup_result = await sandbox.setup_problem_data(problem_id, s3_data_source, s3_datasets, None, question_tables)
        
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
            # Get S3 data sources and question tables for the problem
            s3_data_source = problem.s3_data_source if hasattr(problem, 's3_data_source') and problem.s3_data_source else None
            s3_datasets = problem.s3_datasets if hasattr(problem, 's3_datasets') and problem.s3_datasets else None
            question_tables = None
            
            # Extract tables from question field if available
            if hasattr(problem, 'question') and problem.question:
                question_tables = problem.question.get('tables', [])
            
            setup_result = await sandbox.setup_problem_data(problem_id, s3_data_source, s3_datasets, None, question_tables)
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
            # Get S3 data source for testing
            s3_data_source = problem.s3_data_source if hasattr(problem, 's3_data_source') and problem.s3_data_source else None
            
            if not s3_data_source:
                return {
                    "success": False,
                    "message": "No S3 data source configured for this problem",
                    "problem_id": problem_id,
                    "sandbox_type": "duckdb"
                }
            
            # Extract question tables for testing
            question_tables = None
            if hasattr(problem, 'question') and problem.question:
                question_tables = problem.question.get('tables', [])
            
            # Test data setup
            test_result = await test_sandbox.setup_problem_data(problem_id, s3_data_source, None, question_tables)
            
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

@sandbox_router.post("/duckdb/{problem_id}/debug-datasets", response_model=Dict[str, Any])
async def debug_s3_datasets(
    problem_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Debug S3 datasets loading for problems that use s3_datasets instead of s3_data_source"""
    try:
        # Verify problem exists
        from .models import Problem
        problem = db.query(Problem).filter(Problem.id == problem_id).first()
        if not problem:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Problem not found"
            )
        
        # Create temporary sandbox to test s3_datasets loading
        with DuckDBSandbox() as test_sandbox:
            # Get both S3 configurations for comparison
            s3_data_source = problem.s3_data_source if hasattr(problem, 's3_data_source') and problem.s3_data_source else None
            s3_datasets = problem.s3_datasets if hasattr(problem, 's3_datasets') and problem.s3_datasets else None
            
            # Extract question tables
            question_tables = None
            if hasattr(problem, 'question') and problem.question:
                question_tables = problem.question.get('tables', [])
            
            # Test s3_datasets setup specifically
            test_result = await test_sandbox.setup_problem_data(problem_id, s3_data_source, s3_datasets, None, question_tables)
            
            # Get table list from sandbox after setup
            table_list = []
            if test_result["success"]:
                try:
                    # List all tables in the sandbox
                    tables_query_result = test_sandbox.conn.execute("SHOW TABLES").fetchall()
                    table_list = [row[0] for row in tables_query_result]
                except Exception as e:
                    table_list = [f"Error getting tables: {str(e)}"]
            
            return {
                "success": test_result["success"],
                "message": test_result.get("message", "Debug test completed"),
                "problem_id": problem_id,
                "sandbox_type": "duckdb",
                "s3_data_source_present": s3_data_source is not None,
                "s3_datasets_present": s3_datasets is not None,
                "s3_datasets_config": s3_datasets,
                "question_tables_present": question_tables is not None and len(question_tables) > 0,
                "data_source_used": test_result.get("data_source"),
                "tables_created": table_list,
                "tables_info": test_result.get("tables", []),
                "error": test_result.get("error") if not test_result["success"] else None,
                "full_result": test_result
            }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to debug S3 datasets: {str(e)}"
        )