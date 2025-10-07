# SQLGym

## Overview
SQLGym is a gamified SQL learning platform designed to teach SQL through coding practice. It combines fitness-themed motivation with an XP system, leaderboards, and a community forum. The platform offers a comprehensive problem set with varying difficulty, submission tracking, and a badge system to provide an engaging and effective learning experience. The business vision is to create a leading interactive platform for SQL education, leveraging gamification to enhance user engagement and retention, and fostering a strong community of learners.

## Recent Changes
- **October 7, 2025**: Fixed submission output display for problems without test cases - (1) Identified that problems with `master_solution` but no explicit test cases were not displaying submission outputs (user_output and expected_output), (2) Enhanced the `_execute_minimal_validation` function in secure_execution.py to check for `master_solution` field and create validation test cases from it automatically, (3) Added logic to execute user queries against master_solution, apply the 6-step validation pipeline, and return properly formatted test results with user_output and expected_output fields, (4) This fix ensures all problems now show submission output comparison in the frontend, regardless of whether they use traditional test_cases or master_solution for validation.
- **October 5, 2025**: Implemented Google and GitHub OAuth authentication - (1) Added OAuth routes using Authlib library for secure third-party authentication, (2) Implemented login flows for both Google and GitHub with `/api/auth/google/login`, `/api/auth/google/callback`, `/api/auth/github/login`, `/api/auth/github/callback` endpoints, (3) Enhanced security by using HttpOnly secure cookies for JWT tokens instead of query parameters to prevent token exposure, (4) Updated authentication middleware to support both Bearer tokens (for API clients) and cookies (for OAuth flows), (5) Added `/api/auth/logout` endpoint to properly clear authentication cookies, (6) OAuth credentials (Client IDs and Secrets) are securely managed via Replit Secrets integration. The User model's existing `google_id`, `github_id`, and `auth_provider` fields support OAuth user management with automatic account creation/merging.
- **October 4, 2025**: Profile page visualization updates - (1) Removed "Your Speed" line chart from Progress Charts section, (2) Replaced ECharts calendar with GitHub-style contribution heatmap using `react-calendar-heatmap` and `react-tooltip` libraries to visualize daily problem-solving activity over the past year with color-coded intensity (5 color scales from empty to high activity), (3) Removed Topic Progress section to streamline the profile page, (4) Removed Recommendations section including learning path suggestions and recommended problems to simplify the user experience, (5) Added GitHub-style heatmap CSS with light/dark mode support.
- **October 2, 2025**: Added helpful resources feature - (1) Created `helpful_links` database table with HelpfulLink model for storing user-shared resources, (2) Implemented API endpoints: GET /api/helpful-links (view all links), POST /api/helpful-links (create link - premium only), DELETE /api/helpful-links/:id (delete link - creator or admin only), (3) Added read-only "Helpful Resources" sidebar to home page displaying recent community-shared links, (4) Added "Share Helpful Resources" management section to profile page where premium users can create and manage their shared links, (5) Non-premium users see a premium feature promotion in the profile section.
- **October 2, 2025**: Enhanced user profiles with professional information - (1) Added LinkedIn URL and company name fields to user profile editing, (2) Updated `/api/user/profile` endpoint to return company_name and linkedin_url, (3) Enhanced UserProfilePopover to display company and LinkedIn information when hovering over followed users, (4) Updated home page to display user's full name (first + last) and company instead of just username, (5) Extended FollowerResponse schema to include company and LinkedIn data for follower/following lists.
- **October 2, 2025**: Fixed hardcoded values in profile page - (1) Backend now returns total user count in the `/api/user/profile` endpoint's performance_stats, (2) Frontend displays dynamic global rank as "#rank / total_users" instead of hardcoded "#rank / 10,000", (3) Verified difficulty breakdown (Easy/Medium/Hard) is correctly calculated from database and displayed in real-time based on solved problems.
- **October 2, 2025**: Profile page dynamic data update - Replaced all hardcoded values in the profile page with dynamic data from the API. Changes include: (1) Fastest solve time now calculated from recent_activity execution_time data with proper null handling, (2) Removed unsupported head-to-head wins section, (3) Replaced hardcoded topic leaderboards with TopicProgressSection using real topic_breakdown data, (4) Made comparison averages dynamic with optional allUsersStats prop and smart defaults. The difficulty breakdown chart properly uses API data and updates in real-time.
- **October 2, 2025**: Database cleanup - Removed unused `problem_schemas` table and ProblemSchema model from the codebase after confirming it was never queried or used in application logic. Confirmed `test_cases` and `execution_results` tables are actively used for problem validation and submission tracking.
- **October 2, 2025**: Added follower feature - Implemented a comprehensive follower system with database table, API endpoints (follow/unfollow, search users, get followers/following lists), and profile page UI integration. This feature will support future recommendation system implementation.
- **October 2, 2025**: Removed friends functionality - Completely removed the friendship system including database model, API endpoints, frontend UI components, and the friends leaderboard feature to simplify the application.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture
### Frontend
The frontend is built with React and TypeScript using Vite. It utilizes `shadcn/ui` and Radix UI for design, styled with Tailwind CSS. Routing is handled by Wouter, server state management by TanStack Query, and form handling/validation by React Hook Form with Zod.

