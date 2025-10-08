# SQLGym Docker Deployment Guide

## Quick Start

### 1. Setup Environment Variables
```bash
# Copy the example env file
cp .env.docker .env

# Edit .env and add your actual values (especially JWT_SECRET and ADMIN_SECRET_KEY)
nano .env
```

### 2. Build and Run with Docker Compose
```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down

# Stop and remove all data (including database)
docker-compose down -v
```

### 3. Access the Application
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Database**: localhost:5432

## Production Deployment

### Option 1: Deploy to Any VPS (DigitalOcean, AWS, etc.)

1. **Install Docker and Docker Compose on your server**
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

2. **Clone your repository**
```bash
git clone <your-repo-url>
cd sqlgym
```

3. **Configure environment variables**
```bash
cp .env.docker .env
nano .env  # Add production values
```

4. **Update CORS settings in docker-compose.yml**
```yaml
environment:
  - FRONTEND_URL=https://yourdomain.com
```

5. **Start the application**
```bash
docker-compose up -d
```

6. **Setup Nginx reverse proxy (recommended)**
```nginx
# /etc/nginx/sites-available/sqlgym
server {
    listen 80;
    server_name yourdomain.com;

    # Frontend
    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Backend API
    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

7. **Setup SSL with Let's Encrypt**
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

### Option 2: Deploy to Cloud Platforms

#### **Railway.app**
1. Connect your GitHub repository to Railway
2. Add environment variables in Railway dashboard
3. Railway will auto-detect docker-compose.yml

#### **DigitalOcean App Platform**
1. Connect GitHub repository
2. Configure as "Docker Compose" deployment
3. Add environment variables

#### **AWS ECS / Google Cloud Run**
1. Build and push images to container registry
2. Deploy using their respective services

## Database Management

### Backup Database
```bash
docker exec sqlgym_db pg_dump -U sqlgym sqlgym > backup.sql
```

### Restore Database
```bash
cat backup.sql | docker exec -i sqlgym_db psql -U sqlgym sqlgym
```

### Access Database CLI
```bash
docker exec -it sqlgym_db psql -U sqlgym sqlgym
```

## Troubleshooting

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f db
```

### Restart Services
```bash
# Restart all
docker-compose restart

# Restart specific service
docker-compose restart backend
```

### Rebuild After Code Changes
```bash
docker-compose down
docker-compose up -d --build
```

### Check Service Health
```bash
docker-compose ps
```

## Environment Variables Reference

| Variable | Description | Required |
|----------|-------------|----------|
| POSTGRES_USER | Database username | Yes |
| POSTGRES_PASSWORD | Database password | Yes |
| POSTGRES_DB | Database name | Yes |
| JWT_SECRET | JWT secret for authentication | Yes |
| ADMIN_SECRET_KEY | Admin panel secret | Yes |
| GOOGLE_CLIENT_ID | Google OAuth client ID | Optional |
| GOOGLE_CLIENT_SECRET | Google OAuth secret | Optional |
| FRONTEND_URL | Frontend URL for CORS | Yes |
| VITE_API_URL | Backend API URL | Yes |

## Security Checklist

- [ ] Change all default passwords
- [ ] Use strong JWT_SECRET (32+ random characters)
- [ ] Use strong ADMIN_SECRET_KEY
- [ ] Configure proper CORS origins
- [ ] Enable HTTPS in production
- [ ] Restrict database port (5432) access
- [ ] Keep Docker images updated
- [ ] Regular database backups
