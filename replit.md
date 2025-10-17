# SQLGym

## Overview
SQLGym is a gamified SQL learning platform designed to teach SQL through coding practice. It combines fitness-themed motivation with an XP system, leaderboards, and a community forum to provide an engaging and effective learning experience. The platform offers a comprehensive problem set with varying difficulty, submission tracking, and a badge system. The business vision is to create a leading interactive platform for SQL education, leveraging gamification to enhance user engagement and retention, and fostering a strong community of learners.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture
### Frontend
The frontend is built with React and TypeScript using Vite. It utilizes `shadcn/ui` and Radix UI for design, styled with Tailwind CSS. Routing is handled by Wouter, server state management by TanStack Query, and form handling/validation by React Hook Form with Zod.

### Backend
The backend is a RESTful API developed with FastAPI and Python. It uses SQLAlchemy ORM with Pydantic for type safety. Authentication is managed via JWT tokens and bcrypt for password hashing. Middleware handles CORS, request logging, and error management.

### Database
PostgreSQL is the primary database, managed via SQLAlchemy ORM. Redis is used for result caching (10 min TTL) and high-performance sorted-set leaderboards. Database connection pool settings are environment-specific and configured via environment variables (`DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `DB_POOL_TIMEOUT`, `DB_POOL_RECYCLE`). A 6-month data retention policy is implemented for `execution_results` to prevent unbounded database growth.

### Authentication System
Authentication supports traditional email/password login with JWT tokens, and OAuth flows for Google and GitHub using secure HttpOnly cookies. OAuth credentials and all secrets are managed via environment variables with environment-specific configuration. User registration includes bcrypt password hashing and checks for unique usernames and emails. OAuth users are automatically created or merged with existing accounts.

### Key Features
-   **Gamification**: XP system with levels and badge rewards, GitHub-style contribution heatmap for daily activity.
-   **Problem Management**: Categorized SQL problems with hints and expected outputs.
-   **Code Execution**: SQL query submission and validation with an anti-hardcode detection system.
-   **AI-Powered Hints**: Google Gemini integration provides intelligent hints for failed submissions without revealing solutions. Rate limited to 5 hints per problem per hour per user.
-   **Social Features**: Community posts with likes and comments, rich text editor with markdown and syntax-highlighted code blocks, follower system, helpful resources sharing.
-   **Progress Tracking**: User submission history, leaderboards, and dynamic profile statistics.
-   **Responsive Design**: Mobile-friendly interface.
-   **Admin Panel**: Allows manual schema definition for problem data.

### System Design Choices
-   PostgreSQL for all data persistence, complemented by Redis for caching and leaderboards.
-   SQL query processing uses a Redis-based job queue with a background worker for asynchronous execution.
-   **Redis Fallback Mechanism**: Submissions automatically fall back to PostgreSQL (`fallback_submissions` table) if Redis is unavailable, ensuring zero data loss. The worker recovers these submissions when Redis becomes available.
-   **Worker Availability Detection**: A heartbeat mechanism detects worker availability; if the worker is down, submissions are executed directly to prevent jobs from getting stuck.
-   The architecture has been simplified by removing chat and friends functionality to reduce complexity.
-   Data retention policies and worker availability mechanisms are in place to ensure system stability and performance.

### Required Workflows
Two workflows must run simultaneously:
1. **SQLGym Dev Server**: Main application server (API + Frontend)
2. **Redis Worker**: Background worker that processes SQL submission jobs from the Redis queue

## External Dependencies
### Database Services
-   **Neon Database**: PostgreSQL hosting.
-   **SQLAlchemy ORM**: Python SQL toolkit and Object Relational Mapper.
-   **redis**: Python client for Redis.

### UI Libraries
-   **Radix UI**: Unstyled, accessible UI primitives.
-   **shadcn/ui**: Pre-built component library.
-   **Tailwind CSS**: Utility-first CSS framework.
-   **Lucide React**: Icon library.
-   **react-calendar-heatmap**: GitHub-style contribution heatmap.

### Development Tools
-   **Vite**: Fast build tool.
-   **TypeScript**: Typed superset of JavaScript.
-   **TanStack Query**: Server state management and caching.
-   **React Hook Form**: Form handling and validation.
-   **Zod**: Schema validation.

### Authentication & Security
-   **jsonwebtoken**: For token-based authentication.
-   **bcrypt**: For password hashing.
-   **Authlib**: OAuth 2.0 client library for Google and GitHub authentication.
-   **httpx**: Async HTTP client for OAuth requests.
-   **itsdangerous**: Session data signing and validation.

### Content Rendering & Editing
-   **react-markdown**: Renders Markdown content.
-   **react-syntax-highlighter**: Syntax highlighting for code blocks.
-   **remark-gfm**: GitHub Flavored Markdown support.
-   **CodeMirror**: In-editor syntax highlighting for code blocks.

### AI & Machine Learning
-   **Google Gemini**: AI model (gemini-2.0-flash-exp) for generating educational hints on failed submissions.

### Other
-   **Wouter**: Lightweight client-side routing.

## Deployment

### CI/CD Pipeline - Two-Stage Deployment
The application uses an automated CI/CD pipeline with Google Cloud Build for two separate environments:

- **Staging** (`main` branch) → `sqlgym-staging` service
- **Production** (`prod` branch) → `sqlgym-production` service

**All configuration is managed through environment variables** and **Google Secret Manager** for enhanced security - no .env files are used.

### Configuration Management

#### Centralized Configuration
All configuration is managed through `api/config.py`, which provides:
- Environment detection (staging, prod, local) via `ENV` variable
- Environment-specific settings
- Configuration validation on startup
- Security-first approach with required secrets
- Direct environment variable reading (no .env files)

#### Required Environment Variables
Critical variables that must be set via Cloud Run Secret Manager:

**Staging Environment:**
- `staging-database-url` - Neon Postgres connection string for staging
- `staging-redis-url` - Redis connection string for staging
- `staging-jwt-secret` - JWT authentication secret
- `staging-admin-secret` - Admin access secret

**Production Environment:**
- `prod-database-url` - Neon Postgres connection string for production
- `prod-redis-url` - Redis connection string for production
- `prod-jwt-secret` - JWT authentication secret
- `prod-admin-secret` - Admin access secret

#### Optional Features (via Secret Manager)
- `google-client-id`, `google-client-secret` - Google OAuth
- `github-client-id`, `github-client-secret` - GitHub OAuth
- `resend-api-key` - Email verification service
- `gemini-api-key` - AI-powered hints
- `aws-access-key-id`, `aws-secret-access-key` - AWS S3

See `CICD_SETUP.md` for complete CI/CD setup guide.

### Automated Deployments

#### Branch-Based Deployment Strategy
- **Push to `main` branch** → Automatically builds and deploys to **Staging**
- **Push to `prod` branch** → Automatically builds and deploys to **Production**

#### Deployment Workflow
1. Developer pushes code to `main` branch
2. Cloud Build trigger activates automatically
3. Docker image is built and pushed to Artifact Registry
4. Application is deployed to `sqlgym-staging` on Cloud Run
5. After testing in staging, merge `main` → `prod` for production deployment

#### Environment Configuration

**Staging Environment:**
- Service: `sqlgym-staging`
- Branch: `main`
- Memory: 1Gi
- CPU: 1
- Max Instances: 5
- Min Instances: 0 (scales to zero)
- Config File: `cloudbuild.staging.yaml`

**Production Environment:**
- Service: `sqlgym-production`
- Branch: `prod`
- Memory: 2Gi
- CPU: 2
- Max Instances: 20
- Min Instances: 1 (always available)
- Config File: `cloudbuild.prod.yaml`

### Manual Deployment

#### Local Development
```bash
# Build the image
docker build -t sqlgym:latest .

# Run with environment variables
docker run -p 8080:8080 \
  -e DATABASE_URL="your-database-url" \
  -e JWT_SECRET="your-jwt-secret" \
  -e ADMIN_SECRET_KEY="your-admin-secret" \
  -e ENV="local" \
  sqlgym:latest
```

#### One-Time Manual Deployment
```bash
# Deploy to staging
gcloud builds submit --config=cloudbuild.staging.yaml

# Deploy to production
gcloud builds submit --config=cloudbuild.prod.yaml
```

### Security Features
- **No .env Files**: All secrets stored in Google Secret Manager
- **Environment Separation**: Separate secrets for staging and production
- **Artifact Registry**: Secure Docker image storage
- **IAM-Based Access**: Least-privilege service account permissions
- **Bucket Allowlisting**: S3 bucket access restricted to configured buckets
- **CORS Protection**: Environment-specific frontend URL allowlisting
- **Configuration Validation**: Startup validation ensures required variables are set

### Monitoring & Rollback

#### View Deployment Logs
```bash
# View Cloud Build logs
gcloud builds list --limit=10
gcloud builds log BUILD_ID

# View Cloud Run logs
gcloud run services logs read sqlgym-staging --region=us-central1
gcloud run services logs read sqlgym-production --region=us-central1
```

#### Rollback to Previous Version
```bash
# List revisions
gcloud run revisions list --service=sqlgym-production --region=us-central1

# Rollback to specific revision
gcloud run services update-traffic sqlgym-production \
  --region=us-central1 \
  --to-revisions=REVISION_NAME=100
```

### Health Check
The application exposes a health check endpoint: `/api/health`