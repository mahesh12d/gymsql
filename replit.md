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

### Multi-Stage Deployment Pipeline
The application now supports a three-stage deployment pipeline with environment-based configuration:
- **Development (dev)**: Local development and testing
- **UAT/Staging (uat)**: User acceptance testing and staging
- **Production (prod)**: Production deployment

**All configuration is managed through environment variables** - no hardcoded values for enhanced security and multi-environment support.

### Configuration Management

#### Centralized Configuration
All configuration is managed through `api/config.py`, which provides:
- Environment detection (dev, UAT, prod, local)
- Environment-specific settings
- Configuration validation on startup
- Security-first approach with required secrets
- **Additive .env file loading**: Files are loaded in priority order (.env → .env.{env} → .env.local) to support base configurations, environment-specific settings, and local overrides

#### Environment Templates
Environment-specific templates are provided:
- `.env.dev.template` - Development configuration
- `.env.uat.template` - UAT/staging configuration
- `.env.prod.template` - Production configuration

Copy the appropriate template and fill in actual values:
```bash
cp .env.dev.template .env.dev  # For development
cp .env.uat.template .env.uat  # For UAT
cp .env.prod.template .env.prod  # For production
```

#### Additive Environment File Loading
The configuration system loads `.env` files additively in priority order:
1. **`.env`** - Base configuration (lowest priority)
2. **`.env.{dev|uat|prod}`** - Environment-specific configuration (overrides base)
3. **`.env.local`** - Local overrides (highest priority)

This allows developers to:
- Use `.env.dev` as their primary configuration
- Override specific values with `.env.local` without recreating the entire configuration
- Share base configuration across environments with `.env`

#### Required Environment Variables (All Environments)
Critical variables that must be set:
- `ENV` - Deployment environment (`dev`, `uat`, or `prod`)
- `DATABASE_URL` - PostgreSQL connection string
- `JWT_SECRET` - JWT authentication secret (use strong random value)
- `ADMIN_SECRET_KEY` - Admin access secret (use strong random value)

#### AWS S3 Configuration (Required if using S3 features)
- `AWS_ACCESS_KEY_ID` - AWS access key
- `AWS_SECRET_ACCESS_KEY` - AWS secret key
- `AWS_REGION` - AWS region (e.g., `us-east-1`)
- `S3_ALLOWED_BUCKETS` - Comma-separated list of allowed buckets (environment-specific)

#### Optional Features
- `REDIS_URL` - Redis connection string (caching and rate limiting)
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` - Google OAuth
- `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET` - GitHub OAuth
- `RESEND_API_KEY` - Email verification service
- `GEMINI_API_KEY` - AI-powered hints
- `FRONTEND_URLS` - Comma-separated list of allowed frontend URLs

See `ENVIRONMENT_CONFIGURATION.md` for complete configuration guide.

### Google Cloud Run Deployment

#### Environment-Specific Dockerfiles
- `Dockerfile.dev` - Development (hot reload enabled)
- `Dockerfile.uat` - UAT/staging (2 workers)
- `Dockerfile.prod` - Production (4 workers, optimized)

#### Environment-Specific Cloud Build Configurations
- `cloudbuild.dev.yaml` - Dev deployment (512Mi RAM, 3 max instances)
- `cloudbuild.uat.yaml` - UAT deployment (1Gi RAM, 5 max instances)
- `cloudbuild.prod.yaml` - Prod deployment (2Gi RAM, 2 CPU, 20 max instances)

#### Deployment Commands

**Development:**
```bash
gcloud builds submit --config=cloudbuild.dev.yaml
```

**UAT/Staging:**
```bash
gcloud builds submit --config=cloudbuild.uat.yaml
```

**Production:**
```bash
gcloud builds submit --config=cloudbuild.prod.yaml
```

#### Setting Environment Variables
After deployment, configure environment variables in Cloud Run:

```bash
# Example: Configure dev environment
gcloud run services update sqlgym-backend-dev \
  --region=us-central1 \
  --set-env-vars="ENV=dev,DATABASE_URL=postgresql://...,JWT_SECRET=..." \
  --set-env-vars="AWS_ACCESS_KEY_ID=...,AWS_SECRET_ACCESS_KEY=..." \
  --set-env-vars="S3_ALLOWED_BUCKETS=bucket1,bucket2"
```

Or use an environment file:
```bash
gcloud run services update sqlgym-backend-dev \
  --region=us-central1 \
  --env-vars-file=env.dev.yaml
```

### GitHub Actions CI/CD Pipeline (Recommended)

The project includes automated deployment workflows using GitHub Actions:

#### Branch-Based Deployment Strategy
- **`develop` branch** → Automatically deploys to Development environment
- **`staging` branch** → Automatically deploys to UAT/Staging environment  
- **`main` branch** → Automatically deploys to Production environment

#### Automated Workflow
1. Push code to a branch
2. GitHub Actions automatically builds and deploys backend to Cloud Run
3. GitHub Actions automatically builds and deploys frontend to Vercel
4. Deployment URLs are posted as commit comments

#### Setup Requirements
Configure the following secrets in your GitHub repository:
- `GCP_SERVICE_ACCOUNT_KEY` - Service account JSON for Cloud Run deployment
- `GCP_PROJECT_ID` - Google Cloud Project ID
- `VERCEL_TOKEN` - Vercel deployment token
- `VERCEL_ORG_ID` - Vercel organization ID
- `VERCEL_PROJECT_ID` - Vercel project ID

See `GITHUB_ACTIONS_SETUP.md` for complete setup instructions.

#### Benefits Over Manual Deployment
- ✅ Fully automated - no manual commands needed
- ✅ Branch-based deployment strategy
- ✅ Deployment history and logs in GitHub UI
- ✅ Works for entire team without local setup
- ✅ Automatic deployment URLs in commit comments

### Security Features
- **No Hardcoded Values**: All configuration via environment variables
- **Environment-Specific Secrets**: Different secrets for dev, UAT, and prod
- **Bucket Allowlisting**: S3 bucket access restricted to configured buckets
- **CORS Protection**: Environment-specific frontend URL allowlisting
- **Configuration Validation**: Startup validation ensures required variables are set

### Health Check
All environments expose a health check endpoint: `/api/health`