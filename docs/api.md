# API Usage

All business routes use `/api/v1`. Protected routes require `Authorization: Bearer <access-token>`. Access tokens expire in 20 minutes and have server-side revocation. `POST /api/v1/auth/logout` revokes the current session. Infrastructure endpoints `/health` and `/ready` are outside the business prefix; readiness returns 503 when PostgreSQL is unavailable.

## Implemented routes

- `POST /api/v1/auth/login`, `GET /api/v1/auth/me`, `POST /api/v1/auth/logout`
- `POST /api/v1/auth/password-reset/request`, `POST /api/v1/auth/password-reset/confirm`
- `POST /api/v1/organizations` (platform admin), `GET /api/v1/organizations/{id}`
- `POST /api/v1/organizations/invitations`, `POST /api/v1/organizations/invitations/register`
- `GET /api/v1/users`, `PATCH /api/v1/users/{id}`
- `GET`, `POST`, `PATCH /api/v1/vehicles`; `GET /api/v1/vehicles/{id}`
- `GET`, `POST`, `PATCH /api/v1/drivers`
- `POST /api/v1/assignments`, `POST /api/v1/assignments/{id}/end`
- `GET`, `POST /api/v1/fuel-records`; `GET /api/v1/fuel-records/{id}`
- `POST`, `GET /api/v1/fuel-records/{id}/corrections`
- `POST /api/v1/sync/fuel-records`
- `POST /api/v1/fuel-records/{id}/attachments?kind=RECEIPT|ODOMETER`; attachment download by ID
- `GET /api/v1/analytics/summary`, `GET /api/v1/dashboard/summary`
- `GET /api/v1/alerts`, `PATCH /api/v1/alerts/{id}`
- `GET /api/v1/audit-logs`, `GET /api/v1/reports/fuel-records.csv`

## Fuel and synchronization

The backend calculates `total_amount` using decimal arithmetic and two-place half-up rounding. Currency must match the organization's configured three-letter currency; conversion is not performed. Clients cannot submit totals, receipt timestamps, or sync statuses.

`client_record_id` is unique per organization. An identical retry returns the existing record with status 200 and `Idempotency-Replayed: true`; changed data with the same identifier returns 409. Odometer readings are checked against adjacent event timestamps. Administrators may correct accepted records; correction requests validate values, recalculate totals, retain old/new values, and produce audit events. Ordinary users cannot edit or delete accepted records.

`POST /api/v1/sync/fuel-records` accepts at most 50 records and returns a result for each item: accepted, already accepted, validation rejection, authorization rejection, or safe temporary retry. Upload attachments after the associated fuel record is accepted. Retry with the same client record UUID and identical attachment bytes.

## Analytics and exports

Totals describe recorded purchases. Distance comes from ordered odometer events for the same vehicle with nondecreasing readings. The API does not call purchase litres divided by distance exact consumption. Alerts compare a purchase total with that vehicle's recent median once sufficient history exists; they request human review and do not prove misconduct.

List endpoints use `limit` (maximum 100) and `offset`. Analytics cap inputs at 10,000 records and mark `summary_truncated` if the cap is reached. CSV exports cap at 10,000 rows, require administrator/fleet-manager access, neutralize spreadsheet formula prefixes, and create an audit event.
