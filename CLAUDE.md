# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Hermes Knowledge Base - A FastAPI-based knowledge management system with Agent authentication, task board module, and dual interface (REST API + HTML pages).

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start development server
uvicorn app:app --reload --host 0.0.0.0 --port 8000

# Docker
docker-compose up --build
```

## Architecture

### Layered Structure
```
app/
├── api/          # Routes → Services → Repositories → Models
├── core/         # Config, database, security, storage
├── models/       # SQLAlchemy ORM models
├── repositories/ # Data access layer
├── services/     # Business logic
├── tasks/        # APScheduler background jobs
├── utils/        # Security checks, helpers
├── web/          # Jinja2 templates + page routes
└── modules/
    └── task_board/  # Task board feature module
```

### Dual Interface
- **REST API**: `/api/*` endpoints for agent/client communication
- **Web Pages**: `/*` routes serving Jinja2 HTML templates

### Entry Points
- `app/__init__.py` - `create_app()` factory, route registration
- `app/main.py` - Lifespan events (DB init, scheduler startup)

## Authentication

### Agent Auth (HMAC-SHA256)
Headers required: `x-agent-id`, `x-access-key`, `x-timestamp`, `x-nonce`, `x-content-sha256`, `x-signature`
- Timestamp validation (configurable window, default 300s)
- Nonce tracking prevents replay attacks
- Secret keys encrypted at rest with Fernet

### Admin Auth (JWT)
- JWT tokens in HTTP-only cookies
- Algorithm: HS256, 24h expiry
- Password hashing: werkzeug/bcrypt

## Database

- **Engine**: SQLAlchemy 2.0 + MySQL 8
- **Migrations**: Alembic (versions in `alembic/versions/`)
- **Session**: `get_db()` dependency for injection
- **Config**: Environment-specific `.env` files (`.env.dev`, `.env.local_prod`)

## Storage

`StorageClient` factory supports two backends:
- **LOCAL**: Filesystem at `LOCAL_STORAGE_PATH`
- **MINIO**: S3-compatible object storage

## Key Patterns

1. **Dependency Injection**: `Depends(get_db)`, `Depends(get_current_agent)`
2. **Exceptions**: Use `app.core.exceptions.ResourceNotFoundError`, `PermissionDeniedError`
3. **Enums**: Define in models, import for type hints in schemas
4. **Task Board Module**: `app/modules/task_board/` - models, routers, services, schemas

## Critical Files

| File | Purpose |
|------|---------|
| `app/__init__.py` | App factory, route registration |
| `app/core/config.py` | All settings (DB, storage, security) |
| `app/core/security.py` | HMAC signatures, Fernet encryption |
| `app/api/middleware/auth.py` | Agent HMAC authentication |
| `app/api/middleware/admin_auth.py` | Admin JWT authentication |
| `app/utils/security_check.py` | File upload security validation |

## Environment Config

`app/core/config.py` selects env file by `ENVIRONMENT` var:
- `dev` → `.env.dev`
- `local_prod` → `.env.local_prod`
- default → `.env`
