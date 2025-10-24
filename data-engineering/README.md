# SQLGym Data Engineering Pipeline

## 📦 What's Included

This folder contains a complete, production-ready data pipeline to sync your SQLGym Neon Postgres database to AWS S3 for analytics and data warehousing.

## ⚡ Quick Start

```bash
# 1. Configure
cp .env.example .env
# Edit .env with your credentials

# 2. Deploy
source .env
make deploy

# 3. Run
make invoke

# 4. Monitor
make monitor
```

See [QUICK_START.md](QUICK_START.md) for detailed instructions.

## 🏗️ Architecture

```
Neon Postgres → Lambda Function → S3 Bucket (Parquet)
```

- **Incremental Sync**: Only new/changed data (efficient)
- **Full Sync**: Complete table sync (for tables without timestamps)
- **Parquet Format**: Optimized columnar storage
- **Scheduled**: Runs hourly via CloudWatch Events

## 📁 Structure

```
data-engineering/
├── lambda/           # Lambda function code
├── config/          # Pipeline configuration
├── scripts/         # Deployment & monitoring tools
├── utils/           # Data validation utilities
├── tests/           # Unit tests
└── docs/            # Documentation
```

## 🎯 Features

✅ Incremental sync for 10 tables with timestamps  
✅ Full sync for 11 tables without timestamps  
✅ Parquet format with Snappy compression  
✅ Date-based partitioning (YYYY/MM/DD)  
✅ Metadata tracking  
✅ Error handling & retry logic  
✅ Data quality validation  
✅ CloudWatch monitoring  
✅ Cost optimization ($5-11/month)  

## 📚 Documentation

- **Quick Start**: [QUICK_START.md](QUICK_START.md) - 5-minute setup
- **Full Guide**: [PIPELINE_OVERVIEW.md](PIPELINE_OVERVIEW.md) - Complete documentation
- **Setup**: [setup_instructions.txt](setup_instructions.txt) - Detailed setup

## 🔧 Commands

| Command | Purpose |
|---------|---------|
| `make deploy` | Deploy to AWS |
| `make invoke` | Trigger sync |
| `make monitor` | View reports |
| `make logs` | Check logs |
| `make test` | Run tests |

## 💡 Use Cases

- **Analytics**: Query data with Athena/Redshift Spectrum
- **Data Warehousing**: Load into Redshift/Snowflake
- **Reporting**: Build dashboards with QuickSight/Tableau
- **Backup**: Historical data snapshots
- **Machine Learning**: Feature engineering pipelines

## 🛠️ Technologies

- **AWS Lambda**: Serverless compute
- **AWS S3**: Object storage
- **Parquet**: Columnar file format
- **Python 3.11**: Runtime
- **Pandas**: Data processing
- **Boto3**: AWS SDK

## 📊 Data Flow

1. **Trigger**: CloudWatch Event (hourly) or manual
2. **Extract**: Query Neon Postgres
3. **Transform**: Convert to Pandas DataFrame
4. **Load**: Upload Parquet to S3
5. **Track**: Store metadata for next sync

## 🔐 Security

- Database credentials via environment variables
- IAM roles for S3 access
- S3 bucket encryption
- VPC support (optional)
- Audit logging

## 💰 Cost

Estimated monthly cost: **$5-11**
- Lambda: $1-5
- S3: $2-3
- Transfer: $1-2

## 🆘 Support

Check documentation or run:
```bash
make logs      # View Lambda logs
make monitor   # Check sync status
make validate  # Verify data quality
```

---

**Ready to deploy?** Start with [QUICK_START.md](QUICK_START.md)
