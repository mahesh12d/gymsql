"""
DuckDB Sandbox Service for SQL Learning Platform
===============================================
Handles SQL execution against parquet datasets from GitHub for secure sandbox environments.
"""

import duckdb
import os
import logging
from typing import Dict, Any, List, Optional
from fastapi import HTTPException
import tempfile
import time

logger = logging.getLogger(__name__)

class DuckDBSandbox:
    """
    Isolated DuckDB instance for executing user SQL queries against problem datasets
    """
    
    def __init__(self, timeout_seconds: int = 30, memory_limit_mb: int = 256):
        """
        Initialize DuckDB sandbox with memory and time limits
        
        Args:
            timeout_seconds: Maximum query execution time
            memory_limit_mb: Memory limit for DuckDB instance
        """
        self.timeout_seconds = timeout_seconds
        self.memory_limit_mb = memory_limit_mb
        self.conn = None
        self.github_repo_base = "https://github.com/mahesh12d/GymSql-problems_et/raw/main"
        
        # Initialize DuckDB connection
        self._initialize_connection()
    
    def _initialize_connection(self):
        """Initialize DuckDB connection with security and performance settings"""
        try:
            # Create in-memory DuckDB instance for isolation
            self.conn = duckdb.connect(":memory:")
            
            # Configure DuckDB settings
            self.conn.execute("SET memory_limit = ?", [f"{self.memory_limit_mb}MB"])
            self.conn.execute("SET threads = 1")  # Limit threads for sandbox
            
            # Install and load httpfs for remote parquet access
            self.conn.execute("INSTALL httpfs")
            self.conn.execute("LOAD httpfs")
            
            logger.info(f"DuckDB sandbox initialized with {self.memory_limit_mb}MB memory limit")
            
        except Exception as e:
            logger.error(f"Failed to initialize DuckDB connection: {e}")
            raise HTTPException(status_code=500, detail="Failed to initialize sandbox environment")
    
    async def setup_problem_data(self, problem_id: str) -> Dict[str, Any]:
        """
        Load problem dataset from GitHub parquet file into DuckDB
        
        Args:
            problem_id: Unique identifier for the problem
            
        Returns:
            Dict with success status and any error messages
        """
        try:
            # Construct parquet file URL
            parquet_url = f"{self.github_repo_base}/problems/{problem_id}.parquet"
            
            logger.info(f"Loading problem data from: {parquet_url}")
            
            # Test if parquet file exists and is accessible
            test_query = f"SELECT COUNT(*) as row_count FROM '{parquet_url}'"
            result = self.conn.execute(test_query).fetchone()
            
            if result is None:
                return {"success": False, "error": f"Parquet file not found or inaccessible: {problem_id}.parquet"}
            
            # Create main problem_data table
            self.conn.execute(f"CREATE TABLE problem_data AS SELECT * FROM '{parquet_url}'")
            
            # Get table schema for user reference
            schema_result = self.conn.execute("DESCRIBE problem_data").fetchall()
            schema = [{"column": row[0], "type": row[1]} for row in schema_result]
            
            row_count = result[0] if result else 0
            
            return {
                "success": True,
                "message": f"Problem data loaded successfully",
                "schema": schema,
                "row_count": row_count,
                "parquet_url": parquet_url
            }
            
        except Exception as e:
            error_msg = f"Failed to load problem data for {problem_id}: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    def execute_query(self, query: str) -> Dict[str, Any]:
        """
        Execute user SQL query safely with security validations
        
        Args:
            query: SQL query string to execute
            
        Returns:
            Dict containing query results or error information
        """
        start_time = time.time()
        
        try:
            # Security validation - block dangerous operations
            forbidden_keywords = [
                'DROP', 'DELETE', 'INSERT', 'UPDATE', 'ALTER', 'CREATE', 
                'TRUNCATE', 'REPLACE', 'ATTACH', 'DETACH', 'PRAGMA',
                'INSTALL', 'LOAD', 'SET'
            ]
            
            query_upper = query.upper()
            for keyword in forbidden_keywords:
                if keyword in query_upper:
                    return {
                        "success": False,
                        "error": f"Forbidden SQL operation detected: {keyword}",
                        "execution_time_ms": 0
                    }
            
            # Additional validation for table names - only allow problem_data
            if 'FROM' in query_upper:
                # Simple check for allowed table names
                allowed_tables = ['problem_data']
                words = query_upper.split()
                for i, word in enumerate(words):
                    if word == 'FROM' and i + 1 < len(words):
                        next_word = words[i + 1].strip('();,')
                        if next_word not in [t.upper() for t in allowed_tables]:
                            return {
                                "success": False,
                                "error": f"Access to table '{next_word}' is not allowed. Use 'problem_data' table.",
                                "execution_time_ms": 0
                            }
            
            # Execute query with timeout
            try:
                result_df = self.conn.execute(query).fetchdf()
                execution_time = (time.time() - start_time) * 1000  # Convert to milliseconds
                
                # Limit result size for safety
                max_rows = 1000
                if len(result_df) > max_rows:
                    result_df = result_df.head(max_rows)
                    truncated = True
                else:
                    truncated = False
                
                return {
                    "success": True,
                    "results": result_df.to_dict(orient="records"),
                    "columns": list(result_df.columns),
                    "row_count": len(result_df),
                    "execution_time_ms": round(execution_time, 2),
                    "truncated": truncated
                }
                
            except Exception as query_error:
                execution_time = (time.time() - start_time) * 1000
                return {
                    "success": False,
                    "error": str(query_error),
                    "execution_time_ms": round(execution_time, 2)
                }
                
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            logger.error(f"Query execution failed: {e}")
            return {
                "success": False,
                "error": f"Query execution failed: {str(e)}",
                "execution_time_ms": round(execution_time, 2)
            }
    
    def get_table_info(self) -> Dict[str, Any]:
        """
        Get information about available tables and their schema
        
        Returns:
            Dict containing table information
        """
        try:
            # Get table schema
            schema_result = self.conn.execute("DESCRIBE problem_data").fetchall()
            schema = [{"column": row[0], "type": row[1]} for row in schema_result]
            
            # Get row count
            count_result = self.conn.execute("SELECT COUNT(*) FROM problem_data").fetchone()
            row_count = count_result[0] if count_result else 0
            
            # Get sample data (first 5 rows)
            sample_result = self.conn.execute("SELECT * FROM problem_data LIMIT 5").fetchdf()
            sample_data = sample_result.to_dict(orient="records") if not sample_result.empty else []
            
            return {
                "success": True,
                "tables": [{
                    "name": "problem_data",
                    "schema": schema,
                    "row_count": row_count,
                    "sample_data": sample_data
                }]
            }
            
        except Exception as e:
            logger.error(f"Failed to get table info: {e}")
            return {
                "success": False,
                "error": f"Failed to get table information: {str(e)}"
            }
    
    def cleanup(self):
        """Clean up DuckDB connection and resources"""
        try:
            if self.conn:
                self.conn.close()
                self.conn = None
            logger.info("DuckDB sandbox cleaned up successfully")
        except Exception as e:
            logger.error(f"Error during sandbox cleanup: {e}")

    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensure cleanup"""
        self.cleanup()


class DuckDBSandboxManager:
    """
    Manager for DuckDB sandbox instances with resource management
    """
    
    def __init__(self):
        self.active_sandboxes = {}
        self.max_concurrent_sandboxes = 10
    
    async def create_sandbox(self, user_id: str, problem_id: str) -> DuckDBSandbox:
        """
        Create a new DuckDB sandbox for a user and problem
        
        Args:
            user_id: User identifier
            problem_id: Problem identifier
            
        Returns:
            DuckDBSandbox instance
        """
        sandbox_key = f"{user_id}_{problem_id}"
        
        # Clean up existing sandbox if present
        if sandbox_key in self.active_sandboxes:
            self.active_sandboxes[sandbox_key].cleanup()
        
        # Check resource limits
        if len(self.active_sandboxes) >= self.max_concurrent_sandboxes:
            # Clean up oldest sandbox
            oldest_key = next(iter(self.active_sandboxes))
            self.active_sandboxes[oldest_key].cleanup()
            del self.active_sandboxes[oldest_key]
        
        # Create new sandbox
        sandbox = DuckDBSandbox()
        self.active_sandboxes[sandbox_key] = sandbox
        
        return sandbox
    
    def get_sandbox(self, user_id: str, problem_id: str) -> Optional[DuckDBSandbox]:
        """Get existing sandbox for user and problem"""
        sandbox_key = f"{user_id}_{problem_id}"
        return self.active_sandboxes.get(sandbox_key)
    
    def cleanup_sandbox(self, user_id: str, problem_id: str):
        """Clean up specific sandbox"""
        sandbox_key = f"{user_id}_{problem_id}"
        if sandbox_key in self.active_sandboxes:
            self.active_sandboxes[sandbox_key].cleanup()
            del self.active_sandboxes[sandbox_key]
    
    def cleanup_all(self):
        """Clean up all active sandboxes"""
        for sandbox in self.active_sandboxes.values():
            sandbox.cleanup()
        self.active_sandboxes.clear()


# Global sandbox manager instance
sandbox_manager = DuckDBSandboxManager()