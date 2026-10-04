from conftest import FIXTURES, load_script, run_json, run_main

mod = load_script("agent-context-writer", "context_lint.py")
BASE = FIXTURES / "agent_context"
REPO = BASE / "repo"


def test_planted_duplicates_and_missing_paths_are_flagged():
    rc, rep = run_json(mod, [str(BASE / "AGENTS_bad.md"), str(REPO), "--json"])
    assert rc == 1
    got = {(f["code"], f["line"]) for f in rep["findings"]}
    assert got == {
        ("CTX-MANIFEST", 3), ("CTX-DEPS", 5), ("CTX-RUNTIME", 5), ("CTX-TREE", 7), ("CTX-PATH", 13),
        ("CTX-GENERIC", 15),
    }
    assert rep["counts"]["CTX-MANIFEST"] == 2
    messages = " ".join(f["message"] for f in rep["findings"])
    assert "make lint" in messages and "npm run test" in messages


def test_lines_with_non_inferable_knowledge_pass():
    rc, rep = run_json(mod, [str(BASE / "AGENTS_good.md"), str(REPO), "--json"])
    assert rc == 0 and rep["findings"] == []
    assert rep["length"]["within_budget"] is True


def test_budget(tmp_path):
    ctx = tmp_path / "CLAUDE.md"
    ctx.write_text("\n".join(f"- rule {i}: ask before touching module {i}" for i in range(30)))
    rc, rep = run_json(mod, [str(ctx), str(REPO), "--json", "--max-lines", "20"])
    assert rc == 1 and [f["code"] for f in rep["findings"]] == ["CTX-BUDGET"]
    rc, rep = run_json(mod, [str(ctx), str(REPO), "--json"])
    assert rc == 0


def test_pyproject_console_script_and_requirements(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname="t"\nrequires-python=">=3.11"\ndependencies=["httpx>=0.27", "pydantic", "rich"]\n'
        '[project.scripts]\nmytool = "t.cli:main"\n')
    ctx = tmp_path / "AGENTS.md"
    ctx.write_text("Run `mytool --check`.\nWe use httpx, pydantic and rich on Python 3.11.\n")
    rc, rep = run_json(mod, [str(ctx), str(tmp_path), "--json"])
    assert {f["code"] for f in rep["findings"]} == {"CTX-MANIFEST", "CTX-DEPS", "CTX-RUNTIME"}


def test_pdm_scripts_and_uv_deps(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[tool.pdm.scripts]\nbuild = "python -m build"\ntest = "pytest"\n'
        '[tool.uv]\ndev-dependencies = ["pytest>=8.0", "ruff"]\n')
    ctx = tmp_path / "AGENTS.md"
    ctx.write_text("Run `pdm run test` and `pdm run unknown_script`.\nWe use pytest and ruff.\n")
    rc, rep = run_json(mod, [str(ctx), str(tmp_path), "--json"])
    # pdm run test is flagged because it's in pdm.scripts. pdm run unknown_script is NOT flagged.
    # pytest and ruff are flagged under CTX-DEPS.
    codes = {f["code"] for f in rep["findings"]}
    assert "CTX-MANIFEST" in codes
    assert "CTX-DEPS" in codes
    messages = " ".join(f["message"] for f in rep["findings"])
    assert "pdm run test" in messages
    assert "pdm run unknown_script" not in messages


def test_text_output_and_errors(tmp_path):
    rc, out, _ = run_main(mod, [str(BASE / "AGENTS_bad.md"), str(REPO)])
    assert rc == 1 and "CTX-TREE" in out and "within budget" in out
    assert run_main(mod, [str(tmp_path / "missing.md"), str(REPO)])[0] == 2
    assert run_main(mod, [str(BASE / "AGENTS_bad.md"), str(tmp_path / "nope")])[0] == 2
    rc, out, _ = run_main(mod, ["--help"])
    assert rc == 0 and "--max-lines" in out
