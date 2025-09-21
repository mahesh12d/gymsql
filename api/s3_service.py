"""
AWS S3 Service for Answer File Management
========================================
Handles S3 operations for fetching answer files, caching with ETag validation,
and supporting multiple file formats (CSV, JSON, Parquet).
"""

import os
import boto3
import json
import io
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime, timezone
from botocore.exceptions import ClientError, NoCredentialsError
import logging

logger = logging.getLogger(__name__)

# Optional pandas import for CSV/Parquet support
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    logger.warning("pandas not available - CSV and Parquet parsing will be limited")

# Configuration from environment with defaults
MAX_FILE_SIZE_MB = int(os.getenv('S3_MAX_FILE_SIZE_MB', '5'))  # Maximum file size in MB
MAX_ROWS = int(os.getenv('S3_MAX_ROWS', '1000'))  # Maximum number of rows to parse
MAX_CACHE_ENTRIES = int(os.getenv('S3_MAX_CACHE_ENTRIES', '1000'))  # Maximum cache entries

# Dataset-specific configuration
S3_DATASET_MAX_FILE_SIZE_MB = int(os.getenv('S3_DATASET_MAX_FILE_SIZE_MB', '100'))  # Max dataset file size
S3_DATASET_MAX_ROWS = int(os.getenv('S3_DATASET_MAX_ROWS', '1000000'))  # Max dataset rows
S3_ALLOWED_BUCKETS = [bucket.strip().lower() for bucket in os.getenv('S3_ALLOWED_BUCKETS', 'sql-learning-datasets,sql-learning-answers,sqlplatform-datasets,sqlplatform-answers').split(',')]

class CacheResult:
    """Structured result for cached file operations"""
    def __init__(self, status: str, data: List[Dict[str, Any]] = None, 
                 etag: str = None, last_modified: datetime = None):
        self.status = status  # 'cache_hit', 'fetched', 'error'
        self.data = data or []
        self.etag = etag
        self.last_modified = last_modified

