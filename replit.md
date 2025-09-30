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