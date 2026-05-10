.PHONY: up down logs test lint fmt build

up:
	docker compose up --build -d

down:
	docker compose down -v

logs:
	docker compose logs -f --tail=200

test:
	@for s in services/api-gateway services/patient-service services/ai-engine services/auth-service services/notification-service; do \
		echo "▶ $$s"; (cd $$s && pytest -q) || exit 1; \
	done

lint:
	ruff check services shared
	black --check services shared
	mypy services shared || true

fmt:
	ruff check --fix services shared
	black services shared

build:
	docker compose build
