# Agent notes

- Seed the database with `./scripts/seed-db.sh` before the API tests; it is not wired into package.json.
- Never log card numbers or tokens from `src/billing/`; the payment provider audits our logs.
- Do not edit generated files under `src/billing/`, change the schema first and regenerate.
- Ask before changing anything that touches refunds: finance reconciles them by hand each Friday.
