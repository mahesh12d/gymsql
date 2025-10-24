.PHONY: help install test deploy invoke monitor clean

ENVIRONMENT ?= production
AWS_REGION ?= us-east-1

help:
	@echo "SQLGym Postgres to S3 Data Pipeline"
	@echo "===================================="
	@echo ""
	@echo "Available commands:"
	@echo "  make install    - Install dependencies"
	@echo "  make test       - Run unit tests"
	@echo "  make deploy     - Deploy to AWS (ENVIRONMENT=production|staging|dev)"
	@echo "  make invoke     - Invoke Lambda function"
	@echo "  make monitor    - Show sync monitoring report"
	@echo "  make clean      - Clean build artifacts"
	@echo ""
	@echo "Examples:"
	@echo "  make deploy ENVIRONMENT=staging"
	@echo "  make invoke ENVIRONMENT=production"

install:
	@echo "Installing dependencies..."
	pip install -r requirements.txt
	pip install pytest pytest-cov

test:
	@echo "Running tests..."
	./scripts/run_tests.sh

deploy:
	@echo "Deploying to $(ENVIRONMENT)..."
	./scripts/deploy.sh $(ENVIRONMENT)

deploy-docker:
	@echo "Building and deploying Docker image..."
	./scripts/build_docker.sh $(ENVIRONMENT)

invoke:
	@echo "Invoking Lambda function..."
	./scripts/invoke_lambda.sh $(ENVIRONMENT) incremental

invoke-full:
	@echo "Invoking Lambda function with full sync..."
	./scripts/invoke_lambda.sh $(ENVIRONMENT) full

monitor:
	@echo "Generating sync monitoring report..."
	python scripts/monitor_sync.py --bucket $(S3_BUCKET_NAME) --hours 24

validate:
	@echo "Validating S3 data..."
	python -c "from utils.data_validator import run_validation_checks; \
		results = run_validation_checks('$(S3_BUCKET_NAME)', ['users', 'problems', 'submissions']); \
		print('Valid tables:', results['valid_tables']); \
		print('Invalid tables:', results['invalid_tables'])"

local-test:
	@echo "Running local test..."
	python scripts/test_local.py --test single

clean:
	@echo "Cleaning build artifacts..."
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf .aws-sam
	rm -rf .pytest_cache
	rm -f response.json
	rm -f output.json
	@echo "Clean complete!"

logs:
	@echo "Tailing Lambda logs..."
	aws logs tail /aws/lambda/$(ENVIRONMENT)-sqlgym-postgres-to-s3 --follow --region $(AWS_REGION)
