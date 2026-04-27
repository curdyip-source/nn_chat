#!/usr/bin/env bash

set -euo pipefail

if [[ $# -ne 1 ]]; then
    echo "Usage: $0 <base-url>" >&2
    exit 1
fi

base_url="${1%/}"

headers_file="$(mktemp)"
body_file="$(mktemp)"
trap 'rm -f "$headers_file" "$body_file"' EXIT

request() {
    local method="$1"
    local url="$2"
    local payload="${3:-}"

    : > "$headers_file"
    : > "$body_file"

    if [[ -n "$payload" ]]; then
        curl -sS -X "$method" "$url" \
            -H "Content-Type: application/json" \
            -d "$payload" \
            -D "$headers_file" \
            -o "$body_file" \
            -w '%{http_code}'
    else
        curl -sS -X "$method" "$url" \
            -D "$headers_file" \
            -o "$body_file" \
            -w '%{http_code}'
    fi
}

assert_header() {
    local header_name="$1"
    grep -iq "^${header_name}:" "$headers_file"
}

echo "Checking frontend root..."
status_code="$(request GET "$base_url/")"
[[ "$status_code" == "200" ]]
grep 'myclearproject' "$body_file" >/dev/null
assert_header "x-content-type-options"

echo "Checking live health..."
status_code="$(request GET "$base_url/api/v1/health/live")"
[[ "$status_code" == "200" ]]
grep '"status":"ok"' "$body_file" >/dev/null

echo "Checking ready health..."
status_code="$(request GET "$base_url/api/v1/health/ready")"
[[ "$status_code" == "200" ]]
grep '"database":"ok"' "$body_file" >/dev/null

echo "Checking setup status..."
status_code="$(request GET "$base_url/api/v1/setup-status")"
[[ "$status_code" == "200" ]]
grep '"users_count"' "$body_file" >/dev/null
grep '"bootstrap_required"' "$body_file" >/dev/null

echo "Checking protected endpoints reject anonymous access..."
status_code="$(request GET "$base_url/api/v1/auth/me")"
[[ "$status_code" == "401" ]]
grep '"error"' "$body_file" >/dev/null
assert_header "x-request-id"

status_code="$(request GET "$base_url/api/v1/users")"
[[ "$status_code" == "401" ]]
grep '"error"' "$body_file" >/dev/null

status_code="$(request GET "$base_url/api/v1/db-info")"
[[ "$status_code" == "401" ]]
grep '"error"' "$body_file" >/dev/null

echo "Post-deploy check passed for $base_url"