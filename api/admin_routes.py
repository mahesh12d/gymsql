"""
Admin routes for creating and managing problems
"""
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from pydantic import BaseModel, Field
import uuid
import duckdb
import logging

from .database import get_db
from .models import Problem, Topic, Solution, User, TestCase
from .auth import verify_admin_access, verify_admin_user_access
from .schemas import DifficultyLevel, QuestionData, TableData, TableColumn, SolutionCreate, SolutionResponse, S3AnswerSource
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
    expected_output: List[Dict[str, Any]] = Field(..., alias="expectedOutput")

class AdminProblemCreate(BaseModel):
    title: str
    difficulty: str
    question: AdminQuestionData
    tags: List[str] = []
    company: str = ""
    hints: List[str] = []
    premium: bool = False
    topic_id: str = ""

class SchemaInfo(BaseModel):
    """Response model for schema information"""
    problem_structure: Dict[str, Any]
    example_problem: Dict[str, Any]
    difficulty_options: List[str]
    available_topics: List[Dict[str, str]]

# Enhanced AWS S3 Question Creation Schemas
class S3SolutionSource(BaseModel):
    """Schema for S3 solution SQL file configuration"""
    bucket: str
    key: str  # S3 object key (file path) - must be .sql
    description: Optional[str] = None
    etag: Optional[str] = None  # For cache validation

class EnhancedQuestionCreateRequest(BaseModel):
    """Enhanced request model for creating questions with S3 dataset and solution"""
    problem_id: str = Field(..., description="Unique problem identifier (e.g., 'q101')")
    title: str = Field(..., description="Problem title")
    difficulty: str = Field(..., description="Difficulty level: BEGINNER, EASY, MEDIUM, HARD, EXPERT")
    tags: List[str] = Field(default=[], description="Problem tags (e.g., ['window-function', 'ranking'])")
    dataset_path: str = Field(..., description="S3 path to dataset (e.g., 's3://bucket/problems/q101/dataset.parquet')")
    solution_path: str = Field(..., description="S3 path to solution SQL (e.g., 's3://bucket/problems/q101/solution.sql')")
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
        ],
        "expectedOutput": problem_data.question.expected_output
    }
    
    
    # Create the problem
    problem = Problem(
        id=str(uuid.uuid4()),
        title=problem_data.title,
        difficulty=problem_data.difficulty,
        question=question_data,
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
def create_solution(
    problem_id: str,
    solution_data: SolutionCreate,
    current_user: User = Depends(verify_admin_user_access),
    db: Session = Depends(get_db)
):
    """Create an official solution for a problem"""
    # Verify problem exists
    problem = db.query(Problem).filter(Problem.id == problem_id).first()
    if not problem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Problem not found"
        )
    
    # Check for existing official solution if this is meant to be official
    if solution_data.is_official:
        existing_official = db.query(Solution).filter(
            Solution.problem_id == problem_id,
            Solution.is_official == True
        ).first()
        
        if existing_official:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"An official solution already exists for this problem. Use PUT /api/admin/solutions/{existing_official.id} to update it instead."
            )
    
    # Create solution
    solution = Solution(
        id=str(uuid.uuid4()),
        problem_id=problem_id,
        created_by=current_user.id,
        title=solution_data.title,
        content=solution_data.content,
        sql_code=solution_data.sql_code,
        is_official=solution_data.is_official
    )
    
    db.add(solution)
    db.commit()
    db.refresh(solution)
    
    # Load creator relationship
    solution = db.query(Solution).options(joinedload(Solution.creator)).filter(
        Solution.id == solution.id
    ).first()
    
    return SolutionResponse.from_orm(solution)

@admin_router.get("/problems/{problem_id}/solutions", response_model=List[SolutionResponse])
def get_problem_solutions(
    problem_id: str,
    _: bool = Depends(verify_admin_access),
    db: Session = Depends(get_db)
):
    """Get all solutions for a problem (admin view)"""
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