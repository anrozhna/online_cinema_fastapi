# Online Cinema (FastAPI)

An async FastAPI backend for an online movie rental/purchase platform:
accounts with JWT auth, a movie catalog with comments/ratings/reactions,
a shopping cart, and admin/moderator tooling — built with a strict
layered architecture (`routes → services → repositories → database`).

## Tech stack

- **FastAPI** + **Pydantic v2** — API layer and schemas
- **SQLAlchemy 2.0 (async)** + **Alembic** — ORM and migrations
- **PostgreSQL** — primary database
- **Redis** + **Celery** — background tasks (emails, periodic cleanup)
- **MinIO** (S3-compatible) — avatar/file storage
- **Poetry** — dependency management
- **Docker Compose** — local orchestration of all services

## Local setup

1. Copy the environment file and adjust values if needed:

   ```bash
   cp .env.sample .env
   ```

2. Build and start everything (app, Postgres, Redis, Celery worker/beat,
   MinIO):

   ```bash
   docker compose up --build
   ```

   The API is available at http://localhost:8000, interactive docs at
   http://localhost:8000/docs. MinIO console is at http://localhost:9001.

3. On container start, `src/commands/run_migration.sh` automatically
   applies any pending Alembic migrations and seeds default data
   (user groups). No manual migration step is needed for a fresh setup.

4. Stop everything:

   ```bash
   docker compose down
   ```

## Database migrations (Alembic)

Migrations live in `src/database/migrations` and use SQLAlchemy's async
engine. The connection URL is built from `Settings`
(`src/config/settings.py`), which reads the same `POSTGRES_*` variables
as `.env`.

To create a new migration after changing/adding models:

```bash
docker compose exec app alembic revision --autogenerate -m "describe the change"
docker compose exec app alembic upgrade head
```

Always review the generated migration file before applying it —
autogenerate doesn't always infer constraint names or complex changes
correctly.

## Architecture

The codebase is organized by **layer**, not by feature folder. Each
layer has a strict, one-directional dependency on the layer below it:

```
routes  →  services  →  repositories  →  database
```

- **`routes/`** — thin FastAPI routers. Each endpoint does nothing but
  validate input (via Pydantic) and call exactly one service method.
- **`services/`** — business logic and transaction orchestration
  (commit/rollback, coordinating multiple repositories, calling
  Celery tasks). Services never write raw SQL.
- **`repositories/`** — the only layer allowed to use SQLAlchemy
  `select`/`execute` directly. One repository per model or closely
  related group of models (e.g. `MovieRepository`,
  `NamedEntityRepository` for Genre/Star/Director/Certification).
- **`database/`** — SQLAlchemy models, the async session/engine
  (`database/session.py`), and Alembic migrations.

`config/settings.py` and `database/session.py` intentionally sit below
`config/dependencies.py` in this chain — `get_settings` and `get_db`
are defined there specifically to avoid circular imports, since
`repositories/` and `services/` both depend on them.

```
src/
├── config/
│   ├── settings.py       # Settings, TestingSettings, get_settings
│   └── dependencies.py   # DI aliases (DataBase, GetSettings, *Repo, *ServiceDep)
├── database/
│   ├── models/           # accounts.py, movies.py, cart.py
│   ├── migrations/       # Alembic
│   ├── session.py        # engine, AsyncSessionLocal, get_db, DataBase
│   ├── seed.py           # idempotent default-data seeding (user groups)
│   └── validators/       # model-adjacent validators (email, password)
├── repositories/         # one file per model/group; NamedEntityRepository,
│                         # BaseMovieRepository shared base classes
├── services/             # business logic; one service per bounded concern
├── schemas/              # Pydantic schemas, grouped by domain
├── routes/               # thin routers
├── security/             # password hashing, JWT, token hashing
├── validation/           # standalone input validation (profile fields)
├── notifications/        # EmailSender, Celery tasks, Jinja2 templates
├── storages/             # S3/MinIO client wrapper
├── exceptions/           # custom exception hierarchies
├── commands/             # entrypoint script, one-off scripts
└── tests/
    ├── test_unit/        # sync SQLite model-mapping tests, mocked-repo service tests
    ├── test_security/    # password hashing, JWT, token hashing — no DB, no app
    └── test_integration/ # async httpx tests against the real FastAPI app
```

## What's implemented so far

### Accounts
- Registration with email activation (Celery-delivered email)
- Login / refresh / logout with **hashed** refresh tokens (SHA-256 —
  a database leak alone cannot be used to obtain working sessions)
- Password change and forgot/reset-password flow
- User profile with avatar upload (MinIO), partial updates via `PATCH`
- Role-based access: `USER`, `MODERATOR`, `ADMIN` via a generic
  `require_roles(*allowed_groups)` dependency factory
- `routes/user_management.py` (admin-only: role assignment, manual
  activation) is kept separate from `routes/catalog_management.py`
  (admin **or** moderator: catalog CRUD) — same underlying
  `require_roles` factory, different allowed groups

