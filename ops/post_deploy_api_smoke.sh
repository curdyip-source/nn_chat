#!/usr/bin/env bash

set -euo pipefail

if [[ $# -lt 2 ]]; then
    echo "Usage: $0 <compose-file> <env-file> [<env-file> ...]" >&2
    exit 1
fi

compose_file="$1"
shift

[[ -f "$compose_file" ]] || { echo "Compose file not found: $compose_file" >&2; exit 1; }

compose_args=()
for env_file in "$@"; do
    [[ -f "$env_file" ]] || { echo "Env file not found: $env_file" >&2; exit 1; }
    compose_args+=(--env-file "$env_file")
done

docker compose \
    "${compose_args[@]}" \
    -f "$compose_file" \
    exec -T backend python scripts/api_smoke_test.py

echo "Deep API smoke completed successfully"