# SQLGym Postgres to S3 Data Engineering Pipeline

## Overview
This data engineering pipeline automates the extraction of data from your Neon Postgres database and loads it into AWS S3 in an optimized Parquet format for analytics and data warehousing.

## Architecture

```
┌─────────────────┐
│  Neon Postgres  │
│    (Source)     │
└────────┬────────┘
         │
         │ SQL Query Extract
         │
    ┌────▼──────────┐
    │ Lambda        │
    │ Function      │◄────── CloudWatch Events (Scheduled)
    │               │
    │ - Extract     │
    │ - Transform   │
    │ - Upload      │
    └────┬──────────┘
         │
         │ Parquet Files
         │
    ┌────▼──────────┐
    │   S3 Bucket   │
    │  (Data Lake)  │
    │               │
    │ /postgres-sync│
    │   /users/     │
    │   /problems/  │
    │   /...        │
    └───────────────┘
```

## Features

✅ **Incremental Sync** - Only sync changed data for tables with `updated_at` columns  
✅ **Full Sync** - Complete table sync for tables without timestamps  
✅ **Parquet Format** - Efficient columnar storage with Snappy compression  
✅ **Date Partitioning** - Organized by YYYY/MM/DD for easy querying  
✅ **Metadata Tracking** - Complete sync history and statistics  
✅ **Error Handling** - Robust retry logic and detailed error reporting  
✅ **Monitoring** - Built-in monitoring and validation tools  
✅ **Automated Scheduling** - Hourly syncs via CloudWatch Events  

## Directory Structure

```
data-engineering/
├── lambda/
│   └── handler.py              # Main Lambda function code
├── config/
│   └── pipeline_config.json    # Pipeline configuration
├── scripts/
│   ├── deploy.sh              # Deploy to AWS
│   ├── invoke_lambda.sh       # Manually trigger Lambda
│   ├── test_local.py          # Local testing
│   ├── monitor_sync.py        # Monitoring and reporting
│   ├── build_docker.sh        # Docker image build
│   └── run_tests.sh           # Run unit tests
├── utils/
│   ├── __init__.py
│   └── data_validator.py      # Data quality validation
├── tests/
│   └── test_handler.py        # Unit tests
├── template.yaml              # AWS SAM/CloudFormation template
├── requirements.txt           # Python dependencies
├── Dockerfile                 # Container definition
├── Makefile                   # Build automation
├── .env.example              # Environment variables template
└── setup_instructions.txt    # Detailed setup guide
```

## Quick Start

### 1. Configure Environment
```bash
cp .env.example .env
# Edit .env with your credentials
```

### 2. Deploy to AWS
```bash
source .env
make deploy ENVIRONMENT=production
```

### 3. Monitor Sync
```bash
make monitor
```

## Data Flow

### Sync Process
1. **Lambda Triggered** - CloudWatch Event or manual invocation
2. **Extract Data** - Query Neon Postgres tables
3. **Transform** - Convert to Pandas DataFrame
4. **Upload** - Write Parquet files to S3 with metadata
5. **Track** - Store sync metadata for incremental syncs

### S3 Structure
```
s3://your-bucket/
├── postgres-sync/
│   ├── users/
│   │   ├── 2025/10/24/
│   │   │   ├── incremental_20251024_120000.parquet
│   │   │   └── incremental_20251024_130000.parquet
│   │   └── 2025/10/25/
│   │       └── incremental_20251025_120000.parquet
│   ├── problems/
│   │   └── 2025/10/24/
│   │       └── full_20251024_120000.parquet
│   └── _metadata/
│       ├── users/
│       │   └── 20251024_120000.json
│       └── problems/
│           └── 20251024_120000.json
```

## Configuration

### Table Sync Configuration
Edit `config/pipeline_config.json`:

```json
{
  "tables": {
    "users": {
      "pk": "id",
      "updated_col": "updated_at",
      "sync_enabled": true,
      "sync_type": "incremental",
      "priority": 1
    }
  }
}
```

**Parameters:**
- `pk` - Primary key column name
- `updated_col` - Timestamp column for incremental sync (null for full sync)
- `sync_enabled` - Enable/disable table sync
- `sync_type` - "incremental" or "full"
- `priority` - Sync order (1 = highest priority)

## Sync Types

### Incremental Sync
- **Use for**: Tables with `updated_at` or `modified_at` columns
- **Benefits**: Fast, efficient, cost-effective
- **How it works**: Only syncs rows where `updated_col > last_sync_time`

**Example Tables**: users, topics, problems, user_progress

### Full Sync
- **Use for**: Tables without timestamp columns, small tables
- **Benefits**: Complete data guarantee
- **How it works**: Syncs entire table every time

