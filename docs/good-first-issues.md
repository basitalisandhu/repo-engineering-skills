# Good first issues

Small, well-specified pieces of work for a first contribution. Each is self-contained, comes with the test to add, and needs no account, token or network access. Read [CONTRIBUTING.md](../CONTRIBUTING.md) first: standard library only, a planted-defect fixture with every detection change, no network calls, plain language without em-dashes.

To claim one, open an issue with the title below (or comment on the existing one) and say you are working on it. Run `python3 -m pytest -q`, `ruff check .` and `python3 scripts/validate_plugin.py` before opening the pull request.

## 1. docs-truth-check: check documented environment variable defaults

**Labels:** good first issue, docs-truth-check, python

**Context.** `docs_truth_check.py` verifies that an environment variable named in the docs is read somewhere, but not a documented default such as "`GREETER_LANG` defaults to `en`". Python code usually states the default as the second argument of `os.environ.get` or `os.getenv`.

**Acceptance criteria.**
- In `Index._index_python`, record literal second arguments of `os.environ.get(NAME, default)` and `os.getenv(NAME, default)` per variable name.
- `Checker.check_defaults` also handles `ENV_NAME ... defaults to X` lines: `verified` when equal, `stale` when the code literal differs, `unverified` when the default is not a literal.
- A planted wrong env default in `tests/fixtures/docs_truth/sample_repo/README.md` and an updated expected set in `tests/test_docs_truth_check.py`.

## 2. docs-truth-check: support `pyproject.toml` dynamic versions

**Labels:** good first issue, docs-truth-check, python

**Context.** When `[project]` declares `dynamic = ["version"]`, the version lives in a module (`__version__ = "1.2.0"`) or in `[tool.setuptools.dynamic]`. `Index.project()` then returns no version and version claims are skipped silently.

**Acceptance criteria.**
- Read `[tool.setuptools.dynamic] version = {attr = "pkg.__version__"}` and `[tool.hatch.version] path = "..."`, and resolve the literal `__version__` with `ast`.
- When the version cannot be resolved, version claims are reported as `unverified` with the reason instead of being skipped.
- Two tests: a setuptools `attr` layout and a hatch `path` layout.

## 3. cited-codebase-audit: refuse citations through symbolic links

**Labels:** good first issue, cited-codebase-audit, security, python

**Context.** `audit_validate.py` rejects `..` paths and paths that resolve outside the repository, but a citation to a symbolic link inside the repository that points at a file elsewhere is only caught by the resolve check. Make the rule explicit.

**Acceptance criteria.**
- A citation whose path, or any parent directory, is a symbolic link resolving outside the repository is rejected with `CIT-PATH` and the detail "symbolic link leaves the repository".
- A test that creates the link in `tmp_path` (skipped on platforms where `os.symlink` is unavailable).
- `SKILL.md` lists the rule in the validator table.

## 4. agent-context-writer: parse `[tool.uv]` and `[tool.pdm.scripts]`

**Labels:** good first issue, agent-context-writer, python

**Context.** `context_lint.py` knows `[project.scripts]`, Poetry scripts, npm scripts, Makefile and justfile. PDM projects declare commands in `[tool.pdm.scripts]` and run them as `pdm run <name>`; those lines are not flagged today.

**Acceptance criteria.**
- `Manifests` reads `[tool.pdm.scripts]` names; `command_dupes` flags `pdm run <name>` for known names.
- `[tool.uv] dev-dependencies` are added to the dependency set used by `CTX-DEPS`.
- Tests for both, plus one line that uses an unknown PDM script name and must not be flagged.

## 5. readme-who-what-why: recognise reStructuredText READMEs

**Labels:** good first issue, readme-who-what-why, python

**Context.** `readme_check.py` understands Markdown fences and headings only. Many Python projects ship `README.rst`, where code is introduced by `::` or `.. code-block:: bash` and headings are underlined.

**Acceptance criteria.**
- When the file name ends in `.rst`, code blocks are the indented blocks after `::` and `.. code-block::` directives, and headings are lines followed by a line of `=`, `-` or `~`.
- `tests/fixtures/readme/good_README.rst` scores 12 of 12; a test asserts it.
- The "Limits" section of `SKILL.md` is updated.

## 6. untested-entry-points: list public methods of public classes

**Labels:** good first issue, untested-entry-points, python

**Context.** `test_gaps.py` treats a Python class as one unit. A class with ten public methods and one tested method looks fully tested.

