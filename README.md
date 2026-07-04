<div align="center">

# 💬 NufNaf Chat — Backend & Admin

**Серверная часть и веб-панель администратора корпоративного чата с CRM-модулем NufNaf.**

Чат в реальном времени, заказы, склад, документы и push-уведомления — всё в одном API.

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.135-009688?logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17-4169E1?logo=postgresql&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-CA2C2C)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)
![Nginx](https://img.shields.io/badge/Nginx-1.29-009639?logo=nginx&logoColor=white)

</div>

---

## 📖 О проекте

**NufNaf Chat** — это бэкенд и веб-админка корпоративной B2B-платформы, объединяющей **командный чат** и **CRM**. Сервер обслуживает iOS-клиент ([nn_chat-swift](../nn_chat-swift)) и веб-панель администратора, через которую можно управлять заказами, складом, контактами, справочниками и перепиской — без мобильного приложения.

Под капотом — асинхронный REST API на **FastAPI**, JWT-авторизация с поддержкой нескольких устройств, нативные **push-уведомления Apple (APNs)** с маршрутизацией по окружению, аудит всех действий и готовый CI/CD-конвейер с деплоем на VPS.

---

## ✨ Возможности

| Модуль | Что умеет |
|--------|-----------|
| 💬 **Сообщения** | Создание, редактирование, удаление, пагинация, вложения и ответы (reply) |
| 📎 **Вложения** | Загрузка файлов и медиа к сообщениям и заказам |
| 📦 **Заказы** | CRUD, статусы, маршруты, чекпоинты, комментарии с файлами |
| 🚚 **СДЭК** | Создание накладной (город/ПВЗ по названию), PDF-накладные в чат заказа, статусы через вебхук, ПВЗ отправителя, пересоздание |
| 🏷️ **Каталог** | Товары, складские остатки, регистрации товаров |
| 👤 **Пользователи** | Регистрация, роли, контакты, многосессийность |
| 🔑 **Доступы** | Гибкие права: области (свои/склад) на просмотр/создание/редактирование/удаление по каждому складу + разделы меню и режимы приложения (чат/СРМ/прайс). Применяются реалтайм (SSE), раздаёт админ |
| 📱 **Устройства** | Регистрация iOS-устройств для push-уведомлений |
| 🔔 **APNs** | Push через Apple с автоматической маршрутизацией sandbox / production |
| 🔐 **Авторизация** | JWT (access + refresh), хеширование паролей, защита по CORS |
| 📋 **Аудит** | Логирование всех значимых действий (create / update / delete) |
| 📊 **Справочники** | Статусы, категории, валюты и прочие lookup-таблицы |
| 📄 **Документы** | Хранение и управление бизнес-документами |

---

## 🛠️ Технологический стек

**Backend**
- **Python 3.11** + **FastAPI** + **Uvicorn** — асинхронный REST API
- **SQLAlchemy 2.0** — ORM, **Alembic** — миграции
- **PyJWT** — токены доступа и обновления (access / refresh)
- **httpx** — клиент для APNs и внешних сервисов
- **Sentry** — трекинг ошибок (опционально)
- **openpyxl** — экспорт/импорт Excel
- **pytest** — тесты

**Frontend (веб-админка, `web/`)**
- **React + Vite + TypeScript** — SPA-дашборд (сборка статики)
- **Nginx** как статик-сервер и reverse proxy на API (и на `/price-api` → бэкенд прайса)

**Инфраструктура**
- **PostgreSQL 17** — основная БД
- **Docker Compose** — стек из трёх сервисов: `db`, `backend`, `frontend`
- **GitHub Actions** + **GHCR** — CI/CD, сборка образов и деплой на VPS

---

## 🗂️ Структура репозитория

```
nn_chat/
├── backend/             # FastAPI-приложение
│   ├── app/
│   │   ├── api/routes/  # эндпоинты: auth, messages, orders, products, ...
│   │   ├── models/      # SQLAlchemy-модели
│   │   └── ...
│   ├── alembic/         # миграции БД
│   └── requirements.txt
├── web/                     # веб-фронт (React + Vite)
├── ops/                     # скрипты сборки, деплоя, бэкапа и проверок
├── docker-compose.yml       # локальный стек: db + backend + web + сидер
├── docker-compose.prod.yml  # прод-стек для сервера (образы из GHCR)
├── .env.example             # локальный шаблон (порты/БД; прод — в DEPLOYMENT.md)
└── DEPLOYMENT.md            # подробная инструкция по деплою
```

---

## 🚀 Быстрый старт

### Вариант 1 — Docker Compose (локальный стек)

`docker-compose.yml` поднимает локальный стек (Postgres + backend + web + сидер),
секреты и `.env` не нужны:

```bash
docker compose up --build
```

После запуска:
- 🌐 Веб — `http://localhost:8088` (логин: `admin` / `admin123`)
- ⚙️ API — `http://localhost:8001`
- ❤️ Health-check — `http://localhost:8001/api/v1/health/live`

Прод-стек для сервера — `docker-compose.prod.yml` + `.env` (из секрета CI),
см. [DEPLOYMENT.md](DEPLOYMENT.md).

### Вариант 2 — локальная разработка

```bash
# PostgreSQL
docker run -d --name postgres \
  -e POSTGRES_USER=app_user -e POSTGRES_PASSWORD=app_pass \
  -e POSTGRES_DB=appdb -p 5432:5432 postgres:17-alpine

# Backend
cd backend
pip install -r requirements.txt
alembic upgrade head
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Frontend (web/, React + Vite)
cd web
npm install
npm run dev
```

> 📚 Интерактивная документация API доступна по адресу `/docs` (Swagger UI) после запуска бэкенда.

---

## ⚙️ Конфигурация

**Локально** (`docker-compose.yml`) всё работает на дефолтах — `.env` не обязателен.
Чтобы переопределить, скопируй `.env.example` → `.env` (в `.gitignore`). Локальные параметры:

| Переменная | Назначение | Дефолт |
|------------|-----------|--------|
| `WEB_PORT` / `API_PORT` / `PG_PORT` | порты на хосте | `8088` / `8001` / `5433` |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | локальная БД | `app_user` / `app_pass` / `appdb` |
| `AUTH_TOKEN_SECRET` | dev-секрет единого входа с прайсом | `dev-secret-change-me` |
| `CORS_ALLOW_ORIGINS` | разрешённые origin | `*` |

**Прод** конфигурируется отдельно — серверный `.env` живёт в GitHub-секрете
`PRODUCTION_ENV_FILE` (полный шаблон и переменные — в [DEPLOYMENT.md](DEPLOYMENT.md)).
Там же — про сильные секреты и ключ APNs (`.p8`); `ops/preflight_production.sh` их проверит.

---

## 🔧 Операционные скрипты (`ops/`)

| Скрипт | Назначение |
|--------|-----------|
| `release_build.sh` | сборка Docker-образов backend и frontend |
| `release_push.sh` | публикация образов в GHCR |
| `release_deploy.sh` | деплой на VPS + health-check |
| `rollback_to_tag.sh` | откат на предыдущий релиз |
| `preflight_production.sh` | валидация production `.env` |
| `post_deploy_check.sh` | smoke-тесты после деплоя |
| `backup_postgres.sh` / `restore_postgres.sh` | бэкап и восстановление БД |

---

## 📦 Деплой

Деплой автоматизирован через **GitHub Actions**: пуш в `main` запускает тесты (`pytest`), собирает и публикует образы в **GHCR**, после чего по SSH разворачивает стек на VPS и прогоняет smoke-тесты.

Подробности — в [`DEPLOYMENT.md`](./DEPLOYMENT.md).

---

## 🔗 Связанные проекты

- 📱 [**nn_chat-swift**](../nn_chat-swift) — iOS-клиент (SwiftUI + UIKit)
