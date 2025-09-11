# Overview

SQLGym is a gamified SQL learning platform that combines coding practice with fitness-themed motivation. The application allows users to solve SQL problems, track their progress through an XP system, compete on leaderboards, and participate in a community forum. The platform features a comprehensive problem set with different difficulty levels, submission tracking, and a badge system to reward achievements.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Frontend Architecture
The client uses React with TypeScript, built with Vite for fast development. The UI is constructed with shadcn/ui components and Radix UI primitives, providing a consistent design system with Tailwind CSS for styling. The application uses Wouter for lightweight client-side routing and TanStack Query for server state management and caching. Form handling is implemented with React Hook Form and Zod for validation.

## Backend Architecture
The server is built with Express.js and TypeScript, following a RESTful API pattern. The architecture uses a storage abstraction layer that encapsulates all database operations, making it database-agnostic. JWT tokens handle authentication with bcrypt for password hashing. The server includes middleware for request logging and error handling.

## Database Design
The system uses SQLAlchemy ORM with PostgreSQL as the primary database. The schema includes tables for users, problems, submissions, community posts, post comments, post likes, and user badges. The database supports user progression tracking, problem solving statistics, and social features like community posts and comments.

## Authentication System
Authentication is implemented using JWT tokens stored in localStorage on the client side. The server validates tokens using middleware that checks for Authorization headers. User registration includes password hashing with bcrypt, and the system checks for existing usernames and emails to prevent duplicates.

## Key Features
- **Gamification**: XP system with levels (SQL Beginner, Trainee, Athlete, Powerlifter) and badge rewards
- **Problem Management**: SQL problems categorized by difficulty with hints and expected outputs
- **Code Execution**: SQL query submission and validation system
- **Social Features**: Community posts with likes and comments
- **Progress Tracking**: User submissions history and leaderboards
- **Responsive Design**: Mobile-friendly interface with proper breakpoints

## State Management
Client-side state is managed through TanStack Query for server state and React's built-in state management for UI state. Authentication state is handled through a custom AuthContext provider that persists user sessions in localStorage.

# External Dependencies

## Database Services
- **Neon Database**: PostgreSQL hosting service accessed via @neondatabase/serverless driver
- **SQLAlchemy ORM**: Type-safe database operations with automatic schema migration support

## UI Libraries
- **Radix UI**: Unstyled, accessible UI primitives for complex components
- **shadcn/ui**: Pre-built component library built on Radix UI
- **Tailwind CSS**: Utility-first CSS framework for styling
- **Lucide React**: Icon library for consistent iconography

## Development Tools
- **Vite**: Build tool with hot module replacement for development
- **TypeScript**: Type safety across the entire application
- **TanStack Query**: Server state management and caching
- **React Hook Form**: Form handling with validation
- **Zod**: Schema validation for forms and API data

## Authentication & Security
- **JSON Web Tokens (jsonwebtoken)**: Token-based authentication
- **bcrypt**: Password hashing and verification
- **Wouter**: Lightweight client-side routing

## Development Environment
- **Replit Integration**: Special development tools and error overlays for Replit environment
- **ESBuild**: Fast bundling for production builds
- **PostCSS**: CSS processing with Autoprefixer