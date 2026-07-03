#!/usr/bin/env bash

set -euo pipefail

if [[ $# -ne 2 ]]; then
    echo "Usage: $0 <env-file> <release-tag>" >&2
    exit 1
fi

env_file="$1"
release_tag="$2"

[[ -f "$env_file" ]] || { echo "Env file not found: $env_file" >&2; exit 1; }

./ops/preflight_production.sh "$env_file"

export RELEASE_TAG="$release_tag"

docker compose \
    --env-file "$env_file" \
    -f docker-compose.prod.yml \
    pull backend frontend

docker compose \
    --env-file "$env_file" \
    -f docker-compose.prod.yml \
    up -d

front_port="$(grep '^FRONTEND_PORT=' "$env_file" | cut -d= -f2-)"

./ops/post_deploy_check.sh "http://127.0.0.1:${front_port}"
./ops/post_deploy_api_smoke.sh docker-compose.prod.yml "$env_file"

echo "Release ${release_tag} deployed successfully"