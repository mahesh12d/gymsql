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

# Expose port (Cloud Run uses dynamic PORT env var, defaults to 8080)
EXPOSE 8080

# Start both backend and Redis worker
CMD ["python3.11", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "${PORT:-8080}"]
