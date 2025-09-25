"""
Admin routes for creating and managing problems
"""
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from sqlalchemy.orm import Session, joinedload
from pydantic import BaseModel, Field
import uuid
import duckdb
import logging
import pandas as pd
import pyarrow.parquet as pq
import io
import tempfile

from .database import get_db
from .models import Problem, Topic, Solution, User, TestCase
from .auth import verify_admin_access, verify_admin_user_access
from .schemas import DifficultyLevel, QuestionData, TableData, TableColumn, SolutionCreate, SolutionResponse, S3AnswerSource, S3DatasetSource
from .s3_service import s3_service
from .file_processor import file_processor

# Create admin router
admin_router = APIRouter(prefix="/api/admin", tags=["admin"])

# Admin schemas for question creation
class AdminTableColumn(BaseModel):
    name: str
    type: str
    description: str = ""


class AdminTableData(BaseModel):
    name: str
    columns: List[AdminTableColumn]
    sample_data: List[Dict[str, Any]] = []

class AdminQuestionData(BaseModel):
    description: str
    tables: List[AdminTableData] = []
    expected_output: Optional[List[Dict[str, Any]]] = Field(None, alias="expectedOutput")  # Optional for backward compatibility
    s3_data_source: Optional[S3DatasetSource] = None
    
    model_config = {"populate_by_name": True}

class AdminS3SolutionSource(BaseModel):
    bucket: str
    key: str
    description: Optional[str] = None

class AdminProblemCreate(BaseModel):
    title: str
    difficulty: str
    question: AdminQuestionData
    master_solution: Optional[List[Dict[str, Any]]] = Field(None, alias="masterSolution")  # New master solution field
    expected_display: Optional[List[Dict[str, Any]]] = Field(None, alias="expectedDisplay")  # Display output for users (not validation)
    s3_datasets: Optional[List[S3DatasetSource]] = None  # Multiple S3 dataset sources configuration
    tags: List[str] = []
    company: str = ""
    hints: List[str] = []
    premium: bool = False
    topic_id: str = ""
    solution_source: str = "neon"  # Always use 'neon' - S3 solutions deprecated

class SchemaInfo(BaseModel):
    """Response model for schema information"""
    problem_structure: Dict[str, Any]
    example_problem: Dict[str, Any]
    difficulty_options: List[str]
    available_topics: List[Dict[str, str]]

# Enhanced AWS S3 Question Creation Schemas
class S3SolutionSource(BaseModel):
    """Schema for S3 solution parquet file configuration"""
    bucket: str
    key: str  # S3 object key (file path) - must be .parquet
    description: Optional[str] = None
    etag: Optional[str] = None  # For cache validation

class EnhancedQuestionCreateRequest(BaseModel):
    """Enhanced request model for creating questions with S3 dataset and solution"""
    problem_id: str = Field(..., description="Unique problem identifier (e.g., 'q101')")
    title: str = Field(..., description="Problem title")
    difficulty: str = Field(..., description="Difficulty level: BEGINNER, EASY, MEDIUM, HARD, EXPERT")
    tags: List[str] = Field(default=[], description="Problem tags (e.g., ['window-function', 'ranking'])")
    dataset_path: str = Field(..., description="S3 path to dataset (e.g., 's3://bucket/problems/q101/dataset.parquet')")
    solution_path: str = Field(..., description="S3 path to solution parquet (e.g., 's3://bucket/problems/q101/out.parquet')")
    description: Optional[str] = Field(None, description="Problem description in markdown")
    hints: List[str] = Field(default=[], description="Helpful hints for solving the problem")
    company: Optional[str] = Field(None, description="Company name associated with the problem")
    premium: bool = Field(default=False, description="Whether this is a premium problem")
    topic_id: Optional[str] = Field(None, description="Topic ID to categorize the problem")

class EnhancedQuestionCreateResponse(BaseModel):
    """Response model for enhanced question creation"""
    success: bool
    message: str
    problem_id: str
    expected_hash: Optional[str] = None  # MD5 hash of sorted expected results
    preview_rows: List[Dict[str, Any]] = Field(default=[], description="First 5 rows of expected output")
    row_count: Optional[int] = None  # Total number of rows in expected output
    dataset_info: Optional[Dict[str, Any]] = None  # Dataset schema and sample data
    error: Optional[str] = None

# Multi-table S3 schemas
class MultiTableS3Dataset(BaseModel):
    """Schema for a single S3 dataset in multi-table configuration"""
    bucket: str = Field(..., description="S3 bucket name")
    key: str = Field(..., description="S3 object key (path to parquet file)")
    table_name: str = Field(..., description="Table name for DuckDB")
    description: Optional[str] = Field(None, description="Description of the dataset")

class MultiTableQuestionCreateRequest(BaseModel):
    """Request model for creating questions with multiple S3 datasets"""
    problem_id: str = Field(..., description="Unique problem identifier")
    title: str = Field(..., description="Problem title")
    difficulty: str = Field(..., description="Difficulty level: BEGINNER, EASY, MEDIUM, HARD, EXPERT")
    tags: List[str] = Field(default=[], description="Problem tags")
    datasets: List[MultiTableS3Dataset] = Field(..., description="List of S3 datasets for the question")
    solution_path: str = Field(..., description="S3 path to solution parquet file")
    description: Optional[str] = Field(None, description="Problem description in markdown")
    hints: List[str] = Field(default=[], description="Helpful hints")
    company: Optional[str] = Field(None, description="Company name")
    premium: bool = Field(default=False, description="Whether this is premium")
    topic_id: Optional[str] = Field(None, description="Topic ID")

class MultiTableValidationRequest(BaseModel):
    """Request model for validating multiple S3 datasets"""
    datasets: List[MultiTableS3Dataset] = Field(..., description="List of S3 datasets to validate")

class MultiTableValidationResponse(BaseModel):
    """Response model for multi-table S3 validation"""
    success: bool
    message: str
    validated_datasets: List[Dict[str, Any]] = Field(default=[], description="Information about validated datasets")
    total_tables: int = 0
    total_rows: int = 0
    error: Optional[str] = None

