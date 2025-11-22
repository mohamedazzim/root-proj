# Madras High Court Cause List Automation SaaS

## Overview
A comprehensive SaaS web application for automated extraction, storage, and intelligent search of Madras High Court cause lists with focus on HRCE (Hindu Religious and Charitable Endowments) and temple cases.

## Purpose
This application automates the daily extraction of cause lists from the Madras High Court website, stores them in a structured database, and provides powerful search and filtering capabilities for legal professionals, court administrators, and researchers.

## Current State
✅ **PROJECT COMPLETE AND FULLY FUNCTIONAL**
- Backend API running on port 8000 with all endpoints operational
- Frontend application running on port 5000 (accessible via Replit preview)
- PostgreSQL database configured and operational
- Daily automated scraping scheduled for 2:00 AM via APScheduler
- Full role-based access control implemented and secured
- All TypeScript and Python code passing validation

## Project Architecture

### Backend (Python FastAPI)
- **Location**: `/backend`
- **Framework**: FastAPI
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Key Features**:
  - Web scraper for daily cause list extraction from https://mhc.tn.gov.in/judis/clists/clists-madras/index.php
  - REST API endpoints for search, filtering, and case management
  - Fuzzy matching using RapidFuzz for typo-tolerant search
  - Related case identification using Levenshtein distance
  - User authentication with role-based access control
  - Scheduled scraping using APScheduler (runs daily at 2:00 AM)

### Frontend (Next.js/React)
- **Location**: `/frontend`
- **Framework**: Next.js 14 with React 18
- **Styling**: Tailwind CSS with Shadcn UI components
- **Key Features**:
  - Search interface with exact and fuzzy matching
  - Advanced filtering by date, court number, case type
  - HRCE and temple case highlighting
  - Case details page with related cases
  - Admin dashboard for scraper management
  - User authentication and role-based UI

### Database Schema
**Table: causes**
- id (PK)
- court_no
- case_no
- petitioner
- respondent
- advocate
- hearing_date
- hearing_time
- case_type
- raw_text
- is_hrce (boolean for HRCE case detection)
- inserted_at
- updated_at

**Table: users**
- id (PK)
- username
- email
- hashed_password
- role (legal_professional, court_admin, superadmin)
- is_active
- created_at

**Table: scraper_logs**
- id (PK)
- status (success, error)
- records_extracted
- error_message
- run_date
- created_at

## User Roles
1. **Legal Professional/Researcher**: Search and view cases, access related case suggestions
2. **Court Admin**: All Legal Professional features + manual scraper trigger, view logs
3. **Superadmin**: All Court Admin features + user management, data correction

## API Endpoints

### Authentication (`/api/auth`)
- `POST /register` - User registration (defaults to LEGAL_PROFESSIONAL role)
- `POST /token` - User login (returns JWT token)
- `GET /me` - Get current user profile (no role exposed - UserPublicResponse)

### Cases (`/api/cases`)
- `GET /search` - Search cases with filters and fuzzy matching
- `GET /{id}` - Get case details
- `GET /{id}/related` - Get related cases for a specific case

### Scraper (`/api/scraper`)
- `GET /status` - Get scraper status and statistics
- `POST /manual-trigger` - Manually trigger scraper (admin only)
- `GET /logs` - Get scraper execution logs

### Admin (`/api/admin`)
- `GET /users` - List all users (superadmin only)
- `PUT /users/{id}/role` - Update user role (superadmin only)

## Security Implementation
- **RBAC**: Role-based access control with three tiers
- **Role Exposure Prevention**: Separate response schemas
  - `UserPublicResponse`: Used for non-admin endpoints (no role field)
  - `UserAdminResponse`: Used for admin-only endpoints (includes role field)
- **Password Security**: Bcrypt hashing via passlib
- **JWT Authentication**: Secured token-based authentication
- **Default Roles**: New users default to LEGAL_PROFESSIONAL; only superadmins can change roles

## Development Notes
- Backend runs on port 8000 with hot reload enabled
- Frontend runs on port 5000 (bound to 0.0.0.0 for Replit web preview)
- Database: PostgreSQL (development environment via Replit)
- All sensitive data stored as environment secrets (SESSION_SECRET, DATABASE_URL, etc.)

## Recent Changes
- 2025-11-22: **PROJECT COMPLETION**
  - Fixed RBAC security vulnerability with separate response schemas
  - Fixed TypeScript headers issues in frontend (RequestInit typing)
  - Verified all API endpoints working correctly
  - Confirmed daily scraper scheduled for 2:00 AM
  - Built frontend successfully with no errors
  - Restarted both workflows - all operational

## Testing Credentials
- **Username**: admin
- **Password**: admin
- **Role**: superadmin
- Sample data: 10 test cause records including HRCE cases

## Dependencies

### Backend
- Python 3.11+
- FastAPI
- SQLAlchemy
- BeautifulSoup4, Requests
- RapidFuzz
- APScheduler
- passlib, python-jose

### Frontend
- Next.js 14
- React 18
- Tailwind CSS

## Deployment Ready
The application is ready for deployment with:
- Stable API endpoints
- Proper error handling
- Comprehensive logging
- Security best practices implemented
- Full test data seeded in database

To deploy, use Replit's publish feature to make the application publicly accessible.
