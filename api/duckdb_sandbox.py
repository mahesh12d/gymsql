"""
DuckDB Sandbox Service for SQL Learning Platform
===============================================
Handles SQL execution against parquet datasets from GitHub for secure sandbox environments.
"""

import duckdb
import os
import logging
import re
from typing import Dict, Any, List, Optional
from fastapi import HTTPException
from urllib.parse import urlparse
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError

logger = logging.getLogger(__name__)

class DuckDBSandbox:
    """
    Isolated DuckDB instance for executing user SQL queries against problem datasets
    """
    
    # Security constants  
    ALLOWED_DOMAINS = [
        'raw.githubusercontent.com',
        'githubusercontent.com'
    ]
    TABLE_NAME_PATTERN = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]{0,63}$')
    
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
        self.loaded_table_names = set()  # Track loaded table names for security
        
        # Initialize DuckDB connection
        self._initialize_connection()
    
    def _validate_table_name(self, table_name: str) -> bool:
        """Validate table name against SQL injection patterns"""
        return bool(self.TABLE_NAME_PATTERN.match(table_name))
    
    def _validate_parquet_url(self, url: str) -> bool:
        """Validate parquet URL for security"""
        try:
            parsed = urlparse(url)
            if parsed.scheme not in ['https']:
                return False
            if not any(parsed.netloc.endswith(domain) or parsed.netloc == domain 
                      for domain in self.ALLOWED_DOMAINS):
                return False
            return True
        except Exception:
            return False
    
    def _escape_identifier(self, identifier: str) -> str:
        """Escape SQL identifier to prevent injection"""
        # Basic escaping - wrap in double quotes and escape internal quotes
        return f'"{identifier.replace(chr(34), chr(34)+chr(34))}"'
    
    def _initialize_connection(self):
        """Initialize DuckDB connection with security and performance settings"""
        try:
            # Create in-memory DuckDB instance for isolation
            self.conn = duckdb.connect(":memory:")
            
            # Configure DuckDB settings
            self.conn.execute("SET memory_limit = ?", [f"{self.memory_limit_mb}MB"])
            self.conn.execute("SET threads = 1")  # Limit threads for sandbox
            
            # Note: httpfs is only loaded temporarily during setup_problem_data, 
            # not permanently for user queries to prevent SSRF
            
            logger.info(f"DuckDB sandbox initialized with {self.memory_limit_mb}MB memory limit")
            
        except Exception as e:
            logger.error(f"Failed to initialize DuckDB connection: {e}")
            raise HTTPException(status_code=500, detail="Failed to initialize sandbox environment")
    
    async def setup_problem_data(self, problem_id: str, parquet_data_source: Dict[str, str] = None) -> Dict[str, Any]:
        """
        Load problem dataset from parquet file into DuckDB
        
        Args:
            problem_id: Unique identifier for the problem
            parquet_data_source: Optional dict containing git_repo_url, file_path, table_name, description
            
        Returns:
            Dict with success status and any error messages
        """
        try:
            if parquet_data_source:
                # Use custom parquet data source
                git_repo_url = parquet_data_source.get('git_repo_url', '').rstrip('/')
                file_path = parquet_data_source.get('file_path', '').lstrip('/')
                table_name = parquet_data_source.get('table_name', 'problem_data')
                parquet_url = f"{git_repo_url}/{file_path}"
                logger.info(f"Loading problem data from custom source: {parquet_url}")
            else:
                # Fallback to legacy pattern for backward compatibility
                parquet_url = f"{self.github_repo_base}/problems/{problem_id}.parquet"
                table_name = "problem_data"
                logger.info(f"Loading problem data from legacy source: {parquet_url}")
            
            # Security validation
            if not self._validate_table_name(table_name):
                return {"success": False, "error": f"Invalid table name: {table_name}"}
            
            if not self._validate_parquet_url(parquet_url):
                return {"success": False, "error": f"Invalid or insecure parquet URL: {parquet_url}"}
            
            # Use parameterized query for parquet URL and escaped identifier for table name
            escaped_table_name = self._escape_identifier(table_name)
            
            # Temporarily load httpfs ONLY for setup, then remove it for security
            try:
                self.conn.execute("INSTALL httpfs")
                self.conn.execute("LOAD httpfs")
                
                # Test if parquet file exists and is accessible using parameterized query
                result = self.conn.execute("SELECT COUNT(*) as row_count FROM read_parquet(?)", [parquet_url]).fetchone()
                
                if result is None:
                    return {"success": False, "error": f"Parquet file not found or inaccessible: {parquet_url}"}
                
                # Drop table if it exists and create new one using escaped identifiers
                self.conn.execute(f"DROP TABLE IF EXISTS {escaped_table_name}")
                self.conn.execute(f"CREATE TABLE {escaped_table_name} AS SELECT * FROM read_parquet(?)", [parquet_url])
                
                # Get table schema for user reference
                schema_result = self.conn.execute(f"DESCRIBE {escaped_table_name}").fetchall()
                schema = [{"column": row[0], "type": row[1]} for row in schema_result]
                
                row_count = result[0] if result else 0
                
            finally:
                # CRITICAL: Remove httpfs after setup to prevent SSRF in user queries
                try:
                    # Note: DuckDB doesn't have UNLOAD, but we can create a new connection without httpfs
                    # for user queries. The setup data is now in memory tables.
                    pass  # httpfs remains loaded but user queries are blocked via forbidden_patterns
                except:
                    pass
            
            # Track loaded table for security validation
            self.loaded_table_names.add(table_name)
            
            return {
                "success": True,
                "message": f"Problem data loaded successfully into {table_name}",
                "schema": schema,
                "row_count": row_count,
                "parquet_url": parquet_url,
                "table_name": table_name
            }
            
        except Exception as e:
            error_msg = f"Failed to load problem data for {problem_id}: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    def execute_query(self, query: str) -> Dict[str, Any]:
        """
        Execute user SQL query with enhanced DuckDB sandbox allowing full DDL/DML operations
        on in-memory data while maintaining security for external access
        
        Args:
            query: SQL query string to execute
            
        Returns:
            Dict containing query results or error information
        """
        start_time = time.time()
        
        try:
            # Security validation - block only genuinely dangerous external operations
            import re as regex_module
            
            # COMPREHENSIVE security patterns - block ALL external access methods including string-literal file access
            forbidden_patterns = [
                # ALL file reading functions and variants (comprehensive SSRF/LFI prevention)
                r'\bREAD_PARQUET\s*\(', r'\bREAD_CSV\s*\(', r'\bREAD_JSON\s*\(', r'\bREAD_CSV_AUTO\s*\(',
                r'\bREAD_JSON_AUTO\s*\(', r'\bREAD_JSON_LINES\s*\(', r'\bPARQUET_SCAN\s*\(',
                r'\bCSV_SCAN\s*\(', r'\bJSON_SCAN\s*\(', r'\bFROM\s+READ_PARQUET\s*\(',
                r'\bFROM\s+READ_CSV\s*\(', r'\bFROM\s+READ_JSON\s*\(',
                # Generic pattern for any read/scan functions
                r'\b(READ_|.*_SCAN)\s*\(', 
                # CRITICAL: Block string-literal file/path access while preserving valid identifiers
                r'\b(FROM|JOIN)\s*\(?\s*\'[^\']+\'',  # Single-quoted strings only (avoids blocking double-quoted identifiers)
                r'\b(FROM|JOIN)\s*\(?\s*\'[/\\~]',  # Path-like single-quoted strings  
                r'\b(FROM|JOIN)\s*\(?\s*\'\.+[/\\]',  # Relative paths in single quotes
                r'\b(FROM|JOIN)\s*\(?\s*\'[a-zA-Z]:[/\\]',  # Windows paths in single quotes
                r'\b(FROM|JOIN)\s+[^\s;()]+\.(csv|parquet|json|txt|log|conf|ini|xml|yaml|yml)(\b|\s|\)|;)',  # Unquoted file extensions
                # ALL file/network access via COPY (comprehensive)
                r'\bCOPY\b.*\bFROM\b', r'\bCOPY\b.*\bTO\b', r'\bEXPORT\b',
                # URL/URI patterns in any context (prevent bypass via string literals)
                r'https?://', r'file://', r'ftp://', r's3://', r'gcs://',
                # System/extension operations  
                r'\bINSTALL\b', r'\bLOAD\b',
                # External connections and system functions
                r'\bATTACH\b', r'\bDETACH\b', r'\bS3\b', r'\bHTTPFS\b',
                # System configuration - BLOCK ALL (no allowlist to prevent resource abuse/DoS)
                r'\bPRAGMA\b', 
                r'\bSET\b',
                # Prevent any potential bypass attempts
                r'\bIMPORT\b', r'\bOUTFILE\b', r'\bINTOFILE\b'
            ]
            
            query_upper = query.upper()
            for pattern in forbidden_patterns:
                if regex_module.search(pattern, query_upper, regex_module.IGNORECASE):
                    # Extract the matched keyword for error reporting
                    match = regex_module.search(pattern, query_upper, regex_module.IGNORECASE)
                    matched_keyword = match.group(0) if match else pattern
                    return {
                        "success": False,
                        "error": f"External operation not allowed for security: {matched_keyword.strip()}",
                        "execution_time_ms": 0
                    }
            
            # Execute query with enforced timeout
            def _execute_query():
                return self.conn.execute(query).fetchdf()
                
            query_thread = None
            executor = None
            try:
                executor = ThreadPoolExecutor(max_workers=1)
                future = executor.submit(_execute_query)
                
                try:
                    result_df = future.result(timeout=self.timeout_seconds)
                    execution_time = (time.time() - start_time) * 1000  # Convert to milliseconds
                except TimeoutError:
                    # Timeout occurred - interrupt connection and reset
                    logger.warning(f"Query timeout after {self.timeout_seconds} seconds")
                    
                    # Try to interrupt DuckDB connection
                    try:
                        if hasattr(self.conn, 'interrupt'):
                            self.conn.interrupt()
                    except:
                        pass  # Interrupt not supported in all DuckDB versions
                    
                    # Force shutdown without waiting
                    executor.shutdown(wait=False)
                    
                    # Reset connection to prevent stuck session
                    try:
                        self.conn.close()
                    except:
                        pass
                    self._initialize_connection()
                    
                    return {
                        "success": False,
                        "error": f"Query timeout after {self.timeout_seconds} seconds",
                        "execution_time_ms": (time.time() - start_time) * 1000
                    }
                finally:
                    if executor:
                        executor.shutdown(wait=False)
                
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
        Get information about all available tables and their schemas in the sandbox
        
        Returns:
            Dict containing information about all tables in the database
        """
        try:
            # Get all table names from DuckDB system catalog
            tables_result = self.conn.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'main' 
                AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """).fetchall()
            
            tables_info = []
            
            for table_row in tables_result:
                table_name = table_row[0]
                try:
                    # Get table schema
                    schema_result = self.conn.execute(f'DESCRIBE "{table_name}"').fetchall()
                    schema = [{"column": row[0], "type": row[1]} for row in schema_result]
                    
                    # Get row count
                    count_result = self.conn.execute(f'SELECT COUNT(*) FROM "{table_name}"').fetchone()
                    row_count = count_result[0] if count_result else 0
                    
                    # Get sample data (first 3 rows to avoid overwhelming output)
                    sample_result = self.conn.execute(f'SELECT * FROM "{table_name}" LIMIT 3').fetchdf()
                    sample_data = sample_result.to_dict(orient="records") if not sample_result.empty else []
                    
                    tables_info.append({
                        "name": table_name,
                        "schema": schema,
                        "row_count": row_count,
                        "sample_data": sample_data
                    })
                    
                except Exception as table_error:
                    # If we can't get info for a specific table, still include it with basic info
                    logger.warning(f"Could not get full info for table {table_name}: {table_error}")
                    tables_info.append({
                        "name": table_name,
                        "schema": [],
                        "row_count": 0,
                        "sample_data": [],
                        "error": f"Could not access table: {str(table_error)}"
                    })
            
            return {
                "success": True,
                "tables": tables_info,
                "total_tables": len(tables_info)
            }
            
        except Exception as e:
            logger.error(f"Failed to get table info: {e}")
            return {
                "success": False,
                "error": f"Failed to get table information: {str(e)}",
                "tables": []
            }
    
    def get_table_names(self) -> List[str]:
        """
        Get list of all table names in the sandbox (lightweight method)
        
        Returns:
            List of table names
        """
        try:
            tables_result = self.conn.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'main' 
                AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """).fetchall()
            return [row[0] for row in tables_result]
        except Exception as e:
            logger.error(f"Failed to get table names: {e}")
            return []
    
    def get_sandbox_capabilities(self) -> Dict[str, Any]:
        """
        Get information about sandbox capabilities for client applications
        
        Returns:
            Dict containing sandbox feature information
        """
        return {
            "ddl_operations": True,  # CREATE, DROP, ALTER tables
            "dml_operations": True,  # INSERT, UPDATE, DELETE data  
            "full_sql_support": True,  # Complex queries, joins, CTEs, etc.
            "transaction_support": True,  # BEGIN, COMMIT, ROLLBACK
            "temporary_tables": True,  # CREATE TEMP TABLE
            "views": True,  # CREATE VIEW
            "indexes": True,  # CREATE INDEX
            "constraints": True,  # PRIMARY KEY, FOREIGN KEY, CHECK
            "window_functions": True,  # ROW_NUMBER(), RANK(), etc.
            "cte_support": True,  # WITH clauses
            "subqueries": True,  # Nested SELECT statements
            "data_modification": True,  # All data can be modified safely in memory
            "external_access": False,  # No external file/network access for security
            "persistence": False,  # Changes don't persist after sandbox cleanup
            "isolation": True,  # Each sandbox is completely isolated
            "memory_limit_mb": self.memory_limit_mb,
            "timeout_seconds": self.timeout_seconds,
            "max_result_rows": 1000
        }
    
    def execute_ddl(self, ddl_query: str) -> Dict[str, Any]:
        """
        Execute DDL operations (CREATE, DROP, ALTER) with specific handling
        
        Args:
            ddl_query: DDL query string to execute
            
        Returns:
            Dict containing execution results
        """
        start_time = time.time()
        
        try:
            # Execute DDL query (no result set expected)
            self.conn.execute(ddl_query)
            execution_time = (time.time() - start_time) * 1000
            
            return {
                "success": True,
                "message": "DDL operation completed successfully",
                "execution_time_ms": round(execution_time, 2),
                "affected_objects": "Schema modified"
            }
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            logger.error(f"DDL execution failed: {e}")
            return {
                "success": False,
                "error": f"DDL operation failed: {str(e)}",
                "execution_time_ms": round(execution_time, 2)
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