@admin_router.get("/schema-info", response_model=SchemaInfo)
def get_schema_info(
    _: bool = Depends(verify_admin_user_access),
    db: Session = Depends(get_db)
):
    """Get the exact schema structure and example for creating problems"""
    
    # Get available topics
    topics = db.query(Topic).all()
    available_topics = [{"id": topic.id, "name": topic.name} for topic in topics]
    
    problem_structure = {
        "title": "string (required) - The problem title",
        "difficulty": "string (required) - One of: BEGINNER, EASY, MEDIUM, HARD, EXPERT",
        "question": {
            "description": "string (required) - Problem description in markdown",
            "tables": [
                {
                    "name": "string (required) - Table name",
                    "columns": [
                        {
                            "name": "string (required) - Column name",
                            "type": "string (required) - SQL data type (e.g., INTEGER, VARCHAR, DATE)",
                            "description": "string (optional) - Column description"
                        }
                    ],
                    "sample_data": [
                        "object (optional) - Array of sample data objects"
                    ]
                }
            ],
            "expectedOutput": [
                "object (required) - Array of expected result objects"
            ]
        },
        "tags": ["array of strings (optional) - Problem tags"],
        "company": "string (optional) - Company name",
        "hints": ["array of strings (optional) - Helpful hints"],
        "premium": "boolean (optional) - Is premium problem",
        "topic_id": "string (optional) - Topic ID to categorize the problem"
    }
    
    example_problem = {
        "title": "Calculate Total Sales by Region",
        "difficulty": "Medium",
        "question": {
            "description": """
# Calculate Total Sales by Region

Write a SQL query to calculate the total sales amount for each region. The result should include:
- Region name
- Total sales amount (rounded to 2 decimal places)
- Number of orders

Order the results by total sales amount in descending order.

## Requirements:
- Use proper aggregation functions
- Round the total sales to 2 decimal places
- Include regions even if they have zero sales
            """.strip(),
            "tables": [
                {
                    "name": "orders",
                    "columns": [
                        {"name": "id", "type": "INTEGER", "description": "Order ID"},
                        {"name": "region", "type": "VARCHAR(50)", "description": "Sales region"},
                        {"name": "amount", "type": "DECIMAL(10,2)", "description": "Order amount"},
                        {"name": "order_date", "type": "DATE", "description": "Date of order"}
                    ],
                    "sample_data": [
                        {"id": 1, "region": "North", "amount": 1500.00, "order_date": "2024-01-15"},
                        {"id": 2, "region": "South", "amount": 2300.50, "order_date": "2024-01-16"},
                        {"id": 3, "region": "North", "amount": 800.25, "order_date": "2024-01-17"},
                        {"id": 4, "region": "East", "amount": 1200.00, "order_date": "2024-01-18"}
                    ]
                }
            ],
            "expectedOutput": [
                {"region": "South", "total_sales": 2300.50, "order_count": 1},
                {"region": "North", "total_sales": 2300.25, "order_count": 2},
                {"region": "East", "total_sales": 1200.00, "order_count": 1}
            ]
        },
        "tags": ["aggregation", "group-by", "sum", "count"],
        "company": "TechCorp",
        "hints": [
            "Use GROUP BY to group by region",
            "Use SUM() to calculate total sales",
            "Use COUNT() to count orders",
            "Use ROUND() to round to 2 decimal places",
            "Use ORDER BY with DESC for descending order"
        ],
        "premium": False,
        "topic_id": ""
    }
    
    return SchemaInfo(
        problem_structure=problem_structure,
        example_problem=example_problem,
        difficulty_options=["BEGINNER", "EASY", "MEDIUM", "HARD", "EXPERT"],
        available_topics=available_topics
    )


def _map_duckdb_type_to_sql(duckdb_type: str) -> str:
    """Map DuckDB data types to standard SQL types for problem creation"""
    type_lower = duckdb_type.lower().strip()
    
    # Integer types (including unsigned variants)
    if 'hugeint' in type_lower:
        return 'BIGINT'  # Closest equivalent
    elif 'bigint' in type_lower or 'int64' in type_lower:
        return 'BIGINT'
    elif 'ubigint' in type_lower:
        return 'BIGINT'  # Unsigned, but map to signed equivalent
    elif 'int' in type_lower or 'integer' in type_lower:
        return 'INTEGER'
    elif 'uinteger' in type_lower:
        return 'INTEGER'
    elif 'smallint' in type_lower or 'int16' in type_lower:
        return 'SMALLINT'
    elif 'usmallint' in type_lower:
        return 'SMALLINT'
    elif 'tinyint' in type_lower or 'int8' in type_lower:
        return 'TINYINT'
    elif 'utinyint' in type_lower:
        return 'TINYINT'
    
    # Floating point types
    elif 'double' in type_lower or 'float64' in type_lower:
        return 'DOUBLE'
    elif 'float' in type_lower or 'real' in type_lower or 'float32' in type_lower:
        return 'FLOAT'
    
    # Decimal/numeric types (preserve precision if possible)
    elif 'decimal' in type_lower or 'numeric' in type_lower:
        # Try to preserve precision/scale if specified
        if '(' in duckdb_type:
            return duckdb_type.upper()  # Keep original precision
        return 'DECIMAL'
    
    # String types
    elif 'varchar' in type_lower or 'string' in type_lower or 'text' in type_lower:
        # Preserve length if specified
        if '(' in duckdb_type and 'varchar' in type_lower:
            return duckdb_type.upper()
        return 'VARCHAR'
    elif 'char' in type_lower:
        if '(' in duckdb_type:
            return duckdb_type.upper()
        return 'CHAR'
    elif 'clob' in type_lower:
        return 'TEXT'
    
    # Binary types
    elif 'blob' in type_lower or 'binary' in type_lower or 'bytea' in type_lower:
        return 'BLOB'
    elif 'varbinary' in type_lower:
        return 'VARBINARY'
    
    # Date/time types
    elif 'timestamptz' in type_lower or 'timestamp with time zone' in type_lower:
        return 'TIMESTAMPTZ'
    elif 'timestamp' in type_lower:
        return 'TIMESTAMP'
    elif 'date' in type_lower:
        return 'DATE'
    elif 'time' in type_lower:
        return 'TIME'
    elif 'interval' in type_lower:
        return 'INTERVAL'
    
    # UUID type
    elif 'uuid' in type_lower:
        return 'UUID'
    
    # Boolean type
    elif 'bool' in type_lower or 'boolean' in type_lower:
        return 'BOOLEAN'
    
    # JSON and structured types
    elif 'json' in type_lower:
        return 'JSON'
    elif any(x in type_lower for x in ['list', 'array', '[]']):
        return 'JSON'  # Lists/arrays map to JSON
    elif 'struct' in type_lower or 'row(' in type_lower:
        return 'JSON'  # Structs map to JSON
    elif 'map' in type_lower:
        return 'JSON'  # Maps map to JSON
    elif 'union' in type_lower:
        return 'JSON'  # Unions map to JSON
    
    # Fallback to VARCHAR for unknown types
    else:
        return 'VARCHAR'



def _normalize_sql_type(sql_type: str) -> str:
    """Normalize SQL types by removing parameters and handling synonyms"""
    normalized = sql_type.upper().strip()
    
    # Remove parameters (everything in parentheses)
    if '(' in normalized:
        normalized = normalized.split('(')[0]
    
    # Handle common synonyms
    synonyms = {
        'INT': 'INTEGER',
        'BOOL': 'BOOLEAN', 
        'REAL': 'FLOAT',
        'STRING': 'VARCHAR',
        'TEXT': 'VARCHAR',
        'CLOB': 'VARCHAR',
        'NUMERIC': 'DECIMAL',
        'BYTEA': 'BLOB',
        'BINARY': 'BLOB',
        'VARBINARY': 'BLOB'
    }
    
    return synonyms.get(normalized, normalized)

