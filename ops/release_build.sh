#!/usr/bin/env bash

set -euo pipefail

if [[ $# -lt 1 || $# -gt 2 ]]; then
    echo "Usage: $0 <release-tag> [env-file]" >&2
    exit 1
fi

release_tag="$1"
release_env="${2:-.env}"

[[ -f "$release_env" ]] || { echo "Env file not found: $release_env" >&2; exit 1; }

get_value() {
    local key="$1"
    local line

    line="$(grep -E "^${key}=" "$release_env" | tail -n 1 || true)"
    [[ -n "$line" ]] || return 1
    printf '%s' "${line#*=}"
}

backend_image="$(get_value BACKEND_IMAGE)"
frontend_image="$(get_value FRONTEND_IMAGE)"

echo "Building ${backend_image}:${release_tag}"
docker build -t "${backend_image}:${release_tag}" backend

echo "Building ${frontend_image}:${release_tag}"
docker build -t "${frontend_image}:${release_tag}" frontend

echo "Release images built successfully"