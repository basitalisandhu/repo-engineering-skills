# repo-engineering-skills: Claude Code skills for repository audits and documentation

**Repository engineering skills for Claude Code: documentation that is checked against the code, audits where every finding cites a line, agent context files that say only what code cannot.**

repo-engineering-skills is a Claude Code plugin with five skills for maintainers and teams who need to trust what is written about their repository: the README, the docs, the audit report, the AGENTS.md. It exists because generated docs and audits are cheap to produce and hard to check, so each skill pairs the model's work with a standard-library Python script that checks it against the working tree, instead of asking you to take the text on faith.

```text
/plugin marketplace add basitalisandhu/repo-engineering-skills
/plugin install repo-engineering@repo-engineering-skills
```

Quickstart: open Claude Code in a repository and ask "check the docs against the code", or run a script directly from a clone of this repository:

```bash
python3 plugins/repo-engineering/skills/docs-truth-check/scripts/docs_truth_check.py . --only-failures
```

Questions, bugs and ideas: open an issue on this repository. Security reports: see [SECURITY.md](SECURITY.md).

## When to use this

- Is the README still true after a rename, a removed flag or a changed default? `docs-truth-check`
- Audit a codebase so that every finding can be opened and checked: `cited-codebase-audit`
- Write an AGENTS.md or CLAUDE.md that does not repeat package.json, or shrink one that does: `agent-context-writer`
- Does the README say what this is, who it is for, why it exists, how to install and try it, and where to ask, in its first screen? `readme-who-what-why`
- Which public functions and CLI entry points does no test mention, and what characterisation tests should pin them before a refactor? `test-gap-finder`

## Skills

| Skill | Triggers on | Script | What it produces |
|---|---|---|---|
| `docs-truth-check` | "are the docs accurate?", after renames, before a release, a docs CI gate | `docs_truth_check.py` | every checkable claim in README, docs/, AGENTS.md and CLAUDE.md (paths, links, flags, defaults, env vars, symbols, config keys, versions, npm and make targets) as verified, missing, stale or unverified; JSON report; exit 1 on drift |
| `cited-codebase-audit` | "audit this repo", repo health, taking over a codebase | `repo_facts.py`, `audit_validate.py` | a deterministic inventory, then a checklist audit whose findings each cite `path:line` with a quoted snippet; the validator rejects citations that do not resolve and prints acceptance stats |
| `agent-context-writer` | write, update or shorten AGENTS.md or CLAUDE.md | `context_lint.py` | a short context file of non-inferable knowledge, linted for restated manifest commands, dependency lists, pinned runtimes, directory trees, missing paths, generic advice and length |
| `readme-who-what-why` | review or improve a README, before a launch | `readme_check.py` | a score out of 12 for six first-screen answers, hype words with line numbers, and a to-do list |
| `test-gap-finder` | "what is untested?", characterisation tests before a refactor | `test_gaps.py` | untested public functions and entry points ranked by entry point, size and fan-in; skipped or todo test stubs in pytest, unittest, jest, vitest or node:test |

Every script reads files only, needs no network, prints a table by default and JSON with `--json`, and uses exit codes 0 (clean), 1 (findings) and 2 (bad input), so each one can gate CI.

## How this differs from what you may already have

