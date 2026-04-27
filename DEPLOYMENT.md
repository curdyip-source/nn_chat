# myclearproject Deployment

## Production Files

- Development stack: [docker-compose.yml](docker-compose.yml)
- Production stack: [docker-compose.prod.yml](docker-compose.prod.yml)
- Release stack: [docker-compose.release.yml](docker-compose.release.yml)
- Production env template: [.env.production.example](.env.production.example)
- Release env template: [.env.release.example](.env.release.example)

## Prepare Environment

1. Copy [.env.production.example](.env.production.example) to `.env.production`.
2. Set a strong `POSTGRES_PASSWORD`.
3. Set a strong `AUTH_TOKEN_SECRET`.
4. Set explicit `CORS_ALLOW_ORIGINS` domains.
5. Keep `PUBLIC_BOOTSTRAP_ENABLED=false` for production.
6. Run the preflight validation script before the first deploy:

```bash
./ops/preflight_production.sh .env.production
```

The example file is expected to fail preflight until you replace placeholder secrets with real values.

## Start Production Stack

```bash
docker compose \
  --env-file .env.production \
  -f docker-compose.prod.yml \
  up -d --build
```

## Build Tagged Release Images

```bash
./ops/release_build.sh 2026.03.23.1
```

This builds:

- `${BACKEND_IMAGE}:2026.03.23.1`
- `${FRONTEND_IMAGE}:2026.03.23.1`

By default the script uses image names from [.env.release.example](.env.release.example).

## Push Tagged Release Images

```bash
docker login ghcr.io
./ops/release_push.sh .env.release 2026.03.23.1
```

This pushes the already-built tagged images to the registry defined in [.env.release.example](.env.release.example) or `.env.release`.

Before pushing:

1. replace the example image names with your real registry paths
2. make sure the registry repository exists or can be created automatically
3. authenticate with `docker login` for that registry

## Deploy Tagged Release

1. Copy [.env.release.example](.env.release.example) to `.env.release`.
2. Set the real image names if you use a registry.
3. Deploy a specific tag:

```bash
./ops/release_deploy.sh .env.production .env.release 2026.03.23.1
```

This deploys backend and frontend from tagged images through [docker-compose.release.yml](docker-compose.release.yml).

## Full Reset And Clean Release Start

If you want to raise the whole project from scratch with a clean database and create the first administrator through the frontend, use this flow.

1. In `.env.production` or the env file you pass to release compose, set:

```env
PUBLIC_BOOTSTRAP_ENABLED=true
```

2. Fully stop and remove the release stack together with the PostgreSQL volume:

```bash
docker compose \
  --env-file .env.production \
  -f docker-compose.release.yml \
  down -v --remove-orphans
```

3. If you also want to rebuild application images from scratch locally, start with build:

```bash
docker compose \
  --env-file .env.production \
  -f docker-compose.release.yml \
  up -d --build
```

4. Open the frontend and create the first administrator through the bootstrap form. The bootstrap endpoint works only when:

- `PUBLIC_BOOTSTRAP_ENABLED=true`
- the `users` table is empty

5. After the first administrator is created, set `PUBLIC_BOOTSTRAP_ENABLED=false` again and redeploy:

```bash
docker compose \
  --env-file .env.production \
  -f docker-compose.release.yml \
  up -d --build
```

Notes:

- `down -v` removes the named volume `postgres_data`, so the whole database is recreated from zero.
- If you deploy by tagged registry images through your existing release scripts, keep the same idea: first temporarily enable `PUBLIC_BOOTSTRAP_ENABLED=true`, deploy, create the first admin, then switch it back to `false` and redeploy.
- For production internet-facing environments, do not leave bootstrap enabled longer than needed.

## GitHub Release Workflow

There is also a manual workflow for tagged image publication:

- [.github/workflows/release.yml](.github/workflows/release.yml)

It performs:

