from datetime import datetime

from app.core.security import hash_password
from app.models.orders import Order

API_PREFIX = "/api/v1"


def login(client, login: str, password: str) -> dict:
    response = client.post(f"{API_PREFIX}/auth/login", json={"user_login": login, "user_password": password})
    assert response.status_code == 200
    return response.json()


def _admin_headers(client, integration_db_session, integration_admin) -> dict:
    integration_admin.user_password = hash_password("AdminPass123")
    integration_db_session.commit()
    token = login(client, "admin", "AdminPass123")["token"]
    return {"Authorization": f"Bearer {token}"}


def _shipped_status_id(reference_payload: dict) -> int:
    # Свод считает «продано» только позиции в статусе «Отгружено» (order_products) —
    # см. app/services/domain_common.py::SOLD_ITEM_STATUS_NAME.
    return next(
        item["status_id"]
        for item in reference_payload["statuses"]
        if item["status_type"] == "order_products" and item["status_status"] == "Отгружено"
    )


def test_expense_category_and_expense_crud_lifecycle(client, integration_db_session, integration_admin):
    # Нет закрытия месяца — расходы редактируются в любой момент, это просто фильтр по дате.
    headers = _admin_headers(client, integration_db_session, integration_admin)

    create_category = client.post(
        f"{API_PREFIX}/finance/expense-categories",
        headers=headers,
        json={"finance_expense_category_name": "Зарплата"},
    )
    assert create_category.status_code == 201
    category_id = create_category.json()["item"]["finance_expense_category_id"]

    create_expense = client.post(
        f"{API_PREFIX}/finance/expenses",
        headers=headers,
        json={
            "finance_expense_category_id": category_id,
            "finance_expense_period": "2026-09-15",
            "finance_expense_amount": "50000.00",
            "finance_expense_note": "Аванс",
        },
    )
    assert create_expense.status_code == 201
    expense = create_expense.json()["item"]
    expense_id = expense["finance_expense_id"]
    # Точная дата сохраняется как есть, не обрезается до 1-го числа месяца.
    assert expense["finance_expense_period"] == "2026-09-15"

    list_expenses = client.get(f"{API_PREFIX}/finance/expenses?date_from=2026-09-01&date_to=2026-09-30", headers=headers)
    assert list_expenses.status_code == 200
    assert len(list_expenses.json()["items"]) == 1

    update_response = client.put(
        f"{API_PREFIX}/finance/expenses/{expense_id}",
        headers=headers,
        json={"finance_expense_category_id": category_id, "finance_expense_period": "2026-09-01", "finance_expense_amount": "99.00"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["item"]["finance_expense_amount"] == "99.00"

    delete_response = client.delete(f"{API_PREFIX}/finance/expenses/{expense_id}", headers=headers)
    assert delete_response.status_code == 204


def test_order_item_cost_snapshot_from_rate_and_period_overview(client, integration_db_session, integration_admin):
    headers = _admin_headers(client, integration_db_session, integration_admin)

    override_rate = client.put(
        f"{API_PREFIX}/finance/exchange-rates/2026-09-23",
        headers=headers,
        json={"exchange_rate_value": "90.0000"},
    )
    assert override_rate.status_code == 200
    assert override_rate.json()["item"]["exchange_rate_source"] == "manual"

    reference_payload = client.get(f"{API_PREFIX}/reference-data", headers=headers).json()
    establishment_id = reference_payload["establishments"][0]["establishment_id"]
    order_method_id = reference_payload["order_methods"][0]["order_method_id"]
    shipped_status_id = _shipped_status_id(reference_payload)

    create_order_response = client.post(
        f"{API_PREFIX}/orders",
        headers=headers,
        json={
            "order_establishment_id": establishment_id,
            "order_method_id": order_method_id,
            "order_customer": "Марина",
            "order_info": "Тест",
            "items": [
                {
                    "product_article": "FIN-TEST-001",
                    "product_name": "Financed Product",
                    "order_item_quantity": 2,
                    "order_item_price": "500.00",
                    "order_item_status_id": shipped_status_id,
                }
            ],
        },
    )
    assert create_order_response.status_code == 201
    order_item = create_order_response.json()["item"]["items"][0]
    # Товар только что создан вместе с заказом: resolve_product_snapshot сохраняет
    # его product_cost_usd равным переданной цене продажи (500.00) — существующее
    # поведение сервиса заказов, снимок себестоимости просто использует это значение.
    assert float(order_item["order_item_cost_usd"]) == 500.0
    assert float(order_item["order_item_cost_rate"]) == 90.0
    assert float(order_item["order_item_cost_rub"]) == 500.0 * 90.0
    assert order_item["order_item_margin"] is not None

    overview = client.get(f"{API_PREFIX}/finance/summary?date_from=2026-09-01&date_to=2026-09-30", headers=headers)
    assert overview.status_code == 200
    body = overview.json()
    assert float(body["revenue"]) >= 1000.0
    assert float(body["cost_rub"]) >= 500.0 * 90.0 * 2
    assert body["missing_cost_count"] == 0


def test_order_item_without_rate_is_flagged_for_review(client, integration_db_session, integration_admin):
    headers = _admin_headers(client, integration_db_session, integration_admin)

    reference_payload = client.get(f"{API_PREFIX}/reference-data", headers=headers).json()
    establishment_id = reference_payload["establishments"][0]["establishment_id"]
    order_method_id = reference_payload["order_methods"][0]["order_method_id"]
    shipped_status_id = _shipped_status_id(reference_payload)

    create_order_response = client.post(
        f"{API_PREFIX}/orders",
        headers=headers,
        json={
            "order_establishment_id": establishment_id,
            "order_method_id": order_method_id,
            "order_customer": "Без курса",
            "order_info": "Тест",
            "items": [
                {
                    "product_article": "FIN-TEST-002",
                    "product_name": "No Rate Product",
                    "order_item_quantity": 1,
                    "order_item_price": "300.00",
                    "order_item_status_id": shipped_status_id,
                }
            ],
        },
    )
    assert create_order_response.status_code == 201
    order_item = create_order_response.json()["item"]["items"][0]
    # Курса на сегодня ещё нет ни одной записи — себестоимость не проставляется,
    # это нормально, позиция просто попадает в список для ревью.
    assert order_item["order_item_cost_rate"] is None
    order_item_id = order_item["order_item_id"]

    overview = client.get(f"{API_PREFIX}/finance/summary?date_from=2026-09-01&date_to=2026-09-30", headers=headers)
    assert overview.status_code == 200
    body = overview.json()
    assert body["missing_cost_count"] == 1
    assert any(item["order_item_id"] == order_item_id for item in body["items"])

    correction = client.put(
        f"{API_PREFIX}/finance/order-items/{order_item_id}/cost",
        headers=headers,
        json={"order_item_cost_usd": "100.00", "order_item_cost_rate": "95.0000"},
    )
    assert correction.status_code == 200
    assert float(correction.json()["item"]["order_item_cost_rate"]) == 95.0

    overview_after = client.get(f"{API_PREFIX}/finance/summary?date_from=2026-09-01&date_to=2026-09-30", headers=headers)
    assert overview_after.json()["missing_cost_count"] == 0


def test_period_overview_excludes_items_not_shipped(client, integration_db_session, integration_admin):
    headers = _admin_headers(client, integration_db_session, integration_admin)

    reference_payload = client.get(f"{API_PREFIX}/reference-data", headers=headers).json()
    establishment_id = reference_payload["establishments"][0]["establishment_id"]
    order_method_id = reference_payload["order_methods"][0]["order_method_id"]
    cancelled_status_id = next(
        item["status_id"]
        for item in reference_payload["statuses"]
        if item["status_type"] == "order_products" and item["status_status"] == "Отменен"
    )

    # Один товар не тронут (дефолтный статус «Не обработан» — ещё не собран),
    # второй явно отменён. Оба не должны попасть в свод месяца.
    create_order_response = client.post(
        f"{API_PREFIX}/orders",
        headers=headers,
        json={
            "order_establishment_id": establishment_id,
            "order_method_id": order_method_id,
            "order_customer": "Не отгружено",
            "order_info": "Тест",
            "items": [
                {
                    "product_article": "FIN-TEST-003",
                    "product_name": "Not Shipped Product",
                    "order_item_quantity": 1,
                    "order_item_price": "1000.00",
                },
                {
                    "product_article": "FIN-TEST-004",
                    "product_name": "Cancelled Product",
                    "order_item_quantity": 1,
                    "order_item_price": "2000.00",
                    "order_item_status_id": cancelled_status_id,
                },
            ],
        },
    )
    assert create_order_response.status_code == 201

    overview = client.get(f"{API_PREFIX}/finance/summary?date_from=2026-09-01&date_to=2026-09-30", headers=headers)
    assert overview.status_code == 200
    body = overview.json()
    assert body["items_count"] == 0
    assert body["items"] == []
    assert float(body["revenue"]) == 0.0


def test_revenue_converts_usd_price_to_rub_not_treated_as_rub(client, integration_db_session, integration_admin):
    # Регрессия: order_item_price хранится в валюте позиции (по умолчанию USD, см.
    # get_default_currency_or_400), а не всегда в рублях. Раньше свод считал цену
    # напрямую рублями, из-за чего валовая прибыль по долларовым позициям уходила
    # в глубокий минус даже при нормальной марже в долларах.
    headers = _admin_headers(client, integration_db_session, integration_admin)

    override_rate = client.put(
        f"{API_PREFIX}/finance/exchange-rates/2026-09-23",
        headers=headers,
        json={"exchange_rate_value": "90.0000"},
    )
    assert override_rate.status_code == 200

    create_product = client.post(
        f"{API_PREFIX}/products",
        headers=headers,
        json={"product_article": "FIN-TEST-005", "product_name": "USD Priced Product", "product_cost_usd": "10.00"},
    )
    assert create_product.status_code == 201

    reference_payload = client.get(f"{API_PREFIX}/reference-data", headers=headers).json()
    establishment_id = reference_payload["establishments"][0]["establishment_id"]
    order_method_id = reference_payload["order_methods"][0]["order_method_id"]
    shipped_status_id = _shipped_status_id(reference_payload)
    usd_currency_id = next(c["currency_id"] for c in reference_payload["currencies"] if c["currency_name"] == "USD")

    create_order_response = client.post(
        f"{API_PREFIX}/orders",
        headers=headers,
        json={
            "order_establishment_id": establishment_id,
            "order_method_id": order_method_id,
            "order_customer": "USD Sale",
            "order_info": "Тест",
            "items": [
                {
                    "product_article": "FIN-TEST-005",
                    "product_name": "USD Priced Product",
                    "order_item_quantity": 1,
                    "order_item_price": "150.00",
                    "order_item_status_id": shipped_status_id,
                    "order_item_currency_id": usd_currency_id,
                }
            ],
        },
    )
    assert create_order_response.status_code == 201
    order_item = create_order_response.json()["item"]["items"][0]

    assert order_item["order_item_currency_name"] == "USD"
    # 150 USD -> 13500 RUB по курсу 90; себестоимость 10 USD -> 900 RUB; маржа 12600 RUB.
    assert float(order_item["order_item_price_rub"]) == 13500.0
    assert float(order_item["order_item_cost_rub"]) == 900.0
    assert float(order_item["order_item_margin"]) == 12600.0

    overview = client.get(f"{API_PREFIX}/finance/summary?date_from=2026-09-01&date_to=2026-09-30", headers=headers)
    body = overview.json()
    assert float(body["revenue"]) == 13500.0
    assert float(body["cost_rub"]) == 900.0
    assert float(body["gross_profit"]) == 12600.0


def test_bulk_set_cost_rate_updates_selected_items_only(client, integration_db_session, integration_admin):
    headers = _admin_headers(client, integration_db_session, integration_admin)

    reference_payload = client.get(f"{API_PREFIX}/reference-data", headers=headers).json()
    establishment_id = reference_payload["establishments"][0]["establishment_id"]
    order_method_id = reference_payload["order_methods"][0]["order_method_id"]
    shipped_status_id = _shipped_status_id(reference_payload)

    def _create_item(article: str, price: str) -> int:
        response = client.post(
            f"{API_PREFIX}/orders",
            headers=headers,
            json={
                "order_establishment_id": establishment_id,
                "order_method_id": order_method_id,
                "order_customer": "Bulk",
                "order_info": "Тест",
                "items": [
                    {
                        "product_article": article,
                        "product_name": article,
                        "order_item_quantity": 1,
                        "order_item_price": price,
                        "order_item_status_id": shipped_status_id,
                    }
                ],
            },
        )
        assert response.status_code == 201
        return response.json()["item"]["items"][0]["order_item_id"]

    # Курса на сегодня ещё нет — обе позиции без курса.
    item_a = _create_item("FIN-TEST-006", "100.00")
    item_b = _create_item("FIN-TEST-007", "200.00")
    item_c = _create_item("FIN-TEST-008", "300.00")

    bulk_response = client.put(
        f"{API_PREFIX}/finance/order-items/bulk-cost-rate",
        headers=headers,
        json={"order_item_ids": [item_a, item_b], "order_item_cost_rate": "88.5000"},
    )
    assert bulk_response.status_code == 200
    body = bulk_response.json()
    assert sorted(body["updated_ids"]) == sorted([item_a, item_b])
    assert body["not_found_ids"] == []

    overview = client.get(f"{API_PREFIX}/finance/summary?date_from=2026-09-01&date_to=2026-09-30", headers=headers)
    items_by_id = {item["order_item_id"]: item for item in overview.json()["items"]}
    assert float(items_by_id[item_a]["order_item_cost_rate"]) == 88.5
    assert float(items_by_id[item_b]["order_item_cost_rate"]) == 88.5
    # Третья позиция не была отмечена — курс так и не проставлен.
    assert items_by_id[item_c]["order_item_cost_rate"] is None
    assert overview.json()["missing_cost_count"] == 1


def test_period_overview_paginates_and_sorts_newest_first(client, integration_db_session, integration_admin):
    headers = _admin_headers(client, integration_db_session, integration_admin)

    reference_payload = client.get(f"{API_PREFIX}/reference-data", headers=headers).json()
    establishment_id = reference_payload["establishments"][0]["establishment_id"]
    order_method_id = reference_payload["order_methods"][0]["order_method_id"]
    shipped_status_id = _shipped_status_id(reference_payload)

    order_item_ids = []
    for i in range(3):
        response = client.post(
            f"{API_PREFIX}/orders",
            headers=headers,
            json={
                "order_establishment_id": establishment_id,
                "order_method_id": order_method_id,
                "order_customer": f"Page {i}",
                "order_info": "Тест",
                "items": [
                    {
                        "product_article": f"FIN-PAGE-{i}",
                        "product_name": f"Page Product {i}",
                        "order_item_quantity": 1,
                        "order_item_price": "10.00",
                        "order_item_status_id": shipped_status_id,
                    }
                ],
            },
        )
        assert response.status_code == 201
        order_item_ids.append(response.json()["item"]["items"][0]["order_item_id"])

    # page_size=2: первая страница — 2 последних созданных (новые сверху).
    page1 = client.get(f"{API_PREFIX}/finance/summary?date_from=2026-09-01&date_to=2026-09-30&page=1&page_size=2", headers=headers).json()
    assert [item["order_item_id"] for item in page1["items"]] == list(reversed(order_item_ids))[:2]
    assert page1["pagination"] == {"page": 1, "page_size": 2, "total": 3, "total_pages": 2}
    # items_count — это общее число позиций месяца, а не размер текущей страницы.
    assert page1["items_count"] == 3

    page2 = client.get(f"{API_PREFIX}/finance/summary?date_from=2026-09-01&date_to=2026-09-30&page=2&page_size=2", headers=headers).json()
    assert [item["order_item_id"] for item in page2["items"]] == [order_item_ids[0]]


def test_manual_cost_correction_survives_unrelated_order_edit(client, integration_db_session, integration_admin):
    # Регрессия: полное редактирование заказа (PUT /orders/{id}) удаляет и заново
    # создаёт ВСЕ позиции (см. OrderRepository.update_with_items) — не только ту,
    # что реально поменялась. Без переноса ручной коррекции по identity (артикул)
    # правка количества у одной позиции незаметно стирала бы поправленную вручную
    # себестоимость/курс, откатывая её к автоснимку из прайса.
    headers = _admin_headers(client, integration_db_session, integration_admin)

    override_rate = client.put(
        f"{API_PREFIX}/finance/exchange-rates/2026-09-23",
        headers=headers,
        json={"exchange_rate_value": "80.0000"},
    )
    assert override_rate.status_code == 200

    create_product = client.post(
        f"{API_PREFIX}/products",
        headers=headers,
        json={"product_article": "FIN-TEST-EDIT", "product_name": "Edit Survives Product", "product_cost_usd": "5.00"},
    )
    assert create_product.status_code == 201

    reference_payload = client.get(f"{API_PREFIX}/reference-data", headers=headers).json()
    establishment_id = reference_payload["establishments"][0]["establishment_id"]
    order_method_id = reference_payload["order_methods"][0]["order_method_id"]
    shipped_status_id = _shipped_status_id(reference_payload)

    create_order_response = client.post(
        f"{API_PREFIX}/orders",
        headers=headers,
        json={
            "order_establishment_id": establishment_id,
            "order_method_id": order_method_id,
            "order_customer": "Edit Test",
            "order_info": "Тест",
            "items": [
                {
                    "product_article": "FIN-TEST-EDIT",
                    "product_name": "Edit Survives Product",
                    "order_item_quantity": 1,
                    "order_item_price": "50.00",
                    "order_item_status_id": shipped_status_id,
                }
            ],
        },
    )
    assert create_order_response.status_code == 201
    order = create_order_response.json()["item"]
    order_id = order["order_id"]
    order_item = order["items"][0]
    # До ручной коррекции — автоснимок из прайса (product_cost_usd=5.00, курс 80).
    assert float(order_item["order_item_cost_usd"]) == 5.0

    # Ревью в «Финансах»: поправили себестоимость вручную (реальная закупка вышла дороже).
    correction = client.put(
        f"{API_PREFIX}/finance/order-items/{order_item['order_item_id']}/cost",
        headers=headers,
        json={"order_item_cost_usd": "7.50", "order_item_cost_rate": "82.0000"},
    )
    assert correction.status_code == 200

    # Не связанная правка заказа: просто увеличили количество той же позиции.
    update_response = client.put(
        f"{API_PREFIX}/orders/{order_id}",
        headers=headers,
        json={
            "order_establishment_id": establishment_id,
            "order_method_id": order_method_id,
            "order_status_id": order["order_status_id"],
            "order_customer": "Edit Test",
            "order_info": "Тест",
            "items": [
                {
                    "product_article": "FIN-TEST-EDIT",
                    "product_name": "Edit Survives Product",
                    "order_item_quantity": 3,
                    "order_item_price": "50.00",
                    "order_item_status_id": shipped_status_id,
                }
            ],
        },
    )
    assert update_response.status_code == 200
    updated_item = update_response.json()["item"]["items"][0]
    assert updated_item["order_item_quantity"] == 3
    # Ручная коррекция должна пережить пересборку позиций, а не откатиться к автоснимку.
    assert float(updated_item["order_item_cost_usd"]) == 7.5
    assert float(updated_item["order_item_cost_rate"]) == 82.0


def test_expenses_list_respects_date_range_not_whole_months(client, integration_db_session, integration_admin):
    # Регрессия: список расходов должен реагировать на диапазон дат из фильтра, а не
    # всегда показывать целиком месяц даты «от» (иначе сужение диапазона внутри
    # того же месяца выглядит так, будто фильтр вообще ничего не делает).
    headers = _admin_headers(client, integration_db_session, integration_admin)

    create_category = client.post(
        f"{API_PREFIX}/finance/expense-categories",
        headers=headers,
        json={"finance_expense_category_name": "Аренда"},
    )
    category_id = create_category.json()["item"]["finance_expense_category_id"]

    sept_expense = client.post(
        f"{API_PREFIX}/finance/expenses",
        headers=headers,
        json={"finance_expense_category_id": category_id, "finance_expense_period": "2026-09-10", "finance_expense_amount": "100.00"},
    )
    assert sept_expense.status_code == 201

    oct_expense = client.post(
        f"{API_PREFIX}/finance/expenses",
        headers=headers,
        json={"finance_expense_category_id": category_id, "finance_expense_period": "2026-10-05", "finance_expense_amount": "200.00"},
    )
    assert oct_expense.status_code == 201

    only_september = client.get(f"{API_PREFIX}/finance/expenses?date_from=2026-09-01&date_to=2026-09-30", headers=headers)
    assert [e["finance_expense_amount"] for e in only_september.json()["items"]] == ["100.00"]

    both_months = client.get(f"{API_PREFIX}/finance/expenses?date_from=2026-09-01&date_to=2026-10-31", headers=headers)
    assert sorted(e["finance_expense_amount"] for e in both_months.json()["items"]) == ["100.00", "200.00"]

    only_october = client.get(f"{API_PREFIX}/finance/expenses?date_from=2026-10-01&date_to=2026-10-31", headers=headers)
    assert [e["finance_expense_amount"] for e in only_october.json()["items"]] == ["200.00"]

    # Сужение ВНУТРИ того же месяца (день в день, не по месяцу целиком) — тот самый
    # сценарий, из-за которого фильтр раньше выглядел нерабочим: расход от 10-го числа
    # не должен попадать в диапазон 1–9 сентября того же месяца.
    before_expense_day = client.get(f"{API_PREFIX}/finance/expenses?date_from=2026-09-01&date_to=2026-09-09", headers=headers)
    assert before_expense_day.json()["items"] == []

    including_expense_day = client.get(f"{API_PREFIX}/finance/expenses?date_from=2026-09-10&date_to=2026-09-10", headers=headers)
    assert [e["finance_expense_amount"] for e in including_expense_day.json()["items"]] == ["100.00"]


def test_finance_access_gated_by_crm_and_finance_sections(client, integration_db_session, integration_admin, integration_user):
    # «Финансы» — единственный раздел СРМ, где user_sections реально проверяется на
    # бэкенде (require_section в app/dependencies/auth.py), а не только скрывает
    # вкладку во фронте — иначе выдача доступа через «Разделы СРМ (веб)» была бы
    # обманкой: раздел был бы виден, но все запросы падали бы 403.
    integration_admin.user_password = hash_password("AdminPass123")
    integration_user.user_password = hash_password("WorkerPass123")
    integration_db_session.commit()
    admin_token = login(client, "admin", "AdminPass123")["token"]
    worker_headers = lambda: {"Authorization": f"Bearer {login(client, 'worker', 'WorkerPass123')['token']}"}  # noqa: E731

    summary_url = f"{API_PREFIX}/finance/summary?date_from=2026-09-01&date_to=2026-09-30"

    # Явно ограничили работнику разделы, finance среди них нет → 403.
    restrict = client.put(
        f"{API_PREFIX}/users/{integration_user.user_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"user_sections": ["chat"]},
    )
    assert restrict.status_code == 200
    assert client.get(summary_url, headers=worker_headers()).status_code == 403

    # Выдали crm+finance через «Разделы СРМ (веб)» → доступ появляется.
    grant = client.put(
        f"{API_PREFIX}/users/{integration_user.user_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"user_sections": ["chat", "crm", "finance"]},
    )
    assert grant.status_code == 200
    assert client.get(summary_url, headers=worker_headers()).status_code == 200

    # crm без finance (или наоборот) — всё ещё не хватает.
    partial = client.put(
        f"{API_PREFIX}/users/{integration_user.user_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"user_sections": ["chat", "crm"]},
    )
    assert partial.status_code == 200
    assert client.get(summary_url, headers=worker_headers()).status_code == 403


def test_summary_filters_by_shipped_date_not_order_created_date(client, integration_db_session, integration_admin):
    # Регрессия: свод фильтровал по дате СОЗДАНИЯ заказа — товар, отгруженный сегодня
    # из заказа недельной давности, не находился фильтром за сегодня. Позиция должна
    # находиться по дате её отгрузки (order_item_shipped_at), а не по order_created_at.
    headers = _admin_headers(client, integration_db_session, integration_admin)

    reference_payload = client.get(f"{API_PREFIX}/reference-data", headers=headers).json()
    establishment_id = reference_payload["establishments"][0]["establishment_id"]
    order_method_id = reference_payload["order_methods"][0]["order_method_id"]
    shipped_status_id = _shipped_status_id(reference_payload)

    # Создаём заказ ещё не отгруженным (дефолтный статус позиции).
    create_response = client.post(
        f"{API_PREFIX}/orders",
        headers=headers,
        json={
            "order_establishment_id": establishment_id,
            "order_method_id": order_method_id,
            "order_customer": "Старый заказ",
            "order_info": "Тест",
            "items": [
                {
                    "product_article": "FIN-TEST-SHIPDATE",
                    "product_name": "Ship Date Product",
                    "order_item_quantity": 1,
                    "order_item_price": "10.00",
                }
            ],
        },
    )
    assert create_response.status_code == 201
    order = create_response.json()["item"]
    order_id = order["order_id"]
    assert order["items"][0]["order_item_shipped_at"] is None

    # "Состарим" сам заказ в базе — как будто он оформлен неделю назад.
    order_row = integration_db_session.query(Order).filter(Order.order_id == order_id).one()
    order_row.order_created_at = datetime(2020, 1, 1)
    integration_db_session.commit()

    # Сегодня отгружаем эту позицию правкой заказа.
    update_response = client.put(
        f"{API_PREFIX}/orders/{order_id}",
        headers=headers,
        json={
            "order_establishment_id": establishment_id,
            "order_method_id": order_method_id,
            "order_status_id": order["order_status_id"],
            "order_customer": "Старый заказ",
            "order_info": "Тест",
            "items": [
                {
                    "product_article": "FIN-TEST-SHIPDATE",
                    "product_name": "Ship Date Product",
                    "order_item_quantity": 1,
                    "order_item_price": "10.00",
                    "order_item_status_id": shipped_status_id,
                }
            ],
        },
    )
    assert update_response.status_code == 200
    updated_item = update_response.json()["item"]["items"][0]
    assert updated_item["order_item_shipped_at"] is not None

    # Фильтр за дату СОЗДАНИЯ заказа (2020 год) больше не должен находить позицию.
    old_date_summary = client.get(f"{API_PREFIX}/finance/summary?date_from=2020-01-01&date_to=2020-01-01", headers=headers)
    assert old_date_summary.json()["items_count"] == 0

    # А фильтр за сегодняшний день (дата фактической отгрузки) — должен.
    today_summary = client.get(f"{API_PREFIX}/finance/summary?date_from=2026-09-23&date_to=2026-09-23", headers=headers)
    body = today_summary.json()
    assert body["items_count"] == 1
    assert body["items"][0]["order_item_id"] == updated_item["order_item_id"]
