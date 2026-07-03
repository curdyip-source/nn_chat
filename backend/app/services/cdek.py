"""Клиент CDEK API v2 (доставка).

Порт логики PHP-демо (cdek-sdk-v2 / web/api.php) на Python. Среда переключается
через env: по умолчанию тест (`api.edu.cdek.ru` + публичные тест-креды SDK), на
проде — `api.cdek.ru` + боевые CDEK_ACCOUNT/CDEK_SECURE.

Read-only методы (поиск города/ПВЗ, тарифы, статус) безопасны в любой среде.
create_order на проде создаёт реальную отправку — для теста используем среду edu
либо create+delete_order.
"""
from __future__ import annotations

import threading
import time

import httpx

from app.core import config

_TIMEOUT = httpx.Timeout(20.0)

# Кеш OAuth-токена (на процесс). CDEK отдаёт токен ~на час.
_token_lock = threading.Lock()
_token_value: str | None = None
_token_expires_at: float = 0.0


class CdekError(Exception):
    """Ошибка обращения к CDEK API (сетевые/логические)."""


def _get_token() -> str:
    global _token_value, _token_expires_at
    with _token_lock:
        if _token_value and time.monotonic() < _token_expires_at - 60:
            return _token_value
        try:
            resp = httpx.post(
                f"{config.CDEK_BASE_URL}/oauth/token",
                params={
                    "grant_type": "client_credentials",
                    "client_id": config.CDEK_ACCOUNT,
                    "client_secret": config.CDEK_SECURE,
                },
                timeout=_TIMEOUT,
            )
        except httpx.HTTPError as exc:
            raise CdekError(f"CDEK OAuth: сеть недоступна ({exc})") from exc
        data = resp.json() if resp.content else {}
        token = data.get("access_token")
        if not token:
            raise CdekError(f"CDEK OAuth не выдал токен: {data or resp.status_code}")
        _token_value = token
        _token_expires_at = time.monotonic() + int(data.get("expires_in", 3600))
        return token


def _request(method: str, path: str, *, params=None, json=None) -> httpx.Response:
    token = _get_token()
    url = f"{config.CDEK_BASE_URL}{path}"
    try:
        resp = httpx.request(
            method,
            url,
            params=params,
            json=json,
            headers={"Authorization": f"Bearer {token}"},
            timeout=_TIMEOUT,
        )
    except httpx.HTTPError as exc:
        raise CdekError(f"CDEK {method} {path}: сеть недоступна ({exc})") from exc
    return resp


def _json(resp: httpx.Response):
    if resp.status_code >= 400:
        raise CdekError(f"CDEK {resp.request.method} {resp.request.url.path}: {resp.status_code} {resp.text[:300]}")
    return resp.json() if resp.content else None


# ——— Поиск (read-only, без кодов у пользователя) ———

def suggest_cities(name: str, country_code: str = "RU") -> list[dict]:
    """Поиск города по названию (автодополнение). Возвращает [{code, full_name, city_uuid}]."""
    name = (name or "").strip()
    if len(name) < 2:
        return []
    data = _json(_request("GET", "/location/suggest/cities", params={"name": name, "country_code": country_code})) or []
    return [{"code": c.get("code"), "full_name": c.get("full_name"), "city_uuid": c.get("city_uuid")} for c in data]


def delivery_points(city_code: int, *, type_: str = "PVZ") -> list[dict]:
    """ПВЗ/постаматы города. Возвращает упрощённые [{code, name, address, work_time, type}]."""
    data = _json(_request("GET", "/deliverypoints", params={"city_code": city_code, "type": type_})) or []
    out = []
    for p in data:
        loc = p.get("location") or {}
        out.append({
            "code": p.get("code"),
            "name": p.get("name") or "",
            "address": loc.get("address_full") or loc.get("address") or "",
            "work_time": p.get("work_time") or "",
            "type": p.get("type") or "",
        })
    return out


def calculate_tariff_list(from_code: int, to_code: int, weight: int = 500, order_type: int = 1) -> list[dict]:
    """Список доступных тарифов (с ценами/сроками) для пары городов."""
    body = {
        "type": order_type,
        "from_location": {"code": from_code},
        "to_location": {"code": to_code},
        "packages": [{"weight": weight}],
    }
    data = _json(_request("POST", "/calculator/tarifflist", json=body)) or {}
    return data.get("tariff_codes", []) if isinstance(data, dict) else []


# ——— Заказ / накладная ———

def create_order(payload: dict) -> dict:
    """Создать заказ (накладную). Возвращает {uuid, requests}. payload — тело CDEK /orders."""
    data = _json(_request("POST", "/orders", json=payload)) or {}
    entity = data.get("entity") or {}
    return {"uuid": entity.get("uuid"), "requests": data.get("requests", [])}


def order_info(uuid: str) -> dict:
    """Инфо по заказу (включая statuses[])."""
    data = _json(_request("GET", f"/orders/{uuid}")) or {}
    return data.get("entity") or {}


def delete_order(uuid: str) -> dict:
    """Удалить заказ (доступно в раннем статусе) — для безопасного теста на проде."""
    return _json(_request("DELETE", f"/orders/{uuid}")) or {}


# ——— Печатные формы (накладная + ШК) ———

def create_invoice_print(order_uuid: str, copy_count: int = 2, type_: str = "tpl_russia") -> str:
    """Создать печать накладной (развёрнутая). Возвращает uuid печатной формы."""
    body = {"orders": [{"order_uuid": order_uuid}], "copy_count": copy_count, "type": type_}
    data = _json(_request("POST", "/print/orders", json=body)) or {}
    return (data.get("entity") or {}).get("uuid")


def create_barcode_print(order_uuid: str, fmt: str = "A6") -> str:
    """Создать печать ШК-этикетки (маленькая). Возвращает uuid печатной формы."""
    body = {"orders": [{"order_uuid": order_uuid}], "format": fmt}
    data = _json(_request("POST", "/print/barcodes", json=body)) or {}
    return (data.get("entity") or {}).get("uuid")


def get_print_pdf(print_uuid: str, *, kind: str = "invoice", attempts: int = 15) -> bytes:
    """Скачать PDF печатной формы. Форма генерируется асинхронно — опрашиваем, пока
    не отдаст именно PDF (как в api.php)."""
    path = f"/print/barcodes/{print_uuid}.pdf" if kind == "barcode" else f"/print/orders/{print_uuid}.pdf"
    for _ in range(attempts):
        resp = _request("GET", path)
        body = resp.content or b""
        if resp.status_code == 200 and body[:4] == b"%PDF":
            return body
        time.sleep(0.8)
    raise CdekError("CDEK: печатная форма не успела сформироваться")


# ——— Вебхуки (статусы) ———

def set_webhook(url: str, type_: str = "ORDER_STATUS") -> dict:
    """Подписаться на вебхук CDEK (статусы заказа шлются на url)."""
    return _json(_request("POST", "/webhooks", json={"url": url, "type": type_})) or {}
