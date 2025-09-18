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
from .models import Problem, Topic, Solution, User
from .auth import verify_admin_access, verify_admin_user_access
from .schemas import DifficultyLevel, QuestionData, TableData, TableColumn, SolutionCreate, SolutionResponse

# Create admin router
admin_router = APIRouter(prefix="/api/admin", tags=["admin"])

# Admin schemas for question creation
class AdminTableColumn(BaseModel):
    name: str
    type: str
    description: str = ""

class ParquetDataSource(BaseModel):
    """Parquet file data source configuration"""
    git_repo_url: str = Field(..., description="Git repository base URL (e.g., https://github.com/user/repo/raw/main)")
    file_path: str = Field(..., description="Path to parquet file within repo (e.g., data/sales.parquet)")
    table_name: str = Field(default="problem_data", description="Name for the table in DuckDB")
    description: str = Field(default="", description="Description of the dataset")

class AdminTableData(BaseModel):
    name: str
    columns: List[AdminTableColumn]
    sample_data: List[Dict[str, Any]] = []

class AdminQuestionData(BaseModel):
    description: str
    tables: List[AdminTableData] = []
    expected_output: List[Dict[str, Any]] = Field(..., alias="expectedOutput")
    parquet_data_source: ParquetDataSource = Field(None, description="Parquet file data source for DuckDB queries")

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

class ParquetValidationResponse(BaseModel):
    """Response model for parquet validation"""
    success: bool
    message: str
    table_schema: Optional[List[Dict[str, str]]] = None
    sample_data: Optional[List[Dict[str, Any]]] = None
    row_count: Optional[int] = None
    parquet_url: Optional[str] = None
    error: Optional[str] = None
    # New fields for schema enforcement
    suggested_table_schema: Optional[List[Dict[str, Any]]] = None
    table_name: Optional[str] = None

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

@admin_router.post("/validate-parquet", response_model=ParquetValidationResponse)
def validate_parquet_file(
    parquet_source: ParquetDataSource,
    _: bool = Depends(verify_admin_user_access)
):
    """Validate parquet file and extract schema information"""
    
    logger = logging.getLogger(__name__)
    
    try:
        # Construct full parquet file URL
        parquet_url = f"{parquet_source.git_repo_url.rstrip('/')}/{parquet_source.file_path.lstrip('/')}"
        
        # Security validation - exact domain matching to prevent bypass
        from urllib.parse import urlparse
        allowed_domains = ['raw.githubusercontent.com']  # Exact match only for security
        
        try:
            parsed = urlparse(parquet_url)
            if parsed.scheme != 'https':
                return ParquetValidationResponse(
                    success=False,
                    message="Only HTTPS URLs are allowed",
                    error="URL must use HTTPS scheme"
                )
            if parsed.netloc not in allowed_domains:
                return ParquetValidationResponse(
                    success=False,
                    message="URL domain not allowed",
                    error=f"Domain {parsed.netloc} not in allowed list: {allowed_domains}"
                )
            # Additional validation: ensure path ends with .parquet
            if not parsed.path.lower().endswith('.parquet'):
                return ParquetValidationResponse(
                    success=False,
                    message="Invalid file type",
                    error="File path must end with .parquet extension"
                )
        except Exception:
            return ParquetValidationResponse(
                success=False,
                message="Invalid URL format",
                error="Could not parse the provided URL"
            )
        
        logger.info(f"Validating parquet file: {parquet_url}")
        
        # Initialize temporary DuckDB connection with limits
        conn = duckdb.connect(":memory:")
        conn.execute("SET memory_limit = '128MB'")
        conn.execute("SET threads = 1")
        
        # Install and load httpfs extension for remote file access
        conn.execute("INSTALL httpfs")
        conn.execute("LOAD httpfs")
        
        # Test accessibility and get basic info
        try:
            # Test if parquet file exists and is accessible using a lightweight query
            # Avoid COUNT(*) which can be expensive on large files
            try:
                conn.execute("SELECT 1 FROM read_parquet(?) LIMIT 1", [parquet_url]).fetchone()
                # File is accessible, use metadata to estimate row count if available
                row_count = None  # We'll skip row count for performance
            except Exception:
                return ParquetValidationResponse(
                    success=False,
                    message="Parquet file not found or inaccessible",
                    error=f"Could not access parquet file at: {parquet_url}"
                )
            
            # Get schema information using parameterized query
            schema_result = conn.execute("DESCRIBE SELECT * FROM read_parquet(?)", [parquet_url]).fetchall()
            schema = [{"column": row[0], "type": row[1]} for row in schema_result]
            
            # Create suggested table schema for auto-population in problem creation
            suggested_columns = []
            for row in schema_result:
                column_name = row[0]
                duckdb_type = row[1]
                sql_type = _map_duckdb_type_to_sql(duckdb_type)
                
                suggested_columns.append({
                    "name": column_name,
                    "type": sql_type,
                    "description": f"{column_name} column ({sql_type})"
                })
            
            suggested_table_schema = [{
                "name": parquet_source.table_name,
                "columns": suggested_columns,
                "sample_data": []  # Will be populated from sample data
            }]
            
            # Get sample data (first 10 rows) using parameterized query - avoid pandas dependency
            sample_query = conn.execute("SELECT * FROM read_parquet(?) LIMIT 10", [parquet_url])
            sample_rows = sample_query.fetchall()
            
            # Get column names from the query
            if sample_rows:
                column_names = [desc[0] for desc in sample_query.description]
                sample_data = [dict(zip(column_names, row)) for row in sample_rows]
            else:
                sample_data = []
            
            # Add sample data to suggested table schema
            if sample_data:
                suggested_table_schema[0]["sample_data"] = sample_data[:5]  # Limit to 5 rows for UI
            
            conn.close()
            
            return ParquetValidationResponse(
                success=True,
                message=f"Parquet file validated successfully. Found {len(schema)} columns with schema auto-population ready.",
                table_schema=schema,
                sample_data=sample_data,
                row_count=row_count,  # Will be None for performance
                parquet_url=parquet_url,
                suggested_table_schema=suggested_table_schema,
                table_name=parquet_source.table_name
            )
            
        except Exception as e:
            conn.close()
            logger.error(f"Error accessing parquet file: {e}")
            return ParquetValidationResponse(
                success=False,
                message="Failed to access or validate parquet file",
                error=f"Error: {str(e)}"
            )
            
    except Exception as e:
        logger.error(f"General error in parquet validation: {e}")
        return ParquetValidationResponse(
            success=False,
            message="Validation failed",
            error=f"Validation error: {str(e)}"
        )

