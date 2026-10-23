# Deployment Guide

## Required configuration

- `FLEETFUEL_ENVIRONMENT=production`
- `FLEETFUEL_DATABASE_URL` with the `postgresql+psycopg` driver
- `FLEETFUEL_JWT_SECRET` with at least 32 unpredictable characters
- Explicit browser origins in `FLEETFUEL_CORS_ORIGINS`
- Durable private attachment storage
- SMTP settings and a client reset URL if password reset is enabled

Production settings fail fast without the database URL and signing secret. OpenAPI documentation is disabled in production by default and can be enabled explicitly with `FLEETFUEL_ENABLE_DOCS=true` when the API schema should be publicly available. Keep credentials in the hosting platform's secret manager, not in source or container build arguments.

## Release operations

The container startup command runs `alembic upgrade head` before starting the API, and `/ready` checks database connectivity. Review generated revisions and take a tested backup before deploying schema changes. Do not use metadata `create_all` as a deployed migration strategy.

The Render Blueprint bootstraps the first platform administrator using the configured email and a Render-generated password. Retrieve that password from the service's Environment settings and store it securely. Bootstrap is idempotent for the configured account on later restarts; it fails if a different platform administrator already exists.

The Blueprint also builds and hosts the Flutter web client at `https://fleetfuel-web.onrender.com`, configured to call the API at `https://fleetfuel-api.onrender.com/api/v1`. Its origin is the only browser origin allowed by the API CORS policy.

The Render Blueprint uses free plans for a demo. Render free web services have ephemeral filesystems and spin down when idle; free PostgreSQL databases expire after 30 days. Uploaded attachments are stored on the web service filesystem and can be lost at any restart or spin-down. Do not use this configuration for production or real customer data. Upgrade to paid persistent resources and configure durable private attachment storage before production use.

Terminate TLS at a trusted ingress, restrict database network access, configure explicit CORS, set request/body limits and distributed rate limits at the proxy, and add security headers there. The application login limiter is database-backed and keyed on the direct client address plus normalized email. Do not trust arbitrary forwarded headers; configure trusted-proxy behavior and edge throttling deliberately.

Compose uses named PostgreSQL and attachment volumes for local persistence. Single-host volumes are not backups. Use encrypted scheduled or point-in-time database backups, preserve attachment objects on the same lifecycle, and regularly test restoration. Monitor readiness, DB connections, failed logins, disk, migrations, and attachment storage.

Logs include validated request IDs and exclude passwords, bearer/reset tokens, and image bytes. Audit events are append-only through the application API; production operators must separately restrict direct database mutation privileges.

## Known deployment limitations

The Docker CLI is unavailable in the local environment, so PostgreSQL Compose startup and the PostgreSQL CI workflow were not run here. GitHub Actions is configured to run migrations and tests against PostgreSQL. Attachments currently use private local filesystem storage; no cloud object-storage provider is configured. Invitation email and Google OAuth are not implemented. Password reset requires SMTP credentials. Review these assumptions before public deployment.