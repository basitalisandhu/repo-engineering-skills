# repo-engineering

Five skills for repository audits and documentation, each with a tested standard-library Python script. Install with `/plugin marketplace add basitalisandhu/repo-engineering-skills` and then `/plugin install repo-engineering@repo-engineering-skills`. Skills appear as `/repo-engineering:<skill>`, and Claude also invokes them on its own when a request matches a skill's description.

| Skill | Script | Use it to |
|---|---|---|
| `docs-truth-check` | `skills/docs-truth-check/scripts/docs_truth_check.py` | verify README, docs/, AGENTS.md and CLAUDE.md claims against the working tree; exit 1 on drift |
| `cited-codebase-audit` | `skills/cited-codebase-audit/scripts/repo_facts.py`, `skills/cited-codebase-audit/scripts/audit_validate.py` | audit a repository from a deterministic inventory, and reject findings whose `path:line` citations do not resolve |
| `agent-context-writer` | `skills/agent-context-writer/scripts/context_lint.py` | write AGENTS.md or CLAUDE.md with only what code cannot say, and lint out what a parser can see |
| `readme-who-what-why` | `skills/readme-who-what-why/scripts/readme_check.py` | score whether a README's first screen says what, who, why, install, example and where to ask |
| `test-gap-finder` | `skills/test-gap-finder/scripts/test_gaps.py` | rank untested public functions and entry points and write characterisation test stubs |

Requirements: Python 3.11 or newer on `PATH` as `python3`. No network access, no third-party packages.
