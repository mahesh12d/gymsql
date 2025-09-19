"""
File Processing Service
======================
Unified interface for processing and validating different data sources including S3 files
and existing tabular data formats. Integrates with the S3 service and database utilities.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from api.s3_service import s3_service, CacheResult
from api.database import parse_tabular_data
from api.schemas import S3AnswerSource

logger = logging.getLogger(__name__)

class FileProcessingService:
    """
    Service for processing files and structured data from various sources.
    Provides unified interface for S3 files, tabular strings, and JSON data.
    """
    
    def __init__(self):
        self.s3_service = s3_service
    
    def process_s3_answer_file(
        self,
        s3_config: S3AnswerSource,
        preview_limit: Optional[int] = None
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Optional[str], Optional[str]]:
        """
        Process S3 answer file and generate both full dataset and preview.
        
        Args:
            s3_config: S3 configuration with bucket, key, format, etag
            preview_limit: Number of rows for preview (defaults to 10, caller should pass test_case.display_limit when available)
            
        Returns:
            Tuple of (full_data, preview_data, new_etag, error_message)
        """
        try:
            # Fetch full answer file from S3
            result: CacheResult = self.s3_service.fetch_answer_file(
                bucket=s3_config.bucket,
                key=s3_config.key,
                file_format=s3_config.format,
                etag=s3_config.etag
            )
            
            if result.status == 'cache_hit':
                logger.info(f"Using cached data for {s3_config.bucket}/{s3_config.key}")
            elif result.status == 'fetched':
                logger.info(f"Fetched fresh data for {s3_config.bucket}/{s3_config.key}")
            
            full_data = result.data
            
            # Generate preview data
            if preview_limit is None:
                preview_limit = 10  # Default preview limit
                
            preview_data = self.s3_service.generate_preview_data(full_data, preview_limit)
            
            # Validate data structure
            self._validate_answer_data(full_data)
            
            logger.info(f"Processed S3 file: {len(full_data)} total rows, {len(preview_data)} preview rows")
            return full_data, preview_data, result.etag, None
            
        except Exception as e:
            error_msg = f"Failed to process S3 answer file: {str(e)}"
            logger.error(error_msg)
            return [], [], None, error_msg
    
    def process_tabular_string(
        self,
        tabular_string: str,
        preview_limit: int = 10
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Optional[str]]:
        """
        Process pipe-delimited tabular string into structured data.
        
        Args:
            tabular_string: Pipe-delimited string data
            preview_limit: Number of rows for preview
            
        Returns:
            Tuple of (full_data, preview_data, error_message)
        """
        try:
            # Use existing database parser for tabular strings
            full_data = parse_tabular_data(tabular_string)
            
            # Generate preview data
            preview_data = full_data[:preview_limit] if full_data else []
            
            # Validate data structure
            self._validate_answer_data(full_data)
            
            logger.info(f"Processed tabular string: {len(full_data)} total rows, {len(preview_data)} preview rows")
            return full_data, preview_data, None
            
        except Exception as e:
            error_msg = f"Failed to process tabular string: {str(e)}"
            logger.error(error_msg)
            return [], [], error_msg
    
    def process_json_data(
        self,
        json_data: List[Dict[str, Any]],
        preview_limit: int = 10
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Optional[str]]:
        """
        Process and validate JSON data that's already structured.
        
        Args:
            json_data: List of dictionaries
            preview_limit: Number of rows for preview
            
        Returns:
            Tuple of (full_data, preview_data, error_message)
        """
        try:
            # Validate data structure
            self._validate_answer_data(json_data)
            
            # Generate preview data
            preview_data = json_data[:preview_limit] if json_data else []
            
            logger.info(f"Processed JSON data: {len(json_data)} total rows, {len(preview_data)} preview rows")
            return json_data, preview_data, None
            
        except Exception as e:
            error_msg = f"Failed to process JSON data: {str(e)}"
            logger.error(error_msg)
            return [], [], error_msg
    
    def validate_s3_configuration(self, s3_config: S3AnswerSource) -> Tuple[bool, Optional[str]]:
        """
        Validate S3 configuration by checking if the file exists and is accessible.
        
        Args:
            s3_config: S3 configuration to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            is_valid = self.s3_service.validate_s3_uri(s3_config.bucket, s3_config.key)
            if not is_valid:
                return False, f"S3 file {s3_config.bucket}/{s3_config.key} is not accessible"
            
            return True, None
            
        except Exception as e:
            error_msg = f"Failed to validate S3 configuration: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def _validate_answer_data(self, data: List[Dict[str, Any]]) -> None:
        """
        Validate that answer data has consistent structure.
        
        Args:
            data: List of dictionaries to validate
            
        Raises:
            ValueError: If data structure is invalid
        """
        if not data:
            return  # Empty data is valid
        
        if not isinstance(data, list):
            raise ValueError("Answer data must be a list")
        
        if not all(isinstance(row, dict) for row in data):
            raise ValueError("All rows must be dictionaries")
        
        # Check that all rows have the same columns
        if data:
            first_row_keys = set(data[0].keys())
            for i, row in enumerate(data[1:], 1):
                row_keys = set(row.keys())
                if row_keys != first_row_keys:
                    logger.warning(f"Row {i} has different columns: {row_keys} vs {first_row_keys}")
                    # Don't raise error, just warn - some flexibility is needed
        
        logger.debug(f"Validated {len(data)} rows of answer data")
    
    def get_data_summary(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate a summary of the data structure and content.
        
        Args:
            data: List of dictionaries to summarize
            
        Returns:
            Dictionary with data summary information
        """
        if not data:
            return {
                'row_count': 0,
                'columns': [],
                'sample_row': None
            }
        
        columns = list(data[0].keys()) if data else []
        
        return {
            'row_count': len(data),
            'columns': columns,
            'column_count': len(columns),
            'sample_row': data[0] if data else None
        }

# Global file processing service instance
file_processor = FileProcessingService()