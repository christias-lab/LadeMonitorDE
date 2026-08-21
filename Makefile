SHELL := /bin/bash

.PHONY: infra-up migrate demo-seed official-import backend-up down logs test test-backend test-mobile mobile-get mobile-run format lint contract

infra-up:
	docker compose up -d db redis minio minio-init

migrate:
	docker compose build api
	docker compose run --rm -v "$(CURDIR):/app" api alembic upgrade head

demo-seed:
	docker compose build ingestion
	docker compose run --rm -v "$(CURDIR):/app" ingestion python -m ladepulse_ingestion.demo --reset

official-import:
	docker compose build ingestion
	docker compose run --rm -v "$(CURDIR):/app" ingestion python -m ladepulse_ingestion.bnetza

backend-up:
	docker compose build api ingestion
	docker compose up -d api ingestion

down:
	docker compose down

logs:
	docker compose logs -f api ingestion

test: test-backend test-mobile

test-backend:
	docker compose build api
	docker compose run --rm -v "$(CURDIR):/app" api pytest

test-mobile:
	cd apps/mobile && flutter test

mobile-get:
	cd apps/mobile && flutter pub get

mobile-run:
	cd apps/mobile && flutter run \
		--dart-define=API_BASE_URL=$${API_BASE_URL:-http://10.0.2.2:8000} \
		--dart-define=DATA_MODE=$${DATA_MODE:-synthetic_demo}

format:
	docker compose build api
	docker compose run --rm -v "$(CURDIR):/app" api ruff format packages services
	cd apps/mobile && dart format lib test

lint:
	docker compose build api
	docker compose run --rm -v "$(CURDIR):/app" api ruff check packages services
	cd apps/mobile && flutter analyze

contract:
	docker compose build api
	docker compose run --rm -v "$(CURDIR):/app" api python -m ladepulse_api.export_openapi
