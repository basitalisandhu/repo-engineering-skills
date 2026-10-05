from conftest import FIXTURES, load_script, run_json, run_main

mod = load_script("docs-truth-check", "docs_truth_check.py")
REPO = FIXTURES / "docs_truth" / "sample_repo"


def test_setuptools_dynamic_attr_resolves_literal_without_executing(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "example"\ndynamic = ["version"]\n'
        '[tool.setuptools.dynamic]\nversion = {attr = "example.__version__"}\n'
    )
    package = tmp_path / "src/example"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text(
        'raise RuntimeError("must not execute")\n__version__ = "1.2.3"\n'
    )
    (tmp_path / "README.md").write_text("example==1.2.3\nexample==1.2.0\n")
    _, rep = run_json(mod, [str(tmp_path), "--json"])
    assert {(c["claim"], c["status"]) for c in rep["claims"] if c["kind"] == "version"} == {
        ("example 1.2.3", "verified"), ("example 1.2.0", "stale"),
    }


def test_hatch_dynamic_path_resolves_literal_and_unverified_nonliteral(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "example"\ndynamic = ["version"]\n'
        '[tool.hatch.version]\npath = "version.py"\n'
    )
    version = tmp_path / "version.py"
    version.write_text('__version__: str = "2.3.4"\n')
    (tmp_path / "README.md").write_text("example version 2.3.4\n")
    _, rep = run_json(mod, [str(tmp_path), "--json"])
    assert any(c["kind"] == "version" and c["status"] == "verified" for c in rep["claims"])
    version.write_text('__version__ = calculate_version()\n')
    _, rep = run_json(mod, [str(tmp_path), "--json"])
    claim = next(c for c in rep["claims"] if c["kind"] == "version")
    assert claim["status"] == "unverified" and claim["detail"]


def test_unconfigured_dynamic_version_is_not_silently_skipped(tmp_path):
    (tmp_path / "pyproject.toml").write_text('[project]\nname="example"\ndynamic=["version"]\n')
    (tmp_path / "README.md").write_text("example@3.2.1\n")
    _, rep = run_json(mod, [str(tmp_path), "--json"])
    assert any(c["kind"] == "version" and c["status"] == "unverified" for c in rep["claims"])

PLANTED = {
    ("version", "greeter 1.1.0", "stale"),
    ("default", "--retries default 3", "stale"),
    ("default", "GREETER_LANG default es", "stale"),
    ("flag", "--color (src/greeter/cli.py)", "missing"),
    ("path", "src/greeter/helpers.py", "missing"),
    ("symbol", "format_name()", "missing"),
    ("link", "docs/guide.md", "missing"),
}


def failing(report):
    return {(c["kind"], c["claim"], c["status"]) for c in report["claims"] if c["status"] in {"missing", "stale"}}


def test_every_planted_defect_is_caught_and_nothing_else():
    rc, rep = run_json(mod, [str(REPO), "--json"])
    assert rc == 1
    assert failing(rep) == PLANTED
    assert rep["summary"]["unverified"] == 0


def test_true_claims_are_verified():
    _, rep = run_json(mod, [str(REPO), "--json"])
    verified = {(c["kind"], c["claim"]) for c in rep["claims"] if c["status"] == "verified"}
    for expected in [
        ("path", "src/greeter/cli.py"),
        ("flag", "--shout (src/greeter/cli.py)"),
        ("flag", "--times (src/greeter/cli.py)"),
        ("flag", "--dry-run (scripts/release.sh)"),
        ("default", "--times default 1"),
        ("default", "--name default world"),
        ("env", "GREETER_LANG"),
        ("symbol", "build_greeting()"),
        ("symbol", "normalise_name()"),
        ("link", "docs/usage.md"),
        ("target", "make test"),
        ("version", "greeter 1.2.0"),
    ]:
        assert expected in verified, expected


