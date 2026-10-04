# Changelog

All notable changes to this project are documented here. The format follows Keep a Changelog, and the project uses semantic versioning.

## [Unreleased]

### Changed

- `docs-truth-check` also verifies environment defaults read through `from os import environ, getenv`, including aliased imports (#13, thanks @harshit3355).

## [0.2.0] - 2026-10-04

Five new skills, each with a standard-library script, a planted-defect fixture and tests, and seven new dispatcher subcommands. The container image now includes git for the two history-based skills.

### Added

- `repo-onboarding-guide`: `onboarding_facts.py` extracts the facts an onboarding guide needs (project, entry points, run and test commands from manifests and CI, test locations, a directory map with purposes from docstrings or names, environment variables and services, CODEOWNERS), each with a `path:line` citation; `onboarding_lint.py` flags guide sentences that name a command, path, variable, service or owner with no matching fact, citations not in the facts, and relationship claims that name nothing checkable. The skill runs `docs-truth-check` on the finished guide.
- `restructure-planner`: `restructure_plan.py` builds a file-level import graph (Python with `ast`, JS and TS with regex over import, export-from, require and dynamic import), reports coupling, file and package cycles, files importing from many packages and god modules with the names each package uses, and proposes a move plan for `--goal split|merge|boundaries` as a table (file, from, to, reason, blast radius) with `git mv` commands that are printed and never run.
- `adr-miner`: `adr_mine.py` finds decision candidates in commit messages, dependency, Dockerfile and CI changes, and rationale comments, and drafts MADR stubs (status proposed) that cite the commit SHA; `adr_lint.py` checks an ADR folder for numbering gaps, duplicate numbers, missing or unknown status, superseded ADRs without a replacement link, broken ADR links and missing back-references.
- `repo-hygiene-bundle`: `hygiene.py` runs offline checks for manifests without lockfiles, lockfile drift, one dependency at several versions across workspaces, licence file and SPDX fields, secret-shaped strings (redacted in all output), actions not pinned to a commit SHA, write-all workflow permissions, missing SECURITY.md and CODE_OF_CONDUCT.md, large files and committed build output; table, JSON or SARIF 2.1.0, with `--fail-on` for CI.
- `release-notes-verifier`: `release_notes_verify.py` compares a CHANGELOG section or a notes file with the commits between two revisions, flagging notes with no matching commit, commits with no note (chores excluded by `--chore-pattern`), manifest versions that disagree with the tag, and missing compare, reference or relative links. Pull request titles are read with `gh pr view` only when `--gh` is passed.
- Dispatcher subcommands `onboarding`, `onboarding-lint`, `restructure`, `adr`, `adr-lint`, `hygiene` and `release-notes`, with tests.
- Six new tasks in `docs/good-first-issues.md`.

### Changed

- The container image installs git and marks `/work` as a git safe directory, so `adr` and `release-notes` work on a mounted repository.
- `adr_mine.py`, `release_notes_verify.py` and `hygiene.py` run read-only git commands with fixed argument lists and no shell; CONTRIBUTING, SECURITY and the README security posture say so.
- Version 0.2.0 in `plugin.json`, `marketplace.json` and `scripts/cli.py`.

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

[Unreleased]: https://github.com/basitalisandhu/repo-engineering-skills/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/basitalisandhu/repo-engineering-skills/compare/v0.1.1...v0.2.0
[0.1.1]: https://github.com/basitalisandhu/repo-engineering-skills/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/basitalisandhu/repo-engineering-skills/releases/tag/v0.1.0
