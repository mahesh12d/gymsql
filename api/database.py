"""
Database configuration and connection setup
"""
import os
import json
from dotenv import load_dotenv
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.dialects.postgresql import JSONB
from .models import Base

# Load environment variables from .env file
load_dotenv()

# Database URL from environment variable (preferred for production)
DATABASE_URL = os.getenv("DATABASE_URL")

# Only fallback to .env file in development if environment variable doesn't exist
if not DATABASE_URL and os.getenv("NODE_ENV", "development") == "development":
    from pathlib import Path
    env_file = Path(".env")
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                if line.strip().startswith('DATABASE_URL=') and not line.strip().startswith('#'):
                    DATABASE_URL = line.strip().split('=', 1)[1]
                    break

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is required")

# Create engine with proper SSL and connection pooling
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # Verify connections before use
    pool_recycle=300,    # Recycle connections every 5 minutes
    pool_timeout=10,     # Timeout for getting connection from pool
    max_overflow=0,      # No overflow connections
    echo=False          # Set to True for SQL logging if needed
)

def parse_tabular_data(tabular_string: str) -> list:
    """
    Parse tabular string format into list of dictionaries
    Format: 'column1 | column2\\nvalue1 | value2\\n...'
    """
    if not tabular_string or tabular_string.strip() == '':
        return []
    
    try:
        lines = tabular_string.strip().split('\\n')
        if len(lines) < 2:
            return []
        
        # First line contains headers
        headers = [h.strip() for h in lines[0].split('|')]
        
        # Remaining lines contain data
        result = []
        for line in lines[1:]:
            if line.strip():
                values = [v.strip() for v in line.split('|')]
                if len(values) == len(headers):
                    row = {}
                    for i, header in enumerate(headers):
                        value = values[i]
                        # Try to convert to number if possible
                        try:
                            if '.' in value:
                                value = float(value)
                            else:
                                value = int(value)
                        except ValueError:
                            pass  # Keep as string
                        row[header] = value
                    result.append(row)
        return result
    except Exception as e:
        print(f"Error parsing tabular data: {e}")
        return []

def run_schema_migrations():
    """
    Idempotent schema migration to handle JSONB question field transition
    """
    with engine.begin() as conn:
        inspector = inspect(engine)
        
        # Check if problems table exists
        if 'problems' not in inspector.get_table_names():
            print("Problems table doesn't exist, will be created by create_tables()")
            return
        
        # Get current columns
        columns = [col['name'] for col in inspector.get_columns('problems')]
        
        # Check if question column exists
        if 'question' not in columns:
            print("Adding question JSONB column to problems table...")
            
            # Add question column
            conn.execute(text("ALTER TABLE problems ADD COLUMN question JSONB NULL"))
            
            # Migrate data from old columns if they exist
            legacy_cols = ['description', 'schema', 'expected_output']
            existing_legacy = [col for col in legacy_cols if col in columns]
            
            if existing_legacy:
                print(f"Migrating data from legacy columns: {existing_legacy}")
                
                # First, get all the data that needs migration
                result = conn.execute(text("SELECT id, description, schema, expected_output FROM problems WHERE question IS NULL"))
                problems = result.fetchall()
                
                for problem in problems:
                    problem_id, description, schema, expected_output = problem
                    
                    # Parse expected_output from tabular format to list of dicts
                    parsed_output = parse_tabular_data(expected_output or '')
                    
                    # Create the question JSONB object
                    question_data = {
                        'description': description or '',
                        'tables': [],  # Schema parsing would need more complex logic
                        'expectedOutput': parsed_output
                    }
                    
                    # Update the specific row
                    conn.execute(text("""
                        UPDATE problems 
                        SET question = :question_data
                        WHERE id = :problem_id
                    """), {'question_data': question_data, 'problem_id': problem_id})
                
                # Drop old columns
                for col in existing_legacy:
                    print(f"Dropping legacy column: {col}")
                    conn.execute(text(f"ALTER TABLE problems DROP COLUMN IF EXISTS {col}"))
            
            # Make question NOT NULL
            conn.execute(text("ALTER TABLE problems ALTER COLUMN question SET NOT NULL"))
            print("Schema migration completed successfully!")
        else:
            # Check if we need to fix existing data with incorrect expectedOutput format
            result = conn.execute(text("""
                SELECT id, question 
                FROM problems 
                WHERE jsonb_typeof(question->'expectedOutput') = 'string'
            """))
            problems_to_fix = result.fetchall()
            
            if problems_to_fix:
                print(f"Fixing {len(problems_to_fix)} problems with incorrect expectedOutput format...")
                for problem_id, question_json in problems_to_fix:
                    # Parse the string expectedOutput to proper list format
                    expected_output_str = question_json.get('expectedOutput', '')
                    parsed_output = parse_tabular_data(expected_output_str)
                    
                    # Update the expectedOutput field
                    conn.execute(text("""
                        UPDATE problems 
                        SET question = jsonb_set(question, '$.expectedOutput', :new_output)
                        WHERE id = :problem_id
                    """), {'new_output': json.dumps(parsed_output), 'problem_id': problem_id})
                print("Fixed incorrect expectedOutput formats!")
            else:
                print("Question column already exists, no migration needed")

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create all tables
def create_tables():
    """Create all tables including new enhanced schema tables"""
    # First create enum types if they don't exist
    create_enum_types()
    
    # Then create all tables
    Base.metadata.create_all(bind=engine)
    print("SUCCESS: All database tables created successfully")
    
    # Initialize enhanced schema with sample data
    initialize_enhanced_schema()

