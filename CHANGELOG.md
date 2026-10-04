# Changelog

All notable changes to this project are documented here. The format follows Keep a Changelog, and the project uses semantic versioning.

## [Unreleased]

## [0.1.0] - 2026-10-04

### Added

- Plugin marketplace `repo-engineering-skills` with one plugin, `repo-engineering`, and five skills, each with a tested standard-library script.
- `docs-truth-check`: `docs_truth_check.py` extracts paths, links, CLI flags and documented defaults, environment variables, symbols and config keys, versions, and npm and make targets from README, docs/, AGENTS.md and CLAUDE.md, and checks each against the working tree; statuses verified, missing, stale and unverified; JSON report; exit 1 on drift.
- `cited-codebase-audit`: `repo_facts.py` deterministic inventory, and `audit_validate.py`, which rejects findings whose `path:line` citations or quoted snippets do not resolve and prints acceptance stats.
- `agent-context-writer`: `context_lint.py` flags AGENTS.md and CLAUDE.md lines that restate manifests, list dependencies, pin runtimes already pinned, dump directory trees, name missing paths or give generic advice, and reports length against a budget.
- `readme-who-what-why`: `readme_check.py` scores what, who, why, install, example and where to ask in a README's first screen, flags hype words, and prints a to-do list.
- `test-gap-finder`: `test_gaps.py` ranks untested public functions and entry points for Python, JavaScript and TypeScript, and writes skipped or todo characterisation test stubs for pytest, unittest, jest, vitest and node:test.
- Fixture repositories with planted defects for every script, an offline pytest suite, `scripts/validate_plugin.py`, and a CI workflow that runs the tests, ruff, the validator, `claude plugin validate --strict`, and the docs and README checkers on this repository.
