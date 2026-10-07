import hashlib

from conftest import FIXTURES, load_script, run_json, run_main

mod = load_script("restructure-planner", "restructure_plan.py")
REPO = FIXTURES / "restructure" / "repo"


def tree_digest(root):
    h = hashlib.sha256()
    for p in sorted(root.rglob("*")):
        if p.is_file() and "__pycache__" not in p.parts:
            h.update(p.relative_to(root).as_posix().encode())
            h.update(p.read_bytes())
    return h.hexdigest()


def test_graph_finds_the_python_and_js_cycles():
    rc, rep = run_json(mod, [str(REPO), "--json"])
    assert rc == 0
    paths = [c["path"] for c in rep["cycles"]]
    assert paths == [["app/billing/invoice.py", "app/users/account.py", "app/billing/invoice.py"],
                     ["web/src/a.ts", "web/src/b.ts", "web/src/a.ts"]]
    assert [c["packages"] for c in rep["package_cycles"]] == [["app/billing", "app/users"]]
    assert rep["summary"]["edges"] == 15
    assert rep["external_packages"] == {"datetime": 1, "json": 1, "lodash": 1, "re": 1}


def test_god_module_and_wide_importer():
    rc, rep = run_json(mod, [str(REPO), "--json"])
    gods = rep["god_modules"]
    assert [g["file"] for g in gods] == ["app/core/utils.py"]
    assert gods[0]["fan_in"] == 5 and gods[0]["importer_packages"] == 4
    assert gods[0]["names_by_package"]["app/reports"] == ["money", "now", "to_csv"]
    assert rep["wide_importers"] == [{"file": "app/api/routes.py", "count": 4,
                                      "packages": ["app/billing", "app/core", "app/reports", "app/users"]}]
    top = rep["coupling"][0]
    assert (top["file"], top["fan_in"], top["fan_out"]) == ("app/api/routes.py", 0, 5)


def test_relative_python_imports_resolve():
    rc, rep = run_json(mod, [str(REPO), "--json", "--top", "50"])
    export = next(r for r in rep["coupling"] if r["file"] == "app/reports/export.py")
    assert export["fan_out"] == 2


def test_split_goal_moves_the_single_consumer_file():
    rc, rep = run_json(mod, [str(REPO), "--goal", "split", "--json"])
    assert [(m["file"], m["from"], m["to"], m["blast_radius"]) for m in rep["moves"]] == [
        ("app/reports/formatting.py", "app/reports", "app/api", 1)]
    assert rep["moves"][0]["importers"] == ["app/api/routes.py"]
    assert rep["commands"] == ["git mv app/reports/formatting.py app/api/formatting.py"]
    assert rep["summary"]["cross_package_edges"] == 11
    assert rep["summary"]["cross_package_edges_after_plan"] == 10
    assert rep["executed"] is False


def test_merge_goal_folds_mutually_dependent_packages():
    rc, rep = run_json(mod, [str(REPO), "--goal", "merge", "--json"])
    assert [(m["file"], m["to"]) for m in rep["moves"]] == [("app/billing/invoice.py", "app/users")]
    assert "import each other" in rep["moves"][0]["reason"]
    assert rep["moves"][0]["blast_radius"] == 2


def test_boundaries_goal_never_moves_the_god_module():
    rc, rep = run_json(mod, [str(REPO), "--goal", "boundaries", "--json"])
    moved = {m["file"] for m in rep["moves"]}
    assert "app/core/utils.py" not in moved
    assert "app/reports/formatting.py" in moved
    assert rep["summary"]["cross_package_edges_after_plan"] < rep["summary"]["cross_package_edges"]


def test_nothing_is_moved_and_commands_are_quoted(tmp_path):
    before = tree_digest(REPO)
    rc, text, _ = run_main(mod, [str(REPO), "--goal", "split"])
    assert rc == 0 and "not executed" in text and "| File | From | To | Reason | Blast radius |" in text
    assert tree_digest(REPO) == before
    (tmp_path / "my pkg").mkdir()
    (tmp_path / "other").mkdir()
    (tmp_path / "my pkg" / "helper.py").write_text("X = 1\n", encoding="utf-8")
    (tmp_path / "other" / "use.py").write_text("import importlib\n", encoding="utf-8")
    (tmp_path / "web").mkdir()
    (tmp_path / "web" / "one.js").write_text("export const one = 1;\n", encoding="utf-8")
    (tmp_path / "ui").mkdir()
    (tmp_path / "ui" / "main.js").write_text("import { one } from '../web/one';\n", encoding="utf-8")
    rc, rep = run_json(mod, [str(tmp_path), "--goal", "split", "--json"])
    assert rep["commands"] == ["git mv web/one.js ui/one.js"]


