#!/usr/bin/env python3
"""Lint an AGENTS.md or CLAUDE.md for lines that repeat what a parser can already read, or point at nothing.

Checks:
  CTX-MANIFEST  a command that a manifest already declares: "npm run X" / "pnpm X" / "yarn X" for a package.json
                script, "make X" for a Makefile target, "just X" for a justfile recipe, a pyproject console script,
                or "pdm run X" for a pdm script.
  CTX-DEPS      a line naming three or more dependencies that the manifests already list
  CTX-RUNTIME   a runtime version the manifest already pins (requires-python, engines.node, .nvmrc, .python-version)
  CTX-TREE      a directory tree listing; the agent can list files itself
  CTX-PATH      a path in backticks or a relative link that does not exist in the repository
  CTX-GENERIC   generic advice that applies to every repository ("write clean code", "follow best practices")
  CTX-BUDGET    the file is longer than the line or word budget

The file's length against the budget is always reported. Reads files only; runs nothing.
Exit codes: 0 no findings, 1 findings, 2 bad input.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tomllib
from pathlib import Path
from urllib.parse import unquote

SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "dist", "build", "__pycache__", ".tox", "target", ".next"}
PATH_SUFFIXES = {
    ".py", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".json", ".toml", ".yml", ".yaml", ".md", ".txt",
    ".cfg", ".ini", ".sh", ".go", ".rs", ".rb", ".java", ".kt", ".sql", ".lock", ".env", ".example", ".html",
    ".css", ".tf", ".proto", ".graphql", ".mdx",
}
BARE_FILENAMES = {"Makefile", "Dockerfile", "LICENSE", "Procfile", "Justfile", "justfile", "Gemfile"}
GENERIC = [
    r"write clean(,)? (readable |maintainable )?code", r"follow (the )?best practices",
    r"meaningful (variable )?names", r"keep (functions|code) (small|simple)", r"write (good|comprehensive) tests",
    r"handle errors (properly|gracefully)",
    r"be consistent", r"use descriptive names", r"follow (the )?(existing )?coding (style|standards)",
    r"make sure (the )?code is (readable|maintainable)", r"(avoid|don't|do not) (write )?duplicate code",
    r"add comments where (necessary|needed)", r"follow solid principles",
]
SPAN_RE = re.compile(r"(?<!`)`([^`\n]+)`(?!`)")
LINK_RE = re.compile(r"\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")


def read(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8", errors="replace") if path.is_file() else None
    except OSError:
        return None


class Manifests:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.npm_scripts: set[str] = set()
        self.make_targets: set[str] = set()
        self.just_recipes: set[str] = set()
        self.console_scripts: set[str] = set()
        self.pdm_scripts: set[str] = set()
        self.python_version: str | None = None
        self.node_version: str | None = None
        self.dependencies: set[str] = set()

        if not root.is_dir():
            return

        for path in root.rglob("*"):
            if any(p in SKIP_DIRS for p in path.relative_to(root).parts):
                continue
            name = path.name
            if name == "package.json":
                if content := read(path):
                    try:
                        data = json.loads(content)
                        if isinstance(data, dict):
                            if isinstance(scripts := data.get("scripts"), dict):
                                self.npm_scripts.update(scripts.keys())
                            if isinstance(engines := data.get("engines"), dict):
                                if isinstance(node := engines.get("node"), str):
                                    self.node_version = node
                            if isinstance(deps := data.get("dependencies"), dict):
                                self.dependencies.update(d.lower() for d in deps.keys())
                            if isinstance(dev_deps := data.get("devDependencies"), dict):
                                self.dependencies.update(d.lower() for d in dev_deps.keys())
                    except Exception:
                        pass
            elif name == "pyproject.toml":
                if content := read(path):
                    try:
                        data = tomllib.loads(content)
                        if isinstance(data, dict):
                            if isinstance(proj := data.get("project"), dict):
                                if isinstance(req := proj.get("requires-python"), str):
                                    self.python_version = req
                                if isinstance(deps := proj.get("dependencies"), list):
                                    for d in deps:
                                        if isinstance(d, str):
                                            pkg = re.split(r"[<>=!~;\s]", d)[0].strip().lower()
                                            if pkg:
                                                self.dependencies.add(pkg)
                                if isinstance(scripts := proj.get("scripts"), dict):
                                    self.console_scripts.update(scripts.keys())
                            if isinstance(tool := data.get("tool"), dict):
                                if isinstance(poetry := tool.get("poetry"), dict):
                                    if isinstance(scripts := poetry.get("scripts"), dict):
                                        self.console_scripts.update(scripts.keys())
                                    if isinstance(deps := poetry.get("dependencies"), dict):
                                        self.dependencies.update(d.lower() for d in deps.keys())
                                    if isinstance(dev_deps := poetry.get("dev-dependencies"), dict):
                                        self.dependencies.update(d.lower() for d in dev_deps.keys())
                                if isinstance(pdm := tool.get("pdm"), dict):
                                    if isinstance(scripts := pdm.get("scripts"), dict):
                                        self.pdm_scripts.update(scripts.keys())
                                if isinstance(uv := tool.get("uv"), dict):
                                    if isinstance(dev_deps := uv.get("dev-dependencies"), list):
                                        for d in dev_deps:
                                            if isinstance(d, str):
                                                pkg = re.split(r"[<>=!~;\s]", d)[0].strip().lower()
                                                if pkg:
                                                    self.dependencies.add(pkg)
                    except Exception:
                        pass
            elif name == "requirements.txt":
                if content := read(path):
                    for line in content.splitlines():
                        line = line.strip()
                        if line and not line.startswith("#"):
                            pkg = re.split(r"[<>=!~;\s]", line)[0].strip().lower()
                            if pkg:
                                self.dependencies.add(pkg)
            elif name.lower() == "makefile":
                if content := read(path):
                    for line in content.splitlines():
                        if m := re.match(r"^([a-zA-Z0-9_.-]+)\s*:", line):
                            target = m.group(1)
                            if not target.startswith("."):
                                self.make_targets.add(target)
            elif name.lower() in ("justfile", ".justfile"):
                if content := read(path):
                    for line in content.splitlines():
                        if m := re.match(r"^([a-zA-Z0-9_.-]+)(\s+.*)?\s*:", line):
                            recipe = m.group(1)
                            if not recipe.startswith("_"):
                                self.just_recipes.add(recipe)
            elif name == ".nvmrc" and not self.node_version:
                if content := read(path):
                    self.node_version = content.strip()
            elif name == ".python-version" and not self.python_version:
                if content := read(path):
                    self.python_version = content.strip()

    def is_manifest_command(self, cmd: str) -> bool:
        cmd = cmd.strip()
        parts = cmd.split()
        if not parts:
            return False
        base = parts[0]
        
        if base in ("npm", "pnpm", "yarn", "bun"):
            if len(parts) >= 2:
                sub = parts[1]
                if sub == "run" and len(parts) >= 3:
                    script = parts[2]
                    return script in self.npm_scripts
                elif sub in self.npm_scripts:
                    return True
        elif base == "pdm":
            if len(parts) >= 3 and parts[1] == "run":
                script = parts[2]
                return script in self.pdm_scripts
        elif base == "make":
            if len(parts) >= 2 and parts[1] in self.make_targets:
                return True
        elif base == "just":
            if len(parts) >= 2 and parts[1] in self.just_recipes:
                return True
        elif base in self.console_scripts:
            return True
        return False
