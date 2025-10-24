# Quick Start Guide - SQLGym Postgres to S3 Pipeline

## 🚀 5-Minute Setup (Production-Ready with AWS Secrets Manager)

### Step 1: Create Database Secret in AWS
```bash
cd data-engineering
python scripts/create_db_secret.py production --region us-east-1
```

Follow the prompts to enter your Neon database credentials. **Save the ARN** that's displayed!

**Alternative:** For development/testing without Secrets Manager, see legacy `.env` setup in `SECRETS_MANAGER_GUIDE.md`

### Step 2: Deploy to AWS
```bash
make deploy ENVIRONMENT=production \
  DATABASE_SECRET_ARN="arn:aws:secretsmanager:us-east-1:123456789012:secret:production/sqlgym/database-AbCdEf" \
  S3_BUCKET_NAME="sqlgym-data-lake-production"
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

- [ ] ✅ Create database secret in AWS Secrets Manager (Step 1)
- [ ] ✅ Save secret ARN securely
- [ ] Deploy to AWS with secret ARN (Step 2)
- [ ] Test with `make invoke`
- [ ] Set up CloudWatch alarms
- [ ] Configure backup policies
- [ ] Document for team

## 🔐 Security Note

This pipeline now uses **AWS Secrets Manager** for credential storage (production-ready). See `SECRETS_MANAGER_GUIDE.md` for:
- Detailed setup instructions
- Secret rotation configuration
- Security best practices
- Troubleshooting guide

---

**Need Help?** Check the logs with `make logs` or monitoring report with `make monitor`
