FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends postgresql-client \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml poetry.lock ./

RUN pip install --no-cache-dir poetry \
    && poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi

COPY alembic.ini .
COPY src/ ./src

RUN chmod +x src/commands/run_migration.sh

EXPOSE 8000

ENTRYPOINT ["src/commands/run_migration.sh"]