# Git to S3 Migration Script

This directory contains scripts to migrate parquet dataset files from Git repositories to S3 storage for the SQLGym platform.

## Overview

The migration process:
1. Identifies problems using Git-based `parquet_data_source` fields
2. Downloads parquet files from Git URLs  
3. Uploads files to S3 with organized structure
4. Updates database records to use `s3_data_source` instead
5. Maintains backward compatibility during transition

## Prerequisites

1. **AWS Credentials**: Configure AWS CLI or set environment variables:
   ```bash
   export AWS_ACCESS_KEY_ID=your_access_key
   export AWS_SECRET_ACCESS_KEY=your_secret_key
   export AWS_DEFAULT_REGION=us-east-1
   ```

2. **Database Access**: Set DATABASE_URL environment variable:
   ```bash
   export DATABASE_URL=postgresql://user:pass@host:port/database
   ```

3. **S3 Bucket**: Create an S3 bucket with appropriate permissions:
   ```json
   {
     "Version": "2012-10-17", 
     "Statement": [
       {
         "Effect": "Allow",
         "Action": [
           "s3:GetObject",
           "s3:PutObject", 
           "s3:DeleteObject"
         ],
         "Resource": "arn:aws:s3:::your-bucket/*"
       }
     ]
   }
   ```

4. **Python 3.8+** with pip installed

## Quick Start

### Option 1: Use the Shell Wrapper (Recommended)

```bash
# Dry run first to see what would happen
./scripts/run_migration.sh your-dataset-bucket --dry-run

# Run the actual migration
./scripts/run_migration.sh your-dataset-bucket
```

### Option 2: Run Python Script Directly

```bash
# Install dependencies
pip install -r scripts/requirements.txt

# Dry run
python3 scripts/migrate_git_to_s3.py --s3-bucket your-dataset-bucket --dry-run

# Actual migration
python3 scripts/migrate_git_to_s3.py --s3-bucket your-dataset-bucket --verbose
```

## Migration Process Details

### File Organization

Files are uploaded to S3 with this structure:
```
your-bucket/
├── migrated-datasets/
│   ├── problem-id-1/
│   │   └── dataset.parquet
│   ├── problem-id-2/
│   │   └── sales.parquet
│   └── ...
```

### Database Changes

Each migrated problem gets:
- `s3_data_source` field populated with S3 details
- `parquet_data_source` field set to NULL  
- `updated_at` timestamp updated

Example `s3_data_source` structure:
```json
{
  "bucket": "your-dataset-bucket",
  "key": "migrated-datasets/problem-uuid/dataset.parquet", 
  "table_name": "problem_data",
  "description": "Migrated from Git: original description",
  "etag": "s3-file-etag-hash"
}
```

### Error Handling

The script includes comprehensive error handling:
- Failed downloads are retried with exponential backoff (3 attempts)
- S3 upload failures use boto3 adaptive retry mode
- HTTPS-only URL validation for security
- Per-problem error isolation (failures don't stop entire migration)
- Temporary files are always cleaned up
- Detailed logging for troubleshooting

## Command Line Options

### migrate_git_to_s3.py

- `--s3-bucket BUCKET` (required): S3 bucket name for storing files
- `--dry-run`: Preview actions without making changes
- `--verbose, -v`: Enable detailed logging
- `--help`: Show full help message

### run_migration.sh

- First argument: S3 bucket name (required)
- `--dry-run`: Preview mode
- Automatically handles prerequisites and dependency installation

## Monitoring Progress

The script provides detailed logging:
```
2024-01-15 10:30:00 - INFO - Found 25 problems with Git parquet sources
2024-01-15 10:30:01 - INFO - Processing 1/25: Calculate Total Sales
2024-01-15 10:30:02 - INFO - Downloading from: https://github.com/.../sales.parquet
2024-01-15 10:30:03 - INFO - Downloaded 2.3 MB to /tmp/temp_file.parquet
2024-01-15 10:30:04 - INFO - Uploaded to s3://bucket/migrated-datasets/uuid/sales.parquet
2024-01-15 10:30:05 - INFO - Updated problem uuid to use S3 source
2024-01-15 10:30:06 - INFO - Successfully migrated problem uuid
```

## Rollback (If Needed)

If you need to rollback migrations:

```sql
-- View migrated problems
SELECT id, title, s3_data_source->>'key' as s3_key 
FROM problems 
WHERE s3_data_source IS NOT NULL;

-- Rollback specific problem (example)
-- Note: This requires manually restoring parquet_data_source data
UPDATE problems 
SET s3_data_source = NULL,
    parquet_data_source = '{"original": "data"}'
WHERE id = 'problem-uuid';
```

## Troubleshooting

### Common Issues

1. **AWS Permission Denied**
   ```
   Solution: Verify AWS credentials and S3 bucket permissions
   ```

2. **Database Connection Failed**  
   ```
   Solution: Check DATABASE_URL format and connectivity
   ```

3. **Git URL Not Accessible**
   ```
   Solution: Check if Git repository is public and URL is correct
   ```

4. **S3 Bucket Not Found**
   ```
   Solution: Create bucket or verify bucket name and region
   ```

### Getting Help

Check logs for detailed error messages. The script provides specific guidance for each type of failure.

## Security Considerations

- Files are encrypted at rest in S3 (AES256)
- Database connections use the existing secure DATABASE_URL
- AWS credentials should follow least-privilege principles  
- Git URLs are validated before download
- Temporary files are securely deleted after use

## Post-Migration

After successful migration:
1. Verify problems load correctly in the admin panel
2. Test DuckDB sandbox functionality with S3 datasets
3. Monitor S3 costs and usage
4. Consider removing old Git repositories if no longer needed
5. Update documentation to reference S3 as the primary method