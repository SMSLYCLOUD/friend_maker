# Production Readiness Review (April 14, 2026)

## Executive Summary
- The app has a solid MVP skeleton (FastAPI backend, Next.js frontend, Rust service, Docker Compose orchestration).
- It is **not yet production-ready** without additional security, reliability, and operational hardening.
- I implemented a small hardening pass in this review cycle:
  - env-driven config loading,
  - safer CORS defaults,
  - readiness/liveness endpoints,
  - SQLite path normalization + WAL/timeout pragmas,
  - timeout + proper 503 propagation for Rust service failures.

## What Was Improved in This Pass

### 1) Configuration hygiene
- `web/app/config.py` now reads key settings from environment variables instead of fixed constants.
- Added support for:
  - `CORS_ALLOWED_ORIGINS`
  - `DATABASE_URL`
  - `RUST_SERVICE_URL`
  - `RUST_SERVICE_TIMEOUT_SECONDS`

### 2) Database resilience
- `web/app/database/connection.py` now resolves SQLite DB path from `DATABASE_URL` (`sqlite:///...`) with fallback to `data/social_growth.db`.
- Added:
  - `timeout=30` for lock contention,
  - `PRAGMA journal_mode=WAL`,
  - `PRAGMA synchronous=NORMAL`,
  - `PRAGMA foreign_keys=ON`.

### 3) API hardening
- `web/app/main.py` CORS moved from permissive wildcard to env-driven allowlist.
- Added health probes:
  - `GET /health/live`
  - `GET /health/ready` (DB check)
- `POST /api/optimize` now:
  - uses timeout for Rust-service calls,
  - raises `503` when upstream is unavailable instead of returning a success-like JSON envelope.

## Remaining Production Gaps (High Priority)

1. **Authentication & Authorization**
   - No API auth for account/campaign endpoints.
   - No tenant isolation / RBAC.

2. **Secrets Management**
   - Encryption key and API keys are not clearly managed via secret manager/KMS.
   - Need rotation strategy + startup validation for required secrets.

3. **Observability**
   - No structured logging (JSON), request IDs, or centralized log shipping.
   - No metrics/tracing (Prometheus/OpenTelemetry).

4. **Background Work Reliability**
   - In-memory scheduler task registry is not resilient to process restarts.
   - Consider durable job queue (RQ/Celery/Arq/Temporal/etc.) + idempotency keys.

5. **API Contract & Validation**
   - Platform/campaign enums should be constrained via typed models.
   - Add explicit error models and consistent response schema.

6. **Data Layer Limits**
   - SQLite is acceptable for local/small deployments but not ideal for multi-instance scale.
   - Plan migration path to PostgreSQL for production workloads.

7. **Security Baselines**
   - Add rate limiting and abuse controls.
   - Add stricter CORS deployment defaults per environment.
   - Add dependency/SAST/container scanning in CI.

8. **Deployment & Ops**
   - Compose is fine for development; production needs orchestration, probes, and rollout strategy.
   - Add runbooks, SLOs, and backup/restore drills.

## Suggested Next Sprint (Practical)
1. Implement JWT auth and tenant scoping for all `/api/*` routes.
2. Add structured logging and request correlation IDs.
3. Add CI pipeline gates:
   - unit tests,
   - lint/type checks,
   - dependency vulnerability scan.
4. Introduce PostgreSQL compatibility layer and migration plan.
5. Move scheduler execution to a durable worker queue.