def _types_compatible(type1: str, type2: str) -> bool:
    """Check if two SQL types are compatible"""
    norm1 = _normalize_sql_type(type1)
    norm2 = _normalize_sql_type(type2)
    
    # Exact match after normalization
    if norm1 == norm2:
        return True
    
    # Integer family compatibility
    int_types = {'INTEGER', 'BIGINT', 'SMALLINT', 'TINYINT'}
    if norm1 in int_types and norm2 in int_types:
        return True
    
    # Float family compatibility 
    float_types = {'FLOAT', 'DOUBLE'}
    if norm1 in float_types and norm2 in float_types:
        return True
    
    # String family compatibility
    string_types = {'VARCHAR', 'CHAR'}
    if norm1 in string_types and norm2 in string_types:
        return True
    
    # Binary family compatibility
    binary_types = {'BLOB', 'VARBINARY'}
    if norm1 in binary_types and norm2 in binary_types:
        return True
    
    # Timestamp compatibility (with and without timezone)
    timestamp_types = {'TIMESTAMP', 'TIMESTAMPTZ'}
    if norm1 in timestamp_types and norm2 in timestamp_types:
        return True
    
    return False

@admin_router.post("/problems")
def create_problem(
    problem_data: AdminProblemCreate,
    _: bool = Depends(verify_admin_user_access),
    db: Session = Depends(get_db)
):
    """Create a new problem with the provided data"""
    
    # Validate difficulty
    valid_difficulties = ["BEGINNER", "EASY", "MEDIUM", "HARD", "EXPERT"]
    if problem_data.difficulty not in valid_difficulties:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid difficulty. Must be one of: {valid_difficulties}"
        )
    
    # Validate topic if provided
    if problem_data.topic_id:
        topic = db.query(Topic).filter(Topic.id == problem_data.topic_id).first()
        if not topic:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid topic_id"
            )
    
    
    # Convert AdminQuestionData to the format expected by the database
    # Note: expectedOutput is now stored in dedicated expected_output column
    question_data = {
        "description": problem_data.question.description,
        "tables": [
            {
                "name": table.name,
                "columns": [
                    {"name": col.name, "type": col.type}
                    for col in table.columns
                ],
                "sampleData": table.sample_data
            }
            for table in problem_data.question.tables
        ]
        # expectedOutput removed - now stored in dedicated expected_output column
    }
    
    # Extract S3 data source if present (legacy single dataset)
    s3_data_source = None
    if hasattr(problem_data.question, 's3_data_source') and problem_data.question.s3_data_source:
        s3_data_source = {
            "bucket": problem_data.question.s3_data_source.bucket,
            "key": problem_data.question.s3_data_source.key,
            "table_name": problem_data.question.s3_data_source.table_name,
            "description": problem_data.question.s3_data_source.description
        }

    # Extract multiple S3 datasets if present
    s3_datasets = None
    if hasattr(problem_data, 's3_datasets') and problem_data.s3_datasets:
        s3_datasets = [
            {
                "bucket": dataset.bucket,
                "key": dataset.key,
                "table_name": dataset.table_name,
                "description": dataset.description or ""
            }
            for dataset in problem_data.s3_datasets
        ]
    
    
    # Solution source is always 'neon' - S3 solutions deprecated
    s3_solution_source = None

    # Normalize master solution: prefer masterSolution, fallback to expectedOutput
    master_solution_data = None
    if problem_data.master_solution:
        master_solution_data = problem_data.master_solution
    elif problem_data.question.expected_output:
        master_solution_data = problem_data.question.expected_output
    
    # Create the problem
    problem = Problem(
        id=str(uuid.uuid4()),
        title=problem_data.title,
        difficulty=problem_data.difficulty,
        question=question_data,
        master_solution=master_solution_data,  # Use normalized master solution
        expected_display=problem_data.expected_display,  # Display output for users (not validation)
        s3_data_source=s3_data_source,  # Legacy single dataset
        s3_datasets=s3_datasets,  # New multiple datasets field
        tags=problem_data.tags,
        company=problem_data.company if problem_data.company else None,
        hints=problem_data.hints,
        premium=problem_data.premium,
        topic_id=problem_data.topic_id if problem_data.topic_id else None
    )
    
    db.add(problem)
    db.commit()
    db.refresh(problem)
    
    return {
        "success": True,
        "message": "Problem created successfully",
        "problem_id": problem.id,
        "title": problem.title
    }

@admin_router.get("/problems")
def list_problems(
    _: bool = Depends(verify_admin_access),
    db: Session = Depends(get_db)
):
    """List all problems for admin management"""
    problems = db.query(Problem).order_by(Problem.created_at.desc()).all()
    
    return [
        {
            "id": problem.id,
            "title": problem.title,
            "difficulty": problem.difficulty,
            "tags": problem.tags,
            "company": problem.company,
            "premium": problem.premium,
            "created_at": problem.created_at.isoformat()
        }
        for problem in problems
    ]

@admin_router.delete("/problems/{problem_id}")
def delete_problem(
    problem_id: str,
    _: bool = Depends(verify_admin_access),
    db: Session = Depends(get_db)
):
    """Delete a problem"""
    problem = db.query(Problem).filter(Problem.id == problem_id).first()
    if not problem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Problem not found"
        )
    
    db.delete(problem)
    db.commit()
    
    return {"success": True, "message": "Problem deleted successfully"}

@admin_router.get("/validate-json")
def validate_problem_json(
    _: bool = Depends(verify_admin_access)
):
    """Validate problem JSON structure"""
    return {
        "message": "Use the POST /api/admin/problems endpoint to validate and create problems",
        "schema_endpoint": "/api/admin/schema-info"
    }

# Solution management routes
@admin_router.post("/problems/{problem_id}/solutions", response_model=SolutionResponse)
def create_or_update_solution(
    problem_id: str,
    solution_data: SolutionCreate,
    current_user: User = Depends(verify_admin_user_access),
    db: Session = Depends(get_db)
):
    """Create or update the solution for a problem (one solution per problem)"""
    # Verify problem exists
    problem = db.query(Problem).filter(Problem.id == problem_id).first()
    if not problem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Problem not found"
        )
    
    # Check for existing solution for this problem
    existing_solution = db.query(Solution).filter(
        Solution.problem_id == problem_id
    ).first()
    
    if existing_solution:
        # Update existing solution
        existing_solution.title = solution_data.title
        existing_solution.content = solution_data.content
        existing_solution.sql_code = solution_data.sql_code
        existing_solution.is_official = True  # Always official since it's the only solution
        
        db.commit()
        db.refresh(existing_solution)
        
        # Load creator relationship
        solution = db.query(Solution).options(joinedload(Solution.creator)).filter(
            Solution.id == existing_solution.id
        ).first()
        
        return SolutionResponse.from_orm(solution)
    else:
        # Create new solution
        solution = Solution(
            id=str(uuid.uuid4()),
            problem_id=problem_id,
            created_by=current_user.id,
            title=solution_data.title,
            content=solution_data.content,
            sql_code=solution_data.sql_code,
            is_official=True  # Always official since it's the only solution
        )
        
        db.add(solution)
        db.commit()
        db.refresh(solution)
        
        # Load creator relationship
        solution = db.query(Solution).options(joinedload(Solution.creator)).filter(
            Solution.id == solution.id
        ).first()
        
        return SolutionResponse.from_orm(solution)

