from conftest import FIXTURES, load_script, run_json, run_main

mod = load_script("cited-codebase-audit", "repo_facts.py")
REPO = FIXTURES / "cited_audit" / "repo"


def test_inventory_of_the_fixture():
    rc, rep = run_json(mod, [str(REPO), "--json"])
    assert rc == 0
    assert rep["languages"]["Python"]["files"] == 4
    assert rep["ci"] == [".github/workflows/ci.yml"]
    assert rep["licence"] == [{"path": "LICENSE", "family": "MIT"}]
    assert rep["tests"]["files"] == ["tests/test_orders.py"]
    req = next(m for m in rep["manifests"] if m["path"] == "requirements.txt")
    assert req["requirements_pins"] == {"total": 2, "exact_pins": 1}
    kinds = {(e["kind"], e["name"]) for e in rep["entry_points"]}
    assert ("python_main_guard", "shop/cli.py") in kinds
    assert [f["path"] for f in rep["untested_files"]] == ["shop/cli.py"]
    assert rep["largest_files"][0]["path"] == "shop/orders.py"


def test_manifest_entry_points_and_lockfiles(tmp_path):
    (tmp_path / "package.json").write_text('{"name": "x", "bin": {"x": "bin/x.js"}, "scripts": {"test": "vitest"}}')
    (tmp_path / "package-lock.json").write_text("{}")
    (tmp_path / "pyproject.toml").write_text('[project]\nname="y"\n[project.scripts]\ny = "y.cli:main"\n')
    (tmp_path / "Dockerfile").write_text("FROM python:3.11\nENTRYPOINT [\"y\"]\n")
    rc, rep = run_json(mod, [str(tmp_path), "--json"])
    kinds = {e["kind"] for e in rep["entry_points"]}
    assert {"npm_bin", "npm_script", "console_script", "docker_entrypoint"} <= kinds
    pj = next(m for m in rep["manifests"] if m["path"] == "package.json")
    assert pj["lockfiles"] == ["package-lock.json"]
    assert rep["licence"] == []


def test_text_output_and_errors(tmp_path):
    rc, out, _ = run_main(mod, [str(REPO), "--top", "2", "--out", str(tmp_path / "facts.json")])
    assert rc == 0 and "Licence: LICENSE (MIT)" in out and (tmp_path / "facts.json").exists()
    rc, _, err = run_main(mod, [str(tmp_path / "missing")])
    assert rc == 2
    rc, out, _ = run_main(mod, ["--help"])
    assert rc == 0 and "--top" in out
