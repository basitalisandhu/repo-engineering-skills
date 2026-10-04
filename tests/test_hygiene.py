import json

from conftest import git_commit, load_script, run_json, run_main

mod = load_script("repo-hygiene-bundle", "hygiene.py")

# Secret-shaped test values are assembled at run time so no committed file contains one.
AWS_ID = "AK" + "IA" + "ABCDEFGHIJKLMNOP"
GH_TOKEN = "gh" + "p_" + "a1B2" * 9
KEY_HEADER = "-----BEGIN " + "RSA PRIVATE KEY" + "-----"
GENERIC = "s3cr3t" + "Value" + "123456"


def rules(rep):
    return {(f["rule"], f["severity"], f["path"]) for f in rep["findings"]}


def test_planted_defects_in_the_fixture(fixture_copy):
    repo = fixture_copy("hygiene/repo")
    rc, rep = run_json(mod, [str(repo), "--json"])
    assert rc == 1
    assert rules(rep) == {
        ("HYG-PERMS", "high", ".github/workflows/ci.yml"),
        ("HYG-PIN", "medium", ".github/workflows/ci.yml"),
        ("HYG-DUPDEP", "medium", "packages/a/package.json"),
        ("HYG-LICENSE", "medium", "."),
        ("HYG-LOCK", "medium", "package.json"),
        ("HYG-LOCK", "medium", "packages/b/package.json"),
        ("HYG-LOCKDRIFT", "medium", "packages/a/package-lock.json"),
        ("HYG-LOCK", "low", "pyproject.toml"),
        ("HYG-SPDX", "low", "packages/b/package.json"),
        ("HYG-SPDX", "low", "pyproject.toml"),
        ("HYG-SECURITY", "low", "."),
        ("HYG-COC", "low", "."),
        ("HYG-GENERATED", "low", "dist/"),
    }
    assert rep["counts"] == {"high": 1, "medium": 6, "low": 6}
    assert not any(f["path"] == "settings.py" for f in rep["findings"]), "placeholders must not be flagged"
    assert not any(f["path"] == ".github/workflows/ok.yml" for f in rep["findings"])


def test_secrets_are_found_and_redacted(fixture_copy):
    repo = fixture_copy("hygiene/repo")
    (repo / "app.py").write_text(f'AWS_ID = "{AWS_ID}"\ntoken = "{GH_TOKEN}"\ndb_password = "{GENERIC}"\n'
                                 f'safe = "{AWS_ID}"  # hygiene: ignore\n')
    (repo / "deploy_key").write_text(KEY_HEADER + "\nabc\n")
    rc, out, _ = run_main(mod, [str(repo), "--rule", "HYG-SECRET"])
    assert rc == 1
    rc, rep = run_json(mod, [str(repo), "--json", "--rule", "hyg-secret"])
    got = {(f["path"], f["line"], f["severity"]) for f in rep["findings"]}
    assert got == {("app.py", 1, "high"), ("app.py", 2, "high"), ("app.py", 3, "medium"), ("deploy_key", 1, "high")}
    dumped = json.dumps(rep) + out
    for secret in (AWS_ID, GH_TOKEN, GENERIC):
        assert secret not in dumped
    assert "AKIA... (20 chars)" in dumped


def test_large_file_and_fail_on_levels(fixture_copy):
    repo = fixture_copy("hygiene/repo")
    (repo / "blob.bin").write_bytes(b"\0" * 3000)
    rc, rep = run_json(mod, [str(repo), "--json", "--max-file-kb", "2", "--rule", "HYG-LARGE"])
    assert [(f["path"], f["severity"]) for f in rep["findings"]] == [("blob.bin", "medium")]
    assert run_main(mod, [str(repo), "--rule", "HYG-COC"])[0] == 0
    assert run_main(mod, [str(repo), "--rule", "HYG-COC", "--fail-on", "low"])[0] == 1
    assert run_main(mod, [str(repo), "--fail-on", "none"])[0] == 0
    assert run_main(mod, [str(repo), "--fail-on", "high", "--rule", "HYG-PIN"])[0] == 0


def test_sarif_output(fixture_copy, tmp_path):
    repo = fixture_copy("hygiene/repo")
    sarif_path = tmp_path / "out.sarif"
    run_main(mod, [str(repo), "--sarif", str(sarif_path)])
    data = json.loads(sarif_path.read_text())
    assert data["version"] == "2.1.0"
    run = data["runs"][0]
    assert run["tool"]["driver"]["name"] == "repo-hygiene-bundle"
    assert {r["id"] for r in run["tool"]["driver"]["rules"]} >= {"HYG-PERMS", "HYG-PIN"}
    perms = next(r for r in run["results"] if r["ruleId"] == "HYG-PERMS")
    assert perms["level"] == "error"
    assert perms["locations"][0]["physicalLocation"]["region"]["startLine"] == 3


