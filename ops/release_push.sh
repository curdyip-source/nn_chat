#!/usr/bin/env bash

set -euo pipefail

if [[ $# -ne 2 ]]; then
    echo "Usage: $0 <release-env-file> <release-tag>" >&2
    exit 1
fi

release_env="$1"
release_tag="$2"

[[ -f "$release_env" ]] || { echo "Release env file not found: $release_env" >&2; exit 1; }

get_value() {
    local key="$1"
    local line

    line="$(grep -E "^${key}=" "$release_env" | tail -n 1 || true)"
    [[ -n "$line" ]] || return 1
    printf '%s' "${line#*=}"
}

backend_image="$(get_value BACKEND_IMAGE)"
frontend_image="$(get_value FRONTEND_IMAGE)"

docker image inspect "${backend_image}:${release_tag}" >/dev/null 2>&1 || {
    echo "Backend image ${backend_image}:${release_tag} is missing. Build it first." >&2
    exit 1
}

docker image inspect "${frontend_image}:${release_tag}" >/dev/null 2>&1 || {
    echo "Frontend image ${frontend_image}:${release_tag} is missing. Build it first." >&2
    exit 1
}

echo "Pushing ${backend_image}:${release_tag}"
docker push "${backend_image}:${release_tag}" || {
    echo "Failed to push ${backend_image}:${release_tag}. Check docker login and registry permissions." >&2
    exit 1
}

echo "Pushing ${frontend_image}:${release_tag}"
docker push "${frontend_image}:${release_tag}" || {
    echo "Failed to push ${frontend_image}:${release_tag}. Check docker login and registry permissions." >&2
    exit 1
}

echo "Release images pushed successfully"