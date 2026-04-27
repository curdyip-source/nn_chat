from __future__ import annotations

import argparse
import csv
from decimal import Decimal, InvalidOperation
from pathlib import Path

from app.core.database import SessionLocal, wait_for_database
from app.models.reference_data import Product


def normalize_text(value: str | None) -> str:
    if value is None:
        return ""
    return value.replace("\u00a0", " ").strip()


def split_insert_rows(values_block: str) -> list[str]:
    rows: list[str] = []
    current: list[str] = []
    depth = 0
    in_string = False
    escape = False

    for char in values_block:
        if escape:
            current.append(char)
            escape = False
            continue

        if char == "\\":
            current.append(char)
            escape = True
            continue

        if char == "'":
            current.append(char)
            in_string = not in_string
            continue

        if not in_string and char == "(":
            if depth == 0:
                current = []
            else:
                current.append(char)
            depth += 1
            continue

        if not in_string and char == ")":
            depth -= 1
            if depth == 0:
                rows.append("".join(current))
                current = []
            else:
                current.append(char)
            continue

        if depth > 0:
            current.append(char)

    return rows


def parse_insert_statement(statement: str) -> list[tuple[str, str, Decimal]]:
    if "VALUES" not in statement:
        return []

    values_block = statement.split("VALUES", 1)[1].rsplit(";", 1)[0]
    parsed_rows: list[tuple[str, str, Decimal]] = []

    for row in split_insert_rows(values_block):
        fields = next(csv.reader([row], delimiter=",", quotechar="'", escapechar="\\", skipinitialspace=True))
        if len(fields) < 3:
            continue

        article = normalize_text(fields[0])
        name = normalize_text(fields[1])
        cost_raw = normalize_text(fields[2])

        if not article or not name or not cost_raw or cost_raw.upper() == "NULL":
            continue

        try:
            cost = Decimal(cost_raw)
        except InvalidOperation:
            continue

        parsed_rows.append((article, name, cost))

    return parsed_rows


def iter_products_from_dump(sql_dump_path: Path) -> list[tuple[str, str, Decimal]]:
    products: list[tuple[str, str, Decimal]] = []
    statement_lines: list[str] = []
    collecting = False

    with sql_dump_path.open("r", encoding="utf-8") as sql_file:
        for line in sql_file:
            if line.startswith("INSERT INTO `NufNaf_Products`"):
                collecting = True
                statement_lines = [line]
                if line.rstrip().endswith(";"):
                    products.extend(parse_insert_statement("".join(statement_lines)))
                    collecting = False
                continue

            if collecting:
                statement_lines.append(line)
                if line.rstrip().endswith(";"):
                    products.extend(parse_insert_statement("".join(statement_lines)))
                    collecting = False

    return products


def import_products(sql_dump_path: Path) -> tuple[int, int, int]:
    wait_for_database()
    db = SessionLocal()
    created_count = 0
    updated_count = 0
    skipped_count = 0

    try:
        existing_by_article = {
            normalize_text(product.product_article): product
            for product in db.query(Product).all()
        }

        for article, name, cost in iter_products_from_dump(sql_dump_path):
            existing = existing_by_article.get(article)
            if existing is None:
                db.add(
                    Product(
                        product_article=article,
                        product_name=name,
                        product_cost_usd=cost,
                        product_owner_user_id=None,
                    )
                )
                created_count += 1
                continue

            if existing.product_name != name or existing.product_cost_usd != cost:
                existing.product_name = name
                existing.product_cost_usd = cost
                updated_count += 1
            else:
                skipped_count += 1

        db.commit()
        return created_count, updated_count, skipped_count
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Import products from NufNaf SQL dump into products table.")
    parser.add_argument("sql_dump_path", help="Path to NufNaf_Products SQL dump file")
    args = parser.parse_args()

    sql_dump_path = Path(args.sql_dump_path).expanduser().resolve()
    if not sql_dump_path.exists():
        raise FileNotFoundError(f"SQL dump not found: {sql_dump_path}")

    created_count, updated_count, skipped_count = import_products(sql_dump_path)
    print(
        f"Import completed. Created: {created_count}, updated: {updated_count}, skipped unchanged: {skipped_count}",
    )


if __name__ == "__main__":
    main()