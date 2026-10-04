"""Tests for scripts/cli.py, the repo-engineering dispatcher used as the container entrypoint."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts" / "cli.py"


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(CLI), *args], capture_output=True, text=True, timeout=60, cwd=ROOT)


def load_cli():
    import importlib.util

    spec = importlib.util.spec_from_file_location("repo_engineering_cli", CLI)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_help_lists_every_subcommand():
    cli = load_cli()
    result = run("--help")
    assert result.returncode == 0
    assert result.stdout.startswith("usage: repo-engineering <subcommand>")
    for name, (_, script, _) in cli.COMMANDS.items():
        assert f"  {name} " in result.stdout
        assert script in result.stdout


def test_every_subcommand_points_at_an_existing_script_and_answers_help():
    cli = load_cli()
    for name in cli.COMMANDS:
        assert cli.script_path(name).is_file(), name
        result = run(name, "--help")
        assert result.returncode == 0, (name, result.stderr)
        assert result.stdout.startswith("usage: "), name


def test_every_skill_script_has_a_subcommand():
    cli = load_cli()
    covered = {cli.script_path(n).resolve() for n in cli.COMMANDS}
    scripts = {p.resolve() for p in cli.SKILLS.glob("*/scripts/[a-z]*.py")}
    assert scripts == covered


def test_help_subcommand_shows_the_script_help():
    result = run("help", "docs-truth")
    assert result.returncode == 0
    assert "docs_truth_check.py" in result.stdout


def test_unknown_subcommand_and_no_arguments_exit_2():
    result = run("no-such-command")
    assert result.returncode == 2
    assert "unknown subcommand" in result.stderr
    assert run().returncode == 2


def test_exit_code_and_arguments_pass_through():
    result = run("docs-truth", "--definitely-not-an-option")
    assert result.returncode == 2
    assert "usage: " in result.stderr


def test_version_matches_the_project_version():
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    plugin_json = ROOT / "plugins" / "repo-engineering" / ".claude-plugin" / "plugin.json"
    plugin = json.loads(plugin_json.read_text(encoding="utf-8"))
    expected = pyproject.get("project", {}).get("version", plugin["version"])
    assert plugin["version"] == expected
    result = run("--version")
    assert result.returncode == 0
    assert result.stdout.strip() == f"repo-engineering {expected}"


def test_cli_is_executable_with_a_shebang():
    assert CLI.read_text(encoding="utf-8").startswith("#!/usr/bin/env python3")
    if os.name == "posix":
        assert os.access(CLI, os.X_OK)


NEW_IN_0_2 = {
    "onboarding": "onboarding_facts.py",
    "onboarding-lint": "onboarding_lint.py",
    "restructure": "restructure_plan.py",
    "adr": "adr_mine.py",
    "adr-lint": "adr_lint.py",
    "hygiene": "hygiene.py",
    "release-notes": "release_notes_verify.py",
}


def test_the_0_2_subcommands_dispatch_to_their_scripts():
    cli = load_cli()
    for name, script in NEW_IN_0_2.items():
        assert cli.script_path(name).name == script
        result = run(name, "--help")
        assert result.returncode == 0, (name, result.stderr)
        assert f"usage: {script}" in result.stdout, name


def test_dispatched_script_runs_on_a_fixture_and_keeps_its_exit_code():
    fixture = ROOT / "tests" / "fixtures" / "restructure" / "repo"
    result = run("restructure", str(fixture), "--json", "--goal", "split")
    assert result.returncode == 0
    assert json.loads(result.stdout)["commands"] == ["git mv app/reports/formatting.py app/api/formatting.py"]
    assert run("restructure", str(fixture), "--fail-on-cycles").returncode == 1
    adr = ROOT / "tests" / "fixtures" / "adr" / "docs_adr"
    assert run("adr-lint", str(adr)).returncode == 1


def test_hygiene_through_the_dispatcher_writes_sarif(tmp_path):
    fixture = ROOT / "tests" / "fixtures" / "hygiene" / "repo"
    sarif = tmp_path / "h.sarif"
    result = run("hygiene", str(fixture), "--fail-on", "high", "--sarif", str(sarif))
    assert result.returncode == 1
    assert json.loads(sarif.read_text(encoding="utf-8"))["version"] == "2.1.0"
