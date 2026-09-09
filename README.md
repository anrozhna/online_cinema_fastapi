# Online Cinema (FastAPI)

## Local setup

1. Copy the environment file and adjust values if needed:

```bash
   cp .env.sample .env
```

2. Build and start the app together with Postgres:

```bash
   make up
```

   The API will be available at http://localhost:8000, with interactive docs
   at http://localhost:8000/docs.

3. Stop the containers:

```bash
   make down
```

## Database migrations (Alembic)

Migrations live in `src/database/migrations` and use SQLAlchemy's async
engine. The connection URL is built from `Settings` (`src/config/settings.py`),
which reads the same `POSTGRES_*` variables as `.env` — there is nothing to
configure separately in `alembic.ini`.

Run migrations inside the running `app` container:

```bash
make migrate
```

To create a new migration after changing/adding models:

```bash
docker compose exec app alembic revision --autogenerate -m "describe the change"
```

Then review the generated file in `src/database/migrations/versions/` before
applying it with `make migrate`.
