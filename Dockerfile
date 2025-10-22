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

# Copy Python requirements and install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy all necessary config files first
COPY package.json package-lock.json* ./
COPY vite.config.ts tsconfig.json ./
COPY tailwind.config.ts postcss.config.js components.json ./

# Install frontend dependencies
RUN npm install --legacy-peer-deps

# Copy the entire application
COPY . .

# Debug: Verify critical files exist
RUN echo "=== Verifying build setup ===" && \
    ls -la && \
    echo "=== Client directory ===" && \
    ls -la client/ && \
    echo "=== Client index.html ===" && \
    test -f client/index.html && echo "✓ client/index.html exists" || echo "✗ client/index.html MISSING" && \
    echo "=== Vite config ===" && \
    head -20 vite.config.ts

# Build frontend
RUN npm run build

# Expose port (Cloud Run uses dynamic PORT env var, defaults to 8080)
EXPOSE 8080

# Start backend with Gunicorn + Uvicorn workers (production-ready)
# Use shell form to support dynamic PORT env var from Cloud Run
CMD gunicorn api.main:app --workers 2 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:${PORT:-8080} --timeout 120 --graceful-timeout 30
