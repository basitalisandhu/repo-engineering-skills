import json

from conftest import FIXTURES, load_script, run_json, run_main

mod = load_script("cited-codebase-audit", "audit_validate.py")
REPO = FIXTURES / "cited_audit" / "repo"
REPORT = FIXTURES / "cited_audit" / "report.json"


def test_good_citations_accepted_and_planted_bad_ones_rejected():
    rc, res = run_json(mod, [str(REPORT), str(REPO), "--json"])
    assert rc == 1
    assert [f["id"] for f in res["accepted"]] == ["F1", "F2"]
    codes = {r["id"]: r["errors"][0]["code"] for r in res["rejected"]}
    assert codes == {"F3": "CIT-SNIPPET", "F4": "CIT-FILE", "F5": "CIT-LINE", "F6": "CIT-PATH", "F7": "CIT-NONE"}
    assert res["stats"] == {"total": 7, "accepted": 2, "rejected": 5, "acceptance_rate": 28.6}
    assert res["warnings"] == []


def test_whitespace_is_normalised_and_multiline_snippets_match(tmp_path):
    report = {"findings": [{"id": "A", "category": "dead-code", "severity": "low", "title": "t",
                            "citations": [{"path": "shop/orders.py", "line": "16-18",
                                           "snippet": "def legacy_export(orders):\n    # Not called anywhere."}]}],
              "considered_and_rejected": [], "not_examined": []}
    p = tmp_path / "r.json"
    p.write_text(json.dumps(report), encoding="utf-8")
    rc, res = run_json(mod, [str(p), str(REPO), "--json"])
    assert rc == 0 and res["stats"]["accepted"] == 1


def test_out_file_keeps_only_accepted_and_min_accept(tmp_path):
    out = tmp_path / "clean.json"
    rc, text, _ = run_main(mod, [str(REPORT), str(REPO), "--out", str(out), "--min-accept", "25"])
    assert rc == 0 and "2 of 7 findings accepted" in text
    cleaned = json.loads(out.read_text(encoding="utf-8"))
    assert [f["id"] for f in cleaned["findings"]] == ["F1", "F2"]
    assert len(cleaned["rejected_findings"]) == 5
    rc, _, _ = run_main(mod, [str(REPORT), str(REPO), "--min-accept", "50"])
    assert rc == 1


def test_warnings_for_unknown_category_and_missing_sections(tmp_path):
    p = tmp_path / "r.json"
    p.write_text(json.dumps({"findings": [{"id": "X", "category": "vibes", "severity": "huge",
                                           "location": "requirements.txt:2", "snippet": "flask==3.0.3"}]}),
                 encoding="utf-8")
    rc, res = run_json(mod, [str(p), str(REPO), "--json"])
    assert rc == 0
    assert len(res["warnings"]) == 4


def test_bad_input(tmp_path):
    p = tmp_path / "r.json"
    p.write_text("not json", encoding="utf-8")
    assert run_main(mod, [str(p), str(REPO)])[0] == 2
    p.write_text("[]", encoding="utf-8")
    assert run_main(mod, [str(p), str(REPO)])[0] == 2
    assert run_main(mod, [str(REPORT), str(tmp_path / "nope")])[0] == 2
    rc, out, _ = run_main(mod, ["--help"])
    assert rc == 0 and "--min-accept" in out


def test_report_that_is_not_utf8_exits_2(tmp_path):
    p = tmp_path / "r.json"
    p.write_bytes(b"\xff\xfe{")
    rc, _, err = run_main(mod, [str(p), str(REPO)])
    assert rc == 2 and "cannot read report" in err


def test_nul_byte_in_path_is_rejected_not_crashed(tmp_path):
    p = tmp_path / "r.json"
    p.write_text(json.dumps({"findings": [{"id": "N", "location": "shop/or\u0000ders.py:1", "snippet": "x"}]}),
                 encoding="utf-8")
    rc, res = run_json(mod, [str(p), str(REPO), "--json"])
    assert rc == 1 and res["rejected"][0]["errors"][0]["code"] == "CIT-PATH"


def test_min_accept_outside_0_to_100_and_unwritable_out_exit_2(tmp_path):
    assert run_main(mod, [str(REPORT), str(REPO), "--min-accept", "150"])[0] == 2
    assert run_main(mod, [str(REPORT), str(REPO), "--min-accept", "-1"])[0] == 2
    rc, _, err = run_main(mod, [str(REPORT), str(REPO), "--out", str(tmp_path / "no" / "x.json")])
    assert rc == 2 and "cannot write" in err


def test_line_that_is_not_a_number_and_absolute_path(tmp_path):
    p = tmp_path / "r.json"
    p.write_text(json.dumps({"findings": [
        {"id": "L", "citations": [{"path": "shop/orders.py", "line": "three", "snippet": "x"}]},
        {"id": "A", "citations": [{"path": str(REPO / "shop" / "orders.py"), "line": 1, "snippet": "x"}]},
        {"id": "S", "citations": ["shop/orders.py:1"]},
    ]}), encoding="utf-8")
    rc, res = run_json(mod, [str(p), str(REPO), "--json"])
    codes = {r["id"]: r["errors"][0]["code"] for r in res["rejected"]}
    assert rc == 1 and codes == {"L": "CIT-LINE", "A": "CIT-PATH", "S": "CIT-SNIPPET"}