@admin_router.get("/problems/{problem_id}/solution", response_model=SolutionResponse)
def get_problem_solution(
    problem_id: str,
    _: bool = Depends(verify_admin_access),
    db: Session = Depends(get_db)
):
    """Get the single solution for a problem (admin view)"""
    solution = db.query(Solution).options(joinedload(Solution.creator)).filter(
        Solution.problem_id == problem_id
    ).first()
    
    if not solution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No solution found for this problem"
        )
    
    return SolutionResponse.from_orm(solution)

@admin_router.get("/problems/{problem_id}/solutions", response_model=List[SolutionResponse])
def get_problem_solutions(
    problem_id: str,
    _: bool = Depends(verify_admin_access),
    db: Session = Depends(get_db)
):
    """Get all solutions for a problem (admin view) - legacy endpoint"""
    solutions = db.query(Solution).options(joinedload(Solution.creator)).filter(
        Solution.problem_id == problem_id
    ).order_by(Solution.created_at.desc()).all()
    
    return [SolutionResponse.from_orm(solution) for solution in solutions]

@admin_router.put("/solutions/{solution_id}", response_model=SolutionResponse)
def update_solution(
    solution_id: str,
    solution_data: SolutionCreate,
    current_user: User = Depends(verify_admin_user_access),
    db: Session = Depends(get_db)
):
    """Update an existing solution"""
    solution = db.query(Solution).filter(Solution.id == solution_id).first()
    if not solution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Solution not found"
        )
    
    # Update solution fields
    solution.title = solution_data.title
    solution.content = solution_data.content
    solution.sql_code = solution_data.sql_code
    solution.is_official = solution_data.is_official
    
    db.commit()
    db.refresh(solution)
    
    # Load creator relationship
    solution = db.query(Solution).options(joinedload(Solution.creator)).filter(
        Solution.id == solution.id
    ).first()
    
    return SolutionResponse.from_orm(solution)

@admin_router.delete("/solutions/{solution_id}")
def delete_solution(
    solution_id: str,
    _: bool = Depends(verify_admin_access),
    db: Session = Depends(get_db)
):
    """Delete a solution"""
    solution = db.query(Solution).filter(Solution.id == solution_id).first()
    if not solution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Solution not found"
        )
    
    db.delete(solution)
    db.commit()
    
    return {"success": True, "message": "Solution deleted successfully"}


# ======= Neon Solution Verification Endpoints =======

class NeonVerificationRequest(BaseModel):
    """Request model for Neon solution verification"""
    problem_id: str = Field(..., description="Problem ID to verify Neon test cases for")

class NeonVerificationResponse(BaseModel):
    """Response model for Neon solution verification"""
    verified: bool = Field(..., description="Whether the problem has valid Neon test cases")
    source: str = Field(default="neon", description="Always 'neon' for this verification")
    test_case_count: int = Field(default=0, description="Number of valid test cases found")
    message: str = Field(default="", description="Verification status message")

@admin_router.post("/verify-neon-solution", response_model=NeonVerificationResponse)
def verify_neon_solution(
    request: NeonVerificationRequest,
    _: bool = Depends(verify_admin_user_access),
    db: Session = Depends(get_db)
):
    """
    Verify that a problem has valid Neon test cases with expected_output
    
    This endpoint checks if the problem has test cases with:
    1. Non-empty expected_output JSONB field
    2. Valid JSON structure in expected_output
    3. At least one test case with expected results
    """
    logger = logging.getLogger(__name__)
    
    try:
        # Check if problem exists
        problem = db.query(Problem).filter(Problem.id == request.problem_id).first()
        if not problem:
            return NeonVerificationResponse(
                verified=False,
                test_case_count=0,
                message=f"Problem '{request.problem_id}' not found"
            )
        
        # Find test cases with valid expected_output
        test_cases = db.query(TestCase).filter(
            TestCase.problem_id == request.problem_id,
            TestCase.expected_output.isnot(None)
        ).all()
        
        valid_test_cases = 0
        for test_case in test_cases:
            # Check if expected_output has valid content
            if test_case.expected_output:
                try:
                    # Ensure it's a list with at least one item
                    if isinstance(test_case.expected_output, list) and len(test_case.expected_output) > 0:
                        # Check if first item looks like a valid result row
                        first_row = test_case.expected_output[0]
                        if isinstance(first_row, dict) and len(first_row) > 0:
                            valid_test_cases += 1
                except Exception as e:
                    logger.warning(f"Invalid expected_output in test case {test_case.id}: {e}")
                    continue
        
        if valid_test_cases > 0:
            return NeonVerificationResponse(
                verified=True,
                test_case_count=valid_test_cases,
                message=f"Found {valid_test_cases} valid Neon test case(s)"
            )
        else:
            return NeonVerificationResponse(
                verified=False,
                test_case_count=0,
                message="No valid test cases with expected_output found"
            )
            
    except Exception as e:
        logger.error(f"Failed to verify Neon solution for problem {request.problem_id}: {e}")
        return NeonVerificationResponse(
            verified=False,
            test_case_count=0,
            message=f"Verification failed: {str(e)}"
        )

# ======= S3 Answer File Management Endpoints =======

class S3UploadRequest(BaseModel):
    """Request model for S3 upload URL generation"""
    bucket: str = Field(..., description="S3 bucket name")
    key_prefix: str = Field(..., description="S3 key prefix (folder path)")
    filename: str = Field(..., description="Original filename")
    content_type: str = Field(default="text/csv", description="MIME type of the file")
    
class S3UploadResponse(BaseModel):
    """Response model for S3 upload POST"""
    upload_url: str = Field(..., description="Presigned POST URL")
    upload_fields: Dict[str, str] = Field(..., description="Form fields for POST upload")
    bucket: str = Field(..., description="S3 bucket name")
    key: str = Field(..., description="Full S3 object key")
    expires_in: int = Field(..., description="URL expiration time in seconds")

class TestCaseS3ConfigRequest(BaseModel):
    """Request model for configuring S3 answer source for test case"""
    bucket: str = Field(..., description="S3 bucket name")
    key: str = Field(..., description="S3 object key (file path)")
    format: str = Field(..., description="File format (csv, json, parquet)")
    display_limit: int = Field(default=10, description="Number of rows to show in preview")
    force_refresh: bool = Field(default=False, description="Force refresh from S3 even if cached")

class TestCaseS3ConfigResponse(BaseModel):
    """Response model for S3 configuration result"""
    success: bool
    message: str
    test_case_id: str
    s3_config: Optional[S3AnswerSource] = None
    preview_rows: int = 0
    total_rows: int = 0
    error: Optional[str] = None

class S3DatasetValidationRequest(BaseModel):
    """Request model for S3 dataset validation"""
    bucket: str = Field(..., description="S3 bucket name")
    key: str = Field(..., description="S3 object key (file path) - must be .parquet")
    table_name: str = Field(..., description="Desired table name for DuckDB")

