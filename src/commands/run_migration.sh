#!/bin/sh

set -e

export PYTHONPATH="/app/src:${PYTHONPATH}"

ALEMBIC_CONFIG="/app/alembic.ini"
MIGRATIONS_DIR="/app/src/database/migrations/versions"

echo "Checking for changes before generating a migration..."

# Ensure the migrations folder exists
if [ ! -d "$MIGRATIONS_DIR" ]; then
    echo "Migrations folder does not exist. Creating it..."
    mkdir -p "$MIGRATIONS_DIR"
fi

export PGPASSWORD="$POSTGRES_PASSWORD"

if ! psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "\dt" | grep -q "alembic_version"; then
    echo "Alembic version table not found. Applying all migrations..."

    if [ -z "$(ls -A "$MIGRATIONS_DIR")" ]; then
        echo "No migration files found. Generating initial migration..."
        alembic -c "$ALEMBIC_CONFIG" revision --autogenerate -m "initial migration"
    fi

    echo "Applying all migrations..."
    alembic -c "$ALEMBIC_CONFIG" upgrade head

    echo "Running database seed script..."
    python -m database.seed
    echo "Database seed script completed."
else
    if ! alembic -c "$ALEMBIC_CONFIG" revision --autogenerate -m "temp_migration"; then
        echo "Error generating migration. Exiting."
        exit 1
    fi

    LAST_MIGRATION=$(find "$MIGRATIONS_DIR" -type f -name "*.py" -printf '%T+ %p\n' | sort | tail -n 1 | awk '{print $2}')

    echo "Generated migration content:"
    cat "$LAST_MIGRATION"

    if grep -qE '^\s*pass\s*$' "$LAST_MIGRATION"; then
        echo "No changes detected. Deleting temporary migration."
        rm "$LAST_MIGRATION"
    else
        echo "Changes detected. Applying migration."
        alembic -c "$ALEMBIC_CONFIG" upgrade head
    fi

    echo "Running database seed script..."
    python -m database.seed
    echo "Database seed script completed."
fi

echo "Starting application..."
exec uvicorn main:app --host 0.0.0.0 --port 8000 --reload --app-dir src
