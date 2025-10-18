FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy Python requirements
COPY requirements.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port (Cloud Run uses dynamic PORT env var, defaults to 8080)
EXPOSE 8080

# Start backend (use shell form to support PORT env var)
# CMD python3.11 -m uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8080}

CMD ["python3.11" ,"-m","uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8080"]