class S3DatasetValidationResponse(BaseModel):
    """Response model for S3 dataset validation"""
    success: bool
    message: str = ""
    table_schema: Optional[List[Dict[str, str]]] = None
    sample_data: Optional[List[Dict[str, Any]]] = None
    row_count: Optional[int] = None
    etag: Optional[str] = None
    table_name: Optional[str] = None
    data_source: Optional[str] = None
    error: Optional[str] = None

class S3ValidationResponse(BaseModel):
    """Response model for S3 configuration validation"""
    valid: bool
    accessible: bool
    file_format: Optional[str] = None
    file_size_mb: Optional[float] = None
    row_count: Optional[int] = None
    columns: Optional[List[str]] = None
    sample_data: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None

@admin_router.post("/s3/upload-url", response_model=S3UploadResponse)
def generate_s3_upload_url(
    request: S3UploadRequest,
    _: bool = Depends(verify_admin_user_access)
):
    """Generate presigned URL for uploading answer files to S3"""
    try:
        # Validate bucket name (basic security check)
        allowed_bucket_prefixes = ["sql-learning-answers", "sqlplatform-answers"]
        if not any(request.bucket.startswith(prefix) for prefix in allowed_bucket_prefixes):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Bucket must start with one of: {allowed_bucket_prefixes}"
            )
        
        # Validate file format
        allowed_formats = ["csv", "json", "parquet"]
        file_extension = request.filename.lower().split('.')[-1]
        if file_extension not in allowed_formats:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File format must be one of: {allowed_formats}"
            )
        
        # Generate safe S3 key
        import time
        timestamp = int(time.time())
        safe_filename = request.filename.replace(" ", "_").replace("/", "_")
        s3_key = f"{request.key_prefix.strip('/')}/{timestamp}_{safe_filename}"
        
        # Generate secure presigned POST with policy
        upload_data = s3_service.get_presigned_upload_url(
            bucket=request.bucket,
            key=s3_key,
            content_type=request.content_type,
            expires_in=300  # 5 minutes for security
        )
        
        return S3UploadResponse(
            upload_url=upload_data['url'],
            upload_fields=upload_data['fields'],
            bucket=request.bucket,
            key=s3_key,
            expires_in=300
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to generate S3 upload URL: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate upload URL: {str(e)}"
        )

@admin_router.post("/s3/validate", response_model=S3ValidationResponse)
def validate_s3_configuration(
    s3_config: S3AnswerSource,
    _: bool = Depends(verify_admin_user_access)
):
    """Validate S3 configuration and preview file content"""
    try:
        # Validate S3 access
        is_valid, error_msg = file_processor.validate_s3_configuration(s3_config)
        if not is_valid:
            return S3ValidationResponse(
                valid=False,
                accessible=False,
                error=error_msg
            )
        
        # Try to fetch and process the file
        full_data, preview_data, etag, error = file_processor.process_s3_answer_file(
            s3_config=s3_config,
            preview_limit=5  # Small preview for validation
        )
        
        if error:
            return S3ValidationResponse(
                valid=True,
                accessible=True,
                error=error
            )
        
        # Get data summary
        summary = file_processor.get_data_summary(full_data)
        
        return S3ValidationResponse(
            valid=True,
            accessible=True,
            file_format=s3_config.format,
            row_count=summary['row_count'],
            columns=summary['columns'],
            sample_data=preview_data,
            error=None
        )
        
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to validate S3 configuration: {e}")
        return S3ValidationResponse(
            valid=False,
            accessible=False,
            error=f"Validation failed: {str(e)}"
        )

