
# Repository Guidelines

## Project Structure & Module Organization
`app/` contains the application code: `api/` for FastAPI routes and schemas, `services/` for business logic, `repositories/` for data access, `models/` for SQLAlchemy models, `core/` for config/database/storage, and `web/` for Jinja templates and static assets. Feature code for the task board lives under `app/modules/task_board/`. Database migrations are in `alembic/versions/`. Tests live in `tests/`. Runtime file storage uses `data/uploads/`, with logs and quarantine data under `data/`.

## Build, Test, and Development Commands
Create an environment and install dependencies with `pip install -r requirements.txt`. Run the API locally with `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`. Start MySQL and the app container with `docker compose up --build`. Apply schema changes with `alembic upgrade head`. Run tests with `pytest tests -q`.

## Coding Style & Naming Conventions
Follow existing Python style: 4-space indentation, type hints where useful, and small service/repository methods with clear responsibilities. Use `snake_case` for modules, functions, and variables; `PascalCase` for classes and Pydantic/SQLAlchemy models; and uppercase for enum members and settings. Keep route handlers thin and move database logic into `repositories/` or feature services. Match the surrounding code before introducing new patterns.

## Testing Guidelines
Tests currently use `pytest`, with simple file-based discovery under `tests/` and names like `test_models.py` or `test_<feature>.py`. Add or update tests whenever model fields, schemas, service behavior, or API contracts change. Prefer focused unit tests close to the changed behavior instead of broad integration coverage unless the change crosses layers.

## Commit & Pull Request Guidelines
Recent history includes merge commits and short experimental messages such as `ceshi`; do not copy that style forward. Prefer concise, imperative commit messages like `add agent registration repository` or `fix task board status validation`. Keep PRs scoped, describe behavior changes, list migration or env impacts, and include screenshots for template or admin-page updates.

## Configuration & Data Notes
Settings are loaded from `.env`, `.env.dev`, or `.env.local_prod` via `app/core/config.py`. Do not commit secrets. If a change affects uploads, storage backends, or allowed file types, note the operational impact in the PR.

## Conservative Refactor Rules
Use a conservative refactor approach for this repository.

### Core Principles
- Do not change existing business behavior, API semantics, auth rules, or database meaning unless the task explicitly requires it.
- Prefer small, incremental refactors over broad rewrites.
- Prefer extracting duplicated logic over redesigning the system.
- Do not introduce complex abstractions or patterns unless they solve an active maintenance problem with clear payoff.

### Layer Boundaries
- `route` should handle request parsing, dependency injection, auth, and response assembly only.
- `service` should own business rules, orchestration, permission checks, and cross-object coordination.
- `repository` should own persistence and query construction.
- `core` should contain reusable infrastructure only, not business decisions.
- Do not move `task_board` business rules into generic services or `core`.

### File Upload And Storage
- Reuse the existing `StorageClient` abstraction. Do not bypass it with module-local disk or MinIO code.
- When multiple modules need upload behavior, extract only the shared infrastructure pieces:
  - upload file reading
  - extension and magic-number validation
  - ZIP safety checks
  - SHA256 generation
  - object key generation
  - storage upload/download wrapping
- Keep business-specific package parsing, attachment persistence rules, and task/material semantics inside their own services.

### Refactor Priorities
- High priority:
  - eliminate duplicated upload and storage logic
  - keep route handlers thin
  - reduce repeated pagination and status-filter boilerplate when safe
- Medium priority:
  - split oversized service methods by responsibility
  - extract repeated response/download helpers
- Low priority:
  - unify parallel utility implementations only after behavior is covered by tests

### Safety Checks
- After each refactor, verify:
  - business behavior is unchanged
  - interface contracts are unchanged
  - auth headers and HMAC signing rules remain intact
  - no unnecessary abstraction was introduced
  - duplication was actually reduced
- If model meaning changes, explicitly state whether an Alembic migration is required. Do not rely on `create_all`.

### Existing Auth Constraints
- Agent API auth headers must remain compatible:
  - `x-agent-id`
  - `x-access-key`
  - `x-timestamp`
  - `x-nonce`
  - `x-content-sha256`
  - `x-signature`
- Admin auth must remain compatible with the current JWT/Cookie flow.
