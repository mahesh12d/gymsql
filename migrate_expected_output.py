#!/usr/bin/env python3
"""
Data migration script to copy expected output from question.expectedOutput 
to the new dedicated expected_output JSONB column.

This script safely migrates existing data to use the new architectural pattern.
"""

import sys
import os
import json
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add the api directory to the path to import models
sys.path.append(os.path.join(os.path.dirname(__file__), 'api'))

# Import with absolute path handling
try:
    from api.database import get_db_url
    from api.models import Problem
except ImportError:
    # Fallback for direct execution
    sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
    from api.database import get_db_url
    from api.models import Problem

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def migrate_expected_output():
    """
    Migrate expected output data from question.expectedOutput to dedicated expected_output column
    """
    try:
        # Get database URL
        db_url = get_db_url()
        engine = create_engine(db_url)
        SessionLocal = sessionmaker(bind=engine)
        
        with SessionLocal() as db:
            # Find all problems that have expectedOutput in question but no expected_output
            logger.info("Starting migration of expected output data...")
            
            # Raw SQL query to safely migrate data
            migration_query = text("""
                UPDATE problems 
                SET expected_output = (question->>'expectedOutput')::jsonb
                WHERE question ? 'expectedOutput' 
                  AND question->>'expectedOutput' != '[]'
                  AND question->>'expectedOutput' IS NOT NULL
                  AND (expected_output IS NULL OR expected_output = '[]'::jsonb)
            """)
            
            # Execute the migration
            result = db.execute(migration_query)
            migrated_count = result.rowcount
            db.commit()
            
            logger.info(f"Successfully migrated {migrated_count} problems")
            
            # Verify migration by checking some examples
            verification_query = text("""
                SELECT id, title, 
                       jsonb_array_length(COALESCE(expected_output, '[]'::jsonb)) as new_count,
                       jsonb_array_length(COALESCE(question->'expectedOutput', '[]'::jsonb)) as old_count
                FROM problems 
                WHERE expected_output IS NOT NULL 
                  AND jsonb_array_length(expected_output) > 0
                LIMIT 5
            """)
            
            verification_results = db.execute(verification_query).fetchall()
            
            logger.info("Migration verification (sample results):")
            for row in verification_results:
                logger.info(f"  Problem {row.id[:8]}... '{row.title}': new={row.new_count}, old={row.old_count}")
            
            # Summary statistics
            stats_query = text("""
                SELECT 
                  COUNT(*) as total_problems,
                  COUNT(CASE WHEN expected_output IS NOT NULL AND jsonb_array_length(expected_output) > 0 THEN 1 END) as with_new_expected,
                  COUNT(CASE WHEN question ? 'expectedOutput' AND jsonb_array_length(question->'expectedOutput') > 0 THEN 1 END) as with_old_expected
                FROM problems
            """)
            
            stats = db.execute(stats_query).fetchone()
            logger.info(f"Migration summary:")
            logger.info(f"  Total problems: {stats.total_problems}")
            logger.info(f"  Problems with new expected_output: {stats.with_new_expected}")
            logger.info(f"  Problems with old question.expectedOutput: {stats.with_old_expected}")
            
            return migrated_count
            
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        raise e

def main():
    """Main migration function"""
    try:
        logger.info("Expected Output Migration Tool")
        logger.info("================================")
        
        migrated_count = migrate_expected_output()
        
        logger.info("Migration completed successfully!")
        logger.info(f"Total records migrated: {migrated_count}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())