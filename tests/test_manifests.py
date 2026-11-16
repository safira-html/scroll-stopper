import json
import re

from conftest import ROOT, git_tracked_text_files


def _load(rel: str) -> dict:
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def test_plugin_manifest():
    m = _load(".claude-plugin/plugin.json")
    assert m["name"] == "scroll-stopper"
    assert re.fullmatch(r"\d+\.\d+\.\d+", m["version"])
    assert m["license"] == "AGPL-3.0"


def test_marketplace_lists_plugin_from_repo_root():
    mk = _load(".claude-plugin/marketplace.json")
    p = [x for x in mk["plugins"] if x["name"] == "scroll-stopper"][0]
    assert p["source"] == "./"


def test_versions_match():
    # a versão do plugin e a da entrada no marketplace andam juntas
    m = _load(".claude-plugin/plugin.json")
    mk = _load(".claude-plugin/marketplace.json")
    p = [x for x in mk["plugins"] if x["name"] == "scroll-stopper"][0]
    assert p.get("version", m["version"]) == m["version"]


# nenhuma marca da empresa nem link para os repositórios de origem
FORBIDDEN = re.compile(r"allevo|\blevo\b|redealumni|motion-ads-studio|editor-videos|qeevo")


def test_no_forbidden_strings_in_repo():
    files = git_tracked_text_files()
    assert files
    for path in files:
        text = path.read_text(encoding="utf-8", errors="ignore").lower()
        assert not FORBIDDEN.search(text), path