### Backend
The backend is a RESTful API developed with FastAPI and Python. It uses SQLAlchemy ORM with Pydantic for type safety. Authentication is managed via JWT tokens and bcrypt for password hashing. Middleware handles CORS, request logging, and error management.

### Database
PostgreSQL is the primary database, managed via SQLAlchemy ORM. The schema supports users, problems, submissions, community posts, comments, likes, user badges, and follower relationships. Redis is used for performance optimization, including result caching (10 min TTL) and high-performance sorted-set leaderboards. The database connection pool is configured with `pool_size=20` and `max_overflow=10`.

### Authentication System
Authentication supports multiple methods: traditional email/password login with JWT tokens stored in localStorage, and OAuth flows (Google and GitHub) using secure HttpOnly cookies. The server validates tokens from both Authorization headers (Bearer tokens) and cookies through unified middleware. OAuth credentials are managed via Replit Secrets. User registration includes bcrypt password hashing and checks for unique usernames and emails. OAuth users are automatically created or merged with existing accounts based on provider IDs.

### Key Features
-   **Gamification**: XP system with levels and badge rewards.
-   **Problem Management**: Categorized SQL problems with hints and expected outputs.
-   **Code Execution**: SQL query submission and validation with an anti-hardcode detection system (static analysis, execution plan analysis, data dependency testing).
-   **Social Features**: Community posts with likes and comments, featuring a rich text editor with markdown formatting and syntax-highlighted code blocks.
-   **Progress Tracking**: User submission history and leaderboards.
-   **Responsive Design**: Mobile-friendly interface.
-   **Admin Panel**: Allows manual schema definition for problem data.

### State Management
Client-side state uses TanStack Query for server state and React's built-in state for UI. A custom `AuthContext` provider manages authentication state, persisting user sessions in localStorage.

### System Design Choices
-   The application uses PostgreSQL for all data persistence, complemented by Redis for caching and leaderboards.
-   SQL query processing uses a Redis-based job queue with a background worker for asynchronous execution, protecting the API from burst traffic.
-   The architecture has been simplified by removing chat functionality and associated WebSocket connections to reduce complexity and overhead.
-   Friends functionality has been removed to streamline the application and focus on core learning features.

### Required Workflows
Two workflows must run simultaneously for the application to function:
1. **SQLGym Dev Server**: Main application server (API + Frontend)
2. **Redis Worker**: Background worker that processes SQL submission jobs from the Redis queue

## External Dependencies
### Database Services
-   **Neon Database**: PostgreSQL hosting via `@neondatabase/serverless` driver.
-   **SQLAlchemy ORM**: Python SQL toolkit and Object Relational Mapper.
-   **redis**: Python client for Redis.

### UI Libraries
-   **Radix UI**: Unstyled, accessible UI primitives.
-   **shadcn/ui**: Pre-built component library.
-   **Tailwind CSS**: Utility-first CSS framework.
-   **Lucide React**: Icon library.

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