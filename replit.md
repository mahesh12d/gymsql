# SQLGym

## Overview
SQLGym is a gamified SQL learning platform designed to teach SQL through coding practice. It combines fitness-themed motivation with an XP system, leaderboards, and a community forum. The platform offers a comprehensive problem set with varying difficulty, submission tracking, and a badge system to provide an engaging and effective learning experience. The business vision is to create a leading interactive platform for SQL education, leveraging gamification to enhance user engagement and retention, and fostering a strong community of learners.

## Recent Changes
- **October 2, 2025**: Removed friends functionality - Completely removed the friendship system including database model, API endpoints, frontend UI components, and the friends leaderboard feature to simplify the application.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture
### Frontend
The frontend is built with React and TypeScript using Vite. It utilizes `shadcn/ui` and Radix UI for design, styled with Tailwind CSS. Routing is handled by Wouter, server state management by TanStack Query, and form handling/validation by React Hook Form with Zod.

### Backend
The backend is a RESTful API developed with FastAPI and Python. It uses SQLAlchemy ORM with Pydantic for type safety. Authentication is managed via JWT tokens and bcrypt for password hashing. Middleware handles CORS, request logging, and error management.

### Database
PostgreSQL is the primary database, managed via SQLAlchemy ORM. The schema supports users, problems, submissions, community posts, comments, likes, and user badges. Redis is used for performance optimization, including result caching (10 min TTL) and high-performance sorted-set leaderboards. The database connection pool is configured with `pool_size=20` and `max_overflow=10`.

### Authentication System
Authentication uses JWT tokens stored in localStorage. The server validates tokens through middleware. User registration includes bcrypt password hashing and checks for unique usernames and emails.

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
-   All SQL query processing is handled synchronously through a secure executor.
-   The architecture has been simplified by removing chat functionality and associated WebSocket connections to reduce complexity and overhead.
-   Friends functionality has been removed to streamline the application and focus on core learning features.

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

### Content Rendering & Editing
-   **react-markdown**: Renders Markdown content.
-   **react-syntax-highlighter**: Syntax highlighting for code blocks.
-   **remark-gfm**: GitHub Flavored Markdown support.
-   **CodeMirror**: In-editor syntax highlighting for code blocks.

### Other
-   **Wouter**: Lightweight client-side routing.