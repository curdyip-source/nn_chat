"""Настройки приложения (key-value). Пока — минимальный допустимый билд iOS
для гейта форс-апдейта: приложение с билдом ниже показывает экран «обновитесь»."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.app_settings import AppSetting

MIN_IOS_BUILD_KEY = "min_supported_ios_build"


def _get(db: Session, key: str) -> str | None:
    row = db.get(AppSetting, key)
    return row.setting_value if row is not None else None


def _set(db: Session, key: str, value: str) -> None:
    row = db.get(AppSetting, key)
    if row is None:
        db.add(AppSetting(setting_key=key, setting_value=value))
    else:
        row.setting_value = value
    db.commit()


def get_min_supported_ios_build(db: Session) -> int:
    """Минимальный билд iOS. 0 = гейт выключен (никого не блокируем)."""
    raw = _get(db, MIN_IOS_BUILD_KEY)
    try:
        return max(0, int(raw)) if raw is not None else 0
    except (TypeError, ValueError):
        return 0


def set_min_supported_ios_build(db: Session, value: int) -> int:
    normalized = max(0, int(value))
    _set(db, MIN_IOS_BUILD_KEY, str(normalized))
    return normalized
