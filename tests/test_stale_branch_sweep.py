"""Tests for stale_branch_sweep.py with synthetic gh and git exports built inside each test (no fixtures, no git)."""

from __future__ import annotations

import json

from conftest import load_script, run_json, run_main

mod = load_script("stale-branch-sweep", "stale_branch_sweep.py")
NOW = "2026-10-05T00:00:00Z"

BRANCHES = [
    {"name": "main", "commit": {"sha": "a" * 40}, "protected": True},
    {"name": "release/1.x", "commit": {"sha": "b" * 40}, "protected": True},
    {"name": "feature/login", "commit": {"sha": "c" * 40}, "protected": False},
    {"name": "feature/squashed", "commit": {"sha": "d" * 40}, "protected": False},
    {"name": "spike/cache", "commit": {"sha": "e" * 40}, "protected": False},
    {"name": "wip/search", "commit": {"sha": "f" * 40}, "protected": False},
    {"name": "fix/recent", "commit": {"sha": "1" * 40}, "protected": False},
    {"name": "ghost", "commit": {"sha": "2" * 40}, "protected": False},
]
REFS = [
    ("origin/HEAD", "a" * 40, "2026-10-01T00:00:00+00:00", "Ada Example"),
    ("origin/main", "a" * 40, "2026-10-01T00:00:00+00:00", "Ada Example"),
    ("origin/release/1.x", "b" * 40, "2025-01-01T00:00:00+00:00", "Ada Example"),
    ("origin/feature/login", "c" * 40, "2026-03-02T10:00:00+00:00", "Ben Example"),
    ("origin/feature/squashed", "d" * 40, "2026-09-20T00:00:00+00:00", "Cy Example"),
    ("origin/spike/cache", "e" * 40, "2026-01-10T00:00:00+00:00", "Ben Example"),
    ("origin/wip/search", "f" * 40, "2025-12-01T00:00:00+00:00", "Dee Example"),
    ("origin/fix/recent", "1" * 40, "2026-10-03T00:00:00+00:00", "Dee Example"),
]
PRS = [
    {"number": 12, "headRefName": "feature/squashed", "headRefOid": "d" * 40, "state": "MERGED", "url": "u12"},
    {"number": 15, "headRefName": "wip/search", "headRefOid": "f" * 40, "state": "OPEN", "url": "u15"},
    {"number": 9, "headRefName": "spike/cache", "headRefOid": "0" * 40, "state": "MERGED", "url": "u9"},
]


def write_inputs(tmp_path, branches=BRANCHES, refs=REFS, merged=("origin/main", "origin/feature/login"), prs=PRS):
    b = tmp_path / "branches.json"
    b.write_text(json.dumps(branches), encoding="utf-8")
    r = tmp_path / "refs.txt"
    r.write_text("".join("\t".join(row) + "\n" for row in refs), encoding="utf-8")
    m = tmp_path / "merged.txt"
    m.write_text("".join(f"{name}\tx\t2026-01-01T00:00:00+00:00\tAda Example\n" for name in merged), encoding="utf-8")
    p = tmp_path / "prs.json"
    p.write_text(json.dumps(prs), encoding="utf-8")
    return ["--branches", str(b), "--refs", str(r), "--merged", str(m), "--prs", str(p), "--now", NOW]


def statuses(rep):
    return {r["branch"]: r["status"] for r in rep["branches"]}


def test_every_branch_gets_one_status(tmp_path):
    rc, rep = run_json(mod, [*write_inputs(tmp_path), "--json"])
    assert rc == 1
    assert statuses(rep) == {
        "main": "base",
        "release/1.x": "protected",
        "wip/search": "open-pr",
        "feature/login": "merged",
        "feature/squashed": "merged",
        "spike/cache": "stale",
        "ghost": "no-ref",
        "fix/recent": "active",
    }
    login = next(r for r in rep["branches"] if r["branch"] == "feature/login")
    assert login["owner"] == "Ben Example" and login["last_commit"] == "2026-03-02T10:00:00Z"
    wip = next(r for r in rep["branches"] if r["branch"] == "wip/search")
    assert wip["prs"] == [{"number": 15, "url": "u15"}]


