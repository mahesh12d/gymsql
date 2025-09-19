#!/usr/bin/env python3
"""
Migration script to move parquet files from Git repositories to S3 storage.

This script:
1. Identifies problems using Git-based parquet_data_source
2. Downloads parquet files from Git URLs
3. Uploads them to S3
4. Updates database records to use s3_data_source

Usage:
    python scripts/migrate_git_to_s3.py --s3-bucket your-dataset-bucket [--dry-run]

Requirements:
    - AWS credentials configured for S3 access
    - DATABASE_URL environment variable set
    - S3 bucket with appropriate permissions
"""

import os
import sys
import json
import argparse
import logging
import tempfile
import urllib.request
from urllib.parse import urlparse
from typing import List, Dict, Optional, Any
import time
from urllib.error import URLError, HTTPError

import boto3
from botocore.exceptions import ClientError
from botocore.config import Config
import psycopg2
from psycopg2.extras import RealDictCursor, register_default_jsonb

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class GitToS3Migrator:
    """Migrates parquet files from Git repositories to S3 storage."""
    
    def __init__(self, s3_bucket: str, dry_run: bool = False):
        self.s3_bucket = s3_bucket
        self.dry_run = dry_run
        
        # Configure S3 with retries
        s3_config = Config(
            retries={
                'max_attempts': 3,
                'mode': 'adaptive'
            },
            connect_timeout=30,
            read_timeout=300
        )
        self.s3_client = boto3.client('s3', config=s3_config)
        
        # Database connection
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            raise ValueError("DATABASE_URL environment variable is required")
        self.db_connection = psycopg2.connect(database_url)
        
        # Register JSONB decoder for psycopg2
        register_default_jsonb(self.db_connection)
        
        logger.info(f"Initialized migrator - bucket: {s3_bucket}, dry_run: {dry_run}")
    
    def get_git_problems(self) -> List[Dict[str, Any]]:
        """Fetch problems that use Git-based parquet sources."""
        query = """
            SELECT id, title, parquet_data_source, s3_data_source
            FROM problems 
            WHERE parquet_data_source IS NOT NULL 
            AND s3_data_source IS NULL
            ORDER BY created_at ASC
        """
        
        with self.db_connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query)
            results = cursor.fetchall()
            logger.info(f"Found {len(results)} problems with Git parquet sources")
            return [dict(row) for row in results]
    
    def download_parquet_file(self, git_url: str, file_path: str) -> str:
        """Download parquet file from Git URL to temporary file with retries."""
        # Construct full URL
        full_url = f"{git_url.rstrip('/')}/{file_path.lstrip('/')}"
        
        # Basic URL validation - require HTTPS for security
        parsed = urlparse(full_url)
        if parsed.scheme != 'https':
            raise ValueError(f"Only HTTPS URLs are allowed, got: {parsed.scheme}")
        
        logger.info(f"Downloading from: {full_url}")
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.parquet') as temp_file:
            temp_path = temp_file.name
        
        # Retry logic for downloads
        max_retries = 3
        retry_delay = 1  # seconds
        
        for attempt in range(max_retries):
            try:
                # Create request with timeout
                request = urllib.request.Request(full_url)
                request.add_header('User-Agent', 'SQLGym-Migration/1.0')
                
                with urllib.request.urlopen(request, timeout=60) as response:
                    with open(temp_path, 'wb') as temp_file:
                        # Download in chunks to handle large files
                        while True:
                            chunk = response.read(8192)
                            if not chunk:
                                break
                            temp_file.write(chunk)
                
                file_size = os.path.getsize(temp_path)
                logger.info(f"Downloaded {file_size:,} bytes to {temp_path}")
                return temp_path
                
            except (URLError, HTTPError, OSError) as e:
                logger.warning(f"Download attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt == max_retries - 1:
                    # Clean up temp file on final failure
                    if os.path.exists(temp_path):
                        os.unlink(temp_path)
                    raise Exception(f"Failed to download {full_url} after {max_retries} attempts: {e}")
                
                # Wait before retry
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
    
    def upload_to_s3(self, local_path: str, s3_key: str) -> Dict[str, str]:
        """Upload parquet file to S3 and return S3 details."""
        logger.info(f"Uploading to s3://{self.s3_bucket}/{s3_key}")
        
        if self.dry_run:
            logger.info("DRY RUN: Would upload to S3")
            return {
                "bucket": self.s3_bucket,
                "key": s3_key,
                "etag": "dry-run-etag"
            }
        
        try:
            # Upload to S3
            self.s3_client.upload_file(
                local_path, 
                self.s3_bucket, 
                s3_key,
                ExtraArgs={'ServerSideEncryption': 'AES256'}
            )
            
            # Get ETag
            response = self.s3_client.head_object(Bucket=self.s3_bucket, Key=s3_key)
            etag = response['ETag'].strip('"')
            
            logger.info(f"Successfully uploaded to S3, ETag: {etag}")
            return {
                "bucket": self.s3_bucket,
                "key": s3_key,
                "etag": etag
            }
        except ClientError as e:
            raise Exception(f"Failed to upload to S3: {e}")
    
    def update_problem_record(self, problem_id: str, s3_data_source: Dict[str, Any]) -> None:
        """Update problem record to use S3 data source."""
        query = """
            UPDATE problems 
            SET s3_data_source = %s,
                parquet_data_source = NULL,
                updated_at = NOW()
            WHERE id = %s
        """
        
        if self.dry_run:
            logger.info(f"DRY RUN: Would update problem {problem_id} with S3 source")
            return
        
        with self.db_connection.cursor() as cursor:
            cursor.execute(query, [json.dumps(s3_data_source), problem_id])
            self.db_connection.commit()
            logger.info(f"Updated problem {problem_id} to use S3 source")
    
    def generate_s3_key(self, problem_id: str, original_file_path: str) -> str:
        """Generate S3 key for the parquet file."""
        file_name = os.path.basename(original_file_path)
        # Use problem ID to avoid conflicts and organize files
        return f"migrated-datasets/{problem_id}/{file_name}"
    
    def migrate_problem(self, problem: Dict[str, Any]) -> bool:
        """Migrate a single problem from Git to S3."""
        problem_id = problem['id']
        title = problem['title']
        parquet_source = problem['parquet_data_source']
        
        # Handle JSONB field - might be string or already parsed dict
        if isinstance(parquet_source, str):
            try:
                parquet_source = json.loads(parquet_source)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse parquet_data_source JSON for problem {problem_id}: {e}")
                return False
        
        logger.info(f"Migrating problem: {title} (ID: {problem_id})")
        
        try:
            git_url = parquet_source['git_repo_url']
            file_path = parquet_source['file_path']
            table_name = parquet_source['table_name']
            description = parquet_source.get('description', '')
            
            # Generate S3 key
            s3_key = self.generate_s3_key(problem_id, file_path)
            
            # Download from Git
            temp_file = self.download_parquet_file(git_url, file_path)
            
            try:
                # Upload to S3
                s3_details = self.upload_to_s3(temp_file, s3_key)
                
                # Create S3 data source object
                s3_data_source = {
                    "bucket": s3_details["bucket"],
                    "key": s3_details["key"],
                    "table_name": table_name,
                    "description": f"Migrated from Git: {description}" if description else f"Migrated from {git_url}/{file_path}",
                    "etag": s3_details["etag"]
                }
                
                # Update database record
                self.update_problem_record(problem_id, s3_data_source)
                
                logger.info(f"Successfully migrated problem {problem_id}")
                return True
                
            finally:
                # Clean up temp file
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
                    
        except Exception as e:
            logger.error(f"Failed to migrate problem {problem_id}: {e}")
            return False
    
    def run_migration(self) -> None:
        """Run the complete migration process."""
        logger.info("Starting Git to S3 migration")
        
        # Get all problems that need migration
        problems = self.get_git_problems()
        if not problems:
            logger.info("No problems found that need migration")
            return
        
        # Migration statistics
        total = len(problems)
        successful = 0
        failed = 0
        
        # Migrate each problem
        for i, problem in enumerate(problems, 1):
            logger.info(f"Processing {i}/{total}: {problem['title']}")
            
            if self.migrate_problem(problem):
                successful += 1
            else:
                failed += 1
        
        # Report results
        logger.info(f"Migration completed: {successful} successful, {failed} failed out of {total} total")
        
        if failed > 0:
            logger.warning(f"{failed} problems failed to migrate - check logs above")
            sys.exit(1)
    
    def close(self):
        """Clean up resources."""
        if self.db_connection:
            self.db_connection.close()

def main():
    parser = argparse.ArgumentParser(description='Migrate parquet files from Git to S3')
    parser.add_argument('--s3-bucket', required=True, help='S3 bucket for storing parquet files')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    migrator = None
    try:
        migrator = GitToS3Migrator(args.s3_bucket, args.dry_run)
        migrator.run_migration()
        logger.info("Migration completed successfully")
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)
    finally:
        if migrator:
            migrator.close()

if __name__ == '__main__':
    main()