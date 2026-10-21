# FleetFuel Backend Tasks

## Status

- [x] Inspect the empty project and available Python runtime.
- [x] Phase 1: FastAPI app, environment settings, liveness/readiness, tests, and run instructions.
- [x] Phase 2: SQLAlchemy database layer, PostgreSQL configuration, domain models, and Alembic migrations.
- [x] Phase 3: Password/JWT auth, organization onboarding/invitations, roles, and tested tenant isolation.
- [x] Phase 4: Organization-scoped vehicle/driver CRUD slices and exclusive assignments.
- [x] Phase 5: Validated decimal fuel records, idempotency, immutable ordinary access, and audited corrections.
- [x] Phase 6: Batch sync with partial results and private, signature-checked image attachments.
- [x] Phase 7: Purchase summaries, odometer intervals, dashboard, and explainable vehicle-history alerts.
- [x] Phase 8: Bounded CSV exports, spreadsheet formula defense, and audit-log reads.
- [ ] Phase 9: Verify PostgreSQL integration locally; complete production storage/proxy hardening and release review.

## Current milestone

Backend implementation slices are complete through reporting and audit APIs. The remaining gate is real PostgreSQL CI execution plus deployment-specific storage, proxy, and security review.

## Verification and known limitations

- Final local checks: `25 passed`, Ruff clean, and Alembic reports no metadata drift.
- SQLite behavior tests pass locally; SQLite is not considered PostgreSQL integration coverage.
- Alembic revisions were generated and applied locally against SQLite. PostgreSQL migration execution is configured in GitHub Actions but was not run locally because Docker is unavailable.
- SMTP is required for password reset delivery. Invitation delivery is a documented manual secure handoff.
- Attachments use a private local filesystem adapter; production object storage is not configured.
- Google OAuth, distributed edge rate limiting, and production security-header configuration are not included.
- Review `docs/deployment.md` before exposing the API publicly.