**Example Tables**: followers, submissions, badges

## Common Operations

### Deploy Pipeline
```bash
make deploy ENVIRONMENT=production
```

### Trigger Manual Sync
```bash
# Incremental sync
make invoke

# Full sync
make invoke-full
```

### Monitor Sync Status
```bash
make monitor
```

### View Lambda Logs
```bash
make logs
```

### Validate Data Quality
```bash
make validate
```

### Run Local Tests
```bash
make test
```

## Monitoring & Alerts

### CloudWatch Metrics
- **Invocations** - Number of Lambda executions
- **Duration** - Execution time per run
- **Errors** - Failed executions
- **Throttles** - Rate limit hits

### Custom Metrics
- Rows synced per table
- File sizes uploaded
- Sync duration per table
- Incremental vs full sync ratio

### Alerts
Default alarm triggers on Lambda errors. Configure additional alarms:
- Long execution times (> 10 minutes)
- No data synced (potential issues)
- S3 upload failures

## Performance Optimization

### Lambda Configuration
```yaml
Timeout: 900 seconds (15 minutes)
Memory: 3008 MB
Reserved Concurrency: 1
```

### Table-Specific Settings
- **Large tables (> 1M rows)**: Use incremental sync
- **Small tables (< 100K rows)**: Full sync acceptable
- **High-priority tables**: Set priority: 1

### Cost Optimization
1. Use incremental sync for large tables
2. Adjust sync frequency based on data velocity
3. Set S3 lifecycle policies (90-day retention)
4. Monitor Lambda duration and optimize memory

## Troubleshooting

### Lambda Timeout
**Symptom**: Function times out before completion  
**Solutions**:
- Increase timeout in `template.yaml`
- Reduce batch size
- Split large tables

### Out of Memory
**Symptom**: Lambda runs out of memory  
**Solutions**:
- Increase memory allocation
- Process tables in smaller batches
- Use chunked reading for very large tables

### Connection Issues
**Symptom**: Cannot connect to Neon Postgres  
**Solutions**:
- Verify credentials in environment variables
- Check Neon firewall settings
- Ensure SSL is enabled

### No Data Synced
**Symptom**: Sync completes but no new data  
**Solutions**:
- Normal for incremental sync with no changes
- Check `last_sync_time` metadata
- Verify `updated_col` configuration

## Data Quality Validation

### Automated Checks
```python
from utils.data_validator import run_validation_checks

results = run_validation_checks('your-bucket', ['users', 'submissions'])
print(results)
```

### Validation Features
- Row count verification
- Column completeness checks
- Duplicate detection
- Data type validation
- NULL value analysis

## Security Best Practices

✅ **Database Credentials**: Store in AWS Secrets Manager  
✅ **IAM Roles**: Use roles instead of access keys  
✅ **S3 Encryption**: Enable server-side encryption  
✅ **Network**: Use VPC endpoints for private connectivity  
✅ **Audit**: Enable CloudTrail logging  
✅ **Access Control**: Restrict S3 bucket with IAM policies  

## Maintenance

### Regular Tasks
- [ ] Weekly: Review sync logs for errors
- [ ] Weekly: Check S3 storage costs
- [ ] Monthly: Validate data quality
- [ ] Monthly: Review and update table configurations
- [ ] Quarterly: Security audit

### Updates
```bash
# Update Lambda code
git pull
make deploy

# Update dependencies
pip install -r requirements.txt --upgrade
make deploy
```

## Integration with Analytics Tools

### Athena
Query S3 data directly:
```sql
CREATE EXTERNAL TABLE users (
  id VARCHAR,
  username VARCHAR,
  email VARCHAR,
  created_at TIMESTAMP
)
STORED AS PARQUET
LOCATION 's3://your-bucket/postgres-sync/users/';
```

### Redshift Spectrum
```sql
CREATE EXTERNAL SCHEMA postgres_sync
FROM DATA CATALOG
DATABASE 'sqlgym'
IAM_ROLE 'arn:aws:iam::xxx:role/RedshiftSpectrumRole';

SELECT * FROM postgres_sync.users;
```

### AWS Glue
Create Glue Crawler to automatically catalog all tables in S3.

## Cost Estimation

**Monthly Costs** (approximate):
- Lambda (1000 executions/month): $1-5
- S3 Storage (100 GB): $2-3
- Data Transfer: $1-2
- CloudWatch Logs: $0.50-1

**Total**: ~$5-11/month for typical usage

## Support & Contribution

For issues or enhancements:
1. Check logs: `make logs`
2. Review monitoring: `make monitor`
3. Run validation: `make validate`
4. Check setup instructions
