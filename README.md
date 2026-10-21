# FleetFuel

FleetFuel is a multi-organization backend for recording fleet fuel purchases and supporting accountable human review. A purchase is an observed event: litres purchased are not treated as litres consumed, and alerts are not proof of theft or misconduct.

## Requirements

- Python 3.14
- PostgreSQL 17 for deployed use
- Docker Compose for the local PostgreSQL/API stack, or a separately managed PostgreSQL service

Dependency versions are pinned in `requirements.txt`. Ruff 0.11.5 is pinned for the available Python 3.14 environment; its syntax target is `py313` because this Ruff version does not recognize `py314`.

## Local setup

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Generate a secret with `python -c "import secrets; print(secrets.token_urlsafe(48))"`. Set `POSTGRES_PASSWORD` and `FLEETFUEL_JWT_SECRET` in the shell and start the local services with `docker compose up --build -d`. Apply migrations with `docker compose exec api alembic upgrade head`. The API serves on port 8000; development OpenAPI is at `/docs`.

For a separately managed database, set `FLEETFUEL_DATABASE_URL` to a SQLAlchemy URL such as `postgresql+psycopg://user:password@host:5432/fleetfuel` and `FLEETFUEL_JWT_SECRET` to a random value of at least 32 characters in production. Never commit `.env` or production credentials.

Run locally with `uvicorn app.main:app --reload`, tests with `python -m pytest`, lint with `ruff check .`, and formatting with `ruff format .`.

## First administrator

Run migrations first. To bootstrap a platform administrator, set `FLEETFUEL_BOOTSTRAP_ADMIN_EMAIL` and `FLEETFUEL_BOOTSTRAP_ADMIN_PASSWORD` (12+ characters), then run `python -m app.cli bootstrap-super-admin`. The platform administrator creates organizations through `POST /api/v1/organizations`. Organization admins issue one-time invitations through `POST /api/v1/organizations/invitations`; deliver the returned token securely. Invitation email delivery is not implemented. For a directly bootstrapped organization administrator, also set `FLEETFUEL_BOOTSTRAP_ORGANIZATION` and `FLEETFUEL_BOOTSTRAP_CURRENCY`, then run `python -m app.cli bootstrap-admin`.

Password reset requires SMTP configuration via `FLEETFUEL_MAIL_HOST`, `FLEETFUEL_MAIL_PORT`, `FLEETFUEL_MAIL_USERNAME`, `FLEETFUEL_MAIL_PASSWORD`, `FLEETFUEL_MAIL_FROM`, and `FLEETFUEL_PASSWORD_RESET_URL`. Without SMTP, reset requests remain non-enumerating but no email can be delivered.

## API and operations

Business routes use `/api/v1`; infrastructure routes are `/health` and database-dependent `/ready`. See [docs/api.md](docs/api.md), [docs/architecture.md](docs/architecture.md), and [docs/deployment.md](docs/deployment.md). Database changes use `alembic upgrade head`; never use `create_all` as a deployed migration strategy.

HTTP behavior tests use isolated SQLite databases for fast deterministic coverage. They do not replace PostgreSQL integration tests. GitHub Actions is configured to start PostgreSQL, apply migrations, and run tests; this workflow was not run locally because Docker is unavailable in the current environment.

Local attachments use private filesystem storage. Production requires durable private object storage or a persistent encrypted volume with backups; do not use an ephemeral filesystem. See [TASKS.md](TASKS.md) for implementation and verification status. This is an initial backend foundation, not a claim of full security or production certification.
