#!/usr/bin/env python3
"""
Simple test script to debug s3_datasets vs s3_data_source issue
"""

import asyncio
import sys
import os

# Add the api directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'api'))

from duckdb_sandbox import DuckDBSandbox

async def test_s3_datasets():
    """Test s3_datasets configuration directly"""
    print("Testing s3_datasets configuration...")
    
    # Create a test sandbox
    sandbox = DuckDBSandbox()
    
    try:
        # Test s3_datasets configuration (the failing case)
        s3_datasets = [
            {
                "key": "problems/test002/sool_docs.parquet",
                "bucket": "sql-learning-datasets",
                "table_name": "s1",
                "description": ""
            },
            {
                "key": "problems/test002/sool_steps.parquet",
                "bucket": "sql-learning-datasets",
                "table_name": "s2",
                "description": ""
            }
        ]
        
        print(f"Attempting to load s3_datasets: {s3_datasets}")
        
        # Test the setup
        result = await sandbox.setup_problem_data(
            problem_id="test",
            s3_data_source=None,
            s3_datasets=s3_datasets,
            parquet_data_source=None,
            question_tables=None
        )
        
        print(f"Setup result: {result}")
        
        if result["success"]:
            # Try to query the tables
            print("\nTesting table queries...")
            try:
                # List tables
                tables = sandbox.conn.execute("SHOW TABLES").fetchall()
                print(f"Available tables: {[row[0] for row in tables]}")
                
                # Try to query s1 table
                s1_result = sandbox.conn.execute("SELECT * FROM s1 LIMIT 5").fetchall()
                print(f"s1 table sample (5 rows): {s1_result}")
                
                # Try to query s2 table
                s2_result = sandbox.conn.execute("SELECT * FROM s2 LIMIT 5").fetchall()
                print(f"s2 table sample (5 rows): {s2_result}")
                
            except Exception as query_e:
                print(f"Query error: {query_e}")
        else:
            print(f"Setup failed: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
    finally:
        sandbox.cleanup()

async def test_s3_data_source():
    """Test s3_data_source configuration (the working case)"""
    print("\n" + "="*50)
    print("Testing s3_data_source configuration...")
    
    # Create a test sandbox
    sandbox = DuckDBSandbox()
    
    try:
        # Test s3_data_source configuration (the working case)
        s3_data_source = {
            "key": "problems/test001/titanic.parquet",
            "bucket": "sql-learning-datasets",
            "table_name": "titanic",
            "description": ""
        }
        
        print(f"Attempting to load s3_data_source: {s3_data_source}")
        
        # Test the setup
        result = await sandbox.setup_problem_data(
            problem_id="test",
            s3_data_source=s3_data_source,
            s3_datasets=None,
            parquet_data_source=None,
            question_tables=None
        )
        
        print(f"Setup result: {result}")
        
        if result["success"]:
            # Try to query the table
            print("\nTesting table queries...")
            try:
                # List tables
                tables = sandbox.conn.execute("SHOW TABLES").fetchall()
                print(f"Available tables: {[row[0] for row in tables]}")
                
                # Try to query titanic table
                result = sandbox.conn.execute("SELECT * FROM titanic LIMIT 5").fetchall()
                print(f"titanic table sample (5 rows): {result}")
                
            except Exception as query_e:
                print(f"Query error: {query_e}")
        else:
            print(f"Setup failed: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
    finally:
        sandbox.cleanup()

if __name__ == "__main__":
    print("S3 Datasets Debug Test")
    print("=" * 50)
    asyncio.run(test_s3_datasets())
    asyncio.run(test_s3_data_source())