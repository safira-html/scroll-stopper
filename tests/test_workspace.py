import json
from pathlib import Path

import pytest

from ss_lib import paths, workspace


@pytest.fixture
def isolated_cache(tmp_path, monkeypatch):
    cache = tmp_path / "cache"
    monkeypatch.setattr(paths, "CACHE", cache)
    return cache


def test_find_workspace_walks_up(tmp_path):
    (tmp_path / ".scroll-stopper").mkdir()
    deep = tmp_path / "a" / "b" / "c"
    deep.mkdir(parents=True)
    assert workspace.find_workspace(deep) == tmp_path / ".scroll-stopper"
    assert workspace.find_workspace(tmp_path / "a") == tmp_path / ".scroll-stopper"


def test_find_workspace_none(tmp_path):
    assert workspace.find_workspace(tmp_path) is None


def test_init_creates_layout(tmp_path):
    ws = workspace.init_workspace(tmp_path)
    assert ws == tmp_path / ".scroll-stopper"
    assert (ws / "marcas").is_dir()
    assert (ws / "kit-de-som" / "music").is_dir()
    assert (ws / "kit-de-som" / "sfx").is_dir()
    assert (ws / "aprendizados.md").is_file()
    assert (ws / "projetos").is_dir()
    assert workspace.kit_dir(ws) == ws / "kit-de-som"


def test_init_is_idempotent(tmp_path):
    ws = workspace.init_workspace(tmp_path)
    (ws / "aprendizados.md").write_text("- keep\n", encoding="utf-8")
    workspace.init_workspace(tmp_path)
    assert (ws / "aprendizados.md").read_text(encoding="utf-8") == "- keep\n"


def test_new_brand_copies_template(tmp_path):
    ws = workspace.init_workspace(tmp_path)
    target = workspace.new_brand_from_template(ws, "acme")
    assert target == workspace.brand_dir(ws, "acme") == ws / "marcas" / "acme"
    assert (target / "BRAND.md").is_file()
    assert (target / "assets" / "logo.svg").is_file()
    data = json.loads((target / "brand.json").read_text(encoding="utf-8"))
    assert data["slug"] == "acme" and data["name"] == "acme"
    assert {"colors", "fonts", "logos", "captions", "endCard", "voice"} <= set(data)
    assert workspace.list_brands(ws) == ["acme"]


def test_new_brand_rejects_existing_and_unsafe(tmp_path):
    ws = workspace.init_workspace(tmp_path)
    workspace.new_brand_from_template(ws, "acme")
    with pytest.raises(FileExistsError):
        workspace.new_brand_from_template(ws, "acme")
    for bad in ("", ".hidden", "a/b", "a\\b"):
        with pytest.raises(ValueError):
            workspace.new_brand_from_template(ws, bad)
        with pytest.raises(ValueError):
            workspace.brand_dir(ws, bad)


def test_list_brands_only_dirs_with_brand_json(tmp_path):
    ws = workspace.init_workspace(tmp_path)
    workspace.new_brand_from_template(ws, "zeta")
    workspace.new_brand_from_template(ws, "alfa")
    (ws / "marcas" / "empty").mkdir()
    assert workspace.list_brands(ws) == ["alfa", "zeta"]


def test_ephemeral_brand_not_written(tmp_path, monkeypatch, isolated_cache):
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    monkeypatch.chdir(cwd)
    target = workspace.new_brand_from_template(None, "temp")
    assert target == isolated_cache / "tmp-brands" / "temp"
    assert (target / "brand.json").is_file()
    assert list(cwd.iterdir()) == []


def test_append_learning_format(tmp_path):
    ws = workspace.init_workspace(tmp_path)
    workspace.append_learning(ws, "gancho curto funciona", "feedback", today="2026-11-12")
    workspace.append_learning(ws, "legenda grande", "teste", today="2026-11-13")
    assert (ws / "aprendizados.md").read_text(encoding="utf-8").endswith(
        "- 2026-11-12 · feedback · gancho curto funciona\n- 2026-11-13 · teste · legenda grande\n")
    assert workspace.read_learnings(ws) == [
        "- 2026-11-12 · feedback · gancho curto funciona",
        "- 2026-11-13 · teste · legenda grande",
    ]


def test_append_learning_default_date_is_local_iso(tmp_path):
    import re
    ws = workspace.init_workspace(tmp_path)
    workspace.append_learning(ws, "x", "s")
    assert re.fullmatch(r"- \d{4}-\d{2}-\d{2} · s · x", workspace.read_learnings(ws)[0])


def test_read_learnings_missing_file(tmp_path):
    assert workspace.read_learnings(tmp_path / ".scroll-stopper") == []


def test_cli_init_brands_learn(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert workspace.main(["init"]) == 0
    assert (tmp_path / ".scroll-stopper" / "marcas").is_dir()
    workspace.new_brand_from_template(tmp_path / ".scroll-stopper", "acme")
    assert workspace.main(["brands"]) == 0
    assert "acme" in capsys.readouterr().out
    assert workspace.main(["learn", "texto de teste"]) == 0
    assert "texto de teste" in workspace.read_learnings(tmp_path / ".scroll-stopper")[0]


def test_cli_without_workspace_fails(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert workspace.main(["brands"]) == 1
    assert "ss workspace init" in capsys.readouterr().err


def test_append_learning_rejects_empty_and_normalizes_source(tmp_path):
    import pytest
    from ss_lib import workspace
    ws = workspace.init_workspace(tmp_path)
    with pytest.raises(ValueError):
        workspace.append_learning(ws, "   ", "manual", today="2026-11-12")
    workspace.append_learning(ws, "ok", "a\nb", today="2026-11-12")
    assert workspace.read_learnings(ws)[-1] == "- 2026-11-12 · a b · ok"
