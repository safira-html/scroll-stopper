import json
import subprocess
from pathlib import Path

import pytest

from ss_lib import paths

ROOT = Path(__file__).resolve().parent.parent
BIN = ROOT / "bin" / "ss"
EXPECTED_KEYS = {"ffmpeg", "node", "python311", "venv", "whisper_model", "yt_dlp", "engine", "ok"}


def test_check_json_keys(tmp_path):
    # roda de outro diretorio para provar que o caminho absoluto basta
    proc = subprocess.run([str(BIN), "setup", "--check", "--json"], cwd=tmp_path,
                          capture_output=True, text=True)
    data = json.loads(proc.stdout)
    assert set(data) == EXPECTED_KEYS
    assert all(isinstance(v, bool) for v in data.values())
    others = [v for k, v in data.items() if k != "ok"]
    assert data["ok"] == all(others)
    assert proc.returncode == (0 if data["ok"] else 1)


def test_paths_under_cache():
    assert paths.CACHE == Path.home() / ".cache" / "scroll-stopper"
    work = paths.work_dir("x")
    assert work == paths.CACHE / "work" / "x"
    assert paths.venv_python() == paths.CACHE / "venv" / "bin" / "python"
    assert paths.engine_dir("0.1.0") == paths.CACHE / "engine" / "0.1.0"


def test_media_dir_kinds():
    for kind in ("video", "audio", "music", "sfx", "stock"):
        assert paths.media_dir("x", kind) == paths.work_dir("x") / "media" / kind
    with pytest.raises(ValueError):
        paths.media_dir("x", "bogus")


@pytest.mark.parametrize("bad", ["", "..", "a/b", "../x", ".hidden", "Video-01", "video_01", "video 01", "-x",
                                 "vídeo", "a.b"])
def test_work_dir_rejects_unsafe_ids(bad):
    with pytest.raises(ValueError):
        paths.work_dir(bad)


@pytest.mark.parametrize("good", ["video-01", "p1", "x", "0a", "e2e-path-a-1f2e3d", "video-01-c12"])
def test_work_dir_accepts_lowercase_digits_and_hyphen(good):
    assert paths.work_dir(good) == paths.CACHE / "work" / good


def test_plugin_version_matches_manifest():
    manifest = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    assert paths.plugin_version() == manifest["version"]


def test_unknown_command_fails_cleanly():
    proc = subprocess.run([str(BIN), "nope"], capture_output=True, text=True)
    assert proc.returncode != 0
    assert "Traceback" not in proc.stderr


@pytest.fixture
def isolated_engine_cache(tmp_path, monkeypatch):
    from ss_lib import setup
    monkeypatch.setattr(paths, "CACHE", tmp_path / "cache")
    target = paths.engine_dir(paths.plugin_version())
    (target / "node_modules").mkdir(parents=True)
    return setup, target


BROWSER = Path("node_modules") / ".remotion" / "chrome-headless-shell"


def test_engine_ok_needs_npm_ci_sentinel_and_browser(isolated_engine_cache):
    setup, target = isolated_engine_cache
    assert setup.engine_ok() is False  # node_modules/ vazio (npm ci interrompido) nao conta
    (target / "node_modules" / ".package-lock.json").write_text("{}", encoding="utf-8")
    assert setup.engine_ok() is False  # sem o navegador do Remotion cada projeto baixaria ~140 MB
    (target / BROWSER).mkdir(parents=True)
    assert setup.engine_ok() is True


LOCK_HASH = __import__("hashlib").sha256((ROOT / "engine" / "package-lock.json").read_bytes()).hexdigest()[:16]


def _fake_npm(calls):
    """npm ci / remotion browser ensure falsos: escrevem o que os reais escreveriam no cwd."""
    def fake_run(cmd, **kwargs):
        cwd = Path(kwargs.get("cwd"))
        calls.append((list(cmd[1:]), cwd))
        if cmd[1:] == ["ci"]:
            (cwd / "node_modules").mkdir(exist_ok=True)
            (cwd / "node_modules" / ".package-lock.json").write_text("{}", encoding="utf-8")
        else:
            (cwd / BROWSER).mkdir(parents=True)
        return subprocess.CompletedProcess(cmd, 0)
    return fake_run


def _installed_deps() -> Path:
    deps = paths.engine_deps_dir(LOCK_HASH)
    (deps / "node_modules" / ".package-lock.json").parent.mkdir(parents=True)
    (deps / "node_modules" / ".package-lock.json").write_text("{}", encoding="utf-8")
    (deps / BROWSER).mkdir(parents=True)
    return deps


