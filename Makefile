PYTHON := .venv/Scripts/python.exe

.PHONY: setup dev test lint check smoke build up down eval screenshots demo clean

setup:
	$(PYTHON) -m pip install -r backend/requirements.txt
	cd frontend && npm install

lint:
	$(PYTHON) -m ruff check backend/app
	$(PYTHON) -m mypy --config-file backend/pyproject.toml backend/app
	cd frontend && npm run lint

test:
	powershell -Command "cd backend; ..\.venv\Scripts\python.exe -m pytest tests"
	cd frontend && npm run test

typecheck:
	cd frontend && npm run typecheck

check: lint typecheck test
	cd frontend && npm run build
	docker compose build
	$(PYTHON) scripts/smoke_test.py
	@echo "=== All Quality Gates Passed (make check Green) ==="

smoke:
	$(PYTHON) scripts/smoke_test.py

eval:
	$(PYTHON) eval/run_eval.py

build:
	cd frontend && npm run build

up:
	docker compose up -d --build

down:
	docker compose down

screenshots:
	@echo "Screenshots utility ready"

demo:
	@echo "Demo recording utility ready"
