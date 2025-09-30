## Overview
SQLGym is a gamified SQL learning platform designed to teach SQL through coding practice, combining it with fitness-themed motivation. It allows users to solve SQL problems, track progress via an XP system, compete on leaderboards, and engage in a community forum. The platform offers a comprehensive problem set with varying difficulty levels, submission tracking, and a badge system for achievements, aiming to provide an engaging and effective learning experience.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture
### Frontend
The frontend uses React with TypeScript, built with Vite. It leverages `shadcn/ui` and Radix UI for consistent design, styled with Tailwind CSS. Wouter is used for routing, TanStack Query for server state management, and React Hook Form with Zod for form handling and validation. Authentication in development mode is bypassed for a fake developer user.

### Backend
The backend is built with FastAPI and Python, implementing a RESTful API. It uses SQLAlchemy ORM with Pydantic for type safety and automatic API documentation. JWT tokens manage authentication, with bcrypt for password hashing. Middleware handles CORS, request logging, and error management.

### Database
PostgreSQL is the primary database, managed via SQLAlchemy ORM. The schema includes tables for users, problems, submissions, community posts, comments, likes, and user badges, supporting progress tracking, problem-solving statistics, and social features.

**Replit Configuration**: Database connection pool configured with pool_size=20 and max_overflow=10 to handle concurrent requests efficiently.

### Authentication System
JWT tokens, stored in localStorage on the client, handle authentication. The server validates tokens via middleware. User registration includes bcrypt password hashing and checks for unique usernames and emails.

### Key Features
- **Gamification**: XP system with levels (SQL Beginner to Powerlifter) and badge rewards.
- **Problem Management**: Categorized SQL problems with hints and expected outputs.
- **Code Execution**: SQL query submission and validation system.
- **Social Features**: Community posts with likes and comments.
- **Progress Tracking**: User submission history and leaderboards.
- **Responsive Design**: Mobile-friendly interface.
- **Anti-Hardcode Detection**: Three-layer system (static analysis, execution plan analysis, data dependency testing) to prevent hardcoded solutions.

### State Management
Client-side state uses TanStack Query for server state and React's built-in state for UI. A custom AuthContext provider manages authentication state, persisting user sessions in localStorage.

## External Dependencies
### Database Services
- **Neon Database**: PostgreSQL hosting via `@neondatabase/serverless` driver.
- **SQLAlchemy ORM**: For type-safe database operations.

### UI Libraries
- **Radix UI**: Unstyled, accessible UI primitives.
- **shadcn/ui**: Pre-built component library based on Radix UI.
- **Tailwind CSS**: Utility-first CSS framework.
- **Lucide React**: Icon library.

### Development Tools
- **Vite**: Fast build tool for development.
- **TypeScript**: For type safety.
- **TanStack Query**: Server state management and caching.
- **React Hook Form**: For form handling and validation.
- **Zod**: Schema validation.

### Authentication & Security
- **jsonwebtoken**: For token-based authentication.
- **bcrypt**: For password hashing.

### Other
- **Wouter**: Lightweight client-side routing.
- **Replit Integration**: Development tools and error overlays for the Replit environment.
- **ESBuild**: Fast bundling for production.
- **PostCSS**: CSS processing.

## Replit Environment Setup

### Development Mode
- **Frontend**: Vite dev server on 0.0.0.0:5000 with hot reload
- **Backend**: FastAPI on localhost:8000 with auto-reload
- **Workflow**: `npm run dev` runs both frontend and backend concurrently
- **Host Configuration**: Vite configured with `allowedHosts: true` for Replit proxy compatibility

### Architecture Notes
- Chat functionality has been removed to reduce overhead
- The application uses PostgreSQL for all data persistence with Redis for performance optimization
- Redis provides result caching (10 min TTL) and high-performance sorted-set leaderboards
- All SQL query processing is handled synchronously through the secure executor

### Production Deployment (Autoscale)
- **Build**: `npm run build` compiles frontend to `dist/public`
- **Run**: Backend serves both API and built frontend static files on port 8000
- **Configuration**: Set in `.replit` deployment section with autoscale target
- **Static Files**: FastAPI serves built assets from `dist/public` with SPA fallback routing

### Environment Variables
- `DATABASE_URL`: PostgreSQL connection string (auto-configured by Replit)
- `REDIS_URL`: Redis connection string (configured via Replit secret)
- `JWT_SECRET`: Auto-generated in development
- `ADMIN_SECRET_KEY`: Auto-generated in development
- `DEV_TOKEN_BYPASS`: Enabled in development for easier testing
- `DEV_ADMIN_BYPASS`: Enabled in development for admin features

### Key Files
- `vite.config.ts`: Frontend build and dev server configuration
- `api/main.py`: FastAPI application entry point
- `api/database.py`: Database connection and pool configuration
- `api/redis_service.py`: Redis connection and performance optimization service
- `api/secure_execution.py`: Secure SQL query execution system
- `scripts/dev_backend.cjs`: Development backend startup script

## Recent Changes

### September 30, 2025 - Redis Integration for Performance
- **Redis Service**: Created comprehensive Redis service with connection management and fallback mechanisms
- **Result Caching**: Implemented query-hash-based caching for test queries (10 min TTL) to prevent stale results
- **High-Performance Leaderboards**: Replaced database queries with Redis sorted sets for instant leaderboard access
- **Idempotent Operations**: SADD-based solved problem tracking prevents race conditions and double-counting
- **Admin Sync**: Added `/api/admin/sync-leaderboard` endpoint to rebuild Redis data from PostgreSQL
- **Dependencies**: Installed `redis` package for Python Redis client

### September 30, 2025 - Replit Environment Setup & Import Fixes
- **GitHub Import**: Successfully imported and configured project for Replit environment
- **Dependency Fixes**: 
  - Fixed `framer-motion` package resolution issue by reinstalling node_modules
  - Fixed `react-syntax-highlighter` import path issue (changed from `/dist/esm/styles/prism` to `/dist/styles/atom-one-dark`)
- **Workflow Configuration**: Set up "Start application" workflow with webview output on port 5000
- **Redis Worker**: Configured and verified Redis Worker workflow for asynchronous SQL submission processing
- **Deployment Config**: Configured autoscale deployment with build and run commands
- **Python Setup**: Python 3.11 module installed with all required dependencies
- **Verification**: All features tested and working (home page, problems, leaderboard, community)

### Earlier Changes - Architecture Simplification
- **Chat System**: Removed user-to-user messaging, chat components, and related database tables (Conversation, Message)
- **WebSocket**: Removed WebSocket connections previously used for real-time chat

### Impact
- Reduced system complexity and overhead
- Simplified deployment requirements
- All data now persists directly to PostgreSQL
- Frontend chat components removed: ChatPanel, ChatRoom, CommunityChatBox, RecentChats