def test_engine_deps_dir_is_keyed_by_lock_hash():
    assert paths.engine_lock_hash(ROOT / "engine") == LOCK_HASH
    assert paths.engine_deps_dir(LOCK_HASH) == paths.CACHE / "engine-deps" / LOCK_HASH


def test_install_engine_installs_deps_by_lock_and_links_them(isolated_engine_cache, monkeypatch):
    setup, target = isolated_engine_cache
    (target / "node_modules").rmdir()
    calls = []
    monkeypatch.setattr(setup.subprocess, "run", _fake_npm(calls))
    monkeypatch.setattr(setup.shutil, "which", lambda name: f"/fake/bin/{name}")
    deps = paths.engine_deps_dir(LOCK_HASH)
    assert setup.install_engine() is True
    assert calls == [(["ci"], deps), (["--no-install", "remotion", "browser", "ensure"], deps)]
    assert (deps / "package-lock.json").read_bytes() == (ROOT / "engine" / "package-lock.json").read_bytes()
    assert (target / "package.json").is_file()
    assert (target / "node_modules").is_symlink()
    assert (target / "node_modules").resolve() == (deps / "node_modules").resolve()
    assert setup.engine_ok() is True

    calls.clear()
    assert setup.install_engine() is True  # tudo instalado: nao roda nada de novo
    assert calls == []


def test_install_engine_reruns_npm_ci_without_sentinel(isolated_engine_cache, monkeypatch):
    setup, target = isolated_engine_cache
    deps = paths.engine_deps_dir(LOCK_HASH)
    (deps / "node_modules").mkdir(parents=True)  # npm ci interrompido: node_modules sem o sentinela
    calls = []
    monkeypatch.setattr(setup.subprocess, "run", _fake_npm(calls))
    monkeypatch.setattr(setup.shutil, "which", lambda name: f"/fake/bin/{name}")
    assert setup.install_engine() is True
    assert calls == [(["ci"], deps), (["--no-install", "remotion", "browser", "ensure"], deps)]


def test_version_bump_with_same_lock_reuses_deps_and_cleans_old_version(isolated_engine_cache, monkeypatch):
    setup, old = isolated_engine_cache
    old_version = paths.plugin_version()
    (old / "node_modules").rmdir()
    deps = _installed_deps()
    stale_deps = paths.engine_deps_dir("0123456789abcdef")
    (stale_deps / "node_modules").mkdir(parents=True)
    calls = []
    monkeypatch.setattr(setup.subprocess, "run", _fake_npm(calls))
    monkeypatch.setattr(setup.shutil, "which", lambda name: f"/fake/bin/{name}")
    assert setup.install_engine() is True
    assert (old / "node_modules").resolve() == (deps / "node_modules").resolve()

    monkeypatch.setattr(paths, "plugin_version", lambda: "9.9.9")
    assert setup.install_engine() is True
    assert calls == []  # so o texto mudou: nada de npm ci nem navegador de novo
    new = paths.engine_dir("9.9.9")
    assert (new / "node_modules").resolve() == (deps / "node_modules").resolve()
    assert not paths.engine_dir(old_version).exists()  # versao antiga sai
    assert not stale_deps.exists()  # dependencias que ninguem usa saem
    assert deps.is_dir()


def test_install_engine_replaces_real_node_modules_with_link(isolated_engine_cache):
    # cache do layout antigo (node_modules dentro de engine/<versao>): vira link para engine-deps
    setup, target = isolated_engine_cache
    (target / "node_modules" / ".package-lock.json").write_text("{}", encoding="utf-8")
    deps = _installed_deps()
    assert setup.install_engine() is True
    assert (target / "node_modules").is_symlink()
    assert (target / "node_modules").resolve() == (deps / "node_modules").resolve()


def test_install_engine_drops_files_removed_from_the_plugin(isolated_engine_cache):
    # o render usa a copia em cache: um arquivo apagado do engine/ do plugin nao pode sobreviver nela
    setup, target = isolated_engine_cache
    (target / "node_modules").rmdir()
    _installed_deps()
    assert setup.install_engine() is True
    stale = target / "src" / "ads" / "Removed.tsx"
    stale.write_text("export const Removed = 1;\n", encoding="utf-8")
    stale_top = target / "removed.config.js"
    stale_top.write_text("module.exports = {};\n", encoding="utf-8")
    render = target / "out" / "draft.mp4"
    render.parent.mkdir()
    render.write_bytes(b"x")
    assert setup.install_engine() is True
    assert not stale.exists() and not stale_top.exists()
    assert (target / "src" / "ads" / "index.ts").is_file()
    assert (target / BROWSER).is_dir()  # node_modules fica
    assert render.is_file()  # out fica