1. backend and stack validation
2. release image build for backend and frontend
3. registry login
4. tagged image push
5. vulnerability scan for published backend and frontend images

The workflow is designed for registry-backed release tags such as `2026.03.23.1`.
By default it publishes to `ghcr.io/<repository_owner>/myclearproject-backend` and `ghcr.io/<repository_owner>/myclearproject-frontend`.

## Validate Deployment

```bash
curl -fsS http://127.0.0.1:${FRONTEND_PORT}/api/v1/health/live
curl -fsS http://127.0.0.1:${FRONTEND_PORT}/api/v1/health/ready
```

Expected responses:

```json
{"status":"ok"}
{"status":"ok","database":"ok"}
```

For a single-command deployment smoke check, run:

```bash
./ops/post_deploy_check.sh http://127.0.0.1:${FRONTEND_PORT}
```

For a deeper authenticated smoke run against the already deployed backend container, run:

```bash
./ops/post_deploy_api_smoke.sh docker-compose.prod.yml .env.production
./ops/post_deploy_api_smoke.sh docker-compose.release.yml .env.production .env.release
```

The deep smoke script reuses [backend/scripts/api_smoke_test.py](backend/scripts/api_smoke_test.py) and validates auth, sessions, users, documents, and audit flow end-to-end.

## Backup Database

```bash
./ops/backup_postgres.sh .env.production backups/appdb-$(date +%Y%m%d-%H%M%S).sql
```

## Restore Database

```bash
./ops/restore_postgres.sh .env.production backups/appdb-20260323-120000.sql
```

The restore script drops and recreates the public schema before importing the dump. Use it only when you intend to fully replace the current database contents.

## Rollback

Recommended rollback order:

1. Take a fresh backup before touching the database.
2. If the issue is application-only, roll back backend and frontend to the previous known-good images first.
3. Re-run [ops/post_deploy_check.sh](ops/post_deploy_check.sh) against the rolled-back stack.
4. Restore the database only if a schema or data migration caused the incident and backward compatibility is broken.

Recommended commands:

```bash
./ops/backup_postgres.sh .env.production backups/pre-rollback-$(date +%Y%m%d-%H%M%S).sql
./ops/rollback_to_tag.sh .env.production .env.release 2026.03.22.3
./ops/post_deploy_check.sh http://127.0.0.1:${FRONTEND_PORT}
```

## Notes

- In production override, PostgreSQL is not exposed publicly.
- Backend is not bind-mounted in production.
- Frontend is built into an nginx image and proxies `/api/` to backend.
- Frontend also proxies `/media/` to backend so uploaded profile photos are reachable by iOS clients and browsers.
- Production PostgreSQL data is stored in the named volume `postgres_data`.
- Backend refuses to start in production with default token secret or wildcard CORS plus credentials.
- Backend also refuses to start in production with non-https CORS origins, localhost database host, placeholder secrets, or invalid auth TTL ranges.
- Backend emits structured JSON logs with request_id, request metadata, auth events, and optional user_id context.
- Backend supports optional Sentry-based error tracking through `SENTRY_DSN`, `SENTRY_ENVIRONMENT`, and `SENTRY_TRACES_SAMPLE_RATE`.
- Backend can send APNs notifications when `APNS_AUTH_KEY_P8`, `APNS_KEY_ID`, `APNS_TEAM_ID`, `APNS_TOPIC`, and `APNS_USE_SANDBOX` are configured.
- Production stack uses pinned base images for PostgreSQL, nginx, and Python.
- Production stack enables `no-new-privileges` for backend and frontend containers, uses read-only filesystems for app containers, and drops Linux capabilities except the frontend bind capability required for port 80.
- Release stack deploys backend and frontend by explicit image tag for reproducible rollout and rollback.
- CI and release workflows run `pip-audit` for Python dependencies and fail on `HIGH`/`CRITICAL` Trivy findings in backend/frontend images.