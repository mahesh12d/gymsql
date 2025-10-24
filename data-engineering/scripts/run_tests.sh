#!/bin/bash

set -e

echo "Running unit tests for data pipeline..."

cd "$(dirname "$0")/.."

export PYTHONPATH="${PYTHONPATH}:$(pwd)/lambda"

python -m pytest tests/ -v --tb=short

echo "All tests passed!"
