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
PostgreSQL is the primary database, managed via SQLAlchemy ORM. Redis is used for result caching (10 min TTL) and high-performance sorted-set leaderboards. The database connection pool is configured with `pool_size=20` and `max_overflow=10`. A 6-month data retention policy is implemented for `execution_results` to prevent unbounded database growth.

### Authentication System
Authentication supports traditional email/password login with JWT tokens, and OAuth flows for Google and GitHub using secure HttpOnly cookies. OAuth credentials are managed via Replit Secrets. User registration includes bcrypt password hashing and checks for unique usernames and emails. OAuth users are automatically created or merged with existing accounts.

### Key Features
-   **Gamification**: XP system with levels and badge rewards, GitHub-style contribution heatmap for daily activity.
-   **Problem Management**: Categorized SQL problems with hints and expected outputs.
-   **Code Execution**: SQL query submission and validation with an anti-hardcode detection system.
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

### Other
-   **Wouter**: Lightweight client-side routing.

## Deployment

### Railway Deployment
The application is configured for deployment on Railway.app with the following setup:

#### Build Process
```bash
pip install --no-cache-dir -r requirements.txt && npm run build
```

#### Docker Configuration
- **Dockerfile**: Unified container that installs Node.js 20 and Python 3.11
- **Build Step**: Installs dependencies and builds React frontend
- **Runtime**: Runs FastAPI backend and Redis worker in same container
- **Port**: Configured to use Railway's dynamic PORT environment variable (defaults to 5000)

#### Required Environment Variables
- `DATABASE_URL` - PostgreSQL connection (auto-set by Railway)
- `REDIS_URL` - Redis connection (auto-set by Railway)
- `JWT_SECRET` - JWT authentication secret (must be set manually)
- `ADMIN_SECRET_KEY` - Admin access secret (must be set manually)
- Optional OAuth credentials: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`

#### Deployment Files
- `Dockerfile` - Unified container configuration
- `railway.toml` - Railway deployment configuration with health check
- `RAILWAY_DEPLOYMENT.md` - Comprehensive deployment guide

See `RAILWAY_DEPLOYMENT.md` for detailed deployment instructions.