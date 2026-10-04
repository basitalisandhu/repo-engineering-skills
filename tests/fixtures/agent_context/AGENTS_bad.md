# Agent notes

Run the tests with `npm run test` and lint with `make lint`.

This project uses express, zod and vitest with Node 20.

```text
src/
├── billing/
└── index.ts
```

Routing lives in `src/legacy/router.ts`.

Write clean code and follow best practices.

Seed the database with `./scripts/seed-db.sh` before the API tests; it is not in package.json.

Never log card numbers from `src/billing/`.
