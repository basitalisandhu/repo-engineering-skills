from conftest import FIXTURES, load_script, run_json, run_main

mod = load_script("readme-who-what-why", "readme_check.py")
BASE = FIXTURES / "readme"


def test_good_readme_scores_full_marks():
    rc, rep = run_json(mod, [str(BASE / "good_README.md"), "--json"])
    assert rc == 0
    assert rep["score"] == rep["max_score"] == 12
    assert all(v["status"] == "first screen" for v in rep["elements"].values())
    assert rep["hype_words"] == [] and rep["todo"] == []


def test_bad_readme_gaps_and_hype():
    rc, rep = run_json(mod, [str(BASE / "bad_README.md"), "--json"])
    assert rc == 1
    status = {k: v["status"] for k, v in rep["elements"].items()}
    assert status == {"what": "first screen", "who": "missing", "why": "missing", "install": "later",
                      "example": "missing", "ask": "missing"}
    assert rep["score"] == 3
    words = {h["word"].lower() for h in rep["hype_words"]}
    assert {"revolutionary", "blazing fast", "next-generation", "seamlessly", "powerful", "robust", "magical"} <= words
    assert any(t.startswith("install: found at line") for t in rep["todo"])


def test_screen_size_and_min_score(tmp_path):
    rc, rep = run_json(mod, [str(BASE / "bad_README.md"), "--json", "--screen-lines", "80"])
    assert rep["elements"]["install"]["status"] == "first screen"
    rc, _, _ = run_main(mod, [str(BASE / "bad_README.md"), "--min-score", "3"])
    assert rc == 0


def test_long_opening_sentence_is_noted(tmp_path):
    p = tmp_path / "README.md"
    p.write_text("# x\n\n" + " ".join(["word"] * 50) + ".\n", encoding="utf-8")
    _, rep = run_json(mod, [str(p), "--json"])
    assert rep["notes"] and "50 words" in rep["notes"][0]


def test_hype_inside_code_is_ignored_and_errors(tmp_path):
    p = tmp_path / "README.md"
    p.write_text("# x\n\nx is a tool.\n\n```bash\necho powerful\n```\n", encoding="utf-8")
    _, rep = run_json(mod, [str(p), "--json"])
    assert rep["hype_words"] == []
    assert run_main(mod, [str(tmp_path / "none.md")])[0] == 2
    rc, out, _ = run_main(mod, ["--help"])
    assert rc == 0 and "--screen-lines" in out


def test_plugin_install_in_a_text_block_counts_as_install(tmp_path):
    p = tmp_path / "README.md"
    p.write_text("# x\n\nx is a plugin for teams who review docs, instead of by hand.\n\n```text\n"
                 "/plugin marketplace add o/x\n/plugin install x@x\n```\n\n## Usage\n\nAsk in issues.\n",
                 encoding="utf-8")
    rc, rep = run_json(mod, [str(p), "--json"])
    assert rep["elements"]["install"]["status"] == "first screen" and rc == 0
