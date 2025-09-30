"""
DuckDB Sandbox Service for SQL Learning Platform
===============================================
Handles SQL execution against parquet datasets from S3 for secure sandbox environments.
"""

import duckdb
import os
import logging
import re
from typing import Dict, Any, List, Optional, Union
from urllib.parse import urlparse
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from .s3_service import s3_service

try:
    from fastapi import HTTPException
except ImportError:
    HTTPException = None

logger = logging.getLogger(__name__)

class DuckDBSandbox:
    """
    Isolated DuckDB instance for executing user SQL queries against problem datasets
    """
    
    # Security constants  
    ALLOWED_DOMAINS = [
        # S3 domains only - removed GitHub domains
    ]
    TABLE_NAME_PATTERN = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]{0,63}$')
    
    # Resource limits for security and performance
    MAX_TABLES_PER_PROBLEM = 20  # Maximum number of tables per problem
    MAX_SAMPLE_ROWS_PER_TABLE = 1000  # Maximum sample rows per table
    
    def __init__(self, timeout_seconds: int = 30, memory_limit_mb: int = 128, sandbox_id: str = None):
        """
        Initialize DuckDB sandbox with memory and time limits
        
        Args:
            timeout_seconds: Maximum query execution time
            memory_limit_mb: Memory limit for DuckDB instance
            sandbox_id: Unique identifier for this sandbox instance
        """
        import uuid
        self.id = sandbox_id or str(uuid.uuid4())
        self.timeout_seconds = timeout_seconds
        self.memory_limit_mb = memory_limit_mb
        self.conn = None
        # GitHub repository removed - using S3 only
        self.loaded_table_names = set()  # Track loaded table names for security
        
        # Initialize DuckDB connection
        self._initialize_connection()
    
    def _validate_table_name(self, table_name: str) -> bool:
        """Validate table name against SQL injection patterns"""
        return bool(self.TABLE_NAME_PATTERN.match(table_name))
    
    # URL validation removed - using S3 only, no external URL access
    
    def _escape_identifier(self, identifier: str) -> str:
        """Escape SQL identifier to prevent injection"""
        # Basic escaping - wrap in double quotes and escape internal quotes
        return f'"{identifier.replace(chr(34), chr(34)+chr(34))}"'
    
    def _validate_column_type(self, col_type: str) -> str:
        """
        Validate and sanitize column type to prevent DDL injection
        
        Args:
            col_type: Column type string from user input
            
        Returns:
            Validated and sanitized column type, or raises ValueError if invalid
        """
        if not col_type or not isinstance(col_type, str):
            return "VARCHAR"
        
        # Clean and normalize
        col_type = col_type.upper().strip()
        
        # Allowed DuckDB types (strict allowlist for security)
        allowed_types = {
            # Integer types
            'BOOLEAN', 'BOOL',
            'TINYINT', 'SMALLINT', 'INTEGER', 'INT', 'BIGINT',
            'UTINYINT', 'USMALLINT', 'UINTEGER', 'UBIGINT',
            
            # Floating point types
            'REAL', 'FLOAT', 'DOUBLE',
            
            # String types  
            'VARCHAR', 'CHAR', 'TEXT', 'STRING',
            
            # Date/time types
            'DATE', 'TIME', 'TIMESTAMP', 'TIMESTAMPTZ',
            
            # Other types
            'UUID', 'BLOB', 'JSON'
        }
        
        # Handle parameterized types (preserve parameters for valid base types)
        base_type = col_type
        parameters = ""
        if '(' in col_type:
            base_type = col_type.split('(')[0].strip()
            # Extract parameters but validate they contain only digits, commas, spaces
            param_part = col_type[col_type.find('('):]
            if re.match(r'^\(\s*\d+(\s*,\s*\d+)?\s*\)$', param_part):
                parameters = param_part
            else:
                # Invalid parameters, strip them
                parameters = ""
        
        # Check if base type is allowed
        if base_type not in allowed_types:
            logger.warning(f"Invalid column type '{col_type}', defaulting to VARCHAR")
            return "VARCHAR"
        
        # Return validated type with parameters if valid
        return base_type + parameters

    def _create_table_from_question_schema(self, table_name: str, columns: List[Dict[str, str]], sample_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Create a table in DuckDB from question schema definition
        
        Args:
            table_name: Name of the table to create
            columns: List of column definitions with 'name' and 'type' keys
            sample_data: List of sample data rows to insert
            
        Returns:
            Dict with success status and table information
        """
        try:
            escaped_table_name = self._escape_identifier(table_name)
            
            # Begin transaction for atomicity
            self.conn.execute("BEGIN TRANSACTION")
            
            try:
                # Build CREATE TABLE statement with validated types
                column_definitions = []
                for col in columns:
                    col_name = col.get('name', '').strip()
                    col_type = col.get('type', 'VARCHAR').strip()
                    
                    if not col_name:
                        self.conn.execute("ROLLBACK")
                        return {"success": False, "error": f"Column name is required for table '{table_name}'"}
                    
                    # Validate column name
                    if not self._validate_table_name(col_name):  # Reuse table name validation for column names
                        self.conn.execute("ROLLBACK")
                        return {"success": False, "error": f"Invalid column name '{col_name}' for table '{table_name}'"}
                    
                    # CRITICAL: Validate and sanitize column type to prevent DDL injection
                    validated_type = self._validate_column_type(col_type)
                    
                    # Escape column name and add validated type
                    escaped_col_name = self._escape_identifier(col_name)
                    column_definitions.append(f"{escaped_col_name} {validated_type}")
                
                # Create the table
                create_sql = f"CREATE TABLE {escaped_table_name} ({', '.join(column_definitions)})"
                logger.info(f"Creating table with SQL: {create_sql}")
                
                # Drop table if it exists first
                self.conn.execute(f"DROP TABLE IF EXISTS {escaped_table_name}")
                self.conn.execute(create_sql)
                
                # Insert sample data if provided
                rows_inserted = 0
                if sample_data and len(sample_data) > 0:
                    rows_inserted = self._insert_sample_data(table_name, sample_data)
                
                # Commit transaction on success
                self.conn.execute("COMMIT")
                
                # Get table schema information for response
                schema_result = self.conn.execute(f"DESCRIBE {escaped_table_name}").fetchall()
                schema = [{"column": row[0], "type": row[1]} for row in schema_result]
                
                # Get actual row count
                count_result = self.conn.execute(f"SELECT COUNT(*) FROM {escaped_table_name}").fetchone()
                actual_row_count = count_result[0] if count_result else 0
                
                # Get sample data for display (limit to 3 rows)
                sample_result = self.conn.execute(f"SELECT * FROM {escaped_table_name} LIMIT 3").fetchdf()
                display_sample_data = sample_result.to_dict(orient="records") if not sample_result.empty else []
                
                table_info = {
                    "name": table_name,
                    "schema": schema,
                    "row_count": actual_row_count,
                    "sample_data": display_sample_data
                }
                
                logger.info(f"Successfully created table '{table_name}' with {actual_row_count} rows")
                
                return {
                    "success": True,
                    "message": f"Table '{table_name}' created successfully with {actual_row_count} rows",
                    "table_info": table_info
                }
                
            except Exception as inner_e:
                # Rollback on any error during table creation
                self.conn.execute("ROLLBACK")
                raise inner_e
            
        except Exception as e:
            logger.error(f"Failed to create table '{table_name}': {e}")
            return {"success": False, "error": f"Failed to create table '{table_name}': {str(e)}"}
    
    def _insert_sample_data(self, table_name: str, sample_data: List[Dict[str, Any]]) -> int:
        """
        Insert sample data into a table
        
        Args:
            table_name: Name of the table
            sample_data: List of data rows to insert
            
        Returns:
            Number of rows inserted
        """
        try:
            if not sample_data or len(sample_data) == 0:
                return 0
            
            escaped_table_name = self._escape_identifier(table_name)
            rows_inserted = 0
            
            # Get table columns to validate data
            schema_result = self.conn.execute(f"DESCRIBE {escaped_table_name}").fetchall()
            table_columns = [row[0] for row in schema_result]
            
            for row_data in sample_data:
                try:
                    # Filter data to only include columns that exist in the table
                    filtered_data = {col: val for col, val in row_data.items() if col in table_columns}
                    
                    if not filtered_data:
                        continue  # Skip empty rows
                    
                    # Build INSERT statement with parameterized queries for safety
                    columns = list(filtered_data.keys())
                    values = list(filtered_data.values())
                    
                    escaped_columns = [self._escape_identifier(col) for col in columns]
                    placeholders = ', '.join(['?' for _ in values])
                    
                    insert_sql = f"INSERT INTO {escaped_table_name} ({', '.join(escaped_columns)}) VALUES ({placeholders})"
                    self.conn.execute(insert_sql, values)
                    rows_inserted += 1
                    
                except Exception as row_error:
                    logger.warning(f"Failed to insert row into '{table_name}': {row_error}. Row data: {row_data}")
                    # Continue with other rows even if one fails
                    continue
            
            logger.info(f"Inserted {rows_inserted} rows into table '{table_name}'")
            return rows_inserted
            
        except Exception as e:
            logger.error(f"Failed to insert sample data into '{table_name}': {e}")
            return 0
    
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
            if HTTPException:
                raise HTTPException(status_code=500, detail="Failed to initialize sandbox environment")
            else:
                raise RuntimeError("Failed to initialize sandbox environment")
    
    async def setup_problem_data(self, problem_id: str, s3_datasets: Union[Dict[str, str], List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """
        Load problem dataset into DuckDB from S3 parquet files.
        Supports both single table and multiple table configurations.
        
        Args:
            problem_id: Unique identifier for the problem
            s3_datasets: Either a single dict or list of dicts containing bucket, key, table_name, description for datasets
            
        Returns:
            Dict with success status and any error messages
        """
        try:
            tables_created = []
            total_rows = 0
            
            if not s3_datasets:
                return {"success": False, "error": "s3_datasets parameter is required"}
            
            # Normalize s3_datasets to always be a list
            if isinstance(s3_datasets, dict):
                datasets_list = [s3_datasets]
            else:
                datasets_list = s3_datasets
            
            # Handle S3 datasets
            if len(datasets_list) > 0:
                # Resource limits enforcement
                if len(datasets_list) > self.MAX_TABLES_PER_PROBLEM:
                    return {"success": False, "error": f"Too many S3 datasets: {len(datasets_list)}. Maximum allowed: {self.MAX_TABLES_PER_PROBLEM}"}
                
                logger.info(f"Loading {len(datasets_list)} tables from S3 datasets for problem {problem_id}")
                
                # Track successes and failures for partial success support
                dataset_errors = []
                
                for dataset in s3_datasets:
                    dataset_table_name = dataset.get('table_name', 'unknown')
                    dataset_s3_path = f"s3://{dataset.get('bucket', 'unknown')}/{dataset.get('key', 'unknown')}"
                    
                    try:
                        bucket = dataset.get('bucket', '').strip()
                        key = dataset.get('key', '').strip()
                        table_name = dataset.get('table_name', '').strip()
                        description = dataset.get('description', '')
                        etag = dataset.get('etag', '')
                        
                        if not bucket or not key or not table_name:
                            error_msg = f"Invalid S3 dataset configuration: bucket, key, and table_name are required"
                            logger.error(f"Dataset {dataset_table_name} ({dataset_s3_path}): {error_msg}")
                            dataset_errors.append({"table": dataset_table_name, "s3_path": dataset_s3_path, "error": error_msg})
                            continue
                        
                        # Security validation
                        if not self._validate_table_name(table_name):
                            error_msg = f"Invalid table name: {table_name}"
                            logger.error(f"Dataset {dataset_table_name} ({dataset_s3_path}): {error_msg}")
                            dataset_errors.append({"table": dataset_table_name, "s3_path": dataset_s3_path, "error": error_msg})
                            continue
                        
                        logger.info(f"Loading table '{table_name}' from S3: s3://{bucket}/{key}")
                        
                        # Use S3 service to download to temporary file
                        temp_file_path = s3_service.download_to_temp_file(bucket, key)
                        
                        try:
                            # Load parquet from local temp file
                            escaped_table_name = self._escape_identifier(table_name)
                            
                            # Test if parquet file is readable
                            result = self.conn.execute("SELECT COUNT(*) as row_count FROM read_parquet(?)", [temp_file_path]).fetchone()
                            
                            if result is None:
                                error_msg = f"Parquet file not readable: s3://{bucket}/{key}"
                                logger.error(f"Dataset {dataset_table_name} ({dataset_s3_path}): {error_msg}")
                                dataset_errors.append({"table": dataset_table_name, "s3_path": dataset_s3_path, "error": error_msg})
                                continue
                            
                            # Drop table if it exists and create new one
                            self.conn.execute(f"DROP TABLE IF EXISTS {escaped_table_name}")
                            self.conn.execute(f"CREATE TABLE {escaped_table_name} AS SELECT * FROM read_parquet(?)", [temp_file_path])
                            
                            # Get table schema information
                            schema_result = self.conn.execute(f"DESCRIBE {escaped_table_name}").fetchall()
                            schema = [{"column": row[0], "type": row[1]} for row in schema_result]
                            
                            row_count = result[0] if result else 0
                            total_rows += row_count
                            
                            # Get sample data for display (limit to 3 rows)
                            sample_result = self.conn.execute(f"SELECT * FROM {escaped_table_name} LIMIT 3").fetchdf()
                            display_sample_data = sample_result.to_dict(orient="records") if not sample_result.empty else []
                            
                            table_info = {
                                "name": table_name,
                                "schema": schema,
                                "row_count": row_count,
                                "sample_data": display_sample_data,
                                "data_source": f"s3://{bucket}/{key}",
                                "etag": etag
                            }
                            
                            tables_created.append(table_info)
                            
                            # Track loaded table for security validation
                            self.loaded_table_names.add(table_name)
                            
                            logger.info(f"Successfully loaded table '{table_name}' with {row_count} rows from S3")
                            
                        finally:
                            # Clean up temporary file
                            try:
                                os.unlink(temp_file_path)
                            except:
                                pass
                        
                    except Exception as e:
                        error_msg = f"Failed to load S3 dataset: {str(e)}"
                        logger.error(f"Dataset {dataset_table_name} ({dataset_s3_path}): {error_msg}", exc_info=True)
                        dataset_errors.append({"table": dataset_table_name, "s3_path": dataset_s3_path, "error": error_msg})
                        continue
                
                # Determine success based on partial results
                if len(tables_created) == 0:
                    # No tables loaded successfully - return complete failure
                    if len(dataset_errors) > 0:
                        consolidated_error = f"Failed to load any S3 datasets. Errors: " + "; ".join([f"{err['table']}: {err['error']}" for err in dataset_errors])
                    else:
                        consolidated_error = "Failed to load any S3 datasets due to unknown errors"
                    
                    logger.error(f"Complete failure loading S3 datasets for problem {problem_id}: {consolidated_error}")
                    return {"success": False, "error": consolidated_error, "dataset_errors": dataset_errors}
                
                elif len(dataset_errors) == 0:
                    # All tables loaded successfully
                    return {
                        "success": True,
                        "message": f"Successfully loaded all {len(tables_created)} tables from S3 datasets",
                        "tables": tables_created,
                        "total_tables": len(tables_created),
                        "total_rows": total_rows,
                        "data_source": "s3_datasets"
                    }
                
                else:
                    # Partial success - some tables loaded, some failed
                    warnings_msg = f"Loaded {len(tables_created)} of {len(s3_datasets)} tables. Failed: " + "; ".join([f"{err['table']}: {err['error']}" for err in dataset_errors])
                    logger.warning(f"Partial success loading S3 datasets for problem {problem_id}: {warnings_msg}")
                    
                    return {
                        "success": True,
                        "message": f"Partially loaded {len(tables_created)} of {len(s3_datasets)} tables from S3 datasets",
                        "tables": tables_created,
                        "total_tables": len(tables_created),
                        "total_rows": total_rows,
                        "data_source": "s3_datasets",
                        "warnings": warnings_msg,
                        "dataset_errors": dataset_errors
                    }
            
            # Fallback to S3 data source (legacy single-table support)
            elif s3_data_source:
                # Use S3 data source
                bucket = s3_data_source.get('bucket', '')
                key = s3_data_source.get('key', '')
                table_name = s3_data_source.get('table_name', 'problem_data')
                description = s3_data_source.get('description', '')
                etag = s3_data_source.get('etag', '')
                
                logger.info(f"Loading problem data from S3: s3://{bucket}/{key}")
                
                # Security validation
                if not self._validate_table_name(table_name):
                    return {"success": False, "error": f"Invalid table name: {table_name}"}
                
                # Use S3 service to download to temporary file
                try:
                    temp_file_path = s3_service.download_to_temp_file(bucket, key)
                    
                    try:
                        # Load parquet from local temp file (no remote access needed)
                        escaped_table_name = self._escape_identifier(table_name)
                        
                        # Test if parquet file is readable
                        result = self.conn.execute("SELECT COUNT(*) as row_count FROM read_parquet(?)", [temp_file_path]).fetchone()
                        
                        if result is None:
                            return {"success": False, "error": f"Parquet file not readable: s3://{bucket}/{key}"}
                        
                        # Drop table if it exists and create new one
                        self.conn.execute(f"DROP TABLE IF EXISTS {escaped_table_name}")
                        self.conn.execute(f"CREATE TABLE {escaped_table_name} AS SELECT * FROM read_parquet(?)", [temp_file_path])
                        
                        # Get table schema for user reference
                        schema_result = self.conn.execute(f"DESCRIBE {escaped_table_name}").fetchall()
                        schema = [{"column": row[0], "type": row[1]} for row in schema_result]
                        
                        row_count = result[0] if result else 0
                        
                        # Track loaded table for security validation
                        self.loaded_table_names.add(table_name)
                        
                        return {
                            "success": True,
                            "message": f"Problem data loaded successfully from S3 into {table_name}",
                            "schema": schema,
                            "row_count": row_count,
                            "data_source": f"s3://{bucket}/{key}",
                            "table_name": table_name,
                            "etag": etag
                        }
                        
                    finally:
                        # Clean up temporary file
                        try:
                            os.unlink(temp_file_path)
                        except:
                            pass
                            
                except Exception as e:
                    logger.error(f"Failed to load from S3: {e}")
                    return {"success": False, "error": f"Failed to load S3 dataset: {str(e)}"}
            
            else:
                # No data source provided
                return {"success": False, "error": "Either question_tables or s3_data_source is required"}
            
        except Exception as e:
            error_msg = f"Failed to load problem data for {problem_id}: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    def analyze_execution_plan(self, query: str) -> Dict[str, Any]:
        """
        Layer 2: Execution Plan Analysis - Verify queries actually scan tables and perform operations
        
        Args:
            query: SQL query string to analyze
            
        Returns:
            Dict containing plan analysis results and anti-hardcode validation
        """
        result = {
            'plan_valid': True,
            'errors': [],
            'warnings': [],
            'analysis': {
                'tables_scanned': [],
                'rows_scanned': 0,
                'has_table_scan': False,
                'has_aggregation': False,
                'has_join': False,
                'is_constant_only': False
            }
        }
        
        try:
            # Get execution plan using DuckDB's EXPLAIN
            plan_query = f"EXPLAIN {query}"
            plan_result = self.conn.execute(plan_query).fetchall()
            
            if not plan_result:
                result['plan_valid'] = False
                result['errors'].append("Unable to generate execution plan")
                return result
            
            # Convert plan to string for analysis
            plan_text = '\n'.join([str(row[0]) if isinstance(row, tuple) else str(row) for row in plan_result])
            plan_text_upper = plan_text.upper()
            
            # Analyze plan for table scanning
            if 'SEQ_SCAN' in plan_text_upper or 'TABLE_SCAN' in plan_text_upper:
                result['analysis']['has_table_scan'] = True
                
                # Extract table names from scan operations
                import re
                table_scan_matches = re.findall(r'(?:SEQ_SCAN|TABLE_SCAN)\s+(\w+)', plan_text_upper)
                result['analysis']['tables_scanned'] = table_scan_matches
            
            # Check for aggregation operations
            if any(op in plan_text_upper for op in ['AGGREGATE', 'HASH_GROUP_BY', 'GROUP_BY']):
                result['analysis']['has_aggregation'] = True
            
            # Check for join operations
            if any(op in plan_text_upper for op in ['HASH_JOIN', 'NESTED_LOOP_JOIN', 'MERGE_JOIN', 'JOIN']):
                result['analysis']['has_join'] = True
            
            # Check for constant-only operations (red flag for hardcoded queries)
            if 'CONSTANT_DATA' in plan_text_upper or 'VALUES' in plan_text_upper:
                if not result['analysis']['has_table_scan']:
                    result['analysis']['is_constant_only'] = True
                    result['plan_valid'] = False
                    result['errors'].append("Query execution plan shows no table access - likely hardcoded constants")
            
            # Verify actual data interaction
            if result['analysis']['has_table_scan']:
                # Get row count statistics using EXPLAIN ANALYZE (with timeout protection)
                try:
                    analyze_query = f"EXPLAIN ANALYZE {query}"
                    analyze_result = self.conn.execute(analyze_query).fetchall()
                    analyze_text = '\n'.join([str(row[0]) if isinstance(row, tuple) else str(row) for row in analyze_result])
                    
                    # Extract row counts from EXPLAIN ANALYZE output
                    rows_pattern = re.findall(r'(\d+)\s+rows', analyze_text, re.IGNORECASE)
                    if rows_pattern:
                        result['analysis']['rows_scanned'] = sum(int(count) for count in rows_pattern)
                        
                        # If no rows were actually scanned despite table references, flag as suspicious
                        if result['analysis']['rows_scanned'] == 0 and result['analysis']['has_table_scan']:
                            result['warnings'].append("Query plan shows table scan but no rows processed - verify query logic")
                    
                except Exception as analyze_error:
                    # EXPLAIN ANALYZE might fail for some queries, but that's not necessarily an error
                    logger.warning(f"EXPLAIN ANALYZE failed: {analyze_error}")
                    result['warnings'].append("Unable to analyze actual row processing")
            
            # Final validation: queries should interact with data
            if not result['analysis']['has_table_scan'] and not result['analysis']['is_constant_only']:
                result['plan_valid'] = False
                result['errors'].append("Query execution plan shows no data interaction")
                
        except Exception as e:
            logger.error(f"Execution plan analysis failed: {e}")
            result['plan_valid'] = False
            result['errors'].append(f"Plan analysis error: {str(e)}")
        
        return result

    def create_data_variants(self, seed: int = 12345) -> Dict[str, Any]:
        """
        Layer 3: Data Dependency Testing - Create slightly modified dataset variants
        to catch hardcoded queries that don't actually analyze the data
        
        Args:
            seed: Random seed for reproducible variants
            
        Returns:
            Dict containing variant creation results
        """
        result = {
            'success': True,
            'errors': [],
            'variant_tables': [],
            'changes_applied': []
        }
        
        try:
            import random
            random.seed(seed)
            
            for table_name in self.loaded_table_names:
                try:
                    # Create variant table name
                    variant_table = f"variant_{table_name}"
                    
                    # Get table schema and sample data
                    schema_query = f"DESCRIBE {table_name}"
                    schema_result = self.conn.execute(schema_query).fetchall()
                    
                    # Get column info
                    columns = []
                    numeric_columns = []
                    text_columns = []
                    
                    for row in schema_result:
                        col_name = row[0]
                        col_type = row[1].upper()
                        columns.append((col_name, col_type))
                        
                        if any(t in col_type for t in ['INT', 'NUMERIC', 'FLOAT', 'DOUBLE', 'DECIMAL']):
                            numeric_columns.append(col_name)
                        elif any(t in col_type for t in ['VARCHAR', 'TEXT', 'CHAR', 'STRING']):
                            text_columns.append(col_name)
                    
                    # Create variant table with modified data
                    # Strategy: Modify 1-2% of rows with small, deterministic changes
                    
                    # Get total row count
                    count_result = self.conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()
                    total_rows = count_result[0] if count_result else 0
                    
                    if total_rows == 0:
                        result['errors'].append(f"Table {table_name} is empty, cannot create variant")
                        continue
                    
                    # Calculate number of rows to modify (1-2% minimum 1 row)
                    rows_to_modify = max(1, int(total_rows * 0.015))  # 1.5%
                    
                    # Create variant table as copy of original
                    create_variant_sql = f"CREATE TEMP TABLE {variant_table} AS SELECT * FROM {table_name}"
                    self.conn.execute(create_variant_sql)
                    
                    changes_made = []
                    
                    # Apply numeric modifications if possible
                    if numeric_columns:
                        for col in numeric_columns[:2]:  # Limit to 2 columns to avoid over-modification
                            # Use deterministic selection based on hash
                            update_sql = f"""
                                UPDATE {variant_table} 
                                SET {col} = {col} + 1 
                                WHERE ABS(HASH(CAST(rowid AS VARCHAR)) % {total_rows}) < {rows_to_modify}
                                  AND {col} IS NOT NULL
                            """
                            try:
                                modified_count = self.conn.execute(update_sql).rowcount or 0
                                if modified_count > 0:
                                    changes_made.append(f"Modified {modified_count} rows in column {col} (+1)")
                            except Exception as e:
                                logger.warning(f"Failed to modify numeric column {col}: {e}")
                    
                    # Apply text modifications if possible (more subtle)
                    if text_columns and not changes_made:  # Only if no numeric changes were made
                        for col in text_columns[:1]:  # Limit to 1 text column
                            # Append a small marker to string values
                            update_sql = f"""
                                UPDATE {variant_table} 
                                SET {col} = {col} || '_v' 
                                WHERE ABS(HASH(CAST(rowid AS VARCHAR)) % {total_rows}) < {rows_to_modify}
                                  AND {col} IS NOT NULL
                                  AND LENGTH({col}) < 100
                            """
                            try:
                                modified_count = self.conn.execute(update_sql).rowcount or 0
                                if modified_count > 0:
                                    changes_made.append(f"Modified {modified_count} rows in column {col} (append '_v')")
                            except Exception as e:
                                logger.warning(f"Failed to modify text column {col}: {e}")
                    
                    if changes_made:
                        result['variant_tables'].append(variant_table)
                        result['changes_applied'].extend(changes_made)
                    else:
                        # Drop the variant table if no changes were made
                        self.conn.execute(f"DROP TABLE IF EXISTS {variant_table}")
                        result['errors'].append(f"Could not create meaningful variant for table {table_name}")
                        
                except Exception as table_error:
                    logger.error(f"Failed to create variant for table {table_name}: {table_error}")
                    result['errors'].append(f"Variant creation failed for {table_name}: {str(table_error)}")
            
            if not result['variant_tables']:
                result['success'] = False
                result['errors'].append("No data variants could be created")
                
        except Exception as e:
            logger.error(f"Data variant creation failed: {e}")
            result['success'] = False
            result['errors'].append(f"Variant creation error: {str(e)}")
        
        return result

    def test_data_dependency(self, query: str, expected_result: List[Dict], tolerance: float = 0.001) -> Dict[str, Any]:
        """
        Test if query results change when using data variants (detects hardcoded answers)
        
        Args:
            query: SQL query to test
            expected_result: Expected result from original data
            tolerance: Numeric tolerance for comparison
            
        Returns:
            Dict containing dependency test results
        """
        result = {
            'is_data_dependent': True,
            'confidence': 1.0,
            'errors': [],
            'warnings': [],
            'test_details': {
                'original_result_count': len(expected_result),
                'variant_result_count': 0,
                'results_differ': False,
                'difference_details': []
            }
        }
        
        try:
            # Create data variants
            variant_creation = self.create_data_variants()
            if not variant_creation['success']:
                result['warnings'].append("Could not create data variants for testing")
                return result
            
            variant_tables = variant_creation['variant_tables']
            if not variant_tables:
                result['warnings'].append("No data variants available for testing")
                return result
            
            # Replace table names in query with variant table names
            variant_query = query
            for table_name in self.loaded_table_names:
                variant_table = f"variant_{table_name}"
                if variant_table in variant_tables:
                    # Simple replacement - this works for most basic queries
                    variant_query = variant_query.replace(table_name, variant_table)
            
            # Execute query on variant data
            try:
                variant_result_raw = self.conn.execute(variant_query).fetchall()
                
                # Convert to list of dicts for comparison
                if variant_result_raw:
                    # Get column names
                    columns = [desc[0] for desc in self.conn.description]
                    variant_result = [dict(zip(columns, row)) for row in variant_result_raw]
                else:
                    variant_result = []
                
                result['test_details']['variant_result_count'] = len(variant_result)
                
                # Compare results
                if len(expected_result) != len(variant_result):
                    result['test_details']['results_differ'] = True
                    result['test_details']['difference_details'].append(
                        f"Row count differs: original={len(expected_result)}, variant={len(variant_result)}"
                    )
                else:
                    # Compare values with tolerance for numeric fields
                    for i, (orig_row, var_row) in enumerate(zip(expected_result, variant_result)):
                        for key in orig_row.keys():
                            if key in var_row:
                                orig_val = orig_row[key]
                                var_val = var_row[key]
                                
                                # Numeric comparison with tolerance
                                if isinstance(orig_val, (int, float)) and isinstance(var_val, (int, float)):
                                    if abs(orig_val - var_val) > tolerance:
                                        result['test_details']['results_differ'] = True
                                        result['test_details']['difference_details'].append(
                                            f"Row {i}, column {key}: {orig_val} vs {var_val}"
                                        )
                                        break
                                # String comparison
                                elif str(orig_val) != str(var_val):
                                    result['test_details']['results_differ'] = True
                                    result['test_details']['difference_details'].append(
                                        f"Row {i}, column {key}: '{orig_val}' vs '{var_val}'"
                                    )
                                    break
                
                # Evaluate data dependency
                if not result['test_details']['results_differ']:
                    # Results are identical despite data changes - likely hardcoded
                    result['is_data_dependent'] = False
                    result['confidence'] = 0.9
                    result['errors'].append(
                        "Query results unchanged despite data modifications - likely hardcoded answer"
                    )
                else:
                    # Results differ appropriately - query appears legitimate
                    result['confidence'] = 1.0
                    
            except Exception as query_error:
                # Query failed on variant data - might indicate data dependency issues
                result['warnings'].append(f"Query failed on variant data: {str(query_error)}")
                result['confidence'] = 0.7  # Lower confidence due to execution failure
                
        except Exception as e:
            logger.error(f"Data dependency test failed: {e}")
            result['errors'].append(f"Dependency test error: {str(e)}")
            result['confidence'] = 0.0
        
        return result

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
        
        # Create new sandbox with unique ID
        sandbox = DuckDBSandbox(sandbox_id=sandbox_key)
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