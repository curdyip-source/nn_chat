#!/usr/bin/env bash

set -euo pipefail

if [[ $# -ne 3 ]]; then
    echo "Usage: $0 <production-env-file> <release-env-file> <release-tag>" >&2
    exit 1
fi

production_env="$1"
release_env="$2"
release_tag="$3"

[[ -f "$production_env" ]] || { echo "Env file not found: $production_env" >&2; exit 1; }
[[ -f "$release_env" ]] || { echo "Release env file not found: $release_env" >&2; exit 1; }

set -a
source "$production_env"
source "$release_env"
export RELEASE_TAG="$release_tag"
set +a

docker compose \
    --env-file "$production_env" \
    --env-file "$release_env" \
    -f docker-compose.release.yml \
    up -d

./ops/post_deploy_check.sh "http://127.0.0.1:${FRONTEND_PORT}"
./ops/post_deploy_api_smoke.sh docker-compose.release.yml "$production_env" "$release_env"

echo "Rollback to ${release_tag} completed successfully"