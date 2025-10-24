#!/usr/bin/env python3
"""
AWS Secrets Manager - Database Secret Creator (Python version)
Creates or updates a database secret in AWS Secrets Manager
"""

import json
import sys
import argparse
import boto3
from getpass import getpass
from botocore.exceptions import ClientError


def create_or_update_secret(secret_name, secret_value, region, environment):
    """Create or update a secret in AWS Secrets Manager"""
    
    client = boto3.client('secretsmanager', region_name=region)
    
    try:
        response = client.describe_secret(SecretId=secret_name)
        print(f"✓ Secret '{secret_name}' already exists. Updating...")
        
        response = client.update_secret(
            SecretId=secret_name,
            SecretString=json.dumps(secret_value)
        )
        
        action = "updated"
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            print(f"✓ Creating new secret '{secret_name}'...")
            
            response = client.create_secret(
                Name=secret_name,
                Description=f"Database credentials for SQLGym {environment} environment",
                SecretString=json.dumps(secret_value),
                Tags=[
                    {'Key': 'Environment', 'Value': environment},
                    {'Key': 'Project', 'Value': 'SQLGym'}
                ]
            )
            
            action = "created"
        else:
            raise
    
    return response['ARN'], action


def main():
    parser = argparse.ArgumentParser(
        description='Create or update database credentials in AWS Secrets Manager'
    )
    parser.add_argument(
        'environment',
        choices=['development', 'staging', 'production'],
        help='Environment name'
    )
    parser.add_argument(
        '--region',
        default='us-east-1',
        help='AWS region (default: us-east-1)'
    )
    parser.add_argument(
        '--secret-name',
        help='Custom secret name (default: <environment>/sqlgym/database)'
    )
    
    args = parser.parse_args()
    
    secret_name = args.secret_name or f"{args.environment}/sqlgym/database"
    
    print("=" * 60)
    print("AWS Secrets Manager - Database Secret Creator")
    print("=" * 60)
    print()
    print(f"Environment: {args.environment}")
    print(f"AWS Region:  {args.region}")
    print(f"Secret Name: {secret_name}")
    print()
    
    print("Enter database credentials:")
    print()
    
    db_host = input("Neon Postgres Host (e.g., your-db.neon.tech): ").strip()
    db_name = input("Database Name [sqlgym]: ").strip() or "sqlgym"
    db_port = input("Database Port [5432]: ").strip() or "5432"
    db_user = input("Database Username: ").strip()
    db_password = getpass("Database Password: ")
    
    print()
    
    secret_value = {
        "host": db_host,
        "port": db_port,
        "database": db_name,
        "username": db_user,
        "password": db_password
    }
    
    try:
        secret_arn, action = create_or_update_secret(
            secret_name=secret_name,
            secret_value=secret_value,
            region=args.region,
            environment=args.environment
        )
        
        print()
        print(f"✅ Secret {action} successfully!")
        print()
        print(f"Secret ARN: {secret_arn}")
        print()
        print("=" * 60)
        print("Next Steps:")
        print("=" * 60)
        print()
        print("1. Save the ARN above securely")
        print("2. Use it when deploying your Lambda function:")
        print()
        print(f"   make deploy ENVIRONMENT={args.environment} \\")
        print(f'     DATABASE_SECRET_ARN="{secret_arn}" \\')
        print('     S3_BUCKET_NAME="your-bucket-name"')
        print()
        print("3. To verify the secret:")
        print(f"   aws secretsmanager get-secret-value --secret-id {secret_name} --region {args.region}")
        print()
        
    except ClientError as e:
        print(f"❌ Error: {e.response['Error']['Message']}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