def test_fail_on_cycles_and_bad_input(tmp_path):
    assert run_main(mod, [str(REPO), "--fail-on-cycles"])[0] == 1
    (tmp_path / "a.py").write_text("import b\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("X = 1\n", encoding="utf-8")
    assert run_main(mod, [str(tmp_path), "--fail-on-cycles"])[0] == 0
    assert run_main(mod, [str(tmp_path / "missing")])[0] == 2
    assert run_main(mod, [str(REPO), "--goal", "explode"])[0] == 2


def test_tests_are_left_out_unless_asked():
    rc, rep = run_json(mod, [str(REPO), "--json", "--top", "50"])
    assert not any(r["file"].startswith("tests/") for r in rep["coupling"])
    rc, rep = run_json(mod, [str(REPO), "--json", "--top", "50", "--include-tests"])
    assert any(r["file"] == "tests/test_routes.py" for r in rep["coupling"])


def test_js_resolution_forms(tmp_path):
    src = tmp_path / "src"
    (src / "lib").mkdir(parents=True)
    (src / "lib" / "index.ts").write_text("export const lib = 1;\n", encoding="utf-8")
    (src / "util.ts").write_text("export const u = 1;\n", encoding="utf-8")
    (src / "lazy.tsx").write_text("export default 1;\n", encoding="utf-8")
    (src / "main.ts").write_text(
        "import { lib } from './lib';\n"
        "export { u } from './util.js';\n"
        "const lazy = () => import('./lazy');\n"
        "// import { gone } from './commented-out';\n"
        "import React from 'react';\nimport { x } from '@scope/pkg/sub';\n", encoding="utf-8")
    rc, rep = run_json(mod, [str(tmp_path), "--json", "--top", "50"])
    main = next(r for r in rep["coupling"] if r["file"] == "src/main.ts")
    assert main["fan_out"] == 3 and main["external"] == 2
    assert rep["external_packages"] == {"@scope/pkg": 1, "react": 1}


def test_merge_goal_folds_a_small_single_consumer_package(tmp_path):
    for pkg in ("core", "tiny"):
        (tmp_path / pkg).mkdir()
    (tmp_path / "core" / "a.py").write_text("from tiny.helper import h\n", encoding="utf-8")
    (tmp_path / "core" / "b.py").write_text("from tiny.helper import h\n", encoding="utf-8")
    (tmp_path / "core" / "c.py").write_text("X = 1\n", encoding="utf-8")
    (tmp_path / "tiny" / "helper.py").write_text("def h():\n    return 1\n", encoding="utf-8")
    rc, rep = run_json(mod, [str(tmp_path), "--goal", "merge", "--json"])
    assert [(m["file"], m["to"], m["blast_radius"]) for m in rep["moves"]] == [("tiny/helper.py", "core", 2)]
    assert rep["commands"] == ["git mv tiny/helper.py core/helper.py"]


def test_name_collision_goes_to_a_subfolder_with_mkdir(tmp_path):
    for pkg in ("api", "reports"):
        (tmp_path / pkg).mkdir()
    (tmp_path / "api" / "fmt.py").write_text("X = 1\n", encoding="utf-8")
    (tmp_path / "api" / "routes.py").write_text("from reports.fmt import f\nfrom api.fmt import X\n", encoding="utf-8")
    (tmp_path / "reports" / "fmt.py").write_text("def f():\n    return 1\n", encoding="utf-8")
    rc, rep = run_json(mod, [str(tmp_path), "--goal", "split", "--json"])
    assert rep["commands"] == ["mkdir -p api/reports", "git mv reports/fmt.py api/reports/fmt.py"]
    assert "already exists" in rep["moves"][0]["note"]
