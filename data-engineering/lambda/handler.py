"""
Lambda Function Handler: Neon Postgres to S3 Data Sync
Extracts data from Neon Postgres and uploads to S3 in Parquet format
"""

import json
import os
import boto3
import psycopg2
import pandas as pd
from datetime import datetime
from io import BytesIO
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3_client = boto3.client('s3')


class DatabaseExtractor:
    """Handles database connection and data extraction"""

    def __init__(self, db_config: Dict[str, str]):
        self.db_config = db_config
        self.connection = None

    def connect(self):
        """Establish database connection"""
        try:
            self.connection = psycopg2.connect(
                host=self.db_config['host'],
                port=self.db_config['port'],
                database=self.db_config['database'],
                user=self.db_config['user'],
                password=self.db_config['password'],
                sslmode='require')
            logger.info("Successfully connected to Neon Postgres")
        except Exception as e:
            logger.error(f"Database connection failed: {str(e)}")
            raise

    def extract_table(self,
                      table_name: str,
                      updated_col: Optional[str] = None,
                      last_sync_time: Optional[str] = None) -> pd.DataFrame:
        """Extract data from a table with optional incremental sync"""

        try:
            if updated_col and last_sync_time:
                query = f"""
                    SELECT * FROM {table_name} 
                    WHERE {updated_col} > '{last_sync_time}'
                    ORDER BY {updated_col}
                """
                logger.info(
                    f"Incremental sync for {table_name} since {last_sync_time}"
                )
            else:
                query = f"SELECT * FROM {table_name}"
                logger.info(f"Full sync for {table_name}")

            df = pd.read_sql_query(query, self.connection)
            logger.info(f"Extracted {len(df)} rows from {table_name}")
            return df

        except Exception as e:
            logger.error(f"Failed to extract from {table_name}: {str(e)}")
            raise

    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            logger.info("Database connection closed")


class S3Uploader:
    """Handles S3 upload operations"""

    def __init__(self, bucket_name: str):
        self.bucket_name = bucket_name

    def upload_dataframe(self,
                         df: pd.DataFrame,
                         table_name: str,
                         sync_type: str = 'full') -> Dict[str, str]:
        """Upload DataFrame to S3 as Parquet"""
        try:
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            date_partition = datetime.utcnow().strftime('%Y/%m/%d')

            s3_key = f"postgres-sync/{table_name}/{date_partition}/{sync_type}_{timestamp}.parquet"

            buffer = BytesIO()
            df.to_parquet(buffer,
                          engine='pyarrow',
                          compression='snappy',
                          index=False)
            buffer.seek(0)

            s3_client.upload_fileobj(buffer,
                                     self.bucket_name,
                                     s3_key,
                                     ExtraArgs={
                                         'ContentType':
                                         'application/x-parquet',
                                         'Metadata': {
                                             'table_name': table_name,
                                             'sync_type': sync_type,
                                             'row_count': str(len(df)),
                                             'sync_timestamp': timestamp
                                         }
                                     })

            logger.info(
                f"Successfully uploaded {table_name} to s3://{self.bucket_name}/{s3_key}"
            )

            return {
                'bucket': self.bucket_name,
                's3_key': s3_key,
                'row_count': len(df),
                'file_size_mb': round(buffer.tell() / (1024 * 1024), 2)
            }

        except Exception as e:
            logger.error(f"Failed to upload {table_name} to S3: {str(e)}")
            raise

    def upload_metadata(self, metadata: Dict[str, Any], table_name: str):
        """Upload sync metadata to S3"""
        try:
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            s3_key = f"postgres-sync/_metadata/{table_name}/{timestamp}.json"

            s3_client.put_object(Bucket=self.bucket_name,
                                 Key=s3_key,
                                 Body=json.dumps(metadata,
                                                 indent=2,
                                                 default=str),
                                 ContentType='application/json')

            logger.info(
                f"Uploaded metadata to s3://{self.bucket_name}/{s3_key}")

        except Exception as e:
            logger.error(f"Failed to upload metadata: {str(e)}")


def get_last_sync_time(bucket_name: str, table_name: str) -> Optional[str]:
    """Retrieve last successful sync timestamp from S3 metadata"""
    try:
        prefix = f"postgres-sync/_metadata/{table_name}/"
        all_objects = []
        continuation_token = None
        
        # Paginate through all metadata files
        while True:
            if continuation_token:
                response = s3_client.list_objects_v2(
                    Bucket=bucket_name,
                    Prefix=prefix,
                    ContinuationToken=continuation_token
                )
            else:
                response = s3_client.list_objects_v2(
                    Bucket=bucket_name,
                    Prefix=prefix
                )
            
            if 'Contents' in response:
                all_objects.extend(response['Contents'])
            
            if not response.get('IsTruncated'):
                break
            
            continuation_token = response.get('NextContinuationToken')

        if len(all_objects) > 0:
            # Sort by LastModified to get the most recent metadata file
            sorted_objects = sorted(all_objects, 
                                   key=lambda x: x['LastModified'], 
                                   reverse=True)
            latest_metadata = sorted_objects[0]['Key']
            obj = s3_client.get_object(Bucket=bucket_name, Key=latest_metadata)
            metadata = json.loads(obj['Body'].read().decode('utf-8'))
            return metadata.get('sync_end_time')
    except Exception as e:
        logger.warning(
            f"Could not retrieve last sync time for {table_name}: {str(e)}")

    return None


