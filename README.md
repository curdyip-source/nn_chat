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
| 🏷️ **Каталог** | Товары, складские остатки, регистрации товаров |
| 👤 **Пользователи** | Регистрация, роли, контакты, многосессийность |
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

**Frontend (админка)**
- Чистый **HTML5 + CSS3 + Vanilla JavaScript** (без фреймворков) — SPA-дашборд
- **Nginx 1.29** как статик-сервер и reverse proxy на API

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
├── .env.prod.example        # шаблон прод-переменных окружения
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

# Frontend (статика)
cd frontend
python -m http.server 8080 --directory .
```

> 📚 Интерактивная документация API доступна по адресу `/docs` (Swagger UI) после запуска бэкенда.

---

## ⚙️ Конфигурация

Все настройки задаются через `.env` (см. `.env.prod.example`). Ключевые параметры:

| Переменная | Назначение | Пример |
|------------|-----------|--------|
| `BACKEND_PORT` | внешний порт API | `32069` |
| `FRONTEND_PORT` | внешний порт админки | `25256` |
| `POSTGRES_HOST` / `POSTGRES_PORT` | подключение к БД | `db` / `5432` |
| `ACCESS_TOKEN_TTL_MINUTES` | время жизни access-токена | `30` |
| `REFRESH_TOKEN_TTL_DAYS` | время жизни refresh-токена | `30` |
| `APNS_TOPIC` | bundle id для push | `com.NufNaf.Vorobev` |
| `APNS_USE_SANDBOX` | окружение push | `false` |
| `CORS_ALLOW_ORIGINS` | разрешённые origin | `https://chat.nufnafchat.su` |

> 🔐 Для production обязательны сильные секреты (`AUTH_TOKEN_SECRET` ≥ 32 символов, `POSTGRES_PASSWORD` ≥ 16) и файл ключа APNs (`.p8`). Скрипт `ops/preflight_production.sh` проверит это за вас.

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
