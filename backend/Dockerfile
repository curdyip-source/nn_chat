FROM python:3.11.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
	PYTHONUNBUFFERED=1

WORKDIR /app

RUN addgroup --system app && adduser --system --ingroup app --home /app app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chown -R app:app /app

USER app

CMD ["sh", "-c", "python -m app.prestart && alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port 8000 --no-access-log"]