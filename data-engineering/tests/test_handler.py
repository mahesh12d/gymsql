"""
Unit tests for Lambda handler
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
from datetime import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'lambda'))

from handler import DatabaseExtractor, S3Uploader, lambda_handler


class TestDatabaseExtractor(unittest.TestCase):
    """Test DatabaseExtractor class"""
    
    def setUp(self):
        self.db_config = {
            'host': 'localhost',
            'port': '5432',
            'database': 'testdb',
            'user': 'testuser',
            'password': 'testpass'
        }
        self.extractor = DatabaseExtractor(self.db_config)
    
    @patch('handler.psycopg2.connect')
    def test_connect_success(self, mock_connect):
        """Test successful database connection"""
        mock_conn = Mock()
        mock_connect.return_value = mock_conn
        
        self.extractor.connect()
        
        mock_connect.assert_called_once()
        self.assertEqual(self.extractor.connection, mock_conn)
    
    @patch('handler.psycopg2.connect')
    def test_connect_failure(self, mock_connect):
        """Test database connection failure"""
        mock_connect.side_effect = Exception("Connection failed")
        
        with self.assertRaises(Exception):
            self.extractor.connect()
    
    @patch('handler.pd.read_sql_query')
    def test_extract_table_full_sync(self, mock_read_sql):
        """Test full table extraction"""
        mock_df = pd.DataFrame({'id': [1, 2, 3], 'name': ['a', 'b', 'c']})
        mock_read_sql.return_value = mock_df
        
        self.extractor.connection = Mock()
        result = self.extractor.extract_table('users')
        
        self.assertEqual(len(result), 3)
        mock_read_sql.assert_called_once()
    
    @patch('handler.pd.read_sql_query')
    def test_extract_table_incremental_sync(self, mock_read_sql):
        """Test incremental table extraction"""
        mock_df = pd.DataFrame({'id': [4, 5], 'name': ['d', 'e']})
        mock_read_sql.return_value = mock_df
        
        self.extractor.connection = Mock()
        result = self.extractor.extract_table(
            'users', 
            updated_col='updated_at',
            last_sync_time='2024-01-01 00:00:00'
        )
        
        self.assertEqual(len(result), 2)
        call_args = mock_read_sql.call_args[0][0]
        self.assertIn('WHERE', call_args)
        self.assertIn('updated_at', call_args)


class TestS3Uploader(unittest.TestCase):
    """Test S3Uploader class"""
    
    def setUp(self):
        self.bucket_name = 'test-bucket'
        self.uploader = S3Uploader(self.bucket_name)
    
    @patch('handler.s3_client.upload_fileobj')
    def test_upload_dataframe(self, mock_upload):
        """Test DataFrame upload to S3"""
        df = pd.DataFrame({'id': [1, 2, 3], 'value': ['a', 'b', 'c']})
        
        result = self.uploader.upload_dataframe(df, 'test_table', 'full')
        
        self.assertEqual(result['bucket'], self.bucket_name)
        self.assertEqual(result['row_count'], 3)
        self.assertIn('s3_key', result)
        self.assertIn('file_size_mb', result)
        mock_upload.assert_called_once()
    
    @patch('handler.s3_client.put_object')
    def test_upload_metadata(self, mock_put):
        """Test metadata upload to S3"""
        metadata = {
            'table_name': 'users',
            'row_count': 100,
            'sync_type': 'full'
        }
        
        self.uploader.upload_metadata(metadata, 'users')
        
        mock_put.assert_called_once()
        call_kwargs = mock_put.call_args[1]
        self.assertEqual(call_kwargs['Bucket'], self.bucket_name)
        self.assertIn('_metadata/users/', call_kwargs['Key'])


class TestLambdaHandler(unittest.TestCase):
    """Test Lambda handler function"""
    
    @patch.dict('os.environ', {
        'DB_HOST': 'localhost',
        'DB_NAME': 'testdb',
        'DB_USER': 'testuser',
        'DB_PASSWORD': 'testpass',
        'S3_BUCKET_NAME': 'test-bucket',
        'TABLES_CONFIG': '{"tables": {"users": {"updated_col": "updated_at"}}}'
    })
    @patch('handler.DatabaseExtractor')
    @patch('handler.S3Uploader')
    def test_lambda_handler_success(self, mock_uploader_class, mock_extractor_class):
        """Test successful Lambda execution"""
        mock_extractor = Mock()
        mock_extractor_class.return_value = mock_extractor
        
        mock_df = pd.DataFrame({'id': [1, 2], 'name': ['a', 'b']})
        mock_extractor.extract_table.return_value = mock_df
        
        mock_uploader = Mock()
        mock_uploader_class.return_value = mock_uploader
        mock_uploader.upload_dataframe.return_value = {
            'bucket': 'test-bucket',
            's3_key': 'test/key.parquet',
            'row_count': 2,
            'file_size_mb': 0.1
        }
        
        event = {
            'tables': ['users'],
            'sync_type': 'full'
        }
        
        result = lambda_handler(event, {})
        
        self.assertEqual(result['statusCode'], 200)
        self.assertIn('body', result)
        self.assertEqual(result['body']['successful_syncs'], 1)
        self.assertEqual(result['body']['total_rows_synced'], 2)


if __name__ == '__main__':
    unittest.main()
