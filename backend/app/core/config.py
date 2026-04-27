import os
from ipaddress import ip_address
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[3] / ".env")

POSTGRES_USER = os.getenv("POSTGRES_USER", "app_user")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "app_pass")
POSTGRES_DB = os.getenv("POSTGRES_DB", "appdb")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "db")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
APP_ENV = os.getenv("APP_ENV", "development").strip().lower()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}",
)

CORS_ALLOW_ORIGINS = [origin.strip() for origin in os.getenv("CORS_ALLOW_ORIGINS", "*").split(",") if origin.strip()]
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_METHODS = ["*"]
CORS_ALLOW_HEADERS = ["*"]
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").strip().upper()
ACCESS_TOKEN_TTL_MINUTES = int(os.getenv("ACCESS_TOKEN_TTL_MINUTES", "30"))
REFRESH_TOKEN_TTL_DAYS = int(os.getenv("REFRESH_TOKEN_TTL_DAYS", os.getenv("SESSION_TTL_DAYS", "30")))
AUTH_TOKEN_SECRET = os.getenv("AUTH_TOKEN_SECRET", "dev-secret-change-me")
SENTRY_DSN = os.getenv("SENTRY_DSN", "").strip()
SENTRY_ENVIRONMENT = os.getenv("SENTRY_ENVIRONMENT", APP_ENV or "development").strip()
SENTRY_TRACES_SAMPLE_RATE = float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0"))
PROFILE_PHOTO_MAX_BYTES = int(os.getenv("PROFILE_PHOTO_MAX_BYTES", str(5 * 1024 * 1024)))
APNS_AUTH_KEY_P8 = os.getenv("APNS_AUTH_KEY_P8", "").strip()
APNS_KEY_ID = os.getenv("APNS_KEY_ID", "").strip()
APNS_TEAM_ID = os.getenv("APNS_TEAM_ID", "").strip()
APNS_TOPIC = os.getenv("APNS_TOPIC", "").strip()
APNS_USE_SANDBOX = os.getenv(
    "APNS_USE_SANDBOX",
    "true" if APP_ENV != "production" else "false",
).strip().lower() in {"1", "true", "yes", "on"}
APNS_ENABLED = all([APNS_AUTH_KEY_P8, APNS_KEY_ID, APNS_TEAM_ID, APNS_TOPIC])
INSECURE_ALLOW_HTTP_ORIGINS = os.getenv("INSECURE_ALLOW_HTTP_ORIGINS", "false").strip().lower() in {"1", "true", "yes", "on"}
FIRST_ADMIN_PASS = os.getenv(
    "FIRST_ADMIN_PASS",
    "dev-first-admin-pass" if APP_ENV != "production" else "",
).strip()


def _is_placeholder(value: str) -> bool:
    normalized = value.strip().lower()
    return normalized.startswith("replace-with-") or normalized.startswith("your-")


def _validate_https_origins(origins: list[str]) -> None:
    for origin in origins:
        parsed = urlparse(origin)
        if parsed.scheme == "https" and parsed.netloc:
            continue

        if parsed.scheme == "http" and parsed.hostname and INSECURE_ALLOW_HTTP_ORIGINS:
            try:
                host_ip = ip_address(parsed.hostname)
            except ValueError as exc:
                raise RuntimeError("HTTP CORS origins in production are allowed only for explicit IP hosts") from exc

            if host_ip.is_loopback or host_ip.is_private or host_ip.is_link_local or host_ip.is_multicast:
                raise RuntimeError("HTTP CORS origins in production cannot point to private or local IP hosts")

            if parsed.netloc:
                continue

        raise RuntimeError("CORS_ALLOW_ORIGINS must contain https origins in production, or explicit public IP http origins when INSECURE_ALLOW_HTTP_ORIGINS=true")
        if not parsed.netloc:
            raise RuntimeError("CORS_ALLOW_ORIGINS must contain valid absolute origins in production")


def _validate_positive_ttl(name: str, value: int, minimum: int, maximum: int) -> None:
    if value < minimum or value > maximum:
        raise RuntimeError(f"{name} must be between {minimum} and {maximum} in production")


def validate_runtime_config() -> None:
    if APP_ENV != "production":
        return

    if AUTH_TOKEN_SECRET == "dev-secret-change-me":
        raise RuntimeError("AUTH_TOKEN_SECRET must be set to a non-default value in production")

    if _is_placeholder(AUTH_TOKEN_SECRET) or len(AUTH_TOKEN_SECRET) < 32:
        raise RuntimeError("AUTH_TOKEN_SECRET must be a strong non-placeholder value with length >= 32 in production")

    if not FIRST_ADMIN_PASS or _is_placeholder(FIRST_ADMIN_PASS) or len(FIRST_ADMIN_PASS) < 12:
        raise RuntimeError("FIRST_ADMIN_PASS must be set to a strong non-placeholder value with length >= 12 in production")

    if "*" in CORS_ALLOW_ORIGINS and CORS_ALLOW_CREDENTIALS:
        raise RuntimeError("CORS_ALLOW_ORIGINS cannot contain '*' when credentials are enabled in production")

    if not CORS_ALLOW_ORIGINS:
        raise RuntimeError("CORS_ALLOW_ORIGINS must not be empty in production")

    _validate_https_origins(CORS_ALLOW_ORIGINS)

    if POSTGRES_HOST.strip().lower() in {"", "localhost", "127.0.0.1"}:
        raise RuntimeError("POSTGRES_HOST must point to a non-localhost database host in production")

    _validate_positive_ttl("ACCESS_TOKEN_TTL_MINUTES", ACCESS_TOKEN_TTL_MINUTES, 5, 1440)
    _validate_positive_ttl("REFRESH_TOKEN_TTL_DAYS", REFRESH_TOKEN_TTL_DAYS, 1, 365)

    if SENTRY_TRACES_SAMPLE_RATE < 0 or SENTRY_TRACES_SAMPLE_RATE > 1:
        raise RuntimeError("SENTRY_TRACES_SAMPLE_RATE must be between 0 and 1")