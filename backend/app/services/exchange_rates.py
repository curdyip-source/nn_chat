"""Курс USD/RUB для себестоимости (раздел «Финансы»).

Источник — официальный ЦБ РФ (XML_daily.asp): бесплатный и стабильный,
в отличие от скрапинга сайта конкретного банка. fetch_and_store_today_rate
апсертит запись на сегодня, но никогда не перезаписывает ручную коррекцию
(source='manual') — она приоритетнее автоматического значения.
"""
from __future__ import annotations

import logging
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from xml.etree import ElementTree

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import config
from app.models.finance import ExchangeRate

logger = logging.getLogger("app.exchange_rates")

_TIMEOUT = httpx.Timeout(15.0)


class ExchangeRateError(Exception):
    """Ошибка получения курса от ЦБ (сетевая или формат ответа)."""


def _fetch_cbr_usd_rate() -> Decimal:
    try:
        response = httpx.get(config.CBR_RATE_URL, timeout=_TIMEOUT)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise ExchangeRateError(f"cbr request failed: {exc}") from exc

    try:
        root = ElementTree.fromstring(response.content)
    except ElementTree.ParseError as exc:
        raise ExchangeRateError(f"cbr response is not valid XML: {exc}") from exc

    for valute in root.findall("Valute"):
        if valute.get("ID") != config.CBR_USD_VALUTE_ID:
            continue
        value_node = valute.find("Value")
        nominal_node = valute.find("Nominal")
        if value_node is None or value_node.text is None:
            break
        try:
            value = Decimal(value_node.text.replace(",", "."))
            nominal = Decimal(nominal_node.text) if nominal_node is not None and nominal_node.text else Decimal(1)
            return value / nominal
        except InvalidOperation as exc:
            raise ExchangeRateError(f"cbr value is not numeric: {value_node.text!r}") from exc

    raise ExchangeRateError(f"USD (ID={config.CBR_USD_VALUTE_ID}) not found in cbr response")


def fetch_and_store_today_rate(db: Session) -> ExchangeRate | None:
    """Подтягивает сегодняшний курс ЦБ и апсертит его в exchange_rates.

    Best-effort: сетевые/парсинговые ошибки логируются и не прокидываются наверх,
    чтобы плановая джоба не падала и не роняла процесс.
    """
    today = date.today()
    try:
        rate_value = _fetch_cbr_usd_rate()
    except ExchangeRateError as exc:
        logger.warning("exchange_rate.fetch_failed error=%s", exc)
        return None

    existing = db.execute(select(ExchangeRate).where(ExchangeRate.exchange_rate_date == today)).scalar_one_or_none()
    if existing is not None:
        if existing.exchange_rate_source == "manual":
            return existing
        existing.exchange_rate_value = rate_value
        existing.exchange_rate_fetched_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return existing

    row = ExchangeRate(
        exchange_rate_date=today,
        exchange_rate_value=rate_value,
        exchange_rate_source="cbr",
        exchange_rate_fetched_at=datetime.utcnow(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    logger.info("exchange_rate.fetched date=%s value=%s", today, rate_value)
    return row


def get_rate_for_date(db: Session, target_date: date) -> ExchangeRate | None:
    """Последний известный курс на дату <= target_date (в выходные ЦБ курс не публикует)."""
    return db.execute(
        select(ExchangeRate)
        .where(ExchangeRate.exchange_rate_date <= target_date)
        .order_by(ExchangeRate.exchange_rate_date.desc())
        .limit(1)
    ).scalar_one_or_none()
