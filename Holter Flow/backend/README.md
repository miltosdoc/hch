# Pulsus Holter Tracker - Backend

This backend module is built with FastAPI, SQLAlchemy (Async), and PostgreSQL. 

## Requirements
- Docker
- Docker Compose

## Running Locally

Because the project relies on the asyncpg driver, the easiest way to launch the system without dealing with local C++ toolchains or python versions is simply to use Docker.

From the `Holter Flow` project root directory:

```bash
docker compose up -d --build
```

This will instantiate your core services:
1. **db**: PostgreSQL instance listening on port 5432
2. **redis**: Redis cache system on port 6379
3. **backend**: FastAPI service available at `http://localhost:8000`

## Database Migrations (Alembic)

To initialize the database schema, issue an Alembic migration from **inside** the running Docker container:

1. Create the initial revision based on the models:
```bash
docker compose exec backend alembic revision --autogenerate -m "initial_schema"
```

2. Apply the migration to build all tables in the `pulsus` database:
```bash
docker compose exec backend alembic upgrade head
```

The database models are structured according to the Pulsus Holter Tracking PRD and include all required relationships and enums (devices, patients, exams, and device_events).