def test_clean_repository_passes(tmp_path):
    (tmp_path / "LICENSE").write_text("MIT License\n\nPermission is hereby granted, free of charge, to any person\n")
    (tmp_path / "SECURITY.md").write_text("# Security\n")
    (tmp_path / ".github").mkdir()
    (tmp_path / ".github" / "CODE_OF_CONDUCT.md").write_text("# Code of conduct\n")
    (tmp_path / "package.json").write_text(json.dumps({"name": "x", "license": "MIT",
                                                        "dependencies": {"lodash": "^4.17.21"}}))
    (tmp_path / "package-lock.json").write_text(json.dumps({"lockfileVersion": 3, "packages": {
        "": {"dependencies": {"lodash": "^4.17.21"}}, "node_modules/lodash": {"version": "4.17.21"}}}))
    rc, rep = run_json(mod, [str(tmp_path), "--json"])
    assert rc == 0 and rep["findings"] == [] and rep["licence_family"] == "MIT"


def test_licence_mismatch_and_uv_lock_drift(tmp_path):
    (tmp_path / "LICENSE").write_text("Apache License, Version 2.0\n")
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "x"\nlicense = "MIT"\n'
                                             'dependencies = ["httpx>=0.27", "rich"]\n')
    (tmp_path / "uv.lock").write_text('version = 1\n[[package]]\nname = "httpx"\nversion = "0.27.0"\n')
    rc, rep = run_json(mod, [str(tmp_path), "--json", "--rule", "HYG-SPDX", "--rule", "HYG-LOCKDRIFT"])
    msgs = sorted((f["rule"], f["severity"], f["message"]) for f in rep["findings"])
    assert msgs[0][:2] == ("HYG-LOCKDRIFT", "medium") and "rich" in msgs[0][2]
    assert msgs[1][:2] == ("HYG-SPDX", "medium") and "Apache-2.0" in msgs[1][2]


def test_git_mode_counts_only_committed_files(tmp_path):
    repo = tmp_path / "r"
    git_commit(repo, "init", {"LICENSE": "MIT License\n", "SECURITY.md": "x\n", "CODE_OF_CONDUCT.md": "x\n"})
    (repo / "dist").mkdir()
    (repo / "dist" / "out.js").write_text("x\n")
    rc, rep = run_json(mod, [str(repo), "--json"])
    assert rep["file_source"] == "git ls-files"
    assert rc == 0 and rep["findings"] == []


def test_bad_input(tmp_path):
    assert run_main(mod, [str(tmp_path / "missing")])[0] == 2
    rc, out, _ = run_main(mod, ["--help"])
    assert rc == 0 and "--sarif" in out


def test_workflow_refs_that_need_no_pin_and_refs_with_none(tmp_path):
    wf = tmp_path / ".github" / "workflows"
    wf.mkdir(parents=True)
    (wf / "a.yml").write_text("permissions:\n  contents: read\njobs:\n  x:\n    steps:\n"
                              "      - uses: ./local-action\n      - uses: docker://alpine:3.20\n"
                              "      - uses: some/action\n      - uses: 'other/action@main'\n")
    rc, rep = run_json(mod, [str(tmp_path), "--json", "--rule", "HYG-PIN", "--rule", "HYG-PERMS"])
    assert [(f["line"], f["message"].split(" ")[0]) for f in rep["findings"]] == [(8, "some/action"),
                                                                                 (9, "other/action@main")]


def test_other_manifests_and_two_js_lockfiles(tmp_path):
    (tmp_path / "Cargo.toml").write_text('[package]\nname = "x"\nlicense = "MIT OR Apache-2.0"\n'
                                         '[dependencies]\nserde = "1"\n')
    (tmp_path / "Gemfile").write_text("gem 'rails'\n")
    (tmp_path / "package.json").write_text('{"name": "y", "license": "MIT", "dependencies": {"a": "1"}}')
    (tmp_path / "yarn.lock").write_text("a@1:\n  version 1\n")
    (tmp_path / "package-lock.json").write_text('{"lockfileVersion": 3, "packages": {"": {"dependencies": '
                                                '{"a": "1"}}, "node_modules/a": {}}}')
    rc, rep = run_json(mod, [str(tmp_path), "--json", "--rule", "HYG-LOCK", "--rule", "HYG-LOCKDRIFT",
                             "--rule", "HYG-SPDX"])
    got = sorted((f["rule"], f["severity"], f["path"]) for f in rep["findings"])
    assert got == [("HYG-LOCK", "low", "Cargo.toml"), ("HYG-LOCK", "medium", "Gemfile"),
                   ("HYG-LOCKDRIFT", "low", "package.json")]


def test_exclude_leaves_paths_out(fixture_copy):
    repo = fixture_copy("hygiene/repo")
    rc, rep = run_json(mod, [str(repo), "--json", "--exclude", "packages", "--exclude", ".github/workflows/*.yml",
                             "--exclude", "dist"])
    paths = {f["path"] for f in rep["findings"]}
    assert not any(p.startswith(("packages/", ".github/", "dist")) for p in paths)
    assert ("HYG-LICENSE", "medium", ".") in rules(rep)