@admin_router.post("/test-cases/{test_case_id}/s3-config", response_model=TestCaseS3ConfigResponse)
def configure_test_case_s3_source(
    test_case_id: str,
    request: TestCaseS3ConfigRequest,
    _: bool = Depends(verify_admin_user_access),
    db: Session = Depends(get_db)
):
    """Configure S3 answer source for a test case"""
    try:
        # Verify test case exists
        test_case = db.query(TestCase).filter(TestCase.id == test_case_id).first()
        if not test_case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Test case not found"
            )
        
        # Create S3 configuration
        s3_config = S3AnswerSource(
            bucket=request.bucket,
            key=request.key,
            format=request.format
        )
        
        # Process S3 file to get full and preview data
        full_data, preview_data, etag, error = file_processor.process_s3_answer_file(
            s3_config=s3_config,
            preview_limit=request.display_limit
        )
        
        if error:
            return TestCaseS3ConfigResponse(
                success=False,
                message="Failed to process S3 file",
                test_case_id=test_case_id,
                error=error
            )
        
        # Update test case with S3 configuration
        s3_config.etag = etag  # Store ETag for caching
        test_case.expected_output_source = s3_config.dict()
        test_case.preview_expected_output = preview_data
        test_case.display_limit = request.display_limit
        
        # Keep backward compatibility - store preview in expected_output too
        test_case.expected_output = preview_data
        
        db.commit()
        db.refresh(test_case)
        
        return TestCaseS3ConfigResponse(
            success=True,
            message=f"S3 source configured successfully. {len(full_data)} total rows, {len(preview_data)} preview rows.",
            test_case_id=test_case_id,
            s3_config=s3_config,
            preview_rows=len(preview_data),
            total_rows=len(full_data)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to configure S3 source for test case {test_case_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to configure S3 source: {str(e)}"
        )

@admin_router.post("/test-cases/{test_case_id}/s3-refresh", response_model=TestCaseS3ConfigResponse)
def refresh_test_case_s3_data(
    test_case_id: str,
    _: bool = Depends(verify_admin_user_access),
    db: Session = Depends(get_db)
):
    """Refresh S3 answer data for a test case (bypass cache)"""
    try:
        # Verify test case exists and has S3 configuration
        test_case = db.query(TestCase).filter(TestCase.id == test_case_id).first()
        if not test_case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Test case not found"
            )
        
        if not test_case.expected_output_source:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Test case does not have S3 configuration"
            )
        
        # Parse existing S3 configuration
        s3_config = S3AnswerSource(**test_case.expected_output_source)
        
        # Force refresh by not passing ETag
        s3_config.etag = None
        
        # Process S3 file to get updated data
        full_data, preview_data, new_etag, error = file_processor.process_s3_answer_file(
            s3_config=s3_config,
            preview_limit=test_case.display_limit or 10
        )
        
        if error:
            return TestCaseS3ConfigResponse(
                success=False,
                message="Failed to refresh S3 data",
                test_case_id=test_case_id,
                error=error
            )
        
        # Update test case with fresh data
        s3_config.etag = new_etag
        test_case.expected_output_source = s3_config.dict()
        test_case.preview_expected_output = preview_data
        test_case.expected_output = preview_data  # Backward compatibility
        
        db.commit()
        db.refresh(test_case)
        
        return TestCaseS3ConfigResponse(
            success=True,
            message=f"S3 data refreshed successfully. {len(full_data)} total rows, {len(preview_data)} preview rows.",
            test_case_id=test_case_id,
            s3_config=s3_config,
            preview_rows=len(preview_data),
            total_rows=len(full_data)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to refresh S3 data for test case {test_case_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refresh S3 data: {str(e)}"
        )

@admin_router.post("/validate-dataset-s3", response_model=S3DatasetValidationResponse)
def validate_s3_dataset(
    request: S3DatasetValidationRequest,
    _: bool = Depends(verify_admin_access)
):
    """Validate S3 dataset file and extract schema information"""
    logger = logging.getLogger(__name__)
    
    try:
        # Use S3 service to validate the dataset file
        validation_result = s3_service.validate_dataset_file(
            bucket=request.bucket,
            key=request.key,
            table_name=request.table_name
        )
        
        if validation_result["success"]:
            logger.info(f"S3 dataset validation successful: s3://{request.bucket}/{request.key}")
            return S3DatasetValidationResponse(
                success=True,
                message=f"Dataset validation successful. {validation_result['row_count']:,} rows found.",
                table_schema=validation_result.get("schema", []),
                sample_data=validation_result.get("sample_data", []),
                row_count=validation_result.get("row_count", 0),
                etag=validation_result.get("etag"),
                table_name=validation_result.get("table_name"),
                data_source=f"s3://{request.bucket}/{request.key}"
            )
        else:
            logger.warning(f"S3 dataset validation failed: {validation_result.get('error', 'Unknown error')}")
            return S3DatasetValidationResponse(
                success=False,
                error=validation_result.get("error", "Validation failed")
            )
            
    except Exception as e:
        logger.error(f"Exception during S3 dataset validation: {e}")
        return S3DatasetValidationResponse(
            success=False,
            error=f"Validation failed: {str(e)}"
        )

@admin_router.post("/create_question", response_model=EnhancedQuestionCreateResponse)
def create_question_enhanced(
    request: EnhancedQuestionCreateRequest,
    _: bool = Depends(verify_admin_user_access),
    db: Session = Depends(get_db)
):
    """
    DEPRECATED: Enhanced question creation with S3 solution workflow
    
    This endpoint is deprecated as part of the migration from S3 to Neon database
    for solution validation. Use the standard /problems endpoint with Neon-based
    test cases instead.
    """
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="This endpoint is deprecated. S3 solution creation has been migrated to Neon database. Use the standard /problems endpoint with test cases instead."
    )
    logger = logging.getLogger(__name__)
    
    try:
        # Validate difficulty
        valid_difficulties = ["BEGINNER", "EASY", "MEDIUM", "HARD", "EXPERT"]
        if request.difficulty not in valid_difficulties:
            return EnhancedQuestionCreateResponse(
                success=False,
                message=f"Invalid difficulty. Must be one of: {valid_difficulties}",
                problem_id=request.problem_id,
                error="Invalid difficulty level"
            )
        
        # Parse S3 paths
        def parse_s3_path(s3_path: str) -> tuple:
            """Parse s3://bucket/key format"""
            if not s3_path.startswith('s3://'):
                raise ValueError(f"Invalid S3 path format: {s3_path}")
            path_parts = s3_path[5:].split('/', 1)  # Remove 's3://'
            if len(path_parts) != 2:
                raise ValueError(f"Invalid S3 path format: {s3_path}")
            return path_parts[0], path_parts[1]  # bucket, key
        
        try:
            dataset_bucket, dataset_key = parse_s3_path(request.dataset_path)
            solution_bucket, solution_key = parse_s3_path(request.solution_path)
        except ValueError as e:
            return EnhancedQuestionCreateResponse(
                success=False,
                message=str(e),
                problem_id=request.problem_id,
                error="Invalid S3 path format"
            )
        
        # Step 1: Validate and load dataset from S3
        logger.info(f"Loading dataset from S3: {request.dataset_path}")
        dataset_validation = s3_service.validate_dataset_file(
            bucket=dataset_bucket,
            key=dataset_key,
            table_name="dataset"
        )
        
        if not dataset_validation["success"]:
            return EnhancedQuestionCreateResponse(
                success=False,
                message=f"Dataset validation failed: {dataset_validation['error']}",
                problem_id=request.problem_id,
                error=dataset_validation["error"]
            )
        
        # Step 2: Fetch solution from S3 (supports both SQL and parquet)
        logger.info(f"Fetching solution from S3: {request.solution_path}")
        solution_result = s3_service.fetch_solution_sql(
            bucket=solution_bucket,
            key=solution_key
        )
        
        if not solution_result["success"]:
            return EnhancedQuestionCreateResponse(
                success=False,
                message=f"Solution fetch failed: {solution_result['error']}",
                problem_id=request.problem_id,
                error=solution_result["error"]
            )
        
        # Step 3: Get expected results based on solution type
        logger.info(f"Processing solution ({solution_result['file_type']})")
        import duckdb
        import tempfile
        
        try:
            if solution_result["file_type"] == "sql":
                # SQL solution: Execute SQL on dataset
                solution_sql = solution_result["sql_content"]
                
                # Download dataset to temporary file
                temp_dataset_path = s3_service.download_to_temp_file(dataset_bucket, dataset_key)
                
                # Create DuckDB connection and load dataset
                conn = duckdb.connect(":memory:")
                conn.execute("CREATE TABLE dataset AS SELECT * FROM read_parquet(?)", [temp_dataset_path])
                
                # Execute solution SQL
                result = conn.execute(solution_sql).fetchall()
                columns = [desc[0] for desc in conn.description]
                
                # Convert to list of dictionaries
                expected_results = [dict(zip(columns, row)) for row in result]
                
                # Clean up temporary file
                try:
                    os.unlink(temp_dataset_path)
                except:
                    pass
                    
            elif solution_result["file_type"] == "parquet":
                # Parquet solution: Use parquet data directly as expected results
                expected_results = solution_result["solution_data"]
                logger.info(f"Using parquet solution with {len(expected_results)} rows")
                
            else:
                raise ValueError(f"Unsupported solution file type: {solution_result['file_type']}")
                
        except Exception as e:
            logger.error(f"Failed to process solution: {e}")
            return EnhancedQuestionCreateResponse(
                success=False,
                message=f"Solution processing failed: {str(e)}",
                problem_id=request.problem_id,
                error=f"Solution processing error: {str(e)}"
            )
        
        # Step 4: Generate expected hash and preview rows
        try:
            expected_hash = s3_service.generate_expected_result_hash(expected_results)
            preview_rows = expected_results[:5]  # First 5 rows
            total_rows = len(expected_results)
            
            logger.info(f"Generated hash: {expected_hash}, Total rows: {total_rows}, Preview rows: {len(preview_rows)}")
            
        except Exception as e:
            logger.error(f"Failed to generate hash: {e}")
            return EnhancedQuestionCreateResponse(
                success=False,
                message=f"Hash generation failed: {str(e)}",
                problem_id=request.problem_id,
                error=f"Hash generation error: {str(e)}"
            )
        
        # Step 5: Store metadata in Postgres
        try:
            # Check if problem already exists
            existing_problem = db.query(Problem).filter(Problem.id == request.problem_id).first()
            if existing_problem:
                return EnhancedQuestionCreateResponse(
                    success=False,
                    message=f"Problem with ID '{request.problem_id}' already exists",
                    problem_id=request.problem_id,
                    error="Problem ID already exists"
                )
            
            # Validate topic if provided
            if request.topic_id:
                topic = db.query(Topic).filter(Topic.id == request.topic_id).first()
                if not topic:
                    return EnhancedQuestionCreateResponse(
                        success=False,
                        message="Invalid topic_id",
                        problem_id=request.problem_id,
                        error="Invalid topic_id"
                    )
            
            # Create S3 data source configuration
            s3_data_source = {
                "bucket": dataset_bucket,
                "key": dataset_key,
                "table_name": "dataset",
                "description": f"Dataset for problem {request.problem_id}",
                "etag": dataset_validation.get("etag")
            }
            
            # Create question data structure
            question_data = {
                "description": request.description or f"# {request.title}\n\nSolve this SQL problem using the provided dataset.",
                "tables": [
                    {
                        "name": "dataset",
                        "columns": [
                            {"name": col["column"], "type": col["type"]}
                            for col in dataset_validation["schema"]
                        ],
                        "sampleData": dataset_validation["sample_data"]
                    }
                ],
                "expectedOutput": preview_rows
            }
            
            # Create the problem
            problem = Problem(
                id=request.problem_id,
                title=request.title,
                difficulty=request.difficulty,
                question=question_data,
                tags=request.tags,
                company=request.company,
                hints=request.hints,
                premium=request.premium,
                topic_id=request.topic_id,
                s3_data_source=s3_data_source,
                expected_hash=expected_hash,
                preview_rows=preview_rows
            )
            
            db.add(problem)
            db.commit()
            db.refresh(problem)
            
            logger.info(f"Successfully created problem: {request.problem_id}")
            
            return EnhancedQuestionCreateResponse(
                success=True,
                message=f"Question '{request.title}' created successfully with {total_rows} expected result rows",
                problem_id=request.problem_id,
                expected_hash=expected_hash,
                preview_rows=preview_rows,
                row_count=total_rows,
                dataset_info={
                    "schema": dataset_validation["schema"],
                    "sample_data": dataset_validation["sample_data"],
                    "row_count": dataset_validation["row_count"],
                    "s3_path": request.dataset_path
                }
            )
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create problem in database: {e}")
            return EnhancedQuestionCreateResponse(
                success=False,
                message=f"Database error: {str(e)}",
                problem_id=request.problem_id,
                error=f"Database storage failed: {str(e)}"
            )
        
    except Exception as e:
        logger.error(f"Unexpected error in create_question_enhanced: {e}")
        return EnhancedQuestionCreateResponse(
            success=False,
            message=f"Unexpected error: {str(e)}",
            problem_id=request.problem_id,
            error=f"Internal server error: {str(e)}"
        )

