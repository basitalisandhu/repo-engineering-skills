# Changelog

All notable changes to this project are documented here. The format follows Keep a Changelog, and the project uses semantic versioning.

## [Unreleased]

## [0.1.1] - 2026-10-04

The skill scripts are published as a container image on GitHub Packages, using only the workflow's `GITHUB_TOKEN`: `ghcr.io/basitalisandhu/repo-engineering-skills`, tagged `0.1.1` and `latest`, for linux/amd64 and linux/arm64, with an SPDX SBOM, a build provenance attestation and a keyless cosign signature. It also carries one skill change, the docs-truth-check environment-variable defaults (last item below).

### Added

- `scripts/cli.py`: a standard-library dispatcher, `repo-engineering <subcommand> [args]`, over the skill scripts (`docs-truth`, `repo-facts`, `audit-validate`, `context-lint`, `readme-check`, `test-gaps`), with `--help` listing the subcommands and `--version`; tests in `tests/test_cli.py`.
- `Dockerfile`: two stages on a digest-pinned `python:3.12-slim`, only the dispatcher and the skill scripts, no pip dependencies, uid 1000, `WORKDIR /work`, entrypoint `repo-engineering`.
- `publish-github-packages.yml`: on a `v*` tag, tests, checks that every version field matches the tag, builds, pushes, attests and signs the image, and creates the GitHub release with the SBOM attached. Pull requests that touch packaging run it as a dry run.
- CI job that builds the image and runs `--help`, every subcommand's `--help` and `--version`, and checks the user and working directory.
- README Install section with the `docker run` usage and the verify commands.
- `docs-truth-check` verifies documented environment-variable defaults when Python uses a literal `os.environ.get` or `os.getenv` default and reports dynamic defaults as unverified (#10, thanks @harshit3355).

## [0.1.0] - 2026-10-04

### Added

- Plugin marketplace `repo-engineering-skills` with one plugin, `repo-engineering`, and five skills, each with a tested standard-library script.
- `docs-truth-check`: `docs_truth_check.py` extracts paths, links, CLI flags and documented defaults, environment variables, symbols and config keys, versions, and npm and make targets from README, docs/, AGENTS.md and CLAUDE.md, and checks each against the working tree; statuses verified, missing, stale and unverified; JSON report; exit 1 on drift.
- `cited-codebase-audit`: `repo_facts.py` deterministic inventory, and `audit_validate.py`, which rejects findings whose `path:line` citations or quoted snippets do not resolve and prints acceptance stats.
- `agent-context-writer`: `context_lint.py` flags AGENTS.md and CLAUDE.md lines that restate manifests, list dependencies, pin runtimes already pinned, dump directory trees, name missing paths or give generic advice, and reports length against a budget.
- `readme-who-what-why`: `readme_check.py` scores what, who, why, install, example and where to ask in a README's first screen, flags hype words, and prints a to-do list.
- `test-gap-finder`: `test_gaps.py` ranks untested public functions and entry points for Python, JavaScript and TypeScript, and writes skipped or todo characterisation test stubs for pytest, unittest, jest, vitest and node:test.
- Fixture repositories with planted defects for every script, an offline pytest suite, `scripts/validate_plugin.py`, and a CI workflow that runs the tests, ruff, the validator, `claude plugin validate --strict`, and the docs and README checkers on this repository.
