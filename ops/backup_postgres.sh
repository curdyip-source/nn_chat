#!/usr/bin/env bash

set -euo pipefail

if [[ $# -ne 2 ]]; then
    echo "Usage: $0 <env-file> <output-sql-file>" >&2
    exit 1
fi

env_file="$1"
output_file="$2"

if [[ ! -f "$env_file" ]]; then
    echo "Env file not found: $env_file" >&2
    exit 1
fi

mkdir -p "$(dirname "$output_file")"

docker compose \
    --env-file "$env_file" \
    -f docker-compose.prod.yml \
    exec -T db \
    pg_dump -U "$(grep '^POSTGRES_USER=' "$env_file" | cut -d= -f2-)" "$(grep '^POSTGRES_DB=' "$env_file" | cut -d= -f2-)" \
    > "$output_file"

echo "Backup written to $output_file"