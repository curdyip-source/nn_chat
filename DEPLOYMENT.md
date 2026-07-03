# nn_chat Deployment

## Production Layout

- Single stack file: [docker-compose.prod.yml](docker-compose.prod.yml)
- Runtime env: GitHub secret `PRODUCTION_ENV_FILE` (полный `.env`; шаблон — блок ниже)
- Deploy scripts: [ops](ops)
- CI/CD workflow: [.github/workflows/deploy.yml](.github/workflows/deploy.yml)

The server does not build the app. Backend and frontend are built in GitHub Actions, Postgres is mirrored to GHCR, then the VPS only pulls images and starts containers.

> Локальный запуск (`docker-compose.yml`) прод-переменных НЕ требует — см.
> [.env.example](.env.example) (локальный шаблон). Ниже — именно **серверный** `.env`.

## Server env template (`PRODUCTION_ENV_FILE` secret)

Реальный серверный `.env` (деплой пишет его в `~/nn_chat/.env` из секрета
`PRODUCTION_ENV_FILE`). Замени пароли/секреты на сильные:

```env
BACKEND_IMAGE=ghcr.io/curdyip-source/nn_chat-backend
FRONTEND_IMAGE=ghcr.io/curdyip-source/nn_chat-frontend
RELEASE_TAG=latest
POSTGRES_CONTAINER_NAME=nufnaf_db

POSTGRES_USER=nufnaf_admin_user
POSTGRES_PASSWORD=CHANGE_ME_STRONG_PASSWORD
POSTGRES_DB=nufnaf_db
POSTGRES_HOST=db
POSTGRES_PORT=5432

BACKEND_PORT=32069
FRONTEND_PORT=25256

APP_ENV=production
CORS_ALLOW_ORIGINS=https://chat.nufnafchat.su
INSECURE_ALLOW_HTTP_ORIGINS=false

ACCESS_TOKEN_TTL_MINUTES=30
SESSION_TTL_DAYS=30
REFRESH_TOKEN_TTL_DAYS=30
AUTH_TOKEN_SECRET=CHANGE_ME_LONG_RANDOM_SECRET_WITH_32_CHARS_MINIMUM

FIRST_ADMIN_PASS=replace-with-first-admin-pass

SENTRY_DSN=
SENTRY_ENVIRONMENT=production
SENTRY_TRACES_SAMPLE_RATE=0

PROFILE_PHOTO_MAX_BYTES=5242880

APNS_AUTH_KEY_P8=/home/dev/nn_chat/secrets/AuthKey_RLV35R5LP5.p8
APNS_KEY_ID=RLV35R5LP5
APNS_TEAM_ID=89CV94WHUK
APNS_TOPIC=com.NufNaf.Vorobev
APNS_USE_SANDBOX=false
```

## Required Secrets And Files

You need:

1. A real server `.env` based on the block above (stored in the `PRODUCTION_ENV_FILE` secret).
2. The APNS key file `AuthKey_RLV35R5LP5.p8`.
3. SSH access to the VPS.
4. A GHCR token with package read access on the server deploy step.

The public entrypoint is expected to be `https://chat.nufnafchat.su`, with TLS terminated on the VPS and proxied to the frontend container on `127.0.0.1:25256`.

## Local Validation

Validate env:

```bash
bash ./ops/preflight_production.sh .env
```

Render compose config:

```bash
docker compose --env-file .env -f docker-compose.prod.yml config
```

The preflight will fail locally until the APNS key exists at the path from `APNS_AUTH_KEY_P8`. This is expected when that key is stored only on the VPS.

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

Workflow [deploy.yml](.github/workflows/deploy.yml) runs on pushes to `main`, plus manual launch.

Jobs:

1. Run backend tests.
2. Build and push backend and frontend images to GHCR.
3. Mirror `postgres:17-alpine` to GHCR for server pulls.
4. Upload `docker-compose.prod.yml`, `ops/`, and `.env` to the VPS.
5. Pull the new tag on the server and restart the stack.
6. Run health and deep smoke checks.

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

- Start from the **Server env template** block above
- Replace database password and auth secret
- Set `CORS_ALLOW_ORIGINS=https://chat.nufnafchat.su`
- Set `INSECURE_ALLOW_HTTP_ORIGINS=false`
- Keep `BACKEND_IMAGE=ghcr.io/curdyip-source/nn_chat-backend`
- Keep `FRONTEND_IMAGE=ghcr.io/curdyip-source/nn_chat-frontend`
- Keep `POSTGRES_IMAGE=ghcr.io/curdyip-source/nn_chat-postgres:17-alpine` or leave it unset to use the compose default
- Keep `APNS_AUTH_KEY_P8=/home/dev/nn_chat/secrets/AuthKey_RLV35R5LP5.p8`

The workflow rewrites `RELEASE_TAG` on the server to the current commit SHA before deploy.

Because the deploy workflow uploads the full `.env` from `PRODUCTION_ENV_FILE`, any domain or CORS change must be updated in that GitHub secret before the next deploy.

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

1. Set a strong `FIRST_ADMIN_PASS` in `.env`.
2. Deploy once.
3. Create the first admin in the frontend using the bootstrap key.
4. Keep `FIRST_ADMIN_PASS` only in your protected env and use it again only if you intentionally bootstrap an empty database.

Do not share the bootstrap key. While your panel is still served over plain HTTP by public IP, treat the first bootstrap as a trusted-network operation only.