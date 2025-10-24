#!/usr/bin/env python3
"""
Monitor S3 sync status and generate reports
"""

import boto3
import json
from datetime import datetime, timedelta
from collections import defaultdict
import argparse

s3_client = boto3.client('s3')


def get_sync_metadata(bucket_name, table_name=None, hours=24):
    """Retrieve sync metadata from S3"""
    
    prefix = f"postgres-sync/_metadata/"
    if table_name:
        prefix += f"{table_name}/"
    
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)
    
    metadata_files = []
    
    paginator = s3_client.get_paginator('list_objects_v2')
    for page in paginator.paginate(Bucket=bucket_name, Prefix=prefix):
        if 'Contents' in page:
            for obj in page['Contents']:
                if obj['LastModified'].replace(tzinfo=None) >= cutoff_time:
                    metadata_files.append(obj['Key'])
    
    metadata_list = []
    for key in metadata_files:
        obj = s3_client.get_object(Bucket=bucket_name, Key=key)
        metadata = json.loads(obj['Body'].read().decode('utf-8'))
        metadata_list.append(metadata)
    
    return metadata_list


def generate_sync_report(bucket_name, hours=24):
    """Generate sync report"""
    
    print(f"\n{'='*80}")
    print(f"SQLGym Postgres to S3 Sync Report")
    print(f"Last {hours} hours")
    print(f"{'='*80}\n")
    
    metadata_list = get_sync_metadata(bucket_name, hours=hours)
    
    if not metadata_list:
        print("No sync operations found in the specified time range.")
        return
    
    by_table = defaultdict(list)
    for meta in metadata_list:
        by_table[meta['table_name']].append(meta)
    
    total_rows = 0
    total_size = 0
    
    print(f"{'Table':<25} {'Syncs':<10} {'Total Rows':<15} {'Total Size (MB)':<20} {'Last Sync'}")
    print("-" * 110)
    
    for table, syncs in sorted(by_table.items()):
        rows = sum(s['row_count'] for s in syncs)
        size = sum(s.get('file_size_mb', 0) for s in syncs)
        last_sync = max(s['sync_end_time'] for s in syncs)
        
        total_rows += rows
        total_size += size
        
        print(f"{table:<25} {len(syncs):<10} {rows:<15,} {size:<20.2f} {last_sync}")
    
    print("-" * 110)
    print(f"{'TOTAL':<25} {len(metadata_list):<10} {total_rows:<15,} {total_size:<20.2f}")
    print()
    
    incremental_count = len([m for m in metadata_list if m['sync_type'] == 'incremental'])
    full_count = len([m for m in metadata_list if m['sync_type'] == 'full'])
    
    print(f"Sync Type Breakdown:")
    print(f"  Incremental: {incremental_count}")
    print(f"  Full: {full_count}")
    print()
    
    failed_syncs = [m for m in metadata_list if m.get('status') != 'success']
    if failed_syncs:
        print(f"⚠️  Failed Syncs: {len(failed_syncs)}")
        for sync in failed_syncs:
            print(f"  - {sync['table_name']}: {sync.get('error', 'Unknown error')}")
    else:
        print("✓ All syncs completed successfully")
    
    print(f"\n{'='*80}\n")


def list_latest_files(bucket_name, table_name):
    """List latest sync files for a table"""
    
    prefix = f"postgres-sync/{table_name}/"
    
    response = s3_client.list_objects_v2(
        Bucket=bucket_name,
        Prefix=prefix,
        MaxKeys=10
    )
    
    if 'Contents' not in response:
        print(f"No files found for table: {table_name}")
        return
    
    print(f"\nLatest sync files for {table_name}:")
    print(f"{'File':<80} {'Size (MB)':<15} {'Last Modified'}")
    print("-" * 120)
    
    for obj in sorted(response['Contents'], key=lambda x: x['LastModified'], reverse=True)[:10]:
        size_mb = obj['Size'] / (1024 * 1024)
        print(f"{obj['Key']:<80} {size_mb:<15.2f} {obj['LastModified']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Monitor Postgres to S3 sync operations')
    parser.add_argument('--bucket', required=True, help='S3 bucket name')
    parser.add_argument('--table', help='Specific table to check')
    parser.add_argument('--hours', type=int, default=24, help='Hours to look back')
    parser.add_argument('--list-files', action='store_true', help='List latest files')
    
    args = parser.parse_args()
    
    if args.list_files and args.table:
        list_latest_files(args.bucket, args.table)
    else:
        generate_sync_report(args.bucket, args.hours)