def test_wrong_default_reports_the_code_value():
    _, rep = run_json(mod, [str(REPO), "--json"])
    stale = next(c for c in rep["claims"] if c["kind"] == "default" and c["status"] == "stale")
    assert "5" in stale["detail"] and stale["location"].startswith("README.md:")


def test_environment_defaults_compare_literal_get_and_getenv_values(tmp_path):
    (tmp_path / "settings.py").write_text(
        'import os\nAPP_LANGUAGE = os.environ.get("APP_LANGUAGE", "en")\n'
        'APP_REGION = os.getenv("APP_REGION", "global")\n'
        'APP_MODE = os.getenv("APP_MODE", configured_mode)\n'
    )
    (tmp_path / "README.md").write_text(
        "APP_LANGUAGE defaults to `en`.\nAPP_REGION defaults to `global`.\nAPP_MODE defaults to `safe`.\n"
    )
    _, rep = run_json(mod, [str(tmp_path), "--json"])
    statuses = {(c["claim"], c["status"]) for c in rep["claims"] if c["kind"] == "default"}
    assert ("APP_LANGUAGE default en", "verified") in statuses
    assert ("APP_REGION default global", "verified") in statuses
    assert ("APP_MODE default safe", "unverified") in statuses


def test_environment_defaults_detect_from_os_imports(tmp_path):
    (tmp_path / "settings.py").write_text(
        "from os import environ, getenv\n"
        'APP_LANGUAGE = environ.get("APP_LANGUAGE", "en")\n'
        'APP_REGION = getenv("APP_REGION", "global")\n'
        "from os import environ as settings, getenv as read_env\n"
        'APP_MODE = settings.get("APP_MODE", "safe")\n'
        'APP_STAGE = read_env("APP_STAGE", "prod")\n'
    )
    (tmp_path / "README.md").write_text(
        "APP_LANGUAGE defaults to `en`.\nAPP_REGION defaults to `global`.\n"
        "APP_MODE defaults to `safe`.\nAPP_STAGE defaults to `prod`.\n"
    )
    _, rep = run_json(mod, [str(tmp_path), "--json"])
    statuses = {(claim["claim"], claim["status"]) for claim in rep["claims"] if claim["kind"] == "default"}
    assert ("APP_LANGUAGE default en", "verified") in statuses
    assert ("APP_REGION default global", "verified") in statuses
    assert ("APP_MODE default safe", "verified") in statuses
    assert ("APP_STAGE default prod", "verified") in statuses


def test_fixing_the_docs_makes_the_gate_pass(fixture_copy):
    repo = fixture_copy("docs_truth/sample_repo")
    readme = repo / "README.md"
    text = readme.read_text()
    text = (text.replace("greeter==1.1.0", "greeter==1.2.0")
            .replace("defaults to `3`", "defaults to `5`")
            .replace("`GREETER_LANG` defaults to `es`", "`GREETER_LANG` defaults to `en`"))
    text = text.replace(" --color red", "").replace("src/greeter/helpers.py", "src/greeter/utils.py")
    text = text.replace("call `format_name()`", "call `normalise_name()`")
    text = text.replace(" and the [old guide](docs/guide.md)", "")
    readme.write_text(text)
    rc, rep = run_json(mod, [str(repo), "--json"])
    assert rc == 0, failing(rep)
    assert rep["summary"]["missing"] == 0 and rep["summary"]["stale"] == 0


def test_fail_on_levels_and_table(tmp_path):
    rc, out, _ = run_main(mod, [str(REPO), "--fail-on", "none", "--only-failures", "--out", str(tmp_path / "r.json")])
    assert rc == 0
    assert "src/greeter/helpers.py" in out and "verified" not in out.split("\n\n")[0]
    assert (tmp_path / "r.json").exists()
    rc, _, _ = run_main(mod, [str(REPO), "--fail-on", "stale"])
    assert rc == 1