def lambda_handler(event, context):
    """
    Main Lambda handler function
    
    Event structure:
    {
        "tables": ["users", "submissions"],  // Optional: specific tables to sync
        "sync_type": "incremental",  // Optional: "full" or "incremental"
        "force_full_sync": false  // Optional: force full sync even for incremental tables
    }
    """

    start_time = datetime.utcnow()

    db_config = {
        'host': os.environ['DB_HOST'],
        'port': os.environ.get('DB_PORT', '5432'),
        'database': os.environ['DB_NAME'],
        'user': os.environ['DB_USER'],
        'password': os.environ['DB_PASSWORD']
    }

    s3_bucket = os.environ['S3_BUCKET_NAME']

    tables_config = json.loads(os.environ.get('TABLES_CONFIG', '{}'))

    tables_to_sync = event.get('tables',
                               list(tables_config.get('tables', {}).keys()))
    sync_type = event.get('sync_type', 'incremental')
    force_full_sync = event.get('force_full_sync', False)

    extractor = DatabaseExtractor(db_config)
    uploader = S3Uploader(s3_bucket)

    results = []
    errors = []

    try:
        extractor.connect()

        for table_name in tables_to_sync:
            try:
                table_info = tables_config.get('tables',
                                               {}).get(table_name, {})
                updated_col = table_info.get('updated_col')

                last_sync = None
                actual_sync_type = 'full'

                if sync_type == 'incremental' and updated_col and not force_full_sync:
                    last_sync = get_last_sync_time(s3_bucket, table_name)
                    if last_sync:
                        actual_sync_type = 'incremental'

                df = extractor.extract_table(table_name, updated_col,
                                             last_sync)

                if len(df) > 0:
                    upload_result = uploader.upload_dataframe(
                        df, table_name, actual_sync_type)

                    metadata = {
                        'table_name': table_name,
                        'sync_type': actual_sync_type,
                        'sync_start_time': start_time.isoformat(),
                        'sync_end_time': datetime.utcnow().isoformat(),
                        'row_count': len(df),
                        'columns': list(df.columns),
                        's3_location': upload_result['s3_key'],
                        'file_size_mb': upload_result['file_size_mb'],
                        'last_sync_time': last_sync,
                        'status': 'success'
                    }

                    uploader.upload_metadata(metadata, table_name)

                    results.append({
                        'table': table_name,
                        'status': 'success',
                        'rows_synced': len(df),
                        'sync_type': actual_sync_type,
                        's3_key': upload_result['s3_key']
                    })
                else:
                    logger.info(f"No new data for {table_name}")
                    
                    # Still update metadata to track "last checked" time
                    # This prevents unnecessary full syncs if metadata upload previously failed
                    metadata = {
                        'table_name': table_name,
                        'sync_type': actual_sync_type,
                        'sync_start_time': start_time.isoformat(),
                        'sync_end_time': datetime.utcnow().isoformat(),
                        'row_count': 0,
                        'columns': list(df.columns) if len(df.columns) > 0 else [],
                        's3_location': None,
                        'file_size_mb': 0,
                        'last_sync_time': last_sync,
                        'status': 'no_new_data'
                    }
                    
                    uploader.upload_metadata(metadata, table_name)
                    
                    results.append({
                        'table': table_name,
                        'status': 'no_new_data',
                        'rows_synced': 0,
                        'sync_type': actual_sync_type
                    })

            except Exception as e:
                error_msg = f"Failed to sync {table_name}: {str(e)}"
                logger.error(error_msg)
                errors.append({'table': table_name, 'error': str(e)})

    finally:
        extractor.close()

    end_time = datetime.utcnow()
    duration_seconds = (end_time - start_time).total_seconds()

    response = {
        'statusCode': 200 if len(errors) == 0 else 207,
        'body': {
            'message':
            'Data sync completed',
            'duration_seconds':
            duration_seconds,
            'tables_processed':
            len(results),
            'successful_syncs':
            len([r for r in results if r['status'] == 'success']),
            'total_rows_synced':
            sum(r['rows_synced'] for r in results),
            'results':
            results,
            'errors':
            errors,
            'sync_timestamp':
            end_time.isoformat()
        }
    }

    logger.info(f"Sync completed: {json.dumps(response['body'], default=str)}")

    return response
