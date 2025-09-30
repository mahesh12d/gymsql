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

### Redis Fallback Mode
Redis is not available in the default Replit environment, so the application automatically uses a fallback mode:
- Chat messages are stored in PostgreSQL instead of Redis
- Real-time updates via WebSocket are disabled (chat still works with polling)
- Problem queue uses database instead of Redis
- All functionality remains available, just without real-time pub/sub features

### Production Deployment (Autoscale)
- **Build**: `npm run build` compiles frontend to `dist/public`
- **Run**: Backend serves both API and built frontend static files on port 8000
- **Configuration**: Set in `.replit` deployment section with autoscale target
- **Static Files**: FastAPI serves built assets from `dist/public` with SPA fallback routing

### Environment Variables
- `DATABASE_URL`: PostgreSQL connection string (auto-configured by Replit)
- `JWT_SECRET`: Auto-generated in development
- `ADMIN_SECRET_KEY`: Auto-generated in development
- `DEV_TOKEN_BYPASS`: Enabled in development for easier testing
- `DEV_ADMIN_BYPASS`: Enabled in development for admin features

### Key Files
- `vite.config.ts`: Frontend build and dev server configuration
- `api/main.py`: FastAPI application entry point
- `api/database.py`: Database connection and pool configuration
- `api/redis_config.py`: Redis configuration with fallback implementation
- `scripts/dev_backend.cjs`: Development backend startup script