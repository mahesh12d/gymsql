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

## Recent Changes
- **September 25, 2025**: ✅ **Successful Replit Import Setup Complete**
  - **Project Type**: Fullstack SQL Learning Platform (SQLGym) - React frontend + Python FastAPI backend
  - **Frontend**: React + Vite running on port 5000 with proper 0.0.0.0 host configuration for Replit proxy
  - **Backend**: Python FastAPI running on port 8000 with auto-installed dependencies (uvicorn, fastapi, etc.)
  - **Bug Fix**: Resolved JavaScript error in SolutionsTab component - fixed undefined .trim() calls with proper null checking
  - **Workflow**: Configured with webview output type for port 5000 frontend preview
  - **Deployment**: ✅ Configured for autoscale deployment (build: npm run build, run: python uvicorn on port 5000)
  - **Status**: ✅ **Fully operational** - API endpoints working, no console errors, hot reload functioning
- **September 24, 2025**: Fixed s3_datasets query failure issue with partial success support
  - **Issue**: "Query failed" errors when users tried to query tables (e.g., `SELECT * FROM s1`) from problems using s3_datasets configuration  
    - **Root Cause**: s3_datasets had all-or-nothing behavior - if ANY single dataset failed to load, the entire sandbox setup would fail and no tables would be created
    - **Problem**: Users couldn't query any tables, even ones that should have loaded successfully, because the sandbox setup aborted completely on first dataset error
    - **Fix**: Implemented partial success support in `api/duckdb_sandbox.py` setup_problem_data method for s3_datasets processing
    - **Solution**: Added per-dataset error tracking, continue-on-failure behavior, and three outcome paths (complete success, partial success, complete failure)
    - **Impact**: ✅ Users can now query tables that load successfully even if other datasets in the same problem fail
  - **Technical Details**: Enhanced error handling with structured error responses, improved logging with exc_info=True, and consolidated error reporting
  - **Status**: ✅ s3_datasets now works reliably with same robustness as s3_data_source (legacy single-table support)
- **September 23, 2025**: Fixed critical admin panel JSON parsing error during question creation
  - **Issue**: "Failed to execute 'json' on 'Response': Unexpected token 'I'" error when creating questions
    - **Root Cause**: `TypeError: 'solution_source' is an invalid keyword argument for Problem` causing 500 errors
    - **Problem**: Backend returned HTML error pages instead of JSON, causing frontend parsing failures
    - **Fix**: Removed invalid `solution_source` and `s3_solution_source` parameters from Problem constructor in `admin_routes.py`
    - **Solution**: Problem model doesn't have these fields; removed lines 469-470 from create_problem function
    - **Impact**: ✅ Admin panel now works correctly, returns proper JSON responses, 200 OK status codes
  - **Verification**: Successfully created test problem with proper authentication using Bearer token
  - **Status**: ✅ Admin panel problem creation fully functional
- **September 21, 2025**: Successfully completed GitHub import and resolved critical encoding issues
  - **Issue**: UnicodeDecodeError causing JSON parsing failures in sandbox API routes
    - **Root Cause**: UTF-8 encoding errors when processing query results containing non-UTF-8 characters (byte 0xa0)
    - **Fix**: Enhanced `sanitize_json_data` function in `secure_execution.py` to handle string encoding issues
    - **Solution**: Added UTF-8 validation, multi-encoding fallback support, and proper bytes-to-string conversion
    - **Impact**: All API endpoints now working correctly, sandbox queries execute successfully
  - **Workflow Configuration**: Fixed workflow setup with proper webview output type for port 5000
  - **Application Status**: ✅ Running correctly - Frontend on port 5000, Backend on port 8000, Database connected
  - **Multi-table Support**: All previous multi-table question creation issues resolved with encoding fixes
- **September 20, 2025**: Initial GitHub project import with basic Replit environment configuration
- **Deployment**: ✅ Configured for autoscale deployment
- **Workflows**: ✅ Configured with webview output for frontend development

## Known Issues
### Resolved ✅: Multi-table Dataset Validation (September 21, 2025)
- **Status**: Fixed - All encoding and parquet solution issues resolved
- **Previous Issues**: UTF-8 decoding errors, missing methods, parquet solution support
- **Current Status**: Multi-table question creation fully functional

### Critical: "kumbhar" Question Data Mismatch  
- **Problem ID**: `30ff47d8-e9a6-4b13-810d-cbea2915d73d`
- **Issue**: Question asks for "sales data analysis by region" but dataset is Titanic passenger data
- **Impact**: All user submissions fail validation regardless of correctness
- **Root Cause**: Question description and expected output don't match the actual loaded dataset
- **Fix Required**: Either update question to match Titanic data OR load correct sales dataset

### Anti-Hardcode Detection System: Foundation Complete ✅ (September 22, 2025)
- **Problem**: Students could cheat by hardcoding expected values (e.g., `SELECT 355 as "sum(passanger)"`) instead of writing proper analytical SQL
- **Solution**: Implemented comprehensive three-layer defense system:
  - **Layer 1 - Static Analysis**: Detects constant-only queries, validates table/column references
  - **Layer 2 - Execution Plan Analysis**: Uses DuckDB EXPLAIN to verify actual data scanning  
  - **Layer 3 - Data Dependency Testing**: Creates dataset variants to catch hardcoded results
- **Status**: Core components implemented in `api/query_validator.py` and `api/duckdb_sandbox.py`
- **Integration Needed**: Coordinate layers in SecureQueryExecutor pipeline with time budgets and JSON plan parsing
- **Impact**: Major advancement in educational SQL platform integrity
