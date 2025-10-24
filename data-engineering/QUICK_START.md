# Quick Start Guide - SQLGym Postgres to S3 Pipeline

## 🚀 5-Minute Setup

### Step 1: Configure Credentials
```bash
cd data-engineering
cp .env.example .env
```

Edit `.env` with your credentials:
```bash
# Neon Postgres
DB_HOST=your-neon-host.neon.tech
DB_NAME=sqlgym
DB_USER=your-username
DB_PASSWORD=your-password

# AWS
AWS_REGION=us-east-1
S3_BUCKET_NAME=sqlgym-data-lake-production
```

### Step 2: Deploy to AWS
```bash
source .env
make deploy ENVIRONMENT=production
```

### Step 3: Trigger First Sync
```bash
make invoke
```

### Step 4: Monitor Results
```bash
make monitor
```

## 📊 Common Commands

| Command | Description |
|---------|-------------|
| `make deploy` | Deploy pipeline to AWS |
| `make invoke` | Trigger incremental sync |
| `make invoke-full` | Trigger full sync |
| `make monitor` | View sync report |
| `make logs` | View Lambda logs |
| `make test` | Run unit tests |
| `make validate` | Validate data quality |

## 🔧 Configuration

Edit `config/pipeline_config.json` to:
- Enable/disable specific tables
- Set sync type (incremental/full)
- Adjust priorities
- Configure retention

## 📈 Monitoring

### Check Last Sync
```bash
python scripts/monitor_sync.py --bucket $S3_BUCKET_NAME --hours 24
```

### View Specific Table
```bash
python scripts/monitor_sync.py --bucket $S3_BUCKET_NAME --table users --list-files
```

### CloudWatch Logs
```bash
make logs
```

## 🎯 Sync Types

**Incremental** (Default for tables with `updated_at`):
- Only syncs new/modified data
- Efficient and cost-effective
- Tables: users, topics, problems, etc.

**Full** (For tables without timestamps):
- Syncs entire table
- Use for small tables
- Tables: followers, badges, etc.

## 💰 Cost Estimate

~$5-11/month for typical usage:
- Lambda: $1-5
- S3 Storage: $2-3
- Data Transfer: $1-2

## 🆘 Troubleshooting

**Lambda Timeout?**
- Increase timeout in `template.yaml`

**Connection Failed?**
- Check Neon credentials in `.env`
- Verify firewall settings

**No New Data?**
- Normal for incremental sync
- Check with `make monitor`

## 📚 Learn More

- Full documentation: `PIPELINE_OVERVIEW.md`
- Setup guide: `setup_instructions.txt`
- Architecture details: See main README

## ✅ Production Checklist

- [ ] Configure `.env` with real credentials
- [ ] Store DB password in AWS Secrets Manager
- [ ] Deploy to AWS
- [ ] Test with `make invoke`
- [ ] Set up CloudWatch alarms
- [ ] Configure backup policies
- [ ] Document for team

---

**Need Help?** Check the logs with `make logs` or monitoring report with `make monitor`
