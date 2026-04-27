#!/usr/bin/env bash

set -euo pipefail

if [[ $# -ne 2 ]]; then
    echo "Usage: $0 <env-file> <input-sql-file>" >&2
    exit 1
fi

env_file="$1"
input_file="$2"

if [[ ! -f "$env_file" ]]; then
    echo "Env file not found: $env_file" >&2
    exit 1
fi

if [[ ! -f "$input_file" ]]; then
    echo "SQL file not found: $input_file" >&2
    exit 1
fi

postgres_user="$(grep '^POSTGRES_USER=' "$env_file" | cut -d= -f2-)"
postgres_db="$(grep '^POSTGRES_DB=' "$env_file" | cut -d= -f2-)"

docker compose \
    --env-file "$env_file" \
    -f docker-compose.yml \
    exec -T db \
    psql -U "$postgres_user" -d "$postgres_db" -c "DROP SCHEMA IF EXISTS public CASCADE; CREATE SCHEMA public;"

docker compose \
    --env-file "$env_file" \
    -f docker-compose.yml \
    exec -T db \
    psql -U "$postgres_user" -d "$postgres_db" \
    < "$input_file"

echo "Restore completed from $input_file"