def test_commands_only_for_merged_and_commented_for_stale(tmp_path):
    rc, rep = run_json(mod, [*write_inputs(tmp_path), "--json"])
    assert rep["delete_commands"] == [
        "git push origin --delete feature/login",
        "git push origin --delete feature/squashed",
    ]
    assert rep["stale_commands_for_review"] == ["# git push origin --delete spike/cache"]


def test_squash_merge_needs_matching_head_commit(tmp_path):
    prs = [{"number": 12, "headRefName": "feature/squashed", "headRefOid": "9" * 40, "state": "MERGED", "url": "u"}]
    rc, rep = run_json(mod, [*write_inputs(tmp_path, prs=prs), "--json"])
    assert statuses(rep)["feature/squashed"] == "active"


def test_days_threshold_remote_and_quoting(tmp_path):
    branches = [{"name": "odd name;rm", "commit": {"sha": "3" * 40}, "protected": False}]
    refs = [("upstream/odd name;rm", "3" * 40, "2026-09-01T00:00:00+00:00", "Eve Example")]
    args = write_inputs(tmp_path, branches=branches, refs=refs, merged=(), prs=[])
    rc, rep = run_json(mod, [*args, "--remote", "upstream", "--days", "10", "--json"])
    assert statuses(rep) == {"odd name;rm": "stale"}
    assert rep["stale_commands_for_review"] == ["# git push upstream --delete 'odd name;rm'"]
    rc, rep = run_json(mod, [*args, "--remote", "upstream", "--days", "60", "--json"])
    assert rc == 0 and statuses(rep) == {"odd name;rm": "active"}


def test_markdown_out_file_and_text(tmp_path):
    args = write_inputs(tmp_path)
    out = tmp_path / "sweep.md"
    rc, stdout, _ = run_main(mod, [*args, "--markdown", "--out", str(out)])
    md = out.read_text(encoding="utf-8")
    assert rc == 1 and stdout == ""
    assert "| merged | `feature/login` | Ben Example |" in md and "```bash" in md
    assert "This script never runs them." in md
    rc, text, _ = run_main(mod, args)
    assert "[stale] spike/cache (Ben Example)" in text and "git push origin --delete feature/login" in text


def test_plain_branch_names_and_slurped_pages(tmp_path):
    args = write_inputs(tmp_path)
    (tmp_path / "merged.txt").write_text("  origin/HEAD -> origin/main\n  origin/feature/login\n", encoding="utf-8")
    (tmp_path / "branches.json").write_text(json.dumps([BRANCHES[:4], BRANCHES[4:]]), encoding="utf-8")
    rc, rep = run_json(mod, [*args, "--json"])
    assert statuses(rep)["feature/login"] == "merged" and len(rep["branches"]) == 8


def test_bad_input_exits_2(tmp_path):
    args = write_inputs(tmp_path)
    (tmp_path / "bad.txt").write_text("origin/x only-two-fields\n", encoding="utf-8")
    bad_refs = [*args]
    bad_refs[bad_refs.index("--refs") + 1] = str(tmp_path / "bad.txt")
    assert run_main(mod, bad_refs)[0] == 2
    missing = [*args]
    missing[missing.index("--branches") + 1] = str(tmp_path / "nope.json")
    rc, _, err = run_main(mod, missing)
    assert rc == 2 and "not found" in err
    (tmp_path / "branches.json").write_text("{}", encoding="utf-8")
    assert run_main(mod, args)[0] == 2
    assert run_main(mod, [*write_inputs(tmp_path), "--now", "later"])[0] == 2
    assert run_main(mod, ["--refs", "x"])[0] == 2


def test_clean_repository_exits_0(tmp_path):
    branches = [{"name": "main", "commit": {"sha": "a" * 40}, "protected": True}]
    rc, rep = run_json(mod, [*write_inputs(tmp_path, branches=branches, prs=[]), "--json"])
    assert rc == 0 and rep["delete_commands"] == [] and rep["counts"]["base"] == 1
