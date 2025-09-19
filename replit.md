## 🚀 ZERO-SETUP IMPORT

This project is 100% ready to run:

1. Dependencies: ✅ Already installed
2. Configuration: ✅ Pre-configured for Replit
3. Database: ✅ Auto-connects
4. Run command: `npm run dev`
5. No agent setup needed - just run!

Overview
SQLGym is a gamified SQL learning platform that combines coding practice with fitness-themed motivation. The application allows users to solve SQL problems, track their progress through an XP system, compete on leaderboards, and participate in a community forum. The platform features a comprehensive problem set with different difficulty levels, submission tracking, and a badge system to reward achievements.

User Preferences
Preferred communication style: Simple, everyday language.

System Architecture
Frontend Architecture
The client uses React with TypeScript, built with Vite for fast development. The UI is constructed with shadcn/ui components and Radix UI primitives, providing a consistent design system with Tailwind CSS for styling. The application uses Wouter for lightweight client-side routing and TanStack Query for server state management and caching. Form handling is implemented with React Hook Form and Zod for validation.

Backend Architecture
The server is built with FastAPI and Python, following a RESTful API pattern. The architecture uses SQLAlchemy ORM with Pydantic schemas for type safety and automatic API documentation. JWT tokens handle authentication with bcrypt for password hashing. The server includes middleware for CORS, request logging, and error handling.

Database Design
The system uses SQLAlchemy ORM with PostgreSQL as the primary database. The schema includes tables for users, problems, submissions, community posts, post comments, post likes, and user badges. The database supports user progression tracking, problem solving statistics, and social features like community posts and comments.

Authentication System
Authentication is implemented using JWT tokens stored in localStorage on the client side. The server validates tokens using middleware that checks for Authorization headers. User registration includes password hashing with bcrypt, and the system checks for existing usernames and emails to prevent duplicates.

**Development Mode**: Authentication is automatically bypassed in development mode (when `import.meta.env.DEV` is true). The app automatically logs in with a fake developer user, eliminating the need to go through the OAuth login flow during development.

Key Features
Gamification: XP system with levels (SQL Beginner, Trainee, Athlete, Powerlifter) and badge rewards
Problem Management: SQL problems categorized by difficulty with hints and expected outputs
Code Execution: SQL query submission and validation system
Social Features: Community posts with likes and comments
Progress Tracking: User submissions history and leaderboards
Responsive Design: Mobile-friendly interface with proper breakpoints
State Management
Client-side state is managed through TanStack Query for server state and React's built-in state management for UI state. Authentication state is handled through a custom AuthContext provider that persists user sessions in localStorage.

External Dependencies
Database Services
Neon Database: PostgreSQL hosting service accessed via @neondatabase/serverless driver
SQLAlchemy ORM: Type-safe database operations with automatic schema migration support
UI Libraries
Radix UI: Unstyled, accessible UI primitives for complex components
shadcn/ui: Pre-built component library built on Radix UI
Tailwind CSS: Utility-first CSS framework for styling
Lucide React: Icon library for consistent iconography
Development Tools
Vite: Build tool with hot module replacement for development
TypeScript: Type safety across the entire application
TanStack Query: Server state management and caching
React Hook Form: Form handling with validation
Zod: Schema validation for forms and API data
Authentication & Security
JSON Web Tokens (jsonwebtoken): Token-based authentication
bcrypt: Password hashing and verification
Wouter: Lightweight client-side routing
Development Environment
Replit Integration: Special development tools and error overlays for Replit environment
ESBuild: Fast bundling for production builds
PostCSS: CSS processing with Autoprefixer
🚀 QUICK SETUP FOR FUTURE IMPORTS (Reduces Agent Usage)
One-Command Setup
For future GitHub imports of this project, run this command to automate everything:

bash scripts/replit-setup.sh && npm run dev
What This Automates
✅ Node.js dependency installation
✅ Python dependency installation
✅ Database connection verification
✅ Environment configuration
✅ Directory creation
✅ Configuration validation
✅ Basic functionality testing
Manual Setup Steps (if needed)
Dependencies: npm install && pip install -r requirements.txt
Database: Ensure DATABASE_URL environment variable is set
Environment: Copy .env.example to .env if needed
Run: npm run dev (starts frontend Vite dev server on :5000 and FastAPI backend on :8000)
Production Deployment
Build: npm run build (builds frontend to dist/public)
Start: npm run start (serves both frontend and backend on port 5000)
Target: Already configured for autoscale deployment
Agent Usage Optimization
This project has comprehensive .replit configuration
All modules, workflows, and integrations pre-configured
Use the setup script for zero-analysis imports
Expert mode enabled for faster agent operations