def create_enum_types():
    """Create PostgreSQL enum types if they don't exist"""
    with engine.begin() as conn:
        # Create difficulty_level enum
        conn.execute(text("""
            DO $$ BEGIN
                CREATE TYPE difficulty_level AS ENUM ('Beginner', 'Easy', 'Medium', 'Hard', 'Expert');
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$;
        """))
        
        # Create execution_status enum
        conn.execute(text("""
            DO $$ BEGIN
                CREATE TYPE execution_status AS ENUM ('SUCCESS', 'ERROR', 'TIMEOUT', 'MEMORY_LIMIT');
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$;
        """))
        
        # Create sandbox_status enum
        conn.execute(text("""
            DO $$ BEGIN
                CREATE TYPE sandbox_status AS ENUM ('ACTIVE', 'EXPIRED', 'CLEANUP_PENDING');
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$;
        """))
        
        print("SUCCESS: PostgreSQL enum types created successfully")

def initialize_enhanced_schema():
    """Initialize the enhanced schema with sample data - handles topics and badges independently"""
    from .models import Topic, Badge, DifficultyLevel
    
    # Create a database session
    db = SessionLocal()
    
    try:
        topics_created = 0
        badges_created = 0
        
        # Initialize Topics independently
        try:
            if db.query(Topic).count() == 0:
                print("Initializing sample topics...")
                
                topics = [
                    Topic(
                        name="Basic SELECT Queries",
                        description="Learn fundamental SELECT statements, filtering, and sorting",
                        difficulty_level=DifficultyLevel.BEGINNER,
                        order_index=1
                    ),
                    Topic(
                        name="Joins and Relationships",
                        description="Master INNER, LEFT, RIGHT, and FULL joins",
                        difficulty_level=DifficultyLevel.EASY,
                        order_index=2
                    ),
                    Topic(
                        name="Aggregate Functions",
                        description="COUNT, SUM, AVG, MIN, MAX and GROUP BY clauses",
                        difficulty_level=DifficultyLevel.MEDIUM,
                        order_index=3
                    ),
                    Topic(
                        name="Subqueries and CTEs",
                        description="Complex nested queries and Common Table Expressions",
                        difficulty_level=DifficultyLevel.HARD,
                        order_index=4
                    ),
                    Topic(
                        name="Advanced Performance",
                        description="Query optimization, indexing, and window functions",
                        difficulty_level=DifficultyLevel.EXPERT,
                        order_index=5
                    )
                ]
                
                db.add_all(topics)
                db.commit()
                topics_created = len(topics)
                print(f"SUCCESS: Created {topics_created} topics")
            else:
                print("Topics already exist, skipping topic initialization")
        except Exception as e:
            print(f"❌ Error initializing topics: {e}")
            db.rollback()
        
        # Initialize Badges independently
        try:
            if db.query(Badge).count() == 0:
                print("Initializing sample badges...")
                
                badges = [
                    Badge(
                        name="First Steps",
                        description="Complete your first SQL query",
                        criteria={"first_successful_submission": True},
                        points_reward=10,
                        rarity="common"
                    ),
                    Badge(
                        name="Problem Solver",
                        description="Solve 10 problems",
                        criteria={"problems_solved": 10},
                        points_reward=50,
                        rarity="common"
                    ),
                    Badge(
                        name="Speed Demon",
                        description="Execute a query in under 100ms",
                        criteria={"execution_time_ms": {"<": 100}},
                        points_reward=25,
                        rarity="rare"
                    ),
                    Badge(
                        name="Master",
                        description="Solve 5 Expert level problems",
                        criteria={"expert_problems_solved": 5},
                        points_reward=200,
                        rarity="legendary"
                    )
                ]
                
                db.add_all(badges)
                db.commit()
                badges_created = len(badges)
                print(f"SUCCESS: Created {badges_created} badges")
            else:
                print("Badges already exist, skipping badge initialization")
        except Exception as e:
            print(f"❌ Error initializing badges: {e}")
            db.rollback()
        
        if topics_created == 0 and badges_created == 0:
            print("Enhanced schema already fully initialized")
        else:
            print(f"Enhanced schema initialization complete: {topics_created} topics, {badges_created} badges")
        
    except Exception as e:
        print(f"❌ Error in enhanced schema initialization: {e}")
        db.rollback()
    finally:
        db.close()

# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()