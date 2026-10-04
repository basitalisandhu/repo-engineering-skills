# Onboarding: inventory

The project is the Python package `inventory` and needs Python `>=3.11` (pyproject.toml:4).

## Run it

The console script `inventory` calls `inventory.cli:main` [F7]. Locally:

```bash
pip install -e .
make run
```

The web front end lives in `web/` and starts with `cd web && npm run start`.

## Test it

Tests live under `tests/` and run with:

```bash
python -m pytest -q
```

## Configuration

The CLI reads `DATABASE_URL` and `INVENTORY_LOG_LEVEL`; the front end reads `API_BASE_URL`.
Local development uses PostgreSQL from `docker-compose.yml`.

## Who owns what

Everything defaults to @acme/platform, and `/web/` belongs to @acme/frontend.

Welcome aboard, and ask questions early.
