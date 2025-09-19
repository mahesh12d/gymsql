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
        file_format: str,
        etag: Optional[str] = None
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
            text_content = content.decode('utf-8')
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
            text_content = content.decode('utf-8')
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
        """Parse Parquet content to list of dictionaries"""
        if not PANDAS_AVAILABLE:
            raise ValueError("Parquet parsing requires pandas and pyarrow. Please install with: pip install pandas pyarrow")
        
        try:
            # Use pandas to read Parquet from bytes
            df = pd.read_parquet(io.BytesIO(content))
            
            # Convert to list of dictionaries
            # Handle NaN values by converting to None
            data = df.where(pd.notnull(df), None).to_dict('records')
            
            return data
            
        except ImportError as e:
            raise ValueError(f"Parquet parsing requires pyarrow: {e}")
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

# Global S3 service instance
s3_service = S3AnswerService()