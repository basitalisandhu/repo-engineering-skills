import pytest
from conftest import git_commit, git_tag, load_script, run_json, run_main

mod = load_script("release-notes-verifier", "release_notes_verify.py")

CHANGELOG_BAD = """# Changelog

## [0.2.0] - 2026-10-01

### Added

- CSV export for reports (#3).
- YAML import support.

### Fixed

- Empty input no longer crashes the `parse_rows` parser.

Read the [upgrade guide](docs/upgrade.md) first.

## [0.1.0] - 2026-09-01

- First release.

[0.1.0]: https://example.com/compare/v0.0.0...v0.1.0
"""

CHANGELOG_GOOD = """# Changelog

## [0.2.0] - 2026-10-01

- CSV export for reports (#3).
- Empty input no longer crashes the `parse_rows` parser.
- Retry failed HTTP client requests with backoff.

[0.2.0]: https://example.com/compare/v0.1.0...v0.2.0
"""


@pytest.fixture(scope="module")
def repo(tmp_path_factory):
    repo = tmp_path_factory.mktemp("rel") / "repo"
    git_commit(repo, "Initial commit", {"CHANGELOG.md": "# Changelog\n", "package.json": '{"version": "0.1.0"}\n',
                                        "pyproject.toml": '[project]\nname = "p"\nversion = "0.1.0"\n'})
    git_tag(repo, "v0.1.0")
    git_commit(repo, "feat: add CSV export (#3)", {"src/export.py": "def to_csv(rows):\n    return rows\n"})
    git_commit(repo, "fix: handle empty input in parse_rows", {"src/parse.py": "def parse_rows(x):\n    return x\n"})
    git_commit(repo, "chore: bump dev dependencies", {"requirements-dev.txt": "pytest\n"})
    git_commit(repo, "feat: retry failed HTTP client requests with backoff", {"src/http.py": "RETRIES = 3\n"})
    git_commit(repo, "Release 0.2.0", {"CHANGELOG.md": CHANGELOG_BAD, "package.json": '{"version": "0.2.0"}\n',
                                       "pyproject.toml": '[project]\nname = "p"\nversion = "0.1.9"\n',
                                       "tests/fixtures/package.json": '{"version": "9.9.9"}\n'})
    git_tag(repo, "v0.2.0")
    return repo


def test_planted_mismatches_are_flagged(repo):
    rc, rep = run_json(mod, [str(repo), "--from", "v0.1.0", "--to", "v0.2.0", "--json"])
    assert rc == 1
    found = sorted((f["rule"], f["location"]) for f in rep["findings"])
    rules = [r for r, _ in found]
    assert rules.count("REL-NOTE-UNMATCHED") == 1
    unmatched = next(f for f in rep["findings"] if f["rule"] == "REL-NOTE-UNMATCHED")
    assert "YAML import" in unmatched["detail"] and unmatched["location"] == "CHANGELOG.md:8"
    unnoted = [f for f in rep["findings"] if f["rule"] == "REL-COMMIT-UNNOTED"]
    assert [f["detail"] for f in unnoted] == ["commit has no note: feat: retry failed HTTP client requests with "
                                              "backoff"]
    assert ("REL-VERSION", "pyproject.toml") in found
    assert not any(loc.startswith("tests/") for _, loc in found)
    links = [f["detail"] for f in rep["findings"] if f["rule"] == "REL-LINK"]
    assert any("[0.2.0] has no reference definition" in d for d in links)
    assert any("docs/upgrade.md does not exist" in d for d in links)
    assert len(rep["findings"]) == 5


def test_matches_use_pr_numbers_backticks_and_words(repo):
    rc, rep = run_json(mod, [str(repo), "--from", "v0.1.0", "--to", "v0.2.0", "--json"])
    notes = {n["text"].split(" ")[0]: n["commits"] for n in rep["notes"]}
    assert len(notes["CSV"]) == 1 and len(notes["Empty"]) == 1
    chores = [c for c in rep["commits"] if c["chore"]]
    assert {c["subject"] for c in chores} == {"chore: bump dev dependencies", "Release 0.2.0"}
    assert rep["gh"].startswith("not used")


