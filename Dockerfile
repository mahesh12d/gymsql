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

# Copy package files first for better layer caching
COPY requirements.txt package.json package-lock.json* ./

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt && npm install

# Copy application code
COPY . .

# Build frontend
RUN npm run build

# Expose port (Railway uses dynamic PORT env var)
EXPOSE 5000

# Start both backend and Redis worker
CMD python3.11 -m uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-5000} & \
    cd /app && python3.11 -m api.redis_worker & \
    wait -n
