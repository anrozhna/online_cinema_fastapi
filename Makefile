.PHONY: up down migrate

up:
	docker compose up --build

down:
	docker compose down

migrate:
	docker compose exec app alembic upgrade head
