import pytest
from conftest import git_commit, load_script, run_json, run_main

mod = load_script("adr-miner", "adr_mine.py")


@pytest.fixture(scope="module")
def history(tmp_path_factory):
    repo = tmp_path_factory.mktemp("adr") / "repo"
    shas = {}
    shas["init"] = git_commit(repo, "Initial commit", {
        "pyproject.toml": '[project]\nname = "svc"\ndependencies = [\n  "requests>=2.31",\n]\n',
        "Dockerfile": "FROM python:3.11-slim\nCMD [\"svc\"]\n",
        "svc/app.py": "def run():\n    return 1\n",
    }, date="2026-01-01T10:00:00")
    shas["httpx"] = git_commit(repo, "Switch HTTP client to httpx in favour of requests\n\nWe need async calls "
                                     "for the webhook fan-out.", {
        "pyproject.toml": '[project]\nname = "svc"\ndependencies = [\n  "httpx>=0.27",\n]\n',
    }, date="2026-02-01T10:00:00")
    shas["typo"] = git_commit(repo, "Fix typo in README", {"README.md": "# svc\n"}, date="2026-02-02T10:00:00")
    shas["base"] = git_commit(repo, "Bump base image", {
        "Dockerfile": "FROM python:3.12-slim\nCMD [\"svc\"]\n",
    }, date="2026-03-01T10:00:00")
    shas["note"] = git_commit(repo, "Add store", {
        "svc/store.py": "# NOTE: we use sqlite here because CI has no database service\nDB = 'sqlite'\n"
                        "# TODO: tidy this up\n",
    }, date="2026-03-05T10:00:00")
    shas["drop"] = git_commit(repo, "docs: drop the old deploy guide", {"README.md": None},
                              date="2026-03-06T10:00:00")
    return repo, shas


def test_finds_message_config_and_comment_candidates(history):
    repo, shas = history
    rc, rep = run_json(mod, [str(repo), "--json"])
    assert rc == 0
    by_sha = {c["sha"]: c for c in rep["candidates"] if c["sha"] and "comment" not in c["source"]}
    assert set(by_sha) == {shas["httpx"], shas["base"], shas["drop"]}
    httpx = by_sha[shas["httpx"]]
    assert httpx["source"] == ["commit", "config"]
    assert {"switch http client to", "in favour of"} <= set(httpx["decision_words"])
    assert httpx["reasons"] == ["pyproject.toml: removed requests; added httpx"]
    assert by_sha[shas["base"]]["source"] == ["config"]
    assert by_sha[shas["base"]]["reasons"] == ["Dockerfile: base image python:3.11-slim -> python:3.12-slim"]
    assert by_sha[shas["drop"]]["source"] == ["commit"]
    comments = [c for c in rep["candidates"] if "comment" in c["source"]]
    assert [(c["citation"], c["sha"], c["tag"]) for c in comments] == [("svc/store.py:1", shas["note"], "NOTE")]
    assert comments[0]["date"] == "2026-03-05"


def test_typo_commit_and_rationale_free_todo_are_ignored(history):
    repo, shas = history
    rc, rep = run_json(mod, [str(repo), "--json"])
    assert shas["typo"] not in {c["sha"] for c in rep["candidates"]}
    assert not any("tidy" in c.get("text", "") for c in rep["candidates"])


def test_stubs_are_madr_and_cite_their_source(history, tmp_path):
    repo, shas = history
    out_dir = tmp_path / "adr"
    out_dir.mkdir()
    (out_dir / "0007-existing.md").write_text("# 7. Existing\n\n- Status: accepted\n")
    rc, rep = run_json(mod, [str(repo), "--json", "--out-dir", str(out_dir)])
    assert rc == 0
    names = sorted(p.name for p in out_dir.iterdir())
    assert names[0] == "0007-existing.md" and names[1].startswith("0008-") and len(names) == 5
    httpx = next(c for c in rep["candidates"] if c["sha"] == shas["httpx"])
    text = open(httpx["stub"], encoding="utf-8").read()
    assert text.startswith("# ") and "- Status: proposed" in text
    assert f"commit {shas['httpx'][:12]}" in text
    assert "removed: `\"requests>=2.31\",`" in text and "added: `\"httpx>=0.27\",`" in text
    assert "## Consequences\n\nTo be written by the author" in text
    assert "Not recorded in the history" in text
    rc, rep2 = run_json(mod, [str(repo), "--json", "--out-dir", str(out_dir)])
    assert len(list(out_dir.iterdir())) == 9


def test_range_no_comments_and_stub_printing(history):
    repo, shas = history
    rc, rep = run_json(mod, [str(repo), "--json", "--range", f"{shas['typo']}..HEAD", "--no-comments"])
    assert {c["sha"] for c in rep["candidates"]} == {shas["base"], shas["drop"]}
    rc, text, _ = run_main(mod, [str(repo), "--no-comments", "--stubs"])
    assert rc == 0 and "## Decision Outcome" in text and "[commit+config]" in text


def test_bad_input(tmp_path, history):
    repo, _ = history
    assert run_main(mod, [str(tmp_path / "missing")])[0] == 2
    plain = tmp_path / "plain"
    plain.mkdir()
    rc, _, err = run_main(mod, [str(plain)])
    assert rc == 2 and "error" in err
    assert run_main(mod, [str(repo), "--range", "--output=/tmp/x"])[0] == 2
    assert run_main(mod, [str(repo), "--range", "nope..HEAD"])[0] == 2


def test_package_json_swap_and_ci_file_added(tmp_path):
    repo = tmp_path / "js"
    git_commit(repo, "init", {"package.json": '{\n  "dependencies": {\n    "moment": "^2.29.0"\n  }\n}\n'})
    swap = git_commit(repo, "Use a smaller date library", {
        "package.json": '{\n  "dependencies": {\n    "dayjs": "^1.11.0"\n  }\n}\n'})
    ci = git_commit(repo, "Set up CI", {".github/workflows/ci.yml": "on: [push]\n"})
    rc, rep = run_json(mod, [str(repo), "--json", "--no-comments"])
    reasons = {c["sha"]: c["reasons"] for c in rep["candidates"]}
    assert reasons == {swap: ["package.json: removed moment; added dayjs"],
                       ci: ["CI file .github/workflows/ci.yml added"]}
