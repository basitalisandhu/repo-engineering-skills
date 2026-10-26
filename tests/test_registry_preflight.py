"""Tests for registry_preflight.py on the synthetic MCP server repositories in tests/fixtures/registry_preflight."""

from __future__ import annotations

import json
import shutil

from conftest import FIXTURES, load_script, run_json, run_main

mod = load_script("mcp-registry-publish-preflight", "registry_preflight.py")
FIX = FIXTURES / "registry_preflight"
PROOFS = FIX / "proofs"


def rules(rep, severity=None):
    return sorted(f["rule"] for f in rep["findings"] if severity is None or f["severity"] == severity)


def copy(tmp_path, name):
    dest = tmp_path / name
    shutil.copytree(FIX / name, dest)
    return dest


def edit_server(repo, **changes):
    path = repo / "server.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data.update(changes)
    path.write_text(json.dumps(data), encoding="utf-8")
    return data


def test_good_repository_is_clean():
    rc, rep = run_json(mod, [str(FIX / "good"), "--json", "--fail-on", "warn"])
    assert rc == 0 and rep["findings"] == []
    assert rep["name"] == "io.github.ada-example/weather-mcp"
    assert rep["files_read"] == ["server.json", "package.json", "pyproject.toml", "README.md", "Dockerfile"]


def test_pyproject_readme_without_marker_and_version_drift():
    rc, rep = run_json(mod, [str(FIX / "pypi_wrong_readme"), "--json"])
    assert rc == 1
    assert rules(rep, "error") == ["marker-in-wrong-readme", "marker-missing"]
    assert rules(rep, "warn") == ["version-mismatch"]
    assert rep["files_read"] == ["server.json", "pyproject.toml", "docs/PYPI.md", "README.md"]
    wrong = next(f for f in rep["findings"] if f["rule"] == "marker-in-wrong-readme")
    assert wrong["where"] == "README.md:5" and "docs/PYPI.md" in wrong["detail"]


def test_marker_glued_to_a_full_stop_and_the_accepted_forms(tmp_path):
    rc, rep = run_json(mod, [str(FIX / "pypi_glued"), "--json"])
    assert rc == 1 and rules(rep) == ["marker-glued"]
    assert rep["findings"][0]["where"] == "README.md:3" and "'.'" in rep["findings"][0]["detail"]
    repo = copy(tmp_path, "pypi_glued")
    name = "io.github.ada-example/todo-mcp"
    for ok in (f"<!-- mcp-name: {name}-->", f"mcp-name: {name}", f"mcp-name: {name} more", f"mcp-name: {name}<br>"):
        (repo / "README.md").write_text(f"# x\n\n{ok}", encoding="utf-8")
        rc, rep = run_json(mod, [str(repo), "--json"])
        assert rc == 0, (ok, rep["findings"])
    (repo / "README.md").write_text(f"mcp-name: {name}-pro\n", encoding="utf-8")
    assert rules(run_json(mod, [str(repo), "--json"])[1]) == ["marker-glued"]


def test_marker_case_and_other_name(tmp_path):
    repo = copy(tmp_path, "pypi_glued")
    (repo / "README.md").write_text("mcp-name: io.github.Ada-Example/todo-mcp\n", encoding="utf-8")
    rc, rep = run_json(mod, [str(repo), "--json"])
    assert rules(rep) == ["marker-case"] and "issue #1707" in rep["findings"][0]["source"]
    (repo / "README.md").write_text("<!-- mcp-name: io.github.ada-example/other -->\n", encoding="utf-8")
    assert rules(run_json(mod, [str(repo), "--json"])[1]) == ["marker-other-name"]


def test_schema_and_registry_rules():
    rc, rep = run_json(mod, [str(FIX / "schema_bad"), "--json"])
    assert rc == 1
    assert rules(rep, "error") == sorted([
        "description-length", "version-range", "meta-too-large", "remote-url-https", "transport-type",
        "version-latest", "registry-base-url", "npm-mcpname-mismatch", "oci-host", "sha256-format", "mcpb-no-mcp",
    ])
    assert rules(rep, "warn") == ["meta-dropped", "repository-not-https"]
    assert rules(rep, "info") == ["not-checked"]


def test_version_range_forms_from_the_versioning_doc():
    prohibited = ["^1.2.3", "~1.2.3", ">=1.2.3", "<=1.2.3", ">1.2.3", "<1.2.3", "1.x", "1.2.*", "1 - 2", "1.2 || 1.3"]
    allowed = ["1.0.0", "2.1.3-alpha", "1.0.0-beta.1", "2025.11.25", "2025.06.18", "2025-06-18", "v1.0", "1.2.3-1"]
    assert all(mod.looks_like_range(v) for v in prohibited)
    assert not any(mod.looks_like_range(v) for v in allowed)


