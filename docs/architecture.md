# Architecture

## Runtime and boundaries

FastAPI mounts infrastructure liveness/readiness routes at `/health` and `/ready`; business routes are under `/api/v1`. Endpoint modules handle HTTP validation and authorization, Pydantic schemas define public contracts, service modules own fuel calculations/storage/audit decisions, and SQLAlchemy models define relational constraints. `pydantic-settings` loads environment-specific settings. Production startup rejects missing database/signing configuration and disables OpenAPI.

## Persistence and tenancy

PostgreSQL is the deployment database. Alembic revisions are the schema authority. Organization IDs are derived from the authenticated principal, used in resource queries, and reinforced by composite foreign keys for fuel records, assignments, attachments, alerts, and corrections. Active vehicle/driver assignments are unique. The local test suite defaults to isolated SQLite; PostgreSQL test runs require an explicit database name ending in `_test` and use transaction rollback.

## Identity and authorization

Passwords use Argon2id. Access tokens are short-lived JWTs with issuer/audience checks and a persistent session row for logout, account deactivation, reset, and tenant-suspension revocation. Organization onboarding is invite-only; a CLI bootstraps platform or organization administrators. Organization roles are checked at endpoint boundaries and drivers are additionally constrained to their linked profile and active vehicle assignment.

## Fuel and sync semantics

Fuel records represent purchase observations. The backend calculates totals with `Decimal`, preserves UTC event and receipt times separately, validates odometer order, and enforces organization-scoped client UUID idempotency. Ordinary accepted records are not editable; organization-admin corrections preserve old/new values and recalculate totals. Offline sync reports per-record outcomes. Attachments use private local storage with signatures, image decoding, size/pixel limits, generated keys, checksums, and content-based retry idempotency.

## Analytics and audit

Analytics report purchase totals and odometer distances only. A configurable vehicle-specific median rule creates review alerts; alerts are explicitly not proof of consumption or misconduct. Sensitive mutations, authentication, exports, and review decisions create audit events with correlation IDs. CSV exports are bounded and neutralize formula prefixes.

## Deployment boundaries

The included local storage adapter is not a cloud object-storage integration. SMTP is an optional reset-delivery boundary; invitation delivery is manual. The deployment guide requires ingress TLS, security headers, request limits, trusted proxy configuration, durable attachments, and backups. PostgreSQL CI is configured, but this local Windows environment lacked a Docker CLI, so no local PostgreSQL run was performed.
