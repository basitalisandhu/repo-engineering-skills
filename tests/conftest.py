"""Shared helpers for the script tests.

Every skill script lives at plugins/repo-engineering/skills/<skill>/scripts/<name>.py and is a standalone program,
not a package. Tests load one by path with load_script() and call its main(argv), capturing stdout. Fixture
repositories with planted defects live under tests/fixtures/ and are never collected as tests.
"""
from __future__ import annotations

import importlib.util
import io
import json
import shutil
import sys
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "plugins" / "repo-engineering" / "skills"
FIXTURES = Path(__file__).resolve().parent / "fixtures"


def script_path(skill: str, name: str) -> Path:
    return SKILLS / skill / "scripts" / name


def load_script(skill: str, name: str):
    """Import a skill script by path under a unique module name."""
    path = script_path(skill, name)
    module_name = f"skill_{skill}_{path.stem}".replace("-", "_")
    if module_name in sys.modules:
        return sys.modules[module_name]
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def run_main(module, argv: list[str]) -> tuple[int, str, str]:
    """Run module.main(argv) and return (exit code, stdout, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        try:
            rc = module.main(argv)
        except SystemExit as exc:  # argparse --help and usage errors
            rc = int(exc.code or 0)
    return rc, out.getvalue(), err.getvalue()


def run_json(module, argv: list[str]) -> tuple[int, dict]:
    rc, out, err = run_main(module, argv)
    try:
        return rc, json.loads(out)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"not JSON (rc={rc}): {out!r} stderr={err!r}") from exc


@pytest.fixture
def fixture_copy(tmp_path: Path):
    """Copy a fixture directory into tmp_path so a test can change it without touching the original."""
    def _copy(rel: str) -> Path:
        dest = tmp_path / Path(rel).name
        shutil.copytree(FIXTURES / rel, dest)
        return dest
    return _copy


GIT_ENV_BASE = {"GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0"}


def git_commit(repo: Path, message: str, files: dict[str, str | None], date: str = "2026-01-01T12:00:00",
               author: str = "Ada Example") -> str:
    """Write (or delete, for None) files in repo, commit them with a fixed author and date, return the SHA.

    Creates the repository on first use. Signing is off and global config is ignored so the test machine's own
    git settings cannot change the result.
    """
    import os
    import subprocess

    env = {**os.environ, **GIT_ENV_BASE, "HOME": str(repo.parent), "GIT_AUTHOR_NAME": author,
           "GIT_AUTHOR_EMAIL": "ada@example.com", "GIT_COMMITTER_NAME": author,
           "GIT_COMMITTER_EMAIL": "ada@example.com", "GIT_AUTHOR_DATE": date, "GIT_COMMITTER_DATE": date}

    def git(*args: str) -> str:
        return subprocess.run(["git", "-c", "commit.gpgsign=false", "-c", "tag.gpgsign=false", "-c",
                               "init.defaultBranch=main", *args], cwd=repo, env=env, check=True,
                              capture_output=True, text=True).stdout

    if not (repo / ".git").exists():
        repo.mkdir(parents=True, exist_ok=True)
        git("init", "-q")
    for rel, content in files.items():
        path = repo / rel
        if content is None:
            git("rm", "-q", rel)
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        git("add", rel)
    git("commit", "-q", "--allow-empty", "-m", message)
    return git("rev-parse", "HEAD").strip()


def git_tag(repo: Path, name: str) -> None:
    import subprocess

    subprocess.run(["git", "-c", "tag.gpgsign=false", "tag", name], cwd=repo, check=True, capture_output=True)