def test_package_type_specific_rules(tmp_path):
    repo = copy(tmp_path, "good")
    edit_server(repo, packages=[
        {"registryType": "pypi", "identifier": "weather-mcp", "transport": {"type": "stdio"}},
        {"registryType": "oci", "identifier": "ada-example/weather-mcp", "version": "1.4.0",
         "transport": {"type": "stdio"}},
        {"registryType": "mcpb", "identifier": "https://example.com/weather-mcp.mcpb", "transport": {"type": "stdio"}},
        {"registryType": "maven", "identifier": "com.example:weather", "transport": {"type": "stdio"}},
        {"registryType": "npm", "identifier": "@ada-example/weather-mcp", "version": "1.4.0",
         "fileSha256": "a" * 64, "transport": {"type": "streamable-http"}},
    ])
    rc, rep = run_json(mod, [str(repo), "--json"])
    got = rules(rep)
    for rule in ("package-version-missing", "oci-field", "oci-no-tag", "mcpb-host", "mcpb-sha256", "registry-type",
                 "sha256-not-allowed", "transport-url"):
        assert rule in got, rule
    assert "oci-host" not in got  # a bare image name is Docker Hub


def test_oci_label_and_github_rename():
    rc, rep = run_json(mod, [str(FIX / "oci_label"), "--json"])
    assert rc == 1 and rules(rep) == ["oci-label-mismatch"] and rep["findings"][0]["where"] == "Dockerfile:2"
    rc, rep = run_json(mod, [str(FIX / "renamed_owner"), "--json"])
    assert rc == 0 and rules(rep) == ["repository-owner-differs"]
    assert run_main(mod, [str(FIX / "renamed_owner"), "--fail-on", "warn"])[0] == 1
    rc, rep = run_json(mod, [str(FIX / "renamed_owner"), "--json", "--github-owner", "new-handle"])
    assert rc == 1 and "github-owner" in rules(rep, "error")
    rc, rep = run_json(mod, [str(FIX / "renamed_owner"), "--json", "--github-owner", "Old-Handle"])
    assert rules(rep, "warn") == ["github-owner-case", "repository-owner-differs"]


def test_domain_namespace(tmp_path):
    repo = copy(tmp_path, "renamed_owner")
    edit_server(repo, name="com.example.tools/recipes-mcp", repository={"url": "https://gitlab.com/example/recipes",
                                                                         "source": "gitlab"})
    rc, rep = run_json(mod, [str(repo), "--json"])
    assert rc == 0 and rules(rep, "info") == ["not-checked"]
    assert run_json(mod, [str(repo), "--json", "--domain", "example.com"])[1]["findings"] == []
    rc, rep = run_json(mod, [str(repo), "--json", "--domain", "example.org"])
    assert rc == 1 and rules(rep) == ["namespace-domain"]


def test_npm_and_cargo_and_nuget_ownership(tmp_path):
    repo = copy(tmp_path, "good")
    edit_server(repo, packages=[{"registryType": "cargo", "identifier": "weather-mcp", "version": "1.4.0",
                                 "transport": {"type": "stdio"}}])
    (repo / "Cargo.toml").write_text('[package]\nname = "weather-mcp"\nversion = "1.4.0"\nreadme = "README.md"\n',
                                     encoding="utf-8")
    rc, rep = run_json(mod, [str(repo), "--json"])
    assert rules(rep) == ["cargo-marker-hidden"]  # the fixture hides the marker in an HTML comment
    edit_server(repo, packages=[{"registryType": "nuget", "identifier": "Example.Weather", "version": "1.4.0",
                                 "transport": {"type": "stdio"}}])
    (repo / "src").mkdir()
    (repo / "src" / "Weather.csproj").write_text(
        "<Project><PropertyGroup><PackageReadmeFile>NUGET.md</PackageReadmeFile><Version>1.3.9</Version>"
        "</PropertyGroup></Project>", encoding="utf-8")
    (repo / "src" / "NUGET.md").write_text("<!-- mcp-name: io.github.ada-example/weather-mcp -->\n", encoding="utf-8")
    rc, rep = run_json(mod, [str(repo), "--json"])
    assert rules(rep) == ["version-mismatch"] and "src/Weather.csproj" in rep["files_read"]
    (repo / "package.json").write_text('{"name": "@ada-example/weather-mcp", "version": "1.4.0"}', encoding="utf-8")
    edit_server(repo, packages=[{"registryType": "npm", "identifier": "@ada-example/weather-mcp", "version": "1.4.0",
                                 "transport": {"type": "stdio"}}])
    assert rules(run_json(mod, [str(repo), "--json"])[1]) == ["npm-mcpname-missing"]


