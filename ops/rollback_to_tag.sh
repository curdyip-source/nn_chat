#!/usr/bin/env bash

set -euo pipefail

if [[ $# -ne 2 ]]; then
    echo "Usage: $0 <env-file> <release-tag>" >&2
    exit 1
fi

env_file="$1"
release_tag="$2"

[[ -f "$env_file" ]] || { echo "Env file not found: $env_file" >&2; exit 1; }

export RELEASE_TAG="$release_tag"
front_port="$(grep '^FRONTEND_PORT=' "$env_file" | cut -d= -f2-)"

docker compose \
    --env-file "$env_file" \
    -f docker-compose.yml \
    pull backend frontend

docker compose \
    --env-file "$env_file" \
    -f docker-compose.yml \
    up -d

./ops/post_deploy_check.sh "http://127.0.0.1:${front_port}"
./ops/post_deploy_api_smoke.sh docker-compose.yml "$env_file"

echo "Rollback to ${release_tag} completed successfully"