def _validate_schema_consistency(table_schema: List[Dict], parquet_data_source: ParquetDataSource) -> tuple[Optional[str], Optional[str]]:
    """
    Validate that the manual table schema is consistent with the parquet schema.
    Returns (error_message, warning_message). error_message is None if successful.
    """
    if not parquet_data_source:
        return None, None
    
    try:
        # Re-validate parquet file to get current schema
        parquet_url = f"{parquet_data_source.git_repo_url.rstrip('/')}/{parquet_data_source.file_path.lstrip('/')}"
        
        # Initialize temporary DuckDB connection
        conn = duckdb.connect(":memory:")
        conn.execute("SET memory_limit = '64MB'")
        conn.execute("INSTALL httpfs")
        conn.execute("LOAD httpfs")
        
        # Get parquet schema
        schema_result = conn.execute("DESCRIBE SELECT * FROM read_parquet(?)", [parquet_url]).fetchall()
        parquet_columns = {row[0]: _map_duckdb_type_to_sql(row[1]) for row in schema_result}
        conn.close()
        
        # Find the table that matches the parquet table name
        matching_table = None
        for table in table_schema:
            if table.get("name") == parquet_data_source.table_name:
                matching_table = table
                break
        
        if not matching_table:
            return f"No table named '{parquet_data_source.table_name}' found in schema to match parquet data", None
        
        # Compare schemas
        table_columns = {col["name"]: col["type"] for col in matching_table.get("columns", [])}
        
        # Check for missing columns (critical error)
        missing_in_table = set(parquet_columns.keys()) - set(table_columns.keys())
        if missing_in_table:
            return f"Columns missing from table schema: {', '.join(sorted(missing_in_table))}", None
        
        # Check for extra columns (warning only)
        extra_in_table = set(table_columns.keys()) - set(parquet_columns.keys())
        warning_message = None
        if extra_in_table:
            warning_message = f"Extra columns in table schema (not in parquet): {', '.join(sorted(extra_in_table))}"
        
        # Check for type mismatches (critical error)
        type_mismatches = []
        for col_name in parquet_columns:
            if col_name in table_columns:
                parquet_type = parquet_columns[col_name]
                table_type = table_columns[col_name]
                # Allow some type flexibility (e.g., INTEGER vs BIGINT)
                if not _types_compatible(parquet_type, table_type):
                    type_mismatches.append(f"{col_name}: parquet={parquet_type}, table={table_type}")
        
        if type_mismatches:
            return f"Column type mismatches: {'; '.join(type_mismatches)}", warning_message
        
        # All validations passed
        return None, warning_message
        
    except Exception as e:
        return f"Schema validation failed: {str(e)}", None

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
    
    # Schema enforcement: validate consistency between table schema and parquet data
    if problem_data.question.parquet_data_source and problem_data.question.tables:
        table_data = [
            {
                "name": table.name,
                "columns": [{"name": col.name, "type": col.type} for col in table.columns]
            }
            for table in problem_data.question.tables
        ]
        
        schema_error, schema_warning = _validate_schema_consistency(table_data, problem_data.question.parquet_data_source)
        if schema_error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Schema validation failed: {schema_error}"
            )
        
        # Log warning if present (could be enhanced to return to frontend)
        if schema_warning:
            logger = logging.getLogger(__name__)
            logger.warning(f"Schema validation warning for problem creation: {schema_warning}")
    
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
    
    # Prepare parquet data source if provided
    parquet_data_source_data = None
    if problem_data.question.parquet_data_source:
        parquet_data_source_data = {
            "git_repo_url": problem_data.question.parquet_data_source.git_repo_url,
            "file_path": problem_data.question.parquet_data_source.file_path,
            "table_name": problem_data.question.parquet_data_source.table_name,
            "description": problem_data.question.parquet_data_source.description
        }
    
    # Create the problem
    problem = Problem(
        id=str(uuid.uuid4()),
        title=problem_data.title,
        difficulty=problem_data.difficulty,
        question=question_data,
        parquet_data_source=parquet_data_source_data,
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