class S3AnswerService:
    """Service for managing answer files stored in AWS S3"""
    
    def __init__(self):
        """Initialize S3 service with lazy client creation"""
        self._s3_client = None
        self._cache = {}  # Simple in-memory cache: {(bucket,key): {etag, last_modified, data}}
        logger.info("S3AnswerService initialized (client will be created on first use)")
    
    @property
    def s3_client(self):
        """Lazy initialization of S3 client"""
        if self._s3_client is None:
            try:
                # Initialize S3 client - uses AWS credentials from environment
                self._s3_client = boto3.client('s3')
                logger.info("S3 client created successfully")
            except NoCredentialsError:
                logger.error("AWS credentials not found. Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY")
                raise
            except Exception as e:
                logger.error(f"Failed to create S3 client: {e}")
                raise
        return self._s3_client
    
    def fetch_answer_file(
        self,
        bucket: str,
        key: str,
        file_format: str = None,
        etag: Optional[str] = None,
        format: str = None  # Backward compatibility alias
    ) -> CacheResult:
        """
        Fetch and parse answer file from S3 with ETag-based caching
        
        Args:
            bucket: S3 bucket name
            key: S3 object key (file path)
            file_format: File format (csv, json, parquet)
            etag: Current ETag for cache validation
            
        Returns:
            CacheResult with status, data, etag, and last_modified
            
        Raises:
            ClientError: If S3 operation fails
            ValueError: If file format is unsupported or parsing fails
        """
        # Handle backward compatibility for format parameter
        if file_format is None and format is not None:
            file_format = format
        elif file_format is None and format is None:
            # Auto-detect format from file extension
            if key.endswith('.csv'):
                file_format = 'csv'
            elif key.endswith('.json'):
                file_format = 'json'
            elif key.endswith('.parquet'):
                file_format = 'parquet'
            else:
                raise ValueError(f"Cannot determine file format for key '{key}'. Please specify file_format parameter.")
        
        # Validate bucket is in allowlist for security
        if bucket.lower() not in S3_ALLOWED_BUCKETS:
            raise ValueError(f"Bucket '{bucket}' not allowed. Allowed buckets: {', '.join(S3_ALLOWED_BUCKETS)}")
        
        cache_key = (bucket, key)
        
        try:
            # Normalize ETag (remove quotes for internal comparison)
            input_etag_stripped = etag.strip('"') if etag else None
            
            # Check in-memory cache first
            if cache_key in self._cache and input_etag_stripped:
                cached = self._cache[cache_key]
                if cached['etag'] == input_etag_stripped:
                    logger.info(f"File {bucket}/{key} served from memory cache")
                    return CacheResult('cache_hit', cached['data'], input_etag_stripped, cached['last_modified'])
            
            # Use conditional GET with If-None-Match header (S3 expects quoted ETag)
            get_params = {'Bucket': bucket, 'Key': key}
            if input_etag_stripped:
                get_params['IfNoneMatch'] = f'"{input_etag_stripped}"'
            
            try:
                obj_response = self.s3_client.get_object(**get_params)
            except ClientError as e:
                # Check for 304 Not Modified via HTTP status code
                http_status = e.response.get('ResponseMetadata', {}).get('HTTPStatusCode')
                error_code = e.response.get('Error', {}).get('Code', '')
                
                if http_status == 304 or error_code in ['NotModified', 'PreconditionFailed']:
                    # Not modified - return cached data if available
                    if cache_key in self._cache:
                        cached = self._cache[cache_key]
                        logger.info(f"File {bucket}/{key} not modified (304)")
                        return CacheResult('cache_hit', cached['data'], input_etag_stripped, cached['last_modified'])
                    else:
                        # No cached data but got 304 - fetch without condition
                        obj_response = self.s3_client.get_object(Bucket=bucket, Key=key)
                else:
                    raise
            
            # Check file size limit
            content_length = obj_response.get('ContentLength', 0)
            if content_length > MAX_FILE_SIZE_MB * 1024 * 1024:
                raise ValueError(f"File too large: {content_length / (1024*1024):.1f}MB (max: {MAX_FILE_SIZE_MB}MB)")
            
            # Get metadata
            new_etag = obj_response['ETag'].strip('"')
            last_modified = obj_response['LastModified']
            
            # Read and parse content
            logger.info(f"Fetching file {bucket}/{key} (format: {file_format}, size: {content_length} bytes)")
            file_content = obj_response['Body'].read()
            
            # Parse content based on format
            parsed_data = self._parse_file_content(file_content, file_format)
            
            # Enforce row limit
            if len(parsed_data) > MAX_ROWS:
                logger.warning(f"File {bucket}/{key} has {len(parsed_data)} rows, truncating to {MAX_ROWS}")
                parsed_data = parsed_data[:MAX_ROWS]
            
            # Update cache with eviction if needed
            self._cache[cache_key] = {
                'etag': new_etag,
                'last_modified': last_modified,
                'data': parsed_data
            }
            
            # Simple cache eviction: remove oldest entries if over limit
            if len(self._cache) > MAX_CACHE_ENTRIES:
                # Remove 20% of oldest entries (simple LRU approximation)
                entries_to_remove = len(self._cache) - int(MAX_CACHE_ENTRIES * 0.8)
                oldest_keys = list(self._cache.keys())[:entries_to_remove]
                for old_key in oldest_keys:
                    del self._cache[old_key]
                logger.info(f"Cache eviction: removed {entries_to_remove} entries")
            
            logger.info(f"Successfully parsed {len(parsed_data)} rows from {bucket}/{key}")
            return CacheResult('fetched', parsed_data, new_etag, last_modified)
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            if error_code == 'NoSuchBucket':
                raise ValueError(f"S3 bucket '{bucket}' does not exist")
            elif error_code == 'NoSuchKey':
                raise ValueError(f"File '{key}' not found in bucket '{bucket}'")
            else:
                logger.error(f"S3 error fetching {bucket}/{key}: {e}")
                raise
        except Exception as e:
            logger.error(f"Error fetching answer file {bucket}/{key}: {e}")
            raise
    
    def _parse_file_content(self, content: bytes, file_format: str) -> List[Dict[str, Any]]:
        """
        Parse file content based on format
        
        Args:
            content: Raw file content bytes
            file_format: File format (csv, json, parquet)
            
        Returns:
            List of dictionaries representing rows
            
        Raises:
            ValueError: If format is unsupported or parsing fails
        """
        try:
            if file_format.lower() == 'csv':
                return self._parse_csv(content)
            elif file_format.lower() == 'json':
                return self._parse_json(content)
            elif file_format.lower() == 'parquet':
                return self._parse_parquet(content)
            else:
                raise ValueError(f"Unsupported file format: {file_format}")
                
        except Exception as e:
            logger.error(f"Failed to parse {file_format} content: {e}")
            raise ValueError(f"Failed to parse {file_format} file: {e}")
    
    def _decode_content(self, content: bytes) -> str:
        """
        Decode bytes content to string with fallback encoding support.
        
        Tries multiple encodings to handle files that might not be UTF-8:
        - utf-8 (preferred)
        - utf-8-sig (UTF-8 with BOM)
        - latin-1 (ISO-8859-1)
        - cp1252 (Windows-1252)
        - ascii
        
        Args:
            content: Raw file content bytes
            
        Returns:
            Decoded string content
            
        Raises:
            ValueError: If content cannot be decoded with any supported encoding
        """
        encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252', 'ascii']
        
        for encoding in encodings:
            try:
                decoded_content = content.decode(encoding)
                logger.debug(f"Successfully decoded content using {encoding} encoding")
                return decoded_content
            except UnicodeDecodeError:
                logger.debug(f"Failed to decode content using {encoding} encoding")
                continue
                
        # If all encodings fail, try with error handling
        try:
            decoded_content = content.decode('utf-8', errors='replace')
            logger.warning("Decoded content using UTF-8 with error replacement - some characters may be corrupted")
            return decoded_content
        except Exception as e:
            raise ValueError(f"Unable to decode file content with any supported encoding: {e}")
    
    def _sanitize_sample_data(self, sample_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Sanitize sample data to ensure JSON serializability.
        
        Converts problematic data types like binary data, datetime objects,
        decimal values, and other non-JSON-serializable types to strings.
        
        Args:
            sample_data: Raw sample data from DuckDB query
            
        Returns:
            Sanitized sample data safe for JSON serialization
        """
        import decimal
        import datetime
        import uuid
        
        def sanitize_value(value):
            """Sanitize a single value for JSON serialization"""
            if value is None:
                return None
            elif isinstance(value, (str, int, float, bool)):
                return value
            elif isinstance(value, bytes):
                # Convert binary data to hex string representation
                try:
                    # Try to decode as UTF-8 first
                    return value.decode('utf-8')
                except UnicodeDecodeError:
                    # If that fails, convert to hex
                    return f"<binary: {value.hex()}>"
            elif isinstance(value, decimal.Decimal):
                return float(value)
            elif isinstance(value, (datetime.date, datetime.datetime, datetime.time)):
                return value.isoformat()
            elif isinstance(value, uuid.UUID):
                return str(value)
            elif hasattr(value, '__dict__'):
                # For complex objects, try to convert to string
                return str(value)
            else:
                # For any other type, convert to string
                return str(value)
        
        sanitized_data = []
        for row in sample_data:
            sanitized_row = {}
            for key, value in row.items():
                try:
                    sanitized_row[key] = sanitize_value(value)
                except Exception as e:
                    # If sanitization fails, use a safe fallback
                    logger.warning(f"Failed to sanitize value for column {key}: {e}")
                    sanitized_row[key] = f"<unsupported: {type(value).__name__}>"
            sanitized_data.append(sanitized_row)
        
        return sanitized_data
    
    def _parse_csv(self, content: bytes) -> List[Dict[str, Any]]:
        """Parse CSV content to list of dictionaries"""
        if not PANDAS_AVAILABLE:
            # Fallback to basic CSV parsing without pandas
            return self._parse_csv_basic(content)
        
        try:
            # Use pandas to parse CSV with automatic type inference
            df = pd.read_csv(io.BytesIO(content))
            
            # Convert to list of dictionaries
            # Handle NaN values by converting to None
            data = df.where(pd.notnull(df), None).to_dict('records')
            
            return data
            
        except Exception as e:
            raise ValueError(f"Invalid CSV format: {e}")
    
    def _parse_csv_basic(self, content: bytes) -> List[Dict[str, Any]]:
        """Basic CSV parsing without pandas"""
        import csv
        
        try:
            text_content = self._decode_content(content)
            reader = csv.DictReader(io.StringIO(text_content))
            data = []
            
            for row in reader:
                # Convert numeric strings to numbers where possible
                parsed_row = {}
                for key, value in row.items():
                    if value is None or value == '':
                        parsed_row[key] = None
                    else:
                        # Try to convert to number
                        try:
                            if '.' in value:
                                parsed_row[key] = float(value)
                            else:
                                parsed_row[key] = int(value)
                        except (ValueError, TypeError):
                            parsed_row[key] = value
                data.append(parsed_row)
            
            return data
            
        except Exception as e:
            raise ValueError(f"Invalid CSV format: {e}")
    
    def _parse_json(self, content: bytes) -> List[Dict[str, Any]]:
        """Parse JSON content to list of dictionaries"""
        try:
            text_content = self._decode_content(content)
            data = json.loads(text_content)
            
            # Ensure data is a list of dictionaries
            if isinstance(data, list):
                if not data or all(isinstance(item, dict) for item in data):
                    return data
                else:
                    raise ValueError("JSON must contain only dictionary objects")
            elif isinstance(data, dict):
                # Single object, wrap in list
                return [data]
            else:
                raise ValueError("JSON must be a list of objects or a single object")
                
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format: {e}")
        except UnicodeDecodeError as e:
            raise ValueError(f"Invalid text encoding: {e}")
    
    def _parse_parquet(self, content: bytes) -> List[Dict[str, Any]]:
        """Parse Parquet content to list of dictionaries with fallback to DuckDB"""
        # Try pandas first if available
        if PANDAS_AVAILABLE:
            try:
                # Use pandas to read Parquet from bytes
                df = pd.read_parquet(io.BytesIO(content))
                
                # Convert to list of dictionaries
                # Handle NaN values by converting to None
                data = df.where(pd.notnull(df), None).to_dict('records')
                
                logger.info("Successfully parsed parquet using pandas")
                return data
                
            except ImportError as e:
                logger.warning(f"Pandas/pyarrow import failed, falling back to DuckDB: {e}")
            except Exception as e:
                logger.warning(f"Pandas parsing failed, falling back to DuckDB: {e}")
        
        # Fallback to DuckDB for reliable parquet parsing
        try:
            import duckdb
            import tempfile
            import os
            
            # Write content to temporary file for DuckDB
            with tempfile.NamedTemporaryFile(delete=False, suffix='.parquet') as temp_file:
                temp_file.write(content)
                temp_file_path = temp_file.name
            
            try:
                # Connect to DuckDB and read parquet
                conn = duckdb.connect(":memory:")
                
                # Read parquet file and convert to list of dictionaries
                query_result = conn.execute(f"SELECT * FROM read_parquet('{temp_file_path}')").fetchall()
                column_names = [desc[0] for desc in conn.description]
                
                # Convert to list of dictionaries
                data = []
                for row in query_result:
                    row_dict = {}
                    for i, col_name in enumerate(column_names):
                        # Handle None values properly
                        value = row[i] if i < len(row) else None
                        row_dict[col_name] = value
                    data.append(row_dict)
                
                logger.info(f"Successfully parsed parquet using DuckDB fallback ({len(data)} rows)")
                return data
                
            finally:
                # Clean up temporary file
                try:
                    os.unlink(temp_file_path)
                except:
                    pass
                    
        except ImportError as e:
            raise ValueError(f"Parquet parsing requires either pandas+pyarrow or duckdb: {e}")
        except Exception as e:
            raise ValueError(f"Invalid Parquet format: {e}")
    
    def generate_preview_data(
        self,
        full_data: List[Dict[str, Any]],
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Generate preview data by taking first N rows
        
        Args:
            full_data: Complete dataset
            limit: Number of rows to include in preview
            
        Returns:
            Limited dataset for frontend display
        """
        if not full_data:
            return []
        
        preview = full_data[:limit]
        logger.info(f"Generated preview with {len(preview)} rows from {len(full_data)} total")
        
        return preview
    
    def validate_s3_uri(self, bucket: str, key: str) -> bool:
        """
        Validate that S3 object exists and is accessible
        
        Args:
            bucket: S3 bucket name
            key: S3 object key
            
        Returns:
            True if object exists and is accessible
        """
        try:
            self.s3_client.head_object(Bucket=bucket, Key=key)
            return True
        except ClientError:
            return False
    
    def get_presigned_upload_url(
        self,
        bucket: str,
        key: str,
        content_type: str = 'application/octet-stream',
        expires_in: int = 300,  # 5 minutes for security
        max_file_size: int = MAX_FILE_SIZE_MB * 1024 * 1024
    ) -> Dict[str, Any]:
        """
        Generate secure presigned POST for uploading files to S3 with strict policies
        
        Args:
            bucket: S3 bucket name
            key: S3 object key
            content_type: MIME type of the file
            expires_in: URL expiration time in seconds (default 5 minutes)
            max_file_size: Maximum file size in bytes
            
        Returns:
            Dictionary with 'url' and 'fields' for secure POST upload
        """
        try:
            # Create secure POST policy with strict conditions
            conditions = [
                {'bucket': bucket},
                {'key': key},
                {'Content-Type': content_type},
                {'x-amz-server-side-encryption': 'AES256'},  # Require encryption
                ['content-length-range', 1, max_file_size]  # File size limits
            ]
            
            fields = {
                'Content-Type': content_type,
                'x-amz-server-side-encryption': 'AES256'
            }
            
            # Generate presigned POST with policy
            response = self.s3_client.generate_presigned_post(
                Bucket=bucket,
                Key=key,
                Fields=fields,
                Conditions=conditions,
                ExpiresIn=expires_in
            )
            
            logger.info(f"Generated secure presigned POST for {bucket}/{key} (expires in {expires_in}s)")
            return response
            
        except Exception as e:
            logger.error(f"Failed to generate presigned POST: {e}")
            raise

    def download_to_temp_file(self, bucket: str, key: str) -> str:
        """
        Download S3 file to a temporary file and return the path
        
        Args:
            bucket: S3 bucket name
            key: S3 object key
            
        Returns:
            Path to temporary file
            
        Raises:
            ValueError: If bucket not allowed or file too large
            ClientError: If S3 operation fails
        """
        import tempfile
        
        # Validate bucket allowlist
        if not self._validate_dataset_bucket(bucket):
            raise ValueError(f"Bucket '{bucket}' not in allowed list: {S3_ALLOWED_BUCKETS}")
        
        try:
            # Check file size before downloading
            response = self.s3_client.head_object(Bucket=bucket, Key=key)
            file_size_mb = response['ContentLength'] / (1024 * 1024)
            
            if file_size_mb > S3_DATASET_MAX_FILE_SIZE_MB:
                raise ValueError(f"File size {file_size_mb:.1f}MB exceeds limit of {S3_DATASET_MAX_FILE_SIZE_MB}MB")
            
            # Create temporary file
            suffix = os.path.splitext(key)[1] or '.tmp'
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            
            # Download to temporary file
            self.s3_client.download_fileobj(bucket, key, temp_file)
            temp_file.close()
            
            logger.info(f"Downloaded {bucket}/{key} ({file_size_mb:.1f}MB) to {temp_file.name}")
            return temp_file.name
            
        except ClientError as e:
            logger.error(f"Failed to download {bucket}/{key}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error downloading dataset file {bucket}/{key}: {e}")
            raise
    
    def download_text_file(self, bucket: str, key: str) -> str:
        """
        Download S3 text file and return its content as string
        
        Args:
            bucket: S3 bucket name
            key: S3 object key
            
        Returns:
            File content as string
            
        Raises:
            ValueError: If bucket not allowed or file too large
            ClientError: If S3 operation fails
        """
        # Validate bucket allowlist
        if not self._validate_dataset_bucket(bucket):
            raise ValueError(f"Bucket '{bucket}' not in allowed list: {S3_ALLOWED_BUCKETS}")
        
        try:
            # Check file size before downloading
            response = self.s3_client.head_object(Bucket=bucket, Key=key)
            file_size_mb = response['ContentLength'] / (1024 * 1024)
            
            # Allow smaller limit for text files like SQL
            max_text_file_size_mb = 1.0  # 1MB should be enough for SQL files
            if file_size_mb > max_text_file_size_mb:
                raise ValueError(f"Text file size {file_size_mb:.1f}MB exceeds limit of {max_text_file_size_mb}MB")
            
            # Download file content directly
            obj_response = self.s3_client.get_object(Bucket=bucket, Key=key)
            content_bytes = obj_response['Body'].read()
            
            # Use robust encoding detection
            content = self._decode_content(content_bytes)
            
            logger.info(f"Downloaded text file {bucket}/{key} ({file_size_mb:.1f}MB)")
            return content
            
        except ClientError as e:
            logger.error(f"Failed to download text file {bucket}/{key}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error downloading text file {bucket}/{key}: {e}")
            raise
    
    def fetch_solution_sql(self, bucket: str, key: str) -> Dict[str, Any]:
        """
        Fetch solution file from S3 and return as structured response
        Supports both SQL files (.sql) and parquet files (.parquet) as solutions
        
        Args:
            bucket: S3 bucket name
            key: S3 object key (SQL or parquet file path)
            
        Returns:
            Dict with success status, sql_content or solution_data, and error information
        """
        try:
            # Determine file type from extension
            file_extension = os.path.splitext(key)[1].lower()
            
            if file_extension == '.sql':
                # Handle SQL file - use text file download
                sql_content = self.download_text_file(bucket, key)
                
                logger.info(f"Successfully fetched solution SQL from {bucket}/{key} ({len(sql_content)} characters)")
                
                return {
                    "success": True,
                    "sql_content": sql_content,
                    "file_type": "sql",
                    "bucket": bucket,
                    "key": key
                }
                
            elif file_extension == '.parquet':
                # Handle parquet file - use existing parquet parsing logic
                cache_result = self.fetch_answer_file(bucket=bucket, key=key, file_format='parquet')
                
                logger.info(f"Successfully fetched solution parquet from {bucket}/{key} ({len(cache_result.data)} rows)")
                
                return {
                    "success": True,
                    "solution_data": cache_result.data,
                    "file_type": "parquet",
                    "bucket": bucket,
                    "key": key,
                    "etag": cache_result.etag
                }
                
            else:
                # Unsupported file type
                error_msg = f"Unsupported solution file type: {file_extension}. Supported types: .sql, .parquet"
                logger.error(f"Unsupported file type for {bucket}/{key}: {error_msg}")
                return {
                    "success": False,
                    "error": error_msg,
                    "bucket": bucket,
                    "key": key
                }
            
        except ValueError as e:
            # Handle validation errors (bucket not allowed, file too large, etc.)
            logger.error(f"Validation error fetching solution from {bucket}/{key}: {e}")
            return {
                "success": False,
                "error": str(e),
                "bucket": bucket,
                "key": key
            }
            
        except ClientError as e:
            # Handle S3 errors
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            if error_code == 'NoSuchBucket':
                error_msg = f"S3 bucket '{bucket}' does not exist"
            elif error_code == 'NoSuchKey':
                error_msg = f"Solution file '{key}' not found in bucket '{bucket}'"
            else:
                error_msg = f"S3 error: {e}"
            
            logger.error(f"S3 error fetching solution from {bucket}/{key}: {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "bucket": bucket,
                "key": key
            }
            
        except Exception as e:
            # Handle any other errors
            logger.error(f"Unexpected error fetching solution from {bucket}/{key}: {e}")
            return {
                "success": False,
                "error": f"Failed to fetch solution: {str(e)}",
                "bucket": bucket,
                "key": key
            }
    
    def validate_dataset_file(self, bucket: str, key: str, table_name: str) -> Dict[str, Any]:
        """
        Validate S3 dataset file and extract schema information
        
        Args:
            bucket: S3 bucket name
            key: S3 object key
            table_name: Desired table name for DuckDB
            
        Returns:
            Dict with validation result, schema, sample data, row count, etag
        """
        try:
            # Validate bucket
            if not self._validate_dataset_bucket(bucket):
                return {
                    "success": False,
                    "error": f"Bucket '{bucket}' not in allowed list: {S3_ALLOWED_BUCKETS}"
                }
            
            # Validate table name pattern (same as DuckDB sandbox)
            import re
            table_pattern = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]{0,63}$')
            if not table_pattern.match(table_name):
                return {
                    "success": False,
                    "error": f"Invalid table name: {table_name}. Must start with letter/underscore, contain only alphanumeric/underscore, max 64 chars."
                }
            
            # Download to temporary file for analysis
            temp_file_path = self.download_to_temp_file(bucket, key)
            
            try:
                # Use DuckDB to analyze the file
                import duckdb
                conn = duckdb.connect(":memory:")
                
                # Get file extension to determine type
                file_ext = os.path.splitext(key)[1].lower()
                
                if file_ext == '.parquet':
                    # Analyze parquet file
                    result = conn.execute("SELECT COUNT(*) as row_count FROM read_parquet(?)", [temp_file_path]).fetchone()
                    row_count = result[0] if result else 0
                    
                    # Get schema
                    schema_result = conn.execute("DESCRIBE SELECT * FROM read_parquet(?)", [temp_file_path]).fetchall()
                    schema = [{"column": row[0], "type": row[1]} for row in schema_result]
                    
                    # Get sample data
                    sample_result = conn.execute("SELECT * FROM read_parquet(?) LIMIT 5", [temp_file_path]).fetchall()
                    column_names = [desc[0] for desc in conn.description]
                    raw_sample_data = [dict(zip(column_names, row)) for row in sample_result]
                    
                    # Sanitize sample data to ensure JSON serializability
                    sample_data = self._sanitize_sample_data(raw_sample_data)
                    
                else:
                    return {"success": False, "error": f"Unsupported file format: {file_ext}. Only .parquet files are supported for datasets."}
                
                # Validate row count
                if row_count > S3_DATASET_MAX_ROWS:
                    return {
                        "success": False, 
                        "error": f"Dataset has {row_count:,} rows, exceeds limit of {S3_DATASET_MAX_ROWS:,}"
                    }
                
                # Get ETag for caching
                head_response = self.s3_client.head_object(Bucket=bucket, Key=key)
                etag = head_response.get('ETag', '').strip('"')
                
                return {
                    "success": True,
                    "schema": schema,
                    "sample_data": sample_data,
                    "row_count": row_count,
                    "etag": etag,
                    "table_name": table_name
                }
                
            finally:
                # Clean up temporary file
                try:
                    os.unlink(temp_file_path)
                except:
                    pass
                    
        except Exception as e:
            logger.error(f"Dataset validation failed for {bucket}/{key}: {e}")
            return {"success": False, "error": str(e)}
    
    
    def generate_expected_result_hash(self, result_data: List[Dict[str, Any]]) -> str:
        """
        Generate MD5 hash of sorted expected result for validation
        
        Args:
            result_data: List of dictionaries representing query result
            
        Returns:
            MD5 hash string
        """
        import hashlib
        import json
        
        try:
            # Sort the data to ensure consistent hashing
            # Sort by converting each row to string and sorting lexically
            sorted_data = sorted(result_data, key=lambda x: json.dumps(x, sort_keys=True, default=str))
            
            # Convert to JSON string with consistent formatting
            json_str = json.dumps(sorted_data, sort_keys=True, separators=(',', ':'), default=str)
            
            # Generate MD5 hash
            hash_object = hashlib.md5(json_str.encode('utf-8'))
            return hash_object.hexdigest()
            
        except Exception as e:
            logger.error(f"Failed to generate result hash: {e}")
            raise ValueError(f"Hash generation failed: {str(e)}")
    
    def fetch_parquet_solution(self, bucket: str, key: str, etag: Optional[str] = None) -> CacheResult:
        """
        Fetch parquet solution file (out.parquet) for result validation
        
        Args:
            bucket: S3 bucket name
            key: S3 object key (should be out.parquet)
            etag: Current ETag for cache validation
            
        Returns:
            CacheResult with parsed parquet data as list of dictionaries
            
        Raises:
            ValueError: If bucket not allowed, file too large, or parsing fails
            ClientError: If S3 operation fails
        """
        # Validate bucket is in allowlist for security
        if bucket.lower() not in S3_ALLOWED_BUCKETS:
            raise ValueError(f"Bucket '{bucket}' not allowed. Allowed buckets: {', '.join(S3_ALLOWED_BUCKETS)}")
        
        # Use higher limits for solution files than regular answer files
        cache_key = (bucket, key)
        
        try:
            # Normalize ETag (remove quotes for internal comparison)
            input_etag_stripped = etag.strip('"') if etag else None
            
            # Check in-memory cache first
            if cache_key in self._cache and input_etag_stripped:
                cached = self._cache[cache_key]
                if cached['etag'] == input_etag_stripped:
                    logger.info(f"Solution file {bucket}/{key} served from memory cache")
                    return CacheResult('cache_hit', cached['data'], input_etag_stripped, cached['last_modified'])
            
            # Use conditional GET with If-None-Match header (S3 expects quoted ETag)
            get_params = {'Bucket': bucket, 'Key': key}
            if input_etag_stripped:
                get_params['IfNoneMatch'] = f'"{input_etag_stripped}"'
            
            try:
                obj_response = self.s3_client.get_object(**get_params)
            except ClientError as e:
                # Check for 304 Not Modified via HTTP status code
                http_status = e.response.get('ResponseMetadata', {}).get('HTTPStatusCode')
                error_code = e.response.get('Error', {}).get('Code', '')
                
                if http_status == 304 or error_code in ['NotModified', 'PreconditionFailed']:
                    # Not modified - return cached data if available
                    if cache_key in self._cache:
                        cached = self._cache[cache_key]
                        logger.info(f"Solution file {bucket}/{key} not modified (304)")
                        return CacheResult('cache_hit', cached['data'], input_etag_stripped, cached['last_modified'])
                    else:
                        # No cached data but got 304 - fetch without condition
                        obj_response = self.s3_client.get_object(Bucket=bucket, Key=key)
                else:
                    raise
            
            # Check file size limit (use dataset limit for solution files)
            content_length = obj_response.get('ContentLength', 0)
            max_size_bytes = S3_DATASET_MAX_FILE_SIZE_MB * 1024 * 1024
            if content_length > max_size_bytes:
                raise ValueError(f"Solution file too large: {content_length / (1024*1024):.1f}MB (max: {S3_DATASET_MAX_FILE_SIZE_MB}MB)")
            
            # Get metadata
            new_etag = obj_response['ETag'].strip('"')
            last_modified = obj_response['LastModified']
            
            # Read and parse parquet content
            logger.info(f"Fetching solution file {bucket}/{key} (size: {content_length} bytes)")
            file_content = obj_response['Body'].read()
            
            # Parse parquet content directly
            parsed_data = self._parse_parquet(file_content)
            
            # Enforce dataset row limit for solution files
            if len(parsed_data) > S3_DATASET_MAX_ROWS:
                logger.warning(f"Solution file {bucket}/{key} has {len(parsed_data)} rows, truncating to {S3_DATASET_MAX_ROWS}")
                parsed_data = parsed_data[:S3_DATASET_MAX_ROWS]
            
            # Update cache with eviction if needed
            self._cache[cache_key] = {
                'etag': new_etag,
                'last_modified': last_modified,
                'data': parsed_data
            }
            
            # Simple cache eviction: remove oldest entries if over limit
            if len(self._cache) > MAX_CACHE_ENTRIES:
                # Remove 20% of oldest entries (simple LRU approximation)
                entries_to_remove = len(self._cache) - int(MAX_CACHE_ENTRIES * 0.8)
                oldest_keys = list(self._cache.keys())[:entries_to_remove]
                for old_key in oldest_keys:
                    del self._cache[old_key]
                logger.info(f"Cache eviction: removed {entries_to_remove} entries")
            
            logger.info(f"Successfully parsed {len(parsed_data)} rows from solution file {bucket}/{key}")
            return CacheResult('fetched', parsed_data, new_etag, last_modified)
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            if error_code == 'NoSuchBucket':
                raise ValueError(f"S3 bucket '{bucket}' does not exist")
            elif error_code == 'NoSuchKey':
                raise ValueError(f"Solution file '{key}' not found in bucket '{bucket}'")
            else:
                logger.error(f"S3 error fetching solution file {bucket}/{key}: {e}")
                raise
        except Exception as e:
            logger.error(f"Error fetching solution file {bucket}/{key}: {e}")
            raise

    def _validate_dataset_bucket(self, bucket: str) -> bool:
        """Validate that bucket is in the allowed list for datasets"""
        return bucket in S3_ALLOWED_BUCKETS

# Global S3 service instance
s3_service = S3AnswerService()