# ============================================================
# HCH UNIFIED SYSTEM ARCHITECTURE
# ============================================================
# This document describes the planned unified architecture
# based on user requirements from transcript + codebase audit.
#
# CORE SERVICES:
# 1. Portal (app/) - Main entry point: login, admin, dashboard, scan, stats
# 2. Holter Review (holter-review/) - ECG PDF analysis and report generation
# 3. Holter Tracker (holter-tracker/) - Device management + WebDoc booking sync
# 4. ECG Archive (ecg-archive/) - Archive viewer for ECG PDFs
#
# SHARED INFRASTRUCTURE:
# - PostgreSQL: shared user table for auth, app-specific tables
# - Redis: session store for Flask-Login SSO
# - Nginx: reverse proxy with path-based routing
#
# AUTH FLOW:
# - Users authenticate via Portal /login
# - Session stored in Redis via Flask-Session
# - All apps validate against same user table
# - Admin can manage users from Portal /admin
#
# NAVIGATION:
# - After login → Dashboard with app launcher buttons
# - Each app has: Home → back to dashboard, Logout → back to login
# - Responsive mobile design for all pages
# ============================================================
