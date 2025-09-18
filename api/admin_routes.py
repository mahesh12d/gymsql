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
            # Test if parquet file exists and is accessible using parameterized query
            result = conn.execute("SELECT COUNT(*) as row_count FROM read_parquet(?)", [parquet_url]).fetchone()
            
            if result is None:
                return ParquetValidationResponse(
                    success=False,
                    message="Parquet file not found or inaccessible",
                    error=f"Could not access parquet file at: {parquet_url}"
                )
            
            row_count = result[0]
            
            # Get schema information using parameterized query
            schema_result = conn.execute("DESCRIBE SELECT * FROM read_parquet(?)", [parquet_url]).fetchall()
            schema = [{"column": row[0], "type": row[1]} for row in schema_result]
            
            # Get sample data (first 10 rows) using parameterized query
            sample_result = conn.execute("SELECT * FROM read_parquet(?) LIMIT 10", [parquet_url]).fetchdf()
            sample_data = sample_result.to_dict(orient="records") if not sample_result.empty else []
            
            conn.close()
            
            return ParquetValidationResponse(
                success=True,
                message=f"Parquet file validated successfully. Found {row_count} rows with {len(schema)} columns.",
                table_schema=schema,
                sample_data=sample_data,
                row_count=row_count,
                parquet_url=parquet_url
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