import json
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

from ss_lib import brand, brand_extract, engine, workspace

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "site"


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture
def fixture_url():
    port = _free_port()
    proc = subprocess.Popen([sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1"],
                            cwd=FIXTURE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(50):
            try:
                socket.create_connection(("127.0.0.1", port), timeout=0.2).close()
                break
            except OSError:
                time.sleep(0.1)
        else:
            pytest.fail(f"http.server never opened port {port}")
        yield f"http://127.0.0.1:{port}/index.html"
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()


def _assert_tokens(result: dict) -> None:
    assert result["cssVariables"]["--accent"] == "#FF6A3D"
    assert "Inter" in result["googleFonts"]
    assert result["themeColor"] == "#101820"
    assert not [k for k in result["cssVariables"] if k.startswith("--wp--preset")]
    assert any(c[0] == "#ff6a3d" for c in result["topColors"])
    assert any(name == '"Inter", sans-serif' for name, _ in result["fonts"])


def test_extract_from_fixture(fixture_url):
    _assert_tokens(brand_extract.extract(fixture_url))


def test_extract_local_folder_and_file():
    _assert_tokens(brand_extract.extract(str(FIXTURE)))
    _assert_tokens(brand_extract.extract(str(FIXTURE / "index.html")))
    _assert_tokens(brand_extract.extract(f"file://{FIXTURE / 'index.html'}"))


def test_extract_file_name_with_spaces(tmp_path):
    shutil.copytree(FIXTURE, tmp_path / "site")
    page = tmp_path / "site" / "minha marca.html"
    (tmp_path / "site" / "index.html").rename(page)
    _assert_tokens(brand_extract.extract(str(page)))


def test_extract_unreachable_url():
    started = time.monotonic()
    with pytest.raises(brand_extract.ExtractionError) as info:
        brand_extract.extract(f"http://127.0.0.1:{_free_port()}/")
    assert time.monotonic() - started < 10
    assert len(str(info.value)) < 300


def test_extract_missing_source():
    with pytest.raises(brand_extract.ExtractionError):
        brand_extract.extract("/nonexistent/site")


def test_cli_extract_prints_json(capsys):
    assert brand.main(["extract", str(FIXTURE)]) == 0
    assert json.loads(capsys.readouterr().out)["cssVariables"]["--accent"] == "#FF6A3D"


@pytest.fixture
def workspace_with_brand(tmp_path, monkeypatch):
    ws = workspace.init_workspace(tmp_path)
    target = workspace.new_brand_from_template(ws, "acme")
    monkeypatch.chdir(tmp_path)
    return target


def test_use_resolves_slug_and_path(workspace_with_brand, tmp_path, monkeypatch, capsys):
    calls = []

    def fake_prepare(project_id, brand_dir, media=None):
        calls.append((project_id, Path(brand_dir), media))
        return tmp_path / "engine-dir"

    monkeypatch.setattr(engine, "prepare", fake_prepare)
    assert brand.main(["use", "acme", "--project", "p1"]) == 0
    assert calls[-1] == ("p1", workspace_with_brand.resolve(), {})
    assert capsys.readouterr().out.strip() == str(tmp_path / "engine-dir")

    assert brand.main(["use", str(workspace_with_brand), "--project", "p2"]) == 0
    assert calls[-1][:2] == ("p2", workspace_with_brand.resolve())


def test_use_unknown_brand_is_clear_error(workspace_with_brand, monkeypatch, capsys):
    monkeypatch.setattr(engine, "prepare", lambda *a, **k: pytest.fail("must not prepare"))
    assert brand.main(["use", "nope", "--project", "p1"]) == 1
    err = capsys.readouterr().err
    assert "nao encontrada" in err and "acme" in err


def test_use_without_workspace(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(brand.workspace, "find_workspace", lambda start: None)
    assert brand.main(["use", "acme", "--project", "p1"]) == 1
    assert "pasta de trabalho" in capsys.readouterr().err


def test_use_requires_project():
    with pytest.raises(SystemExit):
        brand.main(["use", "acme"])


# ---------- ss brand new ----------

def test_brand_new_in_workspace_prints_dir(tmp_path, monkeypatch, capsys):
    ws = workspace.init_workspace(tmp_path)
    monkeypatch.chdir(tmp_path)
    assert brand.main(["new", "minha"]) == 0
    out = capsys.readouterr().out.strip()
    assert Path(out) == (ws / "marcas" / "minha").resolve()
    data = json.loads((ws / "marcas" / "minha" / "brand.json").read_text(encoding="utf-8"))
    assert data["slug"] == "minha"
    assert brand.main(["new", "minha"]) == 1  # ja existe: nao sobrescreve
    assert "ja existe" in capsys.readouterr().err


def test_brand_new_ephemeral_writes_only_cache(tmp_path, monkeypatch, capsys):
    from ss_lib import paths

    monkeypatch.setattr(paths, "CACHE", tmp_path / "cache")
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    monkeypatch.chdir(cwd)
    assert brand.main(["new", "temp", "--ephemeral"]) == 0
    out = Path(capsys.readouterr().out.strip())
    assert out == (tmp_path / "cache" / "tmp-brands" / "temp").resolve()
    assert (out / "brand.json").is_file()
    assert list(cwd.iterdir()) == []


def test_brand_new_without_workspace_fails_in_portuguese(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert brand.main(["new", "minha"]) == 1
    assert "ss workspace init" in capsys.readouterr().err


def test_local_server_rejects_foreign_host_header():
    # DNS rebinding: uma pagina de outro dominio apontado para 127.0.0.1 nao pode ler a pasta servida
    import http.client

    with brand_extract.serve_folder(FIXTURE) as port:
        def get(host):
            conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
            conn.putrequest("GET", "/index.html", skip_host=True)
            if host is not None:
                conn.putheader("Host", host)
            conn.endheaders()
            status = conn.getresponse().status
            conn.close()
            return status

        assert get(f"127.0.0.1:{port}") == 200
        assert get(f"localhost:{port}") == 200
        assert get("evil.example") == 403
        assert get(f"evil.example:{port}") == 403
        assert get("127.0.0.1:1") == 403
        assert get(None) == 403
