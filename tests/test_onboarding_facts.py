from conftest import FIXTURES, load_script, run_json, run_main

mod = load_script("repo-onboarding-guide", "onboarding_facts.py")
REPO = FIXTURES / "onboarding" / "repo"


def facts_by_kind(rep, kind):
    return [f for f in rep["facts"] if f["kind"] == kind]


def test_every_fact_has_an_id_and_a_resolvable_citation():
    rc, rep = run_json(mod, [str(REPO), "--json"])
    assert rc == 0
    assert [f["id"] for f in rep["facts"]] == [f"F{i}" for i in range(1, len(rep["facts"]) + 1)]
    for f in rep["facts"]:
        path, _, line = f["citation"].partition(":")
        assert (REPO / path).exists(), f["citation"]
        if line:
            lines = (REPO / path).read_text(encoding="utf-8").splitlines()
            assert 1 <= int(line) <= len(lines), f["citation"]


def test_entry_points_commands_and_tests():
    rc, rep = run_json(mod, [str(REPO), "--json"])
    entry = {f["citation"] for f in facts_by_kind(rep, "entry_point")}
    assert entry == {"pyproject.toml:7", "inventory/cli.py:13"}
    commands = {f["command"] for f in facts_by_kind(rep, "command")}
    assert {"make run", "cd web && npm run start", "pip install -e ."} <= commands
    tests = {f.get("command") for f in facts_by_kind(rep, "test_command")}
    assert {"python -m pytest -q", "make test", "cd web && npm run test", "pytest"} <= tests
    loc = facts_by_kind(rep, "test_location")
    assert [(f["text"], f["citation"]) for f in loc] == [("1 test file(s) under `tests/`", "tests/test_cli.py:1")]


def test_directories_env_services_and_owners():
    rc, rep = run_json(mod, [str(REPO), "--json"])
    dirs = {f["path"]: (f["purpose"], f["basis"]) for f in facts_by_kind(rep, "directory")}
    assert dirs["inventory/"] == ("Stock tracking service for the warehouse team.",
                                  "first line of inventory/__init__.py")
    assert dirs["docs/"] == ("Operator runbooks and design notes", "first line of docs/README.md")
    assert dirs["web/"] == ("web front end", "directory name")
    env = {f["name"]: f["citation"] for f in facts_by_kind(rep, "env_var")}
    assert env["DATABASE_URL"] == "inventory/cli.py:7"
    assert env["API_BASE_URL"] == "web/src/index.js:1"
    assert {f["service"] for f in facts_by_kind(rep, "external_service")} == {"PostgreSQL"}
    owners = {f["pattern"]: f["owners"] for f in facts_by_kind(rep, "owner")}
    assert owners == {"*": ["@acme/platform"], "/web/": ["@acme/frontend"]}


def test_no_invented_services_or_purposes(tmp_path):
    (tmp_path / "misc").mkdir()
    (tmp_path / "misc" / "notes.txt").write_text("x\n", encoding="utf-8")
    (tmp_path / "app.py").write_text("import os\nTOKEN = os.environ['MY_TOKEN']\n", encoding="utf-8")
    rc, rep = run_json(mod, [str(tmp_path), "--json"])
    assert rc == 0
    misc = facts_by_kind(rep, "directory")[0]
    assert misc["purpose"] is None and misc["basis"] == "none" and "purpose not stated" in misc["text"]
    assert facts_by_kind(rep, "external_service") == []
    assert [f["name"] for f in facts_by_kind(rep, "env_var")] == ["MY_TOKEN"]


def test_text_output_out_file_and_errors(tmp_path):
    out = tmp_path / "facts.json"
    rc, text, _ = run_main(mod, [str(REPO), "--out", str(out)])
    assert rc == 0 and "owner (2):" in text and out.exists()
    rc, _, err = run_main(mod, [str(tmp_path / "missing")])
    assert rc == 2 and "not a directory" in err
    rc, text, _ = run_main(mod, ["--help"])
    assert rc == 0 and "--out" in text


def test_other_entry_point_and_command_sources(tmp_path):
    (tmp_path / "justfile").write_text("serve port='8000':\n    uvicorn app:app\n\ncheck:\n    ruff check .\n",
                                       encoding="utf-8")
    (tmp_path / "Procfile").write_text("web: gunicorn app:app\n", encoding="utf-8")
    (tmp_path / "Dockerfile").write_text("FROM python:3.12-slim\nENTRYPOINT [\"svc\"]\n", encoding="utf-8")
    (tmp_path / "svc").mkdir()
    (tmp_path / "svc" / "__main__.py").write_text("print('hi')\n", encoding="utf-8")
    (tmp_path / "package.json").write_text('{"name": "x", "bin": {"x": "./bin/x.js"}, "main": "index.js"}',
                                           encoding="utf-8")
    (tmp_path / ".env.example").write_text("# comment\nSTRIPE_SECRET_KEY=\nexport SENTRY_DSN=\n", encoding="utf-8")
    rc, rep = run_json(mod, [str(tmp_path), "--json"])
    texts = {f["text"] for f in rep["facts"]}
    assert "`just serve` is a just target" in texts
    assert "`just check` is a just target" in {f["text"] for f in facts_by_kind(rep, "test_command")}
    assert "Procfile process `web` runs `gunicorn app:app`" in texts
    assert "Dockerfile ENTRYPOINT is `[\"svc\"]`" in texts
    assert "`python -m svc` runs svc/__main__.py" in texts
    assert "npm bin `x` runs `./bin/x.js`" in texts
    assert {f["service"] for f in facts_by_kind(rep, "external_service")} == {"Stripe", "Sentry"}
    assert {f["citation"] for f in facts_by_kind(rep, "env_var")} == {".env.example:2", ".env.example:3"}