def test_consistent_release_is_clean(tmp_path):
    clean = tmp_path / "clean"
    git_commit(clean, "Initial commit", {"package.json": '{"version": "0.1.0"}\n'})
    git_tag(clean, "v0.1.0")
    git_commit(clean, "feat: add CSV export (#3)", {"a.py": "x = 1\n"})
    git_commit(clean, "fix: handle empty input in parse_rows", {"b.py": "y = 1\n"})
    git_commit(clean, "feat: retry failed HTTP client requests with backoff", {"c.py": "z = 1\n"})
    git_commit(clean, "Release 0.2.0", {"CHANGELOG.md": CHANGELOG_GOOD, "package.json": '{"version": "0.2.0"}\n'})
    git_tag(clean, "v0.2.0")
    rc, rep = run_json(mod, [str(clean), "--from", "v0.1.0", "--to", "v0.2.0", "--json"])
    assert rc == 0, rep["findings"]
    assert all(len(n["commits"]) == 1 for n in rep["notes"]) and len(rep["notes"]) == 3
    assert rep["versions"] == [{"path": "package.json", "field": "version", "version": "0.2.0"}]


def test_custom_chore_pattern_and_notes_file(repo, tmp_path):
    notes = tmp_path / "notes.md"
    notes.write_text("- CSV export for reports (#3)\n", encoding="utf-8")
    rc, rep = run_json(mod, [str(repo), "--from", "v0.1.0", "--to", "v0.2.0", "--json", "--notes", str(notes),
                             "--chore-pattern", "^(fix|feat: retry|chore|Release)"])
    assert not any(f["rule"] in {"REL-COMMIT-UNNOTED", "REL-NOTE-UNMATCHED"} for f in rep["findings"])
    assert not any(f["rule"] == "REL-LINK" and "reference definition" in f["detail"] for f in rep["findings"])


def test_version_override_before_the_tag_exists(repo):
    rc, rep = run_json(mod, [str(repo), "--from", "v0.1.0", "--to", "HEAD", "--version", "0.2.0", "--json"])
    assert rep["version"] == "0.2.0"
    assert ("REL-VERSION", "pyproject.toml") in {(f["rule"], f["location"]) for f in rep["findings"]}
    assert not any(f["rule"] == "REL-SECTION" for f in rep["findings"])


def test_missing_section_and_text_output(repo):
    rc, out, _ = run_main(mod, [str(repo), "--from", "v0.1.0", "--to", "HEAD~1", "--changelog", "NOPE.md"])
    assert rc == 1 and "REL-SECTION" in out and "NO NOTE" in out


def test_bad_input(repo, tmp_path):
    assert run_main(mod, [str(repo), "--from", "v9.9.9", "--to", "v0.2.0"])[0] == 2
    assert run_main(mod, [str(repo), "--from", "--upload-pack=x", "--to", "v0.2.0"])[0] == 2
    assert run_main(mod, [str(repo), "--from", "v0.1.0", "--to", "v0.2.0", "--chore-pattern", "("])[0] == 2
    assert run_main(mod, [str(repo), "--from", "v0.1.0", "--to", "v0.2.0", "--notes", str(tmp_path / "x")])[0] == 2
    assert run_main(mod, [str(tmp_path), "--from", "a", "--to", "b"])[0] == 2


def test_sha_references_and_unbracketed_heading_without_link(tmp_path):
    r = tmp_path / "r"
    git_commit(r, "start", {"a.txt": "a\n"})
    git_tag(r, "v1.0.0")
    sha = git_commit(r, "Rework the scheduler internals", {"b.txt": "b\n"})
    git_commit(r, "Release", {"CHANGELOG.md": f"## 1.1.0\n\n- Scheduler rework ({sha[:9]}).\n"})
    git_tag(r, "v1.1.0")
    rc, rep = run_json(mod, [str(r), "--from", "v1.0.0", "--to", "v1.1.0", "--json"])
    assert rep["notes"][0]["commits"] == [sha[:12]]
    assert [f["rule"] for f in rep["findings"]] == ["REL-LINK"]
    assert "no compare or release link" in rep["findings"][0]["detail"]