### Movies catalog
- Genres, Stars, Directors, Certifications (simple reference entities,
  full CRUD via a generic `NamedEntityCrud` used by every entity type)
- Movies with a public UUID (used in URLs) separate from the internal
  integer `id`, and a composite unique constraint on
  `(name, year, time)`
- Paginated list with filtering (year, min IMDb), search (title,
  description, director, star names), and sorting (price, year, imdb)
- Comments with nested replies (`parent_comment_id`); the reply tree is
  built in the service layer from a flat query result, deliberately
  avoiding recursive `selectinload` (which can't express unbounded
  depth) and avoiding lazy-loading `Comment.replies` in an async
  context
- 10-point ratings and like/dislike reactions, both upsert (one row per
  user+movie, updated in place on repeat calls)
- Favorites: add/remove/list, with the same filter/search/sort support
  as the main catalog (shared query-building logic lives in
  `BaseMovieRepository`)
- Email notification when a comment receives a reply

### Cart
- One cart per user, created lazily on first access
- Add/remove/view/clear, with duplicate-item protection at the DB level
- Admin/moderator can view any user's cart by ID
  (`GET /cart/users/{user_id}/`)
- Deleting a movie that's present in one or more carts emails every
  moderator a notification, before the cascade delete removes the
  corresponding cart items
- `checkout` currently clears the cart; it's wired end-to-end and
  marked with `TODO(orders)` for the real order-creation flow once
  `Order`/`OrderItem` exist

### Orders
- Placing an order (`POST /orders/`) converts the current cart into an
  `Order` + `OrderItem` rows; each `OrderItem` **snapshots** the
  movie's price at the time of ordering (`price_at_order`), so a later
  price change never retroactively affects an existing order
- Movies already purchased (a `PAID` order item for the same user) or
  already sitting in another `PENDING` order are excluded from the new
  order, and the user is emailed a list of what was excluded
- `OrderItem.movie_id` uses `ondelete="RESTRICT"` (unlike
  `CartItem.movie_id`, which cascades) — the database itself refuses to
  delete a movie that has ever been ordered. `MovieService.delete_movie`
  catches the resulting `IntegrityError` and turns it into a clean
  `409`, which is what finally replaced the long-standing
  `TODO(orders)` placeholder
- Order lifecycle: `PENDING` → `CANCELED` (by the owner, before
  payment) or `PENDING` → `PAID` → `REFUNDED` (refund is a direct
  status flip for now, with no separate approval step)
- `OrderService.revalidate_total_amount` recomputes the total from
  stored `OrderItem` snapshots — not called anywhere yet, but ready for
  the future Payments flow to use as the source of truth right before
  charging
- Admin/moderator can list all orders across all users, filterable by
  user ID, status, and creation date range (`GET /orders/admin/`)
- There is currently no way to transition an order to `PAID` through
  the API — that arrives with the Stripe webhook in the Payments phase

### Cross-cutting
- CI: lint, mypy, pytest with coverage, on every PR
- MinIO images pulled from `quay.io` (not Docker Hub, where the
  official images are unavailable without authentication)
- bcrypt rounds are configurable (`Settings.BCRYPT_ROUNDS`); tests run
  with a low round count for speed, production keeps the strong
  default

## Running tests

```bash
poetry run pytest tests/ -v
```

- `tests/test_unit/` uses synchronous SQLite for model-mapping tests
  (fast, no async plumbing needed for pure ORM checks) and mocked
  repositories for service-level business-rule tests.
- `tests/test_security/` tests pure, side-effect-free security logic in
  isolation — password hashing/complexity validation, JWT
  encoding/decoding, refresh-token hashing — none of it touches a
  database or the FastAPI app.
- `tests/test_integration/` uses async SQLite (StaticPool, one shared
  connection) with the real FastAPI app and `httpx.AsyncClient`,
  exercising the full `routes → services → repositories` stack.
- `ENVIRONMENT=testing` is set for the whole test session, which
  switches `get_settings()` to `TestingSettings` (weak bcrypt rounds,
  test secrets) — see `pyproject.toml`'s `pytest-env` configuration.

## Known follow-ups

- `checkout` needs the real `Order`/`OrderItem` creation flow to move
  from "clears the cart" to actually placing an order — **this is now
  implemented** via `POST /orders/`, but the standalone `POST
  /cart/checkout/` endpoint itself hasn't been updated to call it yet.
- There is no way to mark an order `PAID` yet — that requires the
  Stripe webhook from the Payments phase. `feature/orders-notifications`
  (order confirmation email) is deferred until then, since it only
  makes sense once a real "successful payment" event exists.
- `delete_movie`'s old `TODO(orders)` placeholder is resolved: the
  database itself now rejects deleting a movie that's ever been
  ordered, via `OrderItem.movie_id`'s `ondelete="RESTRICT"` foreign key.
