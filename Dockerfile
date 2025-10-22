FROM python:3.11-slim

WORKDIR /app

# Install system dependencies including Node.js
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Copy Python requirements
COPY requirements.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy package files for frontend
COPY package*.json ./

# Install frontend dependencies
RUN npm ci

# Copy application code
COPY . .

# Build frontend
RUN npm run build

# Expose port (Cloud Run uses dynamic PORT env var, defaults to 8080)
EXPOSE 8080

# Start backend with Gunicorn + Uvicorn workers (production-ready)
# Use shell form to support dynamic PORT env var from Cloud Run
CMD gunicorn api.main:app --workers 2 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:${PORT:-8080} --timeout 120 --graceful-timeout 30
