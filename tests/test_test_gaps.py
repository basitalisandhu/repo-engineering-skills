import ast

from conftest import FIXTURES, load_script, run_json, run_main

mod = load_script("untested-entry-points", "test_gaps.py")
REPO = FIXTURES / "test_gaps" / "project"


def test_planted_untested_units_are_ranked():
    rc, rep = run_json(mod, [str(REPO), "--json"])
    assert rc == 0
    ranked = [(u["name"], u["path"]) for u in rep["ranked_untested"]]
    assert ranked == [("main", "src/calc/cli.py"), ("parse_config", "src/calc/core.py"), ("slugify", "web/format.ts")]
    assert rep["ranked_untested"][0]["entry_point"] is True
    pc = rep["ranked_untested"][1]
    assert pc["fan_in"] == 1 and pc["size"] == 10
    tested = {u["name"] for u in rep["tested_units"]}
    assert tested == {"add", "Calculator", "formatDate"}
    assert "_private_helper" not in str(rep)
    assert rep["frameworks"] == {"js": "vitest", "python": "pytest"}


def test_methods_lists_only_untested_public_method():
    rc, rep = run_json(mod, [str(REPO), "--json", "--methods"])
    assert rc == 0

    method_gaps = [
        u["name"] for u in rep["ranked_untested"]
        if u["kind"] == "method"
    ]
    assert method_gaps == ["Calculator.untested_method"]


def test_method_stub_is_valid_python(tmp_path):
    rc, rep = run_json(
        mod,
        [str(REPO), "--json", "--methods", "--stubs-dir", str(tmp_path)],
    )
    assert rc == 0

    stub = tmp_path / "test_calculator_untested_method_characterisation.py"
    assert stub.exists()

    source = stub.read_text()
    ast.parse(source)

    assert "from calc.calculator import Calculator" in source
    assert "Calculator().untested_method(...)" in source

def test_method_stub_is_valid_unittest_python(tmp_path):
    unit = {
        "name": "Calculator.untested_method",
        "path": "src/calc/calculator.py",
        "line": 10,
        "lang": "python",
        "kind": "method",
        "module": "calc.calculator",
        "params": [],
    }

    source = mod.stub(unit, "unittest")[1]
    ast.parse(source)


def test_stubs_are_valid_and_skipped(tmp_path):
    rc, rep = run_json(mod, [str(REPO), "--json", "--stubs-dir", str(tmp_path)])
    files = sorted(p.name for p in tmp_path.iterdir())
    assert files == ["slugify.characterisation.test.ts", "test_main_characterisation.py",
                     "test_parse_config_characterisation.py"]
    py = (tmp_path / "test_parse_config_characterisation.py").read_text()
    ast.parse(py)
    assert "from calc.core import parse_config" in py and "pytest.mark.skip" in py and "text=..." in py
    assert "test.todo(" in (tmp_path / "slugify.characterisation.test.ts").read_text()
    (tmp_path / "test_main_characterisation.py").write_text("keep me")
    run_main(mod, [str(REPO), "--stubs-dir", str(tmp_path)])
    assert (tmp_path / "test_main_characterisation.py").read_text() == "keep me"


def test_unittest_and_node_frameworks(tmp_path):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "m.py").write_text("def f(x):\n    return x\n")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_x.py").write_text("import unittest\n")
    (tmp_path / "lib.js").write_text("export function g(a) {\n  return a;\n}\n")
    rc, rep = run_json(mod, [str(tmp_path), "--json", "--stubs"])
    assert rep["frameworks"] == {"js": "node:test", "python": "unittest"}
    contents = "\n".join(s["content"] for s in rep["stubs"])
    assert "unittest.skip" in contents and 'from "node:test"' in contents


def test_gate_and_text_output(tmp_path):
    rc, out, _ = run_main(mod, [str(REPO), "--max-untested", "2"])
    assert rc == 1 and "parse_config" in out and "does not mean the code ran" in out
    assert run_main(mod, [str(REPO), "--max-untested", "3"])[0] == 0
    assert run_main(mod, [str(tmp_path / "nope")])[0] == 2
    rc, out, _ = run_main(mod, ["--help"])
    assert rc == 0 and "--stubs-dir" in out
