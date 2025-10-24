"""
Data validation utilities for ensuring data quality in S3
"""

import boto3
import pandas as pd
from io import BytesIO
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)
s3_client = boto3.client('s3')


class DataValidator:
    """Validates synced data in S3"""
    
    def __init__(self, bucket_name: str):
        self.bucket_name = bucket_name
    
    def validate_parquet_file(self, s3_key: str) -> Dict[str, Any]:
        """Validate a Parquet file in S3"""
        try:
            obj = s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)
            df = pd.read_parquet(BytesIO(obj['Body'].read()))
            
            validation_results = {
                'file': s3_key,
                'valid': True,
                'row_count': len(df),
                'column_count': len(df.columns),
                'columns': list(df.columns),
                'null_counts': df.isnull().sum().to_dict(),
                'data_types': df.dtypes.astype(str).to_dict(),
                'memory_usage_mb': df.memory_usage(deep=True).sum() / (1024 * 1024),
                'issues': []
            }
            
            for col in df.columns:
                null_count = df[col].isnull().sum()
                if null_count == len(df):
                    validation_results['issues'].append(f"Column '{col}' has all NULL values")
            
            duplicate_count = df.duplicated().sum()
            if duplicate_count > 0:
                validation_results['issues'].append(f"Found {duplicate_count} duplicate rows")
            
            if len(validation_results['issues']) > 0:
                validation_results['valid'] = False
            
            return validation_results
            
        except Exception as e:
            logger.error(f"Validation failed for {s3_key}: {str(e)}")
            return {
                'file': s3_key,
                'valid': False,
                'error': str(e)
            }
    
    def validate_table_data(self, table_name: str, date_partition: str = None) -> List[Dict]:
        """Validate all files for a table"""
        prefix = f"postgres-sync/{table_name}/"
        if date_partition:
            prefix += f"{date_partition}/"
        
        paginator = s3_client.get_paginator('list_objects_v2')
        results = []
        
        for page in paginator.paginate(Bucket=self.bucket_name, Prefix=prefix):
            if 'Contents' in page:
                for obj in page['Contents']:
                    if obj['Key'].endswith('.parquet'):
                        result = self.validate_parquet_file(obj['Key'])
                        results.append(result)
        
        return results
    
    def compare_row_counts(self, table_name: str, expected_count: int, 
                          date_partition: str = None) -> Dict[str, Any]:
        """Compare actual row count with expected"""
        validations = self.validate_table_data(table_name, date_partition)
        
        total_rows = sum(v['row_count'] for v in validations if v.get('valid'))
        
        return {
            'table': table_name,
            'expected_count': expected_count,
            'actual_count': total_rows,
            'difference': total_rows - expected_count,
            'match': total_rows == expected_count,
            'file_count': len(validations)
        }


def run_validation_checks(bucket_name: str, tables: List[str]) -> Dict[str, List]:
    """Run validation checks on multiple tables"""
    validator = DataValidator(bucket_name)
    
    results = {
        'valid_tables': [],
        'invalid_tables': [],
        'errors': []
    }
    
    for table in tables:
        try:
            validations = validator.validate_table_data(table)
            
            if all(v.get('valid', False) for v in validations):
                results['valid_tables'].append(table)
            else:
                results['invalid_tables'].append({
                    'table': table,
                    'issues': [v for v in validations if not v.get('valid')]
                })
        except Exception as e:
            results['errors'].append({
                'table': table,
                'error': str(e)
            })
    
    return results
