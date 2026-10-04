# Onboarding: inventory

The project is the Python package `inventory` (pyproject.toml:2).

Start the API with `npm run serve`.

The HTTP handlers live in `inventory/server.py`.

Sessions are cached in Redis, configured by `REDIS_URL`.

The billing module is owned by @acme/backend.

The entry point is defined at (inventory/cli.py:99).

The service talks to the payment gateway over a private link.

Tests live under `tests/` and run with `python -m pytest -q`.
