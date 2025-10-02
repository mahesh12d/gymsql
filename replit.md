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
- **Social Features**: Community posts with likes and comments, featuring rich text editing with markdown formatting and syntax-highlighted code blocks.
- **Progress Tracking**: User submission history and leaderboards.
- **Responsive Design**: Mobile-friendly interface.
- **Anti-Hardcode Detection**: Three-layer system (static analysis, execution plan analysis, data dependency testing) to prevent hardcoded solutions.
- **Rich Text Editor**: Markdown-based formatting toolbar with syntax-highlighted code blocks for multiple programming languages.

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

### Content Rendering & Editing
- **react-markdown**: Render Markdown content in posts and comments.
- **react-syntax-highlighter**: Syntax highlighting for code blocks.
- **remark-gfm**: GitHub Flavored Markdown support (tables, strikethrough, task lists).
- **CodeMirror**: In-editor syntax highlighting for code blocks with language-specific extensions.

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

### October 2, 2025 - Discussion Comments Visibility Fix
- **Auto-Expand Comments**: Comments now automatically expand when a discussion has existing comments (instead of being hidden by default)
- **Improved Button Labels**: Changed from unlabeled icon+count to clear "View X comments"/"Hide X comments" text with chevron indicators
- **Better Discoverability**: Users can immediately see existing comments without having to guess the toggle button functionality
- **UX Enhancement**: Addresses issue where users couldn't find comments even though count showed "2"
- **Files Modified**: `client/src/components/ProblemTabsContent.tsx`

### October 2, 2025 - Rich Text Editor Formatting Improvements
- **No Placeholder Text**: Removed confusing placeholder text ("bold text", "italic text") when clicking formatting buttons
- **Smart Cursor Positioning**: Cursor now positioned between formatting markers (e.g., between `**` and `**`) for immediate typing
- **Streamlined UX**: Users can click Bold/Italic and start typing immediately without clearing placeholder text
- **Files Modified**: `client/src/components/RichTextEditor.tsx`

### October 2, 2025 - Rich Text Editor for Problem Discussions
- **Inline Discussion Editor**: Replaced dialog-based "New Discussion" button with inline RichTextEditor in problem detail page
- **Consistent UX**: Discussion tab now matches community page design with inline editor at the top
- **Markdown Rendering**: Discussion content now displays with full markdown formatting and syntax highlighting
- **User Experience**: Streamlined workflow - users can start typing discussions immediately without opening a dialog
- **Files Modified**: `client/src/components/ProblemTabsContent.tsx`
- **Components Used**: RichTextEditor and MarkdownRenderer for consistent formatting across the app

### October 2, 2025 - Rich Text Editor for Community Posts and Comments
- **RichTextEditor Component**: Created markdown-based rich text editor with formatting toolbar
- **Toolbar Features**: Bold, Italic, Strikethrough, Inline Code, Code Block, Unordered/Ordered Lists, Blockquotes
- **Code Block Support**: Multi-language syntax highlighting with CodeMirror editor integration
- **Supported Languages**: PostgreSQL, MySQL, JavaScript, Python, Java, C++, and Plain Text
- **Language Mapping**: Each language has unique value (postgres, mysql, javascript, python, java, cpp, text) mapped to correct CodeMirror extensions and SyntaxHighlighter identifiers
- **MarkdownRenderer Component**: Displays formatted markdown content with react-markdown and syntax-highlighted code blocks
- **Integration**: Replaced plain textareas in community posts and comments with rich text editor
- **Storage Format**: Content stored as Markdown for lightweight, backward-compatible storage
- **Dependencies Installed**: `@codemirror/lang-javascript`, `@codemirror/lang-python`, `@codemirror/lang-java`, `@codemirror/lang-cpp`
- **Files Created**: `client/src/components/RichTextEditor.tsx`, `client/src/components/MarkdownRenderer.tsx`, `client/src/components/ui/select.tsx`
- **Files Modified**: `client/src/pages/community.tsx`

### October 1, 2025 - Admin Panel Table Preview: Sample Data Auto-Population with Manual Schema Definition
- **Data Source Workflow Change**: When applying validated datasets to the problem draft, sample data is now auto-populated from the uploaded file while column types are left empty for manual specification
- **Enhanced Visual Feedback**: 
  - Columns with missing types show a red "Type Required" badge
  - Empty type dropdowns are highlighted with orange styling
  - Alert banner notifies admins when column types need to be set
- **Admin Workflow**: 
  1. Upload and validate dataset file (CSV/Parquet) in Data Source tab
  2. Click "Apply to Draft" - sample data is automatically extracted
  3. Navigate to Create Question tab
  4. Edit table to manually set data types for each column
  5. Sample data remains editable throughout
- **Files Modified**: `client/src/contexts/AdminContext.tsx`, `client/src/components/admin/EnhancedTablePreview.tsx`

### October 1, 2025 - Community Page Performance Optimization
- **Post Count Removal**: Removed post count badges from community page filter dropdown to improve performance
- **Resource Optimization**: Eliminated `postCounts` calculation that was computed on every render
- **Impact**: Reduced computational overhead when filtering community posts
- **Files Modified**: `client/src/pages/community.tsx`

### October 1, 2025 - Replit Environment Configuration
- **Workflow Setup**: Configured "Start application" workflow with webview output on port 5000
- **Frontend Configuration**: Verified Vite server properly configured with `allowedHosts: true` for Replit proxy
- **Backend Configuration**: Confirmed FastAPI running on localhost:8000 with proper proxy setup
- **Deployment**: Configured autoscale deployment target with build and run commands
- **Status**: Application fully operational in Replit environment

### October 1, 2025 - Database Schema Cleanup
- **Chat Tables Removal**: Permanently removed all deprecated chat-related database tables to free up space and align backend with current architecture
- **Tables Removed**: chat_messages, chat_participants, chat_rooms, conversations, conversation_participants, messages, user_presence, submission_queue
- **Space Freed**: Approximately 592 kB of database storage
- **Impact**: Cleaner database schema, improved maintainability, reduced backup size
- **Cleanup Script**: Created `scripts/cleanup_chat_tables.sql` for documentation

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