# ======= Multi-table S3 Management Endpoints =======

@admin_router.post("/validate-multitable-s3", response_model=MultiTableValidationResponse)
async def validate_multitable_s3(
    request: MultiTableValidationRequest,
    _: bool = Depends(verify_admin_user_access)
):
    """Validate multiple S3 datasets for multi-table questions"""
    logger = logging.getLogger(__name__)
    
    try:
        if not request.datasets or len(request.datasets) == 0:
            return MultiTableValidationResponse(
                success=False,
                message="At least one dataset is required",
                error="No datasets provided"
            )
        
        if len(request.datasets) > 10:  # Limit to prevent abuse
            return MultiTableValidationResponse(
                success=False,
                message="Too many datasets. Maximum allowed: 10",
                error="Dataset limit exceeded"
            )
        
        validated_datasets = []
        total_rows = 0
        
        # Validate each dataset
        for i, dataset in enumerate(request.datasets):
            logger.info(f"Validating dataset {i+1}/{len(request.datasets)}: {dataset.bucket}/{dataset.key}")
            
            # Validate the S3 dataset
            validation_result = s3_service.validate_dataset_file(
                bucket=dataset.bucket,
                key=dataset.key,
                table_name=dataset.table_name
            )
            
            if not validation_result["success"]:
                return MultiTableValidationResponse(
                    success=False,
                    message=f"Dataset {i+1} validation failed: {validation_result['error']}",
                    error=validation_result["error"]
                )
            
            # Add dataset info to validated list
            dataset_info = {
                "table_name": dataset.table_name,
                "bucket": dataset.bucket,
                "key": dataset.key,
                "description": dataset.description,
                "schema": validation_result["schema"],
                "sample_data": validation_result["sample_data"][:3],  # Only first 3 rows
                "row_count": validation_result["row_count"],
                "etag": validation_result.get("etag")
            }
            validated_datasets.append(dataset_info)
            total_rows += validation_result["row_count"]
        
        logger.info(f"Successfully validated {len(validated_datasets)} datasets with {total_rows} total rows")
        
        return MultiTableValidationResponse(
            success=True,
            message=f"Successfully validated {len(validated_datasets)} datasets",
            validated_datasets=validated_datasets,
            total_tables=len(validated_datasets),
            total_rows=total_rows
        )
        
    except Exception as e:
        logger.error(f"Failed to validate multi-table S3: {e}")
        return MultiTableValidationResponse(
            success=False,
            message=f"Validation failed: {str(e)}",
            error=f"Internal server error: {str(e)}"
        )

