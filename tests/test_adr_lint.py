from conftest import FIXTURES, load_script, run_json, run_main

mod = load_script("adr-miner", "adr_lint.py")
ADR = FIXTURES / "adr" / "docs_adr"


def test_planted_problems_are_found():
    rc, rep = run_json(mod, [str(ADR), "--json"])
    assert rc == 1
    got = {(f["rule"], f["file"]) for f in rep["findings"]}
    assert got == {
        ("ADR-GAP", ""),
        ("ADR-DUP", "0007-cache-layer.md"),
        ("ADR-STATUS", "0005-adopt-httpx.md"),
        ("ADR-STATUS", "0007-cache-layer.md"),
        ("ADR-SUPERSEDED", "0006-drop-celery.md"),
        ("ADR-LINK", "0007-cache-layer.md"),
        ("ADR-BACKLINK", "0004-use-sqlite-for-tests.md"),
        ("ADR-NAME", "notes.md"),
    }
    assert rep["errors"] == 6 and rep["warnings"] == 2
    gap = next(f for f in rep["findings"] if f["rule"] == "ADR-GAP")
    assert "0003" in gap["detail"]


def test_statuses_in_every_supported_form():
    rc, rep = run_json(mod, [str(ADR), "--json"])
    assert rep["statuses"]["0001-record-architecture-decisions.md"] == "accepted"
    assert rep["statuses"]["0004-use-sqlite-for-tests.md"] == "Accepted"
    assert rep["statuses"]["0002-use-postgresql.md"].startswith("superseded by")


def test_clean_folder_passes_and_strict_counts_warnings(tmp_path):
    (tmp_path / "0001-first.md").write_text("---\nstatus: accepted\n---\n# 1. First\n", encoding="utf-8")
    (tmp_path / "0002-second.md").write_text("# 2. Second\n\n* Status: superseded by [ADR-0003](0003-third.md)\n",
                                             encoding="utf-8")
    (tmp_path / "0003-third.md").write_text("# 3. Third\n\n- Status: accepted\n\nSupersedes ADR-0002.\n",
                                            encoding="utf-8")
    rc, rep = run_json(mod, [str(tmp_path), "--json"])
    assert rc == 0 and rep["findings"] == []
    (tmp_path / "scratch.md").write_text("# not an adr\n", encoding="utf-8")
    assert run_main(mod, [str(tmp_path)])[0] == 0
    assert run_main(mod, [str(tmp_path), "--strict"])[0] == 1


def test_text_output_and_bad_input(tmp_path):
    rc, out, _ = run_main(mod, [str(ADR)])
    assert rc == 1 and "ADR-GAP" in out and "6 error(s), 2 warning(s)" in out
    assert run_main(mod, [str(tmp_path / "missing")])[0] == 2


def test_missing_title_and_numbering_starts_where_the_folder_does(tmp_path):
    (tmp_path / "0010-first.md").write_text("Status: accepted\n\nNo heading here.\n", encoding="utf-8")
    (tmp_path / "0011-second.md").write_text("# 11. Second\n\n## Status\n\nDeprecated\n", encoding="utf-8")
    rc, rep = run_json(mod, [str(tmp_path), "--json"])
    assert [(f["rule"], f["file"]) for f in rep["findings"]] == [("ADR-TITLE", "0010-first.md")]
    assert rep["statuses"]["0011-second.md"] == "Deprecated"


def test_a_run_of_missing_numbers_is_one_gap_finding(tmp_path):
    for n in (1, 2, 9, 12):
        (tmp_path / f"{n:04d}-adr.md").write_text(f"# {n}. ADR\n\nStatus: accepted\n", encoding="utf-8")
    rc, rep = run_json(mod, [str(tmp_path), "--json"])
    gaps = [f["detail"] for f in rep["findings"] if f["rule"] == "ADR-GAP"]
    assert rc == 1 and gaps == ["no ADRs numbered 0003 to 0008 between 0001 and 0012",
                                "no ADRs numbered 0010 to 0011 between 0001 and 0012"]


def test_empty_or_wrong_folder_warns_and_strict_fails(tmp_path):
    (tmp_path / "notes.md").write_text("# notes\n", encoding="utf-8")
    rc, rep = run_json(mod, [str(tmp_path), "--json"])
    rules = {f["rule"] for f in rep["findings"]}
    assert rc == 0 and rules == {"ADR-EMPTY", "ADR-NAME"} and rep["adrs"] == 0
    assert run_main(mod, [str(tmp_path), "--strict"])[0] == 1


def test_upper_case_extension_and_bold_status(tmp_path):
    (tmp_path / "0001-first.MD").write_text("# 1. First\n\n**Status:** Accepted (2026-01-02)\n", encoding="utf-8")
    rc, rep = run_json(mod, [str(tmp_path), "--json"])
    assert rc == 0 and rep["adrs"] == 1 and rep["findings"] == []


def test_superseded_without_a_replacement_and_non_utf8_text(tmp_path):
    (tmp_path / "0001-old.md").write_bytes(b"# 1. Old \xff\n\nStatus: superseded\n")
    (tmp_path / "0002-new.md").write_text("# 2. New\n\nStatus: accepted\n", encoding="utf-8")
    rc, rep = run_json(mod, [str(tmp_path), "--json"])
    assert rc == 1 and [f["rule"] for f in rep["findings"]] == ["ADR-SUPERSEDED"]
