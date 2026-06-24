"""Сидер для локального дев-стека. Запускается backend-образом (есть доступ к БД и моделям).

Создаёт/повышает админа (admin / admin123) и добавляет пару товаров для проверки
поиска и Excel-импорта. Идемпотентен. Миграции засеивают непривилегированного
test_user, поэтому bootstrap через API недоступен — провижионим напрямую через ORM.
"""
from decimal import Decimal

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models import User
from app.models.reference_data import Product

ADMIN_LOGIN = "admin"
ADMIN_PASSWORD = "admin123"

SAMPLE_PRODUCTS = [
    ("BOLT-M6", "Болт М6", "0.50"),
    ("NUT-M6", "Гайка М6", "0.30"),
    ("WASHER-M6", "Шайба М6", "0.10"),
    ("CABLE-2X1", "Кабель 2x1", "1.20"),
    ("LAMP-LED9", "Лампа LED 9W", "3.40"),
]


def main():
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.user_login == ADMIN_LOGIN).first()
        if admin is None:
            admin = User(
                user_login=ADMIN_LOGIN,
                user_password=hash_password(ADMIN_PASSWORD),
                user_admin=True,
                user_active=True,
                user_first_name="Admin",
                user_second_name="Dev",
                user_age=30,
                user_address="dev",
            )
            db.add(admin)
            print("создан админ", flush=True)
        else:
            admin.user_password = hash_password(ADMIN_PASSWORD)
            admin.user_admin = True
            admin.user_active = True
            print("обновлён существующий админ", flush=True)
        db.commit()
        db.refresh(admin)

        for article, name, cost in SAMPLE_PRODUCTS:
            if db.query(Product).filter(Product.product_article == article).first():
                continue
            db.add(
                Product(
                    product_article=article,
                    product_name=name,
                    product_cost_usd=Decimal(cost),
                    product_owner_user_id=admin.user_id,
                )
            )
        db.commit()
        print(f"товаров в базе: {db.query(Product).count()}", flush=True)
        print(f"\nГотово. Логин: {ADMIN_LOGIN} / {ADMIN_PASSWORD}", flush=True)
    finally:
        db.close()


if __name__ == "__main__":
    main()
