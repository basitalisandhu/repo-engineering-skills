#!/usr/bin/env python3
"""repo-engineering: one command for the repo-engineering skill scripts.

    repo-engineering <subcommand> [args]       run one skill script with the given arguments
    repo-engineering <subcommand> --help       that script's own help
    repo-engineering --help                    list the subcommands

Each subcommand runs plugins/repo-engineering/skills/<skill>/scripts/<script>.py unchanged, in a child process with
the same Python, stdin, stdout, stderr and exit code. Standard library only. This is the entrypoint of the
container image ghcr.io/basitalisandhu/repo-engineering-skills.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

__version__ = "0.1.1"

PROG = "repo-engineering"
ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "plugins" / "repo-engineering" / "skills"

# subcommand: (skill directory, script, one-line summary)
COMMANDS: dict[str, tuple[str, str, str]] = {
    "docs-truth": (
        "docs-truth-check",
        "docs_truth_check.py",
        "Check README and docs claims against the working tree",
    ),
    "repo-facts": (
        "cited-codebase-audit",
        "repo_facts.py",
        "Deterministic repository inventory for a cited audit",
    ),
    "audit-validate": (
        "cited-codebase-audit",
        "audit_validate.py",
        "Reject audit findings whose path:line citations do not resolve",
    ),
    "context-lint": (
        "agent-context-writer",
        "context_lint.py",
        "Flag AGENTS.md or CLAUDE.md lines that restate the repository",
    ),
    "readme-check": (
        "readme-who-what-why",
        "readme_check.py",
        "Score whether a README first screen answers what, who and why",
    ),
    "test-gaps": (
        "test-gap-finder",
        "test_gaps.py",
        "Rank public functions and entry points that no test mentions",
    ),
}


def script_path(name: str) -> Path:
    skill, script, _ = COMMANDS[name]
    return SKILLS / skill / "scripts" / script


def usage() -> str:
    width = max(len(n) for n in COMMANDS)
    lines = [
        f"usage: {PROG} <subcommand> [args]",
        "",
        f"Runs one of the repo-engineering skill scripts. Use '{PROG} <subcommand> --help' for its options.",
        "",
        "subcommands:",
    ]
    lines += [f"  {n.ljust(width)}  {h} ({script})" for n, (_, script, h) in COMMANDS.items()]
    lines += ["", "options:", "  -h, --help     show this help and exit", "  --version      show the version and exit"]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print(usage(), file=sys.stderr)
        return 2
    first, rest = args[0], args[1:]
    if first in ("-h", "--help", "help") and not rest:
        print(usage())
        return 0
    if first == "help":
        first, rest = rest[0], ["--help"]
    if first == "--version":
        print(f"{PROG} {__version__}")
        return 0
    if first not in COMMANDS:
        print(f"{PROG}: unknown subcommand {first!r}\n\n{usage()}", file=sys.stderr)
        return 2
    return subprocess.call([sys.executable, str(script_path(first)), *rest])


if __name__ == "__main__":
    sys.exit(main())