def test_docs_selection_and_bad_input(tmp_path):
    rc, rep = run_json(mod, [str(REPO), "--docs", "docs/*.md", "--json"])
    assert rc == 0 and rep["docs"] == ["docs/usage.md"]
    rc, _, err = run_main(mod, [str(tmp_path / "nope")])
    assert rc == 2 and "not a directory" in err
    rc, _, err = run_main(mod, [str(tmp_path)])
    assert rc == 2 and "no documentation" in err


def test_unparseable_script_flags_are_unverified_not_missing(tmp_path):
    (tmp_path / "tool").mkdir()
    (tmp_path / "tool" / "run.py").write_text("import sys\nprint(sys.argv)\n")
    (tmp_path / "README.md").write_text("```bash\npython3 tool/run.py --fast\n```\n")
    rc, rep = run_json(mod, [str(tmp_path), "--json"])
    flag = next(c for c in rep["claims"] if c["kind"] == "flag")
    assert flag["status"] == "unverified" and rc == 0


def test_run_help_reads_flags_from_help_output(tmp_path):
    (tmp_path / "tool").mkdir()
    script = "import sys\nif '--help' in sys.argv:\n    print('usage: run [--fast]')\n"
    (tmp_path / "tool" / "run.py").write_text(script)
    (tmp_path / "README.md").write_text("```bash\npython3 tool/run.py --fast --slow\n```\n")
    _, rep = run_json(mod, [str(tmp_path), "--json", "--run-help"])
    status = {c["claim"]: c["status"] for c in rep["claims"] if c["kind"] == "flag"}
    assert status == {"--fast (tool/run.py)": "verified", "--slow (tool/run.py)": "missing"}


def test_external_names_are_not_claims(tmp_path):
    (tmp_path / "README.md").write_text(
        "Install with `pip install requests` and read `os.environ`; see `owner/repo` and `application/json`.\n"
        "```bash\ngit clone https://example.com/x.git\nnpx something --flag\n```\n")
    rc, rep = run_json(mod, [str(tmp_path), "--json"])
    assert rep["claims"] == [] and rc == 0


def test_help_exits_zero():
    rc, out, _ = run_main(mod, ["--help"])
    assert rc == 0 and "--fail-on" in out


def test_cd_into_a_subproject_checks_its_package_json(tmp_path):
    (tmp_path / "web").mkdir()
    (tmp_path / "web" / "package.json").write_text('{"scripts": {"build": "tsc"}}')
    (tmp_path / "README.md").write_text(
        "```bash\ncd web && npm run build && npm run lint\n```\n\nOr just `npm run build`.\n")
    _, rep = run_json(mod, [str(tmp_path), "--json"])
    status = {(c["claim"], c["line"]): c["status"] for c in rep["claims"]}
    assert status[("npm run build", 2)] == "verified"
    assert status[("npm run lint", 2)] == "missing"
    assert status[("npm run build", 5)] == "unverified"


def test_honest_unverified_cases(tmp_path):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "a.py").write_text(
        "import argparse\np = argparse.ArgumentParser()\np.add_argument('--mode', default='fast')\n")
    (tmp_path / "pkg" / "b.py").write_text(
        "import argparse\np = argparse.ArgumentParser()\np.add_argument('--mode', default='slow')\n")
    (tmp_path / "pkg" / "tools.ts").write_text('server.tool("search_items", handler);\n')
    (tmp_path / "README.md").write_text(
        "`--mode` defaults to `medium`.\n\n`b.py --mode` defaults to `fast`.\n\n"
        "Call `search_items` or `vanished_items`. Edit `settings.local.json`.\n")
    _, rep = run_json(mod, [str(tmp_path), "--json"])
    status = {c["claim"]: (c["status"], c["detail"]) for c in rep["claims"]}
    assert status["--mode default medium"][0] == "unverified"
    assert status["--mode default fast"] == ("stale", "code default is 'slow' in pkg/b.py")
    assert status["search_items"][0] == "unverified"
    assert status["vanished_items"][0] == "missing"
    assert status["settings.local.json"][0] == "unverified"
