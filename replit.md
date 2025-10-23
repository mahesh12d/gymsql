# SQLGym

## Overview
SQLGym is a gamified SQL learning platform designed to teach SQL through coding practice. It features an XP system, leaderboards, and a community forum to provide an engaging and effective learning experience. The platform offers a comprehensive problem set with varying difficulty, submission tracking, and a badge system. The business vision is to create a leading interactive platform for SQL education, leveraging gamification to enhance user engagement and retention.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture
### Frontend
The frontend uses React, TypeScript, and Vite, styled with Tailwind CSS. It leverages `shadcn/ui` and Radix UI for components, Wouter for routing, TanStack Query for server state, and React Hook Form with Zod for forms.

### Backend
The backend is a FastAPI-based RESTful API in Python, using SQLAlchemy ORM with Pydantic. Authentication relies on JWT tokens and bcrypt. Middleware handles CORS, logging, and error management.

### Database
PostgreSQL is the primary database, managed via SQLAlchemy. Redis is used for result caching (10 min TTL) and high-performance sorted-set leaderboards. A 6-month data retention policy is in place for execution results.

### Authentication System
Supports email/password login with JWT, and OAuth for Google and GitHub using HttpOnly cookies. Admin access uses a simplified single-key authentication system - no user login required. The admin panel authenticates directly using only the `ADMIN_SECRET_KEY` via the `X-Admin-Key` header. Security features including rate limiting (5 attempts/hour), audit logging, IP lockout, and optional IP whitelisting remain fully functional with graceful degradation in development (when database security tables don't exist). The backend auto-provisions a single admin user when a valid key is provided.

**Security Status (October 23, 2025):**
- ✅ Production-ready: All development authentication bypasses removed
- ✅ Graceful degradation: Security features work in dev mode without database tables
- ✅ Zero bypass mechanisms: DEV_ADMIN_BYPASS and DEV_TOKEN_BYPASS completely removed
- ✅ Secure authentication: ADMIN_SECRET_KEY required for all admin operations

### Key Features
-   **Gamification**: XP system, levels, badge rewards, and contribution heatmap.
-   **Problem Management**: Categorized SQL problems with hints and expected outputs.
-   **Code Execution**: SQL query submission and validation with anti-hardcode detection.
-   **AI-Powered Hints**: Google Gemini provides intelligent hints for failed submissions (rate-limited).
-   **Social Features**: Community posts with rich text editing, follower system, and helpful resource sharing.
-   **Progress Tracking**: User submission history, leaderboards, and profile statistics.
-   **Admin Panel**: Restricted access for manual schema definition for problem data.

### System Design Choices
-   PostgreSQL for persistence, Redis for caching and leaderboards.
-   SQL query processing uses a Redis-based job queue with a background worker for asynchronous execution.
-   A Redis fallback mechanism (to PostgreSQL) and worker availability detection ensure data integrity and system stability.
-   Email addresses are kept confidential; only usernames are displayed publicly.
-   Simplified architecture by removing chat and friends functionality.

### Required Workflows
1.  **SQLGym Dev Server**: Main application server (API + Frontend).
2.  **Redis Worker**: Background worker for processing SQL submission jobs.

## External Dependencies
### Database Services
-   **Neon Database**: PostgreSQL hosting.
-   **SQLAlchemy ORM**: Python SQL toolkit.
-   **redis**: Python client for Redis.

### UI Libraries
-   **Radix UI**: Unstyled, accessible UI primitives.
-   **shadcn/ui**: Pre-built component library.
-   **Tailwind CSS**: Utility-first CSS framework.
-   **Lucide React**: Icon library.
-   **react-calendar-heatmap**: Contribution heatmap.

### Development Tools
-   **Vite**: Fast build tool.
-   **TypeScript**: Typed JavaScript superset.
-   **TanStack Query**: Server state management.
-   **React Hook Form**: Form handling.
-   **Zod**: Schema validation.

### Authentication & Security
-   **jsonwebtoken**: Token-based authentication.
-   **bcrypt**: Password hashing.
-   **Authlib**: OAuth 2.0 client for Google and GitHub.
-   **httpx**: Async HTTP client.
-   **itsdangerous**: Session data signing.

### Content Rendering & Editing
-   **react-markdown**: Renders Markdown.
-   **react-syntax-highlighter**: Syntax highlighting.
-   **remark-gfm**: GitHub Flavored Markdown.
-   **CodeMirror**: In-editor syntax highlighting.

### AI & Machine Learning
-   **Google Gemini**: AI model for educational hints.

### Other
-   **Wouter**: Lightweight client-side routing.