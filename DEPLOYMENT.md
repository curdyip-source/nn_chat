# nn_chat Deployment

## Production Layout

- Single stack file: [docker-compose.yml](docker-compose.yml)
- Runtime env template: [.env.example](.env.example)
- Deploy scripts: [ops](ops)
- CI/CD workflow: [.github/workflows/deploy.yml](.github/workflows/deploy.yml)

The server does not build the app. Backend and frontend are built in GitHub Actions, pushed to GHCR, then the VPS only pulls tagged images and starts containers.

## Required Secrets And Files

You need:

1. A real `.env` based on [.env.example](.env.example).
2. The APNS key file `AuthKey_RLV35R5LP5.p8`.
3. SSH access to the VPS.
4. A GHCR token with package read access on the server deploy step.

For your current server shape, `.env` can use:

```env
CORS_ALLOW_ORIGINS=http://147.45.253.161:25256
INSECURE_ALLOW_HTTP_ORIGINS=true
FRONTEND_PORT=25256
APNS_AUTH_KEY_P8=/home/dev/nn_chat/secrets/AuthKey_RLV35R5LP5.p8
```

This keeps the app reachable by IP and port until you move to a domain with HTTPS.

## Local Validation

Validate env:

```bash
bash ./ops/preflight_production.sh .env
```

Render compose config:

```bash
docker compose --env-file .env -f docker-compose.yml config
```

The preflight will fail until the APNS key exists at the path from `APNS_AUTH_KEY_P8`.

## Manual Release Flow

Build images locally:

```bash
bash ./ops/release_build.sh 2026.04.27.1 .env
```

Push images:

```bash
docker login ghcr.io
bash ./ops/release_push.sh .env 2026.04.27.1
```

Deploy a tag on the server or any machine that has `.env` and Docker:

```bash
bash ./ops/release_deploy.sh .env 2026.04.27.1
```

Rollback to an older tag:

```bash
bash ./ops/rollback_to_tag.sh .env 2026.04.26.3
```

## GitHub Actions Deploy Flow

Workflow [deploy.yml](.github/workflows/deploy.yml) runs on pushes to `main`, `master`, and `git-action`, plus manual launch.

Jobs:

1. Run backend tests.
2. Build and push backend and frontend images to GHCR.
3. Upload `docker-compose.yml`, `ops/`, `.env`, and the APNS key to the VPS.
4. Pull the new tag on the server and restart the stack.
5. Run health and deep smoke checks.

Required GitHub repository secrets:

1. `VPS_HOST`
2. `VPS_PORT`
3. `VPS_USER`
4. `VPS_SSH_KEY`
5. `GHCR_USERNAME`
6. `GHCR_TOKEN`
7. `PRODUCTION_ENV_FILE`

The APNS key is not required in GitHub Secrets when the file is already present on the VPS at `/home/dev/nn_chat/secrets/AuthKey_RLV35R5LP5.p8`.

Recommended `PRODUCTION_ENV_FILE` base:

- Copy from [.env.example](.env.example)
- Replace database password and auth secret
- Keep `BACKEND_IMAGE=ghcr.io/curdyip-source/nn_chat-backend`
- Keep `FRONTEND_IMAGE=ghcr.io/curdyip-source/nn_chat-frontend`
- Keep `APNS_AUTH_KEY_P8=/home/dev/nn_chat/secrets/AuthKey_RLV35R5LP5.p8`

The workflow rewrites `RELEASE_TAG` on the server to the current commit SHA before deploy.

## Database Operations

Backup:

```bash
bash ./ops/backup_postgres.sh .env backups/appdb-$(date +%Y%m%d-%H%M%S).sql
```

Restore:

```bash
bash ./ops/restore_postgres.sh .env backups/appdb-20260427-120000.sql
```

## First Bootstrap Run

If the database is empty and you need the first administrator:

1. Set `PUBLIC_BOOTSTRAP_ENABLED=true` in `.env`.
2. Deploy once.
3. Create the first admin.
4. Set `PUBLIC_BOOTSTRAP_ENABLED=false`.
5. Deploy again.

Do not leave bootstrap enabled in public production longer than necessary.