@admin_router.post("/create-multitable-question", response_model=EnhancedQuestionCreateResponse)
async def create_multitable_question(
    request: MultiTableQuestionCreateRequest,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin_user_access)
):
    """Create a question with multiple S3 datasets"""
    logger = logging.getLogger(__name__)
    
    try:
        # Validate difficulty
        valid_difficulties = ["BEGINNER", "EASY", "MEDIUM", "HARD", "EXPERT"]
        if request.difficulty not in valid_difficulties:
            return EnhancedQuestionCreateResponse(
                success=False,
                message=f"Invalid difficulty. Must be one of: {valid_difficulties}",
                problem_id=request.problem_id,
                error="Invalid difficulty level"
            )
        
        # Check if problem_id already exists
        existing_problem = db.query(Problem).filter(Problem.id == request.problem_id).first()
        if existing_problem:
            return EnhancedQuestionCreateResponse(
                success=False,
                message=f"Problem ID '{request.problem_id}' already exists",
                problem_id=request.problem_id,
                error="Problem ID already exists"
            )
        
        # Validate datasets
        if not request.datasets or len(request.datasets) == 0:
            return EnhancedQuestionCreateResponse(
                success=False,
                message="At least one dataset is required",
                problem_id=request.problem_id,
                error="No datasets provided"
            )
        
        # Validate all datasets
        validated_datasets = []
        question_tables = []
        
        for i, dataset in enumerate(request.datasets):
            # Validate the S3 dataset
            validation_result = s3_service.validate_dataset_file(
                bucket=dataset.bucket,
                key=dataset.key,
                table_name=dataset.table_name
            )
            
            if not validation_result["success"]:
                return EnhancedQuestionCreateResponse(
                    success=False,
                    message=f"Dataset {i+1} validation failed: {validation_result['error']}",
                    problem_id=request.problem_id,
                    error=validation_result["error"]
                )
            
            # Store validated dataset info
            dataset_info = {
                "bucket": dataset.bucket,
                "key": dataset.key,
                "table_name": dataset.table_name,
                "description": dataset.description,
                "etag": validation_result.get("etag")
            }
            validated_datasets.append(dataset_info)
            
            # Create table definition for question
            table_def = {
                "name": dataset.table_name,
                "columns": [
                    {"name": col["column"], "type": col["type"]}
                    for col in validation_result["schema"]
                ],
                "sampleData": validation_result["sample_data"][:5]  # First 5 rows
            }
            question_tables.append(table_def)
        
        # Parse solution path
        if not request.solution_path.startswith('s3://'):
            return EnhancedQuestionCreateResponse(
                success=False,
                message=f"Invalid solution S3 path format: {request.solution_path}",
                problem_id=request.problem_id,
                error="Invalid S3 path format"
            )
        
        solution_path_parts = request.solution_path[5:].split('/', 1)
        if len(solution_path_parts) != 2:
            return EnhancedQuestionCreateResponse(
                success=False,
                message=f"Invalid solution S3 path format: {request.solution_path}",
                problem_id=request.problem_id,
                error="Invalid S3 path format"
            )
        
        solution_bucket, solution_key = solution_path_parts
        
        # Fetch solution SQL or parquet from S3
        solution_result = s3_service.fetch_solution_sql(
            bucket=solution_bucket,
            key=solution_key
        )
        
        if not solution_result["success"]:
            return EnhancedQuestionCreateResponse(
                success=False,
                message=f"Solution fetch failed: {solution_result['error']}",
                problem_id=request.problem_id,
                error=solution_result["error"]
            )
        
        # Create question data structure
        question_data = {
            "description": request.description or f"# {request.title}\n\nSolve this SQL problem using the provided datasets.",
            "tables": question_tables,
            "expectedOutput": []  # Will be populated by solution execution
        }
        
        # Validate topic if provided
        if request.topic_id:
            topic = db.query(Topic).filter(Topic.id == request.topic_id).first()
            if not topic:
                return EnhancedQuestionCreateResponse(
                    success=False,
                    message="Invalid topic_id",
                    problem_id=request.problem_id,
                    error="Invalid topic_id"
                )
        
        # Create the problem
        problem = Problem(
            id=request.problem_id,
            title=request.title,
            difficulty=request.difficulty,
            question=question_data,
            tags=request.tags,
            company=request.company,
            hints=request.hints,
            premium=request.premium,
            topic_id=request.topic_id,
            solution_source='s3',
            s3_solution_source={
                "bucket": solution_bucket,
                "key": solution_key,
                "description": f"Solution for multi-table problem {request.problem_id}"
            }
        )
        
        db.add(problem)
        db.commit()
        db.refresh(problem)
        
        logger.info(f"Successfully created multi-table problem: {request.problem_id}")
        
        return EnhancedQuestionCreateResponse(
            success=True,
            message=f"Multi-table question '{request.title}' created successfully with {len(validated_datasets)} datasets",
            problem_id=request.problem_id,
            dataset_info={
                "datasets": validated_datasets,
                "table_count": len(validated_datasets),
                "solution_path": request.solution_path
            }
        )
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create multi-table question: {e}")
        return EnhancedQuestionCreateResponse(
            success=False,
            message=f"Failed to create question: {str(e)}",
            problem_id=request.problem_id,
            error=f"Internal server error: {str(e)}"
        )


@admin_router.post("/convert-parquet")
async def convert_parquet_to_jsonb(
    file: UploadFile = File(...),
    admin_key: str = Depends(verify_admin_access)
):
    """
    Convert uploaded Parquet file to JSONB format for master_solution field.
    
    This endpoint allows admins to upload large Parquet files which are then
    converted to the JSONB format expected by the master_solution field.
    Parquet files offer superior compression and performance for large datasets.
    """
    logger = logging.getLogger(__name__)
    try:
        # Validate file type
        if not file.filename.endswith('.parquet'):
            raise HTTPException(
                status_code=400,
                detail="Only Parquet files (.parquet) are supported"
            )
        
        # Read the uploaded file content
        file_content = await file.read()
        
        # Validate file size (25MB limit)
        max_size_mb = 25
        if len(file_content) > max_size_mb * 1024 * 1024:
            raise HTTPException(
                status_code=400,
                detail=f"File size {len(file_content) / (1024 * 1024):.1f}MB exceeds maximum allowed size of {max_size_mb}MB"
            )
        
        # Validate content type (basic check)
        if file.content_type and not file.content_type.startswith('application/'):
            logger.warning(f"Unexpected content type: {file.content_type}")
        
        # Create a temporary file to work with pyarrow
        temp_file_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as temp_file:
                temp_file_path = temp_file.name
                temp_file.write(file_content)
                temp_file.flush()
            
            # Read the parquet file using pandas
            df = pd.read_parquet(temp_file_path)
            
            # Validate the data size (10k rows limit for better performance)
            row_limit = 10000
            if len(df) > row_limit:
                raise HTTPException(
                    status_code=400,
                    detail=f"File contains {len(df)} rows. Maximum allowed is {row_limit} rows for performance reasons."
                )
            
            # Clean problematic float values for JSON serialization
            import numpy as np
            import json
            
            # Replace NaN, inf, -inf with None (which becomes null in JSON)
            df = df.replace([np.inf, -np.inf], None)
            df = df.where(pd.notna(df), None)
            
            # Convert to list of dictionaries (JSONB format)
            jsonb_data = df.to_dict(orient='records')
            
            # Additional safety: Clean any remaining problematic values that pandas might have missed
            def clean_value(value):
                if isinstance(value, float):
                    if np.isnan(value) or np.isinf(value):
                        return None
                return value
            
            # Deep clean the jsonb_data
            for row in jsonb_data:
                for key, value in row.items():
                    row[key] = clean_value(value)
            
            # Test JSON serialization to catch any remaining issues
            try:
                json.dumps(jsonb_data)
            except (ValueError, TypeError) as json_error:
                logger.error(f"JSON serialization test failed: {json_error}")
                raise HTTPException(
                    status_code=400,
                    detail=f"Data contains values that cannot be converted to JSON: {str(json_error)}"
                )
            
            logger.info(f"Successfully converted Parquet file '{file.filename}' with {len(jsonb_data)} rows")
            
            return {
                "success": True,
                "message": f"Parquet file converted successfully",
                "data": jsonb_data,
                "metadata": {
                    "filename": file.filename,
                    "rows": len(jsonb_data),
                    "columns": list(df.columns),
                    "file_size_mb": len(file_content) / (1024 * 1024)
                }
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error reading Parquet file: {e}")
            raise HTTPException(
                status_code=400,
                detail=f"Invalid Parquet file format: {str(e)}"
            )
        finally:
            # Always clean up temporary file
            if temp_file_path:
                try:
                    import os
                    os.unlink(temp_file_path)
                except Exception as cleanup_error:
                    logger.warning(f"Failed to clean up temp file {temp_file_path}: {cleanup_error}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in Parquet conversion: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )