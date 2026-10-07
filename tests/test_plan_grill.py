"""Tests for plan_grill.py with synthetic Markdown plans written inside each test."""

from __future__ import annotations

import json
import re

from conftest import ROOT, load_script, run_json, run_main

mod = load_script("plan-grill", "plan_grill.py")
SKILL = ROOT / "plugins" / "repo-engineering" / "skills" / "plan-grill" / "SKILL.md"


def skill_example() -> str:
    """The example plan in SKILL.md's Inputs section, so the documented example is known to pass."""
    text = SKILL.read_text(encoding="utf-8")
    return re.search(r"```markdown\n(# Search cache.*?)```", text, re.S).group(1)


def write(tmp_path, text, name="plan.md"):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return str(p)


def rules(rep):
    return sorted((g["section"], g["rule"]) for g in rep["gaps"])


def test_documented_example_passes(tmp_path):
    rc, rep = run_json(mod, [write(tmp_path, skill_example()), "--json"])
    assert rep["gaps"] == [] and rc == 0
    assert rep["ready"] == 7 and rep["required"] == 7


def test_missing_sections_reported(tmp_path):
    plan = (
        "# Plan\n## Scope\n"
        + "word " * 30
        + "\n## Tests\nUnit tests for the parser and an integration test. "
        + "x " * 20
    )
    rc, rep = run_json(mod, [write(tmp_path, plan), "--json"])
    assert rc == 1
    missing = sorted(g["section"] for g in rep["gaps"] if g["rule"] == "missing-section")
    assert missing == ["data", "failure-modes", "interfaces", "open-questions", "rollout"]
    assert rep["sections"]["scope"]["status"] == "ok" and rep["sections"]["tests"]["status"] == "ok"


def test_placeholders_thin_sections_and_section_rules(tmp_path):
    plan = (
        "# Plan\n## Goals\nShip it.\n## API\nTBD\n## Storage\nN/A\n"
        "## Risks\nThings may break in various ways that we will handle somehow when they come up later on in prod.\n"
        "## Deployment\nDeploy on Tuesday to all regions at once after the build passes and the team agrees on it.\n"
        "## Testing\nWe will check that it works before shipping it to production with care and attention to detail.\n"
        "## Open questions\n- None\n"
    )
    rc, rep = run_json(mod, [write(tmp_path, plan), "--json", "--min-words", "5"])
    got = rules(rep)
    assert ("scope", "thin-section") in got
    assert ("interfaces", "placeholder") in got and ("data", "placeholder") in got
    assert ("failure-modes", "no-failure-list") in got
    assert ("rollout", "no-rollback") in got
    assert ("tests", "no-test-kind") in got
    assert not any(s == "open-questions" for s, _ in got)
    placeholder = next(g for g in rep["gaps"] if g["rule"] == "placeholder" and g["section"] == "interfaces")
    assert placeholder["line"] == 5


def test_unanswered_questions_with_lines(tmp_path):
    base = skill_example()
    plan = base.replace(
        "- Is 60 seconds acceptable to product? owner: @octocat-p",
        "- Is 60 seconds acceptable to product?\n"
        "- Do we need a cache warmer? -> no, decided in review\n"
        "- [ ] Which Redis?",
    )
    plan += "\nWhat about multi-region?\n\n```text\nwhy is this ignored?\n```\n"
    rc, rep = run_json(mod, [write(tmp_path, plan), "--json"])
    unanswered = [(g["section"], g["line"]) for g in rep["gaps"] if g["rule"] == "unanswered-question"]
    lines = plan.splitlines()
    q1 = lines.index("- Is 60 seconds acceptable to product?") + 1
    q3 = lines.index("- [ ] Which Redis?") + 1
    q4 = lines.index("What about multi-region?") + 1
    assert unanswered == [("open-questions", q1), ("open-questions", q3), ("open-questions", q4)]
    assert rc == 1


def test_sections_subset_and_min_words(tmp_path):
    plan = "# Plan\n## Scope\nSmall fix to the date parser for leap years only.\n"
    rc, rep = run_json(mod, [write(tmp_path, plan), "--json", "--sections", "scope", "--min-words", "5"])
    assert rc == 0 and rep["required"] == 1 and rep["gaps"] == []
    rc, rep = run_json(mod, [write(tmp_path, plan), "--json", "--sections", "scope"])
    assert rc == 1 and rules(rep) == [("scope", "thin-section")]


def test_markdown_and_out_file(tmp_path):
    out = tmp_path / "gaps.md"
    rc, stdout, _ = run_main(mod, [write(tmp_path, "# Plan\n## Scope\nTODO\n"), "--markdown", "--out", str(out)])
    md = out.read_text(encoding="utf-8")
    assert rc == 1 and stdout == ""
    assert md.startswith("## Plan grill:") and "| 3 | scope | placeholder | TODO |" in md
    rc, text, _ = run_main(mod, [write(tmp_path, "# Plan\n## Scope\nTODO\n")])
    assert "0 of 7 sections ready" in text


def test_bad_input_exits_2(tmp_path):
    assert run_main(mod, [str(tmp_path / "missing.md")])[0] == 2
    assert run_main(mod, [write(tmp_path, "  \n", "empty.md")])[0] == 2
    good = write(tmp_path, skill_example())
    rc, _, err = run_main(mod, [good, "--sections", "scope,budget"])
    assert rc == 2 and "budget" in err
    assert run_main(mod, [good, "--min-words", "-1"])[0] == 2


def test_deterministic_json(tmp_path):
    p = write(tmp_path, "# Plan\n## Rollout\nShip it?\n")
    a = run_main(mod, [p, "--json"])
    b = run_main(mod, [p, "--json"])
    assert a == b and json.loads(a[1])["gaps"][0]["section"] == "scope"