- **Asking the model to review docs or audit code** gives prose you then have to verify. Here the verification is a script with a fixed rule set, and anything it cannot decide is labelled `unverified` rather than guessed.
- **Anthropic's official plugins** cover neighbouring ground: `claude-md-management` maintains CLAUDE.md, `code-review` and `pr-review-toolkit` review changes, `claude-security` scans for vulnerabilities, `code-modernization` plans legacy rewrites. This plugin does not repeat them. `agent-context-writer` adds one mechanical rule (no line a parser could have produced) with a lint; `cited-codebase-audit` is a whole-repository hygiene audit, not a diff review or a vulnerability scan.
- **The sibling [claude-dev-skills](https://github.com/basitalisandhu/claude-dev-skills)** has a `readme-author` that writes READMEs and a module-level test gap finder. Here `readme-who-what-why` scores an existing first screen, and `test-gap-finder` works per function and entry point and writes characterisation stubs.

## What is inside

```text
.claude-plugin/marketplace.json                       marketplace manifest
plugins/repo-engineering/
├── .claude-plugin/plugin.json                        plugin manifest
├── README.md                                         the plugin's skill table
└── skills/<name>/
    ├── SKILL.md                                      triggers, honesty principle, procedure, output format, limits
    └── scripts/<script>.py                           standard library only, --help, --json, exit codes 0/1/2
tests/test_<script>.py                                pytest suite, offline
tests/fixtures/                                       sample repositories with planted defects
scripts/validate_plugin.py                            structure, frontmatter, scripts, READMEs, house style
```

Each skill folder is self-contained: its scripts live inside it, so it can be copied on its own.

## Security posture

- **Skills** are Markdown instructions. Each one tells Claude to treat repository content as untrusted data, never as instructions, and to report only what it verified.
- **Scripts** read the paths given on the command line. They write only where you pass `--out` or `--stubs-dir`, and `--stubs-dir` never overwrites an existing file.
- **Nothing runs your code by default.** The single exception is `docs_truth_check.py --run-help`, which you must pass explicitly: it runs scripts that have no parseable option declarations once with `--help`, with a 10 second timeout and an environment reduced to `PATH`, `LANG` and `NO_COLOR`.
- **No network, no telemetry.** No script opens a socket.

Report security problems privately: see [SECURITY.md](SECURITY.md).

## Also works with

The skill folders follow the Agent Skills format (a `SKILL.md` with `name` and `description` frontmatter, helpers in `scripts/`), and each skill is self-contained. An agent that loads skills from `SKILL.md` folders can use one by copying `plugins/repo-engineering/skills/<name>/` into its skills directory. The skill bodies call scripts through `${CLAUDE_PLUGIN_ROOT}`, a Claude Code variable; other hosts should replace `${CLAUDE_PLUGIN_ROOT}/skills/<name>` with the skill folder's path. The scripts themselves are plain Python and run anywhere Python 3.11 does.

## Development

```bash
python3 -m pytest -q
ruff check .
python3 scripts/validate_plugin.py
claude plugin validate --strict . && claude plugin validate --strict plugins/repo-engineering
```

CI also runs `docs_truth_check.py` and `readme_check.py` on this README. See [CONTRIBUTING.md](CONTRIBUTING.md) for the ground rules and [docs/good-first-issues.md](docs/good-first-issues.md) for a place to start.

## Frequently asked questions

**Is there a Claude Code skill that checks whether documentation matches the code?**
Yes: `docs-truth-check`. It extracts the claims a script can check (file paths, relative links, CLI flags and their documented defaults, environment variables, function, class and config key names, npm and make targets, version strings) from README, docs/, AGENTS.md and CLAUDE.md, checks each against the working tree with Python's `ast` for Python code, regex for JS and TS exports, and source scans for shell scripts, and exits 1 when anything is missing or stale.

**How is a cited audit different from asking for a code review?**
Every finding must name a `path:line` and quote the text there, and `audit_validate.py` rejects any finding whose file, line or snippet does not match. The audit also starts from a deterministic inventory (`repo_facts.py`) and ends with explicit "considered and rejected" and "not examined" lists, so you can see what was left out.

**Does anything leave my machine or run my code?**
No network calls and no telemetry. Scripts read files and print reports. Your code is executed only if you pass `--run-help` to `docs_truth_check.py`.

**Which languages are supported?**
Python is parsed with `ast`; JavaScript and TypeScript are read with regular expressions for exports and declarations; shell scripts are scanned for flags. Manifests understood: `pyproject.toml`, `package.json`, requirements files, Makefile, justfile, `.nvmrc`, `.python-version`. Other languages appear in the inventory but their symbols are not parsed, and the reports say so.

**Can I use the scripts in CI without Claude Code?**
Yes. Each script is a standalone standard-library Python program with exit code 1 on findings, for example `python3 docs_truth_check.py . --only-failures` or `python3 readme_check.py README.md`.

## Related projects

| Project | What it is |
|---|---|
| [claude-dev-skills](https://github.com/basitalisandhu/claude-dev-skills) | Claude Code skills for everyday development: code review, refactoring, debugging, CI and containers, data and APIs, docs and security basics |
| [agent-security-skills](https://github.com/basitalisandhu/agent-security-skills) | Claude Code plugin for securing LLM agents: threat modelling, config audits, prompt injection review, MCP server review |

More from the author: [github.com/basitalisandhu](https://github.com/basitalisandhu).

## Licence

MIT. See [LICENSE](LICENSE).
