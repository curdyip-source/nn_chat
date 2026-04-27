#!/usr/bin/env bash

set -euo pipefail

if [[ $# -ne 1 ]]; then
    echo "Usage: $0 <env-file>" >&2
    exit 1
fi

env_file="$1"

if [[ ! -f "$env_file" ]]; then
    echo "Env file not found: $env_file" >&2
    exit 1
fi

get_value() {
    local key="$1"
    local line

    line="$(grep -E "^[[:space:]]*${key}=" "$env_file" | tail -n 1 || true)"
    if [[ -z "$line" ]]; then
        echo ""
        return
    fi

    printf '%s' "${line#*=}"
}

fail() {
    echo "Preflight failed: $1" >&2
    exit 1
}

app_env="$(get_value APP_ENV)"
postgres_password="$(get_value POSTGRES_PASSWORD)"
auth_token_secret="$(get_value AUTH_TOKEN_SECRET)"
cors_allow_origins="$(get_value CORS_ALLOW_ORIGINS)"
public_bootstrap_enabled="$(get_value PUBLIC_BOOTSTRAP_ENABLED)"
apns_auth_key_p8="$(get_value APNS_AUTH_KEY_P8)"
insecure_allow_http_origins="$(get_value INSECURE_ALLOW_HTTP_ORIGINS)"

[[ "$app_env" == "production" ]] || fail "APP_ENV must be set to production"
[[ -n "$postgres_password" ]] || fail "POSTGRES_PASSWORD must be set"
[[ "$postgres_password" != "replace-with-strong-db-password" ]] || fail "POSTGRES_PASSWORD must be replaced"
[[ "$postgres_password" != "CHANGE_ME_STRONG_PASSWORD" ]] || fail "POSTGRES_PASSWORD must be replaced"
[[ -n "$auth_token_secret" ]] || fail "AUTH_TOKEN_SECRET must be set"
[[ "$auth_token_secret" != "replace-with-long-random-secret" ]] || fail "AUTH_TOKEN_SECRET must be replaced"
[[ "$auth_token_secret" != "dev-secret-change-me" ]] || fail "AUTH_TOKEN_SECRET cannot use the development default"
[[ "$cors_allow_origins" != *"*"* ]] || fail "CORS_ALLOW_ORIGINS cannot contain '*' in production"
[[ "$public_bootstrap_enabled" == "false" ]] || fail "PUBLIC_BOOTSTRAP_ENABLED must be false in production"

if [[ "$cors_allow_origins" == *"http://"* && "$insecure_allow_http_origins" != "true" ]]; then
    fail "Set INSECURE_ALLOW_HTTP_ORIGINS=true when using http CORS origins in production"
fi

if [[ "$cors_allow_origins" == *"localhost"* || "$cors_allow_origins" == *"127.0.0.1"* ]]; then
    fail "CORS_ALLOW_ORIGINS cannot point to localhost in production"
fi

if [[ -n "$apns_auth_key_p8" && ! -f "$apns_auth_key_p8" ]]; then
    fail "APNS_AUTH_KEY_P8 points to a missing file: $apns_auth_key_p8"
fi

echo "Production env preflight passed for $env_file"