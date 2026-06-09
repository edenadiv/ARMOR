.PHONY: install test test-cov lint format typecheck up down clean frontend-install frontend-dev

VENV := .venv

# On Windows, standard CPython venvs use Scripts/; on Unix they use bin/.
# Use the Windows `py -3.11` launcher so we pick python.org CPython (which has
# prebuilt numpy/scikit-learn wheels), not an MSYS2 Python.
ifeq ($(OS),Windows_NT)
	VENV_BIN := $(VENV)/Scripts
	BOOTSTRAP_PY := py -3.11
else
	VENV_BIN := $(VENV)/bin
	BOOTSTRAP_PY := python3.11
endif

PY := $(VENV_BIN)/python
PIP := $(VENV_BIN)/pip

install:
	$(BOOTSTRAP_PY) -m venv $(VENV)
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install -e ".[dev]"

test:
	$(VENV_BIN)/pytest

acceptance:
	$(VENV_BIN)/pytest tests/acceptance -v

validate:
	$(PY) -m cdmas.validator

test-cov:
	$(VENV_BIN)/pytest --cov=cdmas --cov-report=term-missing --cov-report=html

lint:
	$(VENV_BIN)/ruff check src tests

format:
	$(VENV_BIN)/ruff format src tests
	$(VENV_BIN)/ruff check --fix src tests

typecheck:
	$(PY) -m mypy

up:
	docker compose up --build

down:
	docker compose down -v

frontend-install:
	cd frontend && npm install

frontend-dev:
	cd frontend && npm run dev

clean:
	rm -rf $(VENV) .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