**Acceptance criteria.**
- A `--methods` flag adds each public method of a public class as a unit named `Class.method`, tested when a test file mentions the method name.
- The default output is unchanged without the flag.
- A fixture class with one tested and one untested method; a test asserts only the untested one is listed with `--methods`.

## 7. repo-onboarding-guide: read commands from a justfile recipe body and `tox.ini`

**Labels:** good first issue, repo-onboarding-guide, python

**Context.** `onboarding_facts.py` records justfile and Makefile target names, and pytest configuration from `pyproject.toml`, but not `[tox]` environments or `[testenv] commands` in `tox.ini`, so a guide that says "run `tox -e py311`" is flagged as unsupported.

**Acceptance criteria.**
- Parse `tox.ini` with `configparser`: each `[testenv:<name>]` section becomes a `test_command` fact `tox -e <name>` citing the section's line.
- `tox` alone is accepted when an `envlist` is declared.
- A fixture `tox.ini` and a test that lints a guide line using `tox -e lint` without a finding.

## 8. repo-onboarding-guide: resolve TypeScript path aliases in the facts' directory map

**Labels:** good first issue, repo-onboarding-guide, typescript

**Context.** A guide may say "shared UI lives in `@/components`". The alias is defined in `tsconfig.json` `compilerOptions.paths`, which the facts script does not read, so the lint flags a true sentence.

**Acceptance criteria.**
- Read `compilerOptions.paths` from a root `tsconfig.json` (JSON with comments stripped) and add each alias and its target directory as terms of a `directory` fact.
- A test with `"@/*": ["src/*"]` where `@/components` is supported and `@/nothing` is not.

## 9. restructure-planner: resolve `tsconfig.json` path aliases in the import graph

**Labels:** good first issue, restructure-planner, typescript

**Context.** `restructure_plan.py` treats `import x from "@/lib/date"` as an external package, so files reached through an alias have no edges and never appear in cycles or moves.

**Acceptance criteria.**
- Read `compilerOptions.baseUrl` and `paths` from the nearest `tsconfig.json` and resolve matching specifiers like relative ones.
- A fixture with an alias cycle (`@/a` imports `@/b`, `@/b` imports `@/a`) that is reported under `cycles`.
- The `Limits` section of `SKILL.md` drops the alias line.

## 10. adr-miner: read the Nygard ADR layout and `adr-tools` supersession lines

**Labels:** good first issue, adr-miner, python

**Context.** Folders created with `adr-tools` write `Superseded by [2. Use X](0002-use-x.md)` under a `## Status` heading and `Supersedes [1. ...]` in the newer record. `adr_lint.py` reads the status, but the back-reference check only looks for the file name or the number.

**Acceptance criteria.**
- Treat a `Supersedes` or `Superseded by` link to an existing ADR as the back-reference, whatever its link text.
- A fixture pair in `adr-tools` style that passes, and one where the newer record lacks `Supersedes` that still warns with `ADR-BACKLINK`.

## 11. repo-hygiene-bundle: pnpm and yarn lockfile drift

**Labels:** good first issue, repo-hygiene-bundle, javascript

**Context.** `hygiene.py` checks drift for `package-lock.json`, `poetry.lock`, `uv.lock` and `pdm.lock`. For `pnpm-lock.yaml` and `yarn.lock` it only checks that the file exists.

**Acceptance criteria.**
- For `pnpm-lock.yaml`, read the `importers` section's dependency names with a line-based parser (no YAML library) and flag package.json dependencies missing from it as `HYG-LOCKDRIFT`.
- For `yarn.lock`, flag package.json dependencies with no `"name@` entry.
- One fixture per format with one planted missing dependency, and one clean case each.

## 12. release-notes-verifier: report breaking-change markers without a note

**Labels:** good first issue, release-notes-verifier, python

**Context.** Conventional commits mark breaking changes with `!` after the type (`feat!:`) or a `BREAKING CHANGE:` footer. `release_notes_verify.py` treats them like any other commit, so a breaking change with no note is reported the same way as a small fix.

**Acceptance criteria.**
- Commits with `!:` in the subject or a `BREAKING CHANGE:` line in the body are reported as `REL-BREAKING-UNNOTED` when no note matches, and are never excluded by `--chore-pattern`.
- When the changelog section has a heading containing "Breaking", a matched note under another heading is reported as a warning.
- Tests built with `git_commit` from `tests/conftest.py`.
