import json

import pytest
from conftest import FIXTURES, load_script, run_json, run_main

facts_mod = load_script("repo-onboarding-guide", "onboarding_facts.py")
mod = load_script("repo-onboarding-guide", "onboarding_lint.py")
HERE = FIXTURES / "onboarding"


@pytest.fixture
def facts_file(tmp_path):
    path = tmp_path / "facts.json"
    rc, _, _ = run_main(facts_mod, [str(HERE / "repo"), "--out", str(path)])
    assert rc == 0
    return path


def test_good_guide_passes(facts_file):
    rc, rep = run_json(mod, [str(HERE / "good_guide.md"), str(facts_file), "--json"])
    assert rc == 0, rep["findings"]
    assert rep["findings"] == []
    assert rep["stats"]["supported"] == rep["stats"]["claims"] >= 9
    assert rep["fact_kinds_not_mentioned"] == []


def test_bad_guide_flags_exactly_the_planted_claims(facts_file):
    rc, rep = run_json(mod, [str(HERE / "bad_guide.md"), str(facts_file), "--json"])
    assert rc == 1
    got = {(f["rule"], f["line"], tuple(f["unmatched"])) for f in rep["findings"]}
    assert got == {
        ("ONB-UNSUPPORTED", 5, ("npm run serve",)),
        ("ONB-UNSUPPORTED", 7, ("inventory/server.py",)),
        ("ONB-UNSUPPORTED", 9, ("REDIS_URL", "Redis")),
        ("ONB-UNSUPPORTED", 11, ("@acme/backend",)),
        ("ONB-CITE", 13, ("inventory/cli.py:99",)),
        ("ONB-NOFACT", 15, ()),
    }
    assert rep["stats"]["supported"] == 2


def test_allow_list_and_fact_ids(facts_file, tmp_path):
    guide = tmp_path / "g.md"
    guide.write_text("Run `ruff check .` before pushing.\n\nThe CLI lives in `inventory/cli.py` [F99].\n")
    rc, rep = run_json(mod, [str(guide), str(facts_file), "--json", "--allow", "ruff check ."])
    assert rc == 1
    assert [(f["rule"], f["unmatched"]) for f in rep["findings"]] == [("ONB-CITE", ["F99"])]


def test_code_block_lines_are_claims(facts_file, tmp_path):
    guide = tmp_path / "g.md"
    guide.write_text("```bash\n# comment lines are skipped\npython -m pytest -q\nnpm run deploy\n```\n")
    rc, rep = run_json(mod, [str(guide), str(facts_file), "--json"])
    assert rc == 1
    assert [(f["line"], f["unmatched"]) for f in rep["findings"]] == [(4, ["npm run deploy"])]


def test_bad_input(tmp_path, facts_file):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"nope": []}))
    guide = HERE / "good_guide.md"
    assert run_main(mod, [str(guide), str(bad)])[0] == 2
    assert run_main(mod, [str(tmp_path / "missing.md"), str(facts_file)])[0] == 2
    rc, out, _ = run_main(mod, [str(HERE / "bad_guide.md"), str(facts_file)])
    assert rc == 1 and "ONB-NOFACT" in out


def test_tables_urls_and_service_aliases(facts_file, tmp_path):
    guide = tmp_path / "g.md"
    guide.write_text("| Variable | Read in |\n|---|---|\n| `DATABASE_URL` | `inventory/cli.py` |\n"
                     "| `SMTP_HOST` | `inventory/mail.py` |\n\n"
                     "Docs are at https://example.com/docs/setup.md and the database is Postgres.\n")
    rc, rep = run_json(mod, [str(guide), str(facts_file), "--json"])
    assert [(f["line"], f["unmatched"]) for f in rep["findings"]] == [(4, ["SMTP_HOST", "inventory/mail.py"])]
    assert rep["stats"]["supported"] == 2


def test_directory_ancestors_and_command_fragments(facts_file, tmp_path):
    guide = tmp_path / "g.md"
    guide.write_text("The front end code is in `web/src/`. CI calls `pytest -q` through `python -m pytest -q`.\n")
    rc, rep = run_json(mod, [str(guide), str(facts_file), "--json"])
    assert rc == 0, rep["findings"]
