#!/usr/bin/env python3
"""
Local testing script for Lambda function
Tests the handler with sample event data
"""

import sys
import os
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'lambda'))

from handler import lambda_handler

os.environ.update({
    'DB_HOST': os.getenv('DB_HOST', 'localhost'),
    'DB_PORT': os.getenv('DB_PORT', '5432'),
    'DB_NAME': os.getenv('DB_NAME', 'sqlgym'),
    'DB_USER': os.getenv('DB_USER', 'postgres'),
    'DB_PASSWORD': os.getenv('DB_PASSWORD', 'password'),
    'S3_BUCKET_NAME': os.getenv('S3_BUCKET_NAME', 'sqlgym-data-lake-dev'),
    'TABLES_CONFIG': json.dumps({
        "tables": {
            "users": {"updated_col": "updated_at"},
            "topics": {"updated_col": "updated_at"},
            "problems": {"updated_col": "updated_at"}
        }
    })
})


def test_full_sync():
    """Test full sync for all tables"""
    print("\n=== Testing Full Sync ===\n")
    
    event = {
        "tables": ["users", "topics", "problems"],
        "sync_type": "full",
        "force_full_sync": True
    }
    
    result = lambda_handler(event, {})
    print(json.dumps(result, indent=2, default=str))
    return result


def test_incremental_sync():
    """Test incremental sync"""
    print("\n=== Testing Incremental Sync ===\n")
    
    event = {
        "tables": ["users", "topics"],
        "sync_type": "incremental",
        "force_full_sync": False
    }
    
    result = lambda_handler(event, {})
    print(json.dumps(result, indent=2, default=str))
    return result


def test_single_table():
    """Test single table sync"""
    print("\n=== Testing Single Table Sync ===\n")
    
    event = {
        "tables": ["users"],
        "sync_type": "incremental"
    }
    
    result = lambda_handler(event, {})
    print(json.dumps(result, indent=2, default=str))
    return result


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Test Lambda handler locally')
    parser.add_argument('--test', choices=['full', 'incremental', 'single'], 
                       default='single', help='Test type to run')
    
    args = parser.parse_args()
    
    try:
        if args.test == 'full':
            test_full_sync()
        elif args.test == 'incremental':
            test_incremental_sync()
        elif args.test == 'single':
            test_single_table()
            
        print("\n✓ Test completed successfully!")
        
    except Exception as e:
        print(f"\n✗ Test failed: {str(e)}")
        sys.exit(1)
