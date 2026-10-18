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


def test_not_utf8_exits_2_and_empty_file_is_noted(tmp_path):
    p = tmp_path / "README.md"
    p.write_bytes(b"\xff\xfe# x\n")
    rc, _, err = run_main(mod, [str(p)])
    assert rc == 2 and "not UTF-8" in err
    p.write_text("", encoding="utf-8")
    rc, rep = run_json(mod, [str(p), "--json"])
    assert rc == 1 and rep["score"] == 0 and rep["notes"] == ["the file is empty"]


def test_front_matter_and_setext_heading_are_not_the_opening_sentence(tmp_path):
    p = tmp_path / "README.md"
    p.write_text("---\ntitle: Tool\nlayout: page\n---\nTool\n====\n\nTool is a linter for YAML files.\n",
                 encoding="utf-8")
    _, rep = run_json(mod, [str(p), "--json"])
    assert rep["elements"]["what"]["line"] == 8
    assert rep["elements"]["what"]["evidence"] == "Tool is a linter for YAML files."
    assert rep["screen"]["first_line"] == 5


def test_hype_in_inline_code_is_ignored_but_prose_hype_counts(tmp_path):
    p = tmp_path / "README.md"
    p.write_text("# x\n\nx is a tool. Pass `--robust` for retries.\n\nIt is a powerful tool.\n", encoding="utf-8")
    _, rep = run_json(mod, [str(p), "--json"])
    assert [(h["line"], h["word"]) for h in rep["hype_words"]] == [(5, "powerful")]


def test_unclosed_code_fence_is_noted_and_its_install_still_counts(tmp_path):
    p = tmp_path / "README.md"
    p.write_text("# x\n\nx is a tool.\n\n```bash\npip install x\n", encoding="utf-8")
    _, rep = run_json(mod, [str(p), "--json"])
    assert any("never closed" in n for n in rep["notes"])
    assert rep["elements"]["install"]["status"] == "first screen"