def test_proof_records():
    ok = run_json(mod, ["--proof-record", str(PROOFS / "dns_ok.txt"), "--domain", "example.com", "--json"])
    assert ok[0] == 0 and ok[1]["findings"] == [] and ok[1]["server_json"] is None
    assert run_json(mod, ["--proof-record", str(PROOFS / "http_ok.txt"), "--proof-kind", "http", "--json"])[0] == 0
    cases = {
        "dns_redacted.txt": ["proof-format"],
        "dns_hex.txt": ["proof-key-size"],
        "dns_selector.txt": ["proof-selector"],
    }
    for name, expected in cases.items():
        rc, rep = run_json(mod, ["--proof-record", str(PROOFS / name), "--json"])
        assert rc == 1 and rules(rep) == expected, name
    rc, rep = run_json(mod, ["--proof-record", str(PROOFS / "http_html.txt"), "--proof-kind", "http", "--json"])
    assert "proof-html" in rules(rep)
    rc, rep = run_json(mod, ["--proof-record", "v=MCPv1; k=rsa; p=AAAA", "--json"])
    assert rules(rep) == ["proof-algorithm"]
    rc, rep = run_json(mod, ["--proof-record", "v=MCPv1; k=ecdsap384; p=" + "A" * 64, "--json"])
    assert rules(rep) == ["proof-key-size"]


def test_proof_comparison_size_and_several_records(tmp_path):
    published = (PROOFS / "dns_ok.txt").read_text(encoding="utf-8").split('"')[1]
    rc, rep = run_json(mod, ["--proof-record", str(PROOFS / "dns_ok.txt"), "--expected-record", published, "--json"])
    assert rc == 0
    other = "v=MCPv1; k=ed25519; p=" + "B" * 43 + "="
    rc, rep = run_json(mod, ["--proof-record", str(PROOFS / "dns_ok.txt"), "--expected-record", other, "--json"])
    assert rc == 1 and rules(rep) == ["proof-key-mismatch"]
    two = tmp_path / "two.txt"
    two.write_text(f'"{published}"\n"{other}"\n', encoding="utf-8")
    assert "proof-several" in rules(run_json(mod, ["--proof-record", str(two), "--json"])[1])
    big = tmp_path / "big.txt"
    big.write_text(published + "\n" + " " * 5000, encoding="utf-8")
    rc, rep = run_json(mod, ["--proof-record", str(big), "--proof-kind", "http", "--json"])
    assert rules(rep) == ["proof-too-large"]


def test_bad_input_exits_2(tmp_path):
    bad = tmp_path / "server.json"
    for content in (b"\xff\xfe{}", b"{", b"[]", b""):
        bad.write_bytes(content)
        rc, out, err = run_main(mod, [str(tmp_path)])
        assert rc == 2 and err.startswith("registry_preflight.py: ") and "Traceback" not in err, content
    assert run_main(mod, [str(tmp_path / "missing")])[0] == 2
    assert run_main(mod, [str(tmp_path / "empty-dir-without-server-json")])[0] == 2
    repo = tmp_path / "r"
    shutil.copytree(FIX / "pypi_glued", repo)
    (repo / "pyproject.toml").write_text("[project\n", encoding="utf-8")
    rc, _, err = run_main(mod, [str(repo)])
    assert rc == 2 and "not valid TOML" in err
    assert run_main(mod, [str(FIX / "good"), "--domain", "localhost"])[0] == 2
    assert run_main(mod, [str(FIX / "good"), "--out", str(tmp_path / "no" / "such" / "dir" / "r.txt")])[0] == 2
    assert run_main(mod, ["--expected-record", "v=MCPv1; k=ed25519; p=AAAA"])[0] == 2
    assert run_main(mod, ["--proof-record", str(PROOFS / "dns_ok.txt"), "--expected-record", "nonsense"])[0] == 2


def test_text_output_and_out_file(tmp_path):
    rc, out, _ = run_main(mod, [str(FIX / "pypi_glued")])
    assert rc == 1
    assert out.startswith("registry preflight: server.json (io.github.ada-example/todo-mcp)")
    assert "marker-glued" in out and "1 error(s), 0 warning(s), 0 not checked" in out
    target = tmp_path / "report.json"
    rc, out, _ = run_main(mod, [str(FIX / "good"), "--json", "--out", str(target)])
    assert rc == 0 and out == "" and json.loads(target.read_text(encoding="utf-8"))["counts"]["error"] == 0
