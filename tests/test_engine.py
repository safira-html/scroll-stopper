import json
import os
import shutil
import struct
import subprocess
import uuid
from pathlib import Path

import pytest

from ss_lib import engine, paths
from ss_lib.setup import engine_installed

ROOT = Path(__file__).resolve().parent.parent
ENGINE_SRC = ROOT / "engine"
TEMPLATE_BRAND = ROOT / "templates" / "marca"
NODE_PATH = f"{Path.home() / '.local' / 'bin'}:/opt/homebrew/bin:/usr/local/bin:{os.environ.get('PATH', '')}"
NODE_ENV = {**os.environ, "PATH": NODE_PATH}
RENDER_TIMEOUT = 900


def node(*args, cwd):
    return subprocess.run(["node", *args], cwd=cwd, env=NODE_ENV, capture_output=True, text=True, timeout=120)


def npx(*args, cwd, timeout=RENDER_TIMEOUT):
    return subprocess.run(["npx", "--no-install", *args], cwd=cwd, env=NODE_ENV, capture_output=True, text=True,
                          timeout=timeout)


def png_size(path: Path) -> tuple[int, int]:
    head = path.read_bytes()[:24]
    assert head[:8] == b"\x89PNG\r\n\x1a\n"
    return struct.unpack(">II", head[16:24])


def unique_id(tag: str) -> str:
    return f"test-{tag}-{uuid.uuid4().hex[:8]}"


# ---------- engine/ no repositorio ----------

def test_active_brand_is_neutral_template():
    active = json.loads((ENGINE_SRC / "src" / "brand" / "active.json").read_text(encoding="utf-8"))
    template = json.loads((TEMPLATE_BRAND / "brand.json").read_text(encoding="utf-8"))
    assert active == template


def test_fonts_ts_matches_active_brand():
    fonts = (ENGINE_SRC / "src" / "brand" / "fonts.ts").read_text(encoding="utf-8")
    for module in ("Inter", "JetBrainsMono", "Fraunces"):
        assert f"@remotion/google-fonts/{module}'" in fonts


def test_public_has_no_media():
    public = ENGINE_SRC / "public"
    assert public.is_dir()
    if not shutil.which("git") or not (ROOT / ".git").exists():
        pytest.skip("git indisponivel: nao da para listar os arquivos versionados")
    tracked = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard", "engine/public"], cwd=ROOT, capture_output=True, text=True).stdout.split()
    assert tracked == ["engine/public/.gitkeep"]


def test_presenter_overlap_fixes_kept():
    presenter = (ENGINE_SRC / "src" / "presenter.tsx").read_text(encoding="utf-8")
    assert "frame > b + 8) return null" in presenter
    assert "durationInFrames={Math.max(1, b - a + 8)}" in presenter


# ---------- use-brand.mjs (numa copia isolada do engine, sem node_modules) ----------

@pytest.fixture
def scratch_engine(tmp_path):
    target = tmp_path / "engine"
    shutil.copytree(ENGINE_SRC, target, ignore=shutil.ignore_patterns("node_modules", "out"))
    return target


def test_use_brand_absolute_path(scratch_engine, tmp_path):
    brand = tmp_path / "outra-marca"
    shutil.copytree(TEMPLATE_BRAND, brand)
    data = json.loads((brand / "brand.json").read_text(encoding="utf-8"))
    data["name"] = "Outra Marca"
    data["fonts"] = {"sans": "Instrument Sans", "mono": "Space Mono", "display": "Instrument Serif"}
    (brand / "brand.json").write_text(json.dumps(data), encoding="utf-8")
    (brand / "assets" / "mark.svg").write_text("<svg/>", encoding="utf-8")

    proc = node(str(scratch_engine / "scripts" / "use-brand.mjs"), str(brand), cwd=tmp_path)
    assert proc.returncode == 0, proc.stderr
    active = json.loads((scratch_engine / "src" / "brand" / "active.json").read_text(encoding="utf-8"))
    assert active == data
    fonts = (scratch_engine / "src" / "brand" / "fonts.ts").read_text(encoding="utf-8")
    assert "@remotion/google-fonts/InstrumentSans'" in fonts
    assert "@remotion/google-fonts/SpaceMono'" in fonts
    assert "@remotion/google-fonts/InstrumentSerif'" in fonts
    assert (scratch_engine / "public" / "brand" / "logo.svg").is_file()
    assert (scratch_engine / "public" / "brand" / "mark.svg").is_file()


def test_use_brand_relative_path_resolves_against_cwd(scratch_engine, tmp_path):
    shutil.copytree(TEMPLATE_BRAND, tmp_path / "marcas" / "minha")
    proc = subprocess.run(["node", str(scratch_engine / "scripts" / "use-brand.mjs"), "marcas/minha"], cwd=tmp_path,
                          env=NODE_ENV, capture_output=True, text=True, timeout=120)
    assert proc.returncode == 0, proc.stderr
    assert (scratch_engine / "public" / "brand" / "logo.svg").is_file()


def test_use_brand_missing_brand_json_fails_in_portuguese(scratch_engine, tmp_path):
    empty = tmp_path / "sem-marca"
    empty.mkdir()
    before = (scratch_engine / "src" / "brand" / "active.json").read_text(encoding="utf-8")
    proc = node("scripts/use-brand.mjs", str(empty), cwd=scratch_engine)
    assert proc.returncode != 0
    assert "brand.json não encontrado" in proc.stderr
    assert str(empty / "brand.json") in proc.stderr
    assert (scratch_engine / "src" / "brand" / "active.json").read_text(encoding="utf-8") == before


def test_use_brand_without_argument_shows_usage(scratch_engine):
    proc = node("scripts/use-brand.mjs", cwd=scratch_engine)
    assert proc.returncode != 0
    assert "Uso:" in proc.stderr


# ---------- prepare() com cache isolado (engine falso, sem node_modules) ----------

@pytest.fixture
def fake_cache(tmp_path, monkeypatch):
    cache = tmp_path / "cache"
    monkeypatch.setattr(paths, "CACHE", cache)
    cached = paths.engine_dir(paths.plugin_version())
    shutil.copytree(ENGINE_SRC, cached, ignore=shutil.ignore_patterns("node_modules", "out"))
    # layout do ss setup: node_modules e um link para CACHE/engine-deps/<hash do lock>/node_modules
    deps = paths.engine_deps_dir(paths.engine_lock_hash(ENGINE_SRC)) / "node_modules"
    deps.mkdir(parents=True)
    (deps / ".package-lock.json").write_text("{}", encoding="utf-8")
    (deps / ".remotion" / "chrome-headless-shell").mkdir(parents=True)
    (cached / "node_modules").symlink_to(deps, target_is_directory=True)
    return cache


def test_prepare_requires_installed_engine(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "CACHE", tmp_path / "cache")
    with pytest.raises(engine.EngineNotInstalled, match="ss setup"):
        engine.prepare("p1", TEMPLATE_BRAND, {})


def test_prepare_copies_engine_links_media_and_activates_brand(fake_cache, tmp_path):
    sfx = tmp_path / "kit" / "sfx"
    sfx.mkdir(parents=True)
    (sfx / "pop.mp3").write_bytes(b"x")
    video = paths.media_dir("p1", "video")
    video.mkdir(parents=True)
    (video / "presenter.mp4").write_bytes(b"x")

    target = engine.prepare("p1", TEMPLATE_BRAND, {"sfx": sfx})

    assert target == paths.work_dir("p1") / "engine"
    assert (target / "src" / "index.ts").is_file()
    assert (target / "node_modules" / ".package-lock.json").is_file()
    assert (target / "public" / "sfx").is_symlink()
    assert (target / "public" / "sfx").resolve() == sfx.resolve()
    assert (target / "public" / "video").resolve() == video.resolve()
    assert (target / "public" / "video" / "presenter.mp4").is_file()
    for kind in ("audio", "music", "stock"):
        assert not (target / "public" / kind).exists()
    assert (target / "public" / "brand" / "logo.svg").is_file()
    active = json.loads((target / "src" / "brand" / "active.json").read_text(encoding="utf-8"))
    assert active["slug"] == "minha-marca"


def test_prepare_again_refreshes_brand_and_links(fake_cache, tmp_path):
    first = tmp_path / "music-a"
    second = tmp_path / "music-b"
    first.mkdir()
    second.mkdir()
    target = engine.prepare("p1", TEMPLATE_BRAND, {"music": first})
    (target / "src" / "ads" / "Custom.tsx").write_text("export {};\n", encoding="utf-8")

    other = tmp_path / "outra"
    shutil.copytree(TEMPLATE_BRAND, other)
    data = json.loads((other / "brand.json").read_text(encoding="utf-8"))
    data["slug"] = "outra"
    (other / "brand.json").write_text(json.dumps(data), encoding="utf-8")

    again = engine.prepare("p1", other, {"music": second})
    assert again == target
    assert (target / "public" / "music").resolve() == second.resolve()
    assert first.is_dir()  # o link antigo sai, a pasta de origem fica
    assert json.loads((target / "src" / "brand" / "active.json").read_text(encoding="utf-8"))["slug"] == "outra"
    assert (target / "src" / "ads" / "Custom.tsx").is_file()  # o trabalho do projeto nao e apagado


def test_prepare_rejects_unknown_kind_and_missing_dir(fake_cache, tmp_path):
    with pytest.raises(ValueError, match="bogus"):
        engine.prepare("p1", TEMPLATE_BRAND, {"bogus": tmp_path})
    with pytest.raises(ValueError, match="nao existe"):
        engine.prepare("p1", TEMPLATE_BRAND, {"audio": tmp_path / "nope"})


def test_prepare_missing_brand_json_fails(fake_cache, tmp_path):
    with pytest.raises(engine.BrandActivationError, match="brand.json"):
        engine.prepare("p1", tmp_path, {})


# ---------- engine instalado de verdade (cache do ss setup) ----------

def _installed_engine() -> Path:
    return paths.engine_dir(paths.plugin_version())


requires_installed_engine = pytest.mark.skipif(
    not engine_installed(_installed_engine()),
    reason="engine nao instalado no cache; rode bin/ss setup",
)


@pytest.fixture(scope="module")
def prepared_engine():
    project_id = unique_id("engine")
    try:
        yield engine.prepare(project_id, TEMPLATE_BRAND, {})
    finally:
        shutil.rmtree(paths.work_dir(project_id), ignore_errors=True)


@requires_installed_engine
def test_engine_typecheck(prepared_engine):
    proc = npx("tsc", "-p", ".", cwd=prepared_engine, timeout=300)
    assert proc.returncode == 0, proc.stdout + proc.stderr


@requires_installed_engine
def test_template_still_neutral_brand(prepared_engine, tmp_path):
    out = tmp_path / "template.png"
    proc = npx("remotion", "still", "src/index.ts", "Template-m", str(out), "--frame=20", "--scale=0.4",
               cwd=prepared_engine)
    assert proc.returncode == 0, proc.stdout[-3000:] + proc.stderr[-3000:]
    assert out.is_file()
    assert png_size(out) == (432, 768)


@requires_installed_engine
def test_presenter_without_media_renders(prepared_engine, tmp_path):
    assert not any((prepared_engine / "public" / kind).exists() for kind in paths.MEDIA_KINDS)
    out = tmp_path / "presenter.mp4"
    proc = npx("remotion", "render", "src/index.ts", "PresenterTemplate-m", str(out), "--scale=0.3",
               cwd=prepared_engine)
    assert proc.returncode == 0, proc.stdout[-3000:] + proc.stderr[-3000:]
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(out)],
                           env=NODE_ENV, capture_output=True, text=True, check=True)
    assert float(probe.stdout.strip()) > 15


@requires_installed_engine
def test_linked_media_is_served():
    # palavras em media/audio (linkada em public/audio) mudam a duracao calculada da composicao
    project_id = unique_id("media")
    try:
        audio = paths.media_dir(project_id, "audio")
        audio.mkdir(parents=True)
        words = [{"w": "Oi.", "s": 0.2, "e": 0.6}, {"w": "Tchau.", "s": 0.7, "e": 1.0}]
        (audio / "PresenterTemplate-m.words.json").write_text(json.dumps(words), encoding="utf-8")
        target = engine.prepare(project_id, TEMPLATE_BRAND, {})
        proc = npx("remotion", "compositions", "src/index.ts", cwd=target, timeout=300)
        assert proc.returncode == 0, proc.stdout[-3000:] + proc.stderr[-3000:]
        # linha da tabela: "PresenterTemplate-m  30  1080x1920  116 (3.87 sec)"
        row = next(ln.split() for ln in proc.stdout.splitlines() if ln.startswith("PresenterTemplate-m "))
        # 1.0 s de fala + 0.35 + 2.5 s de saida = 3.85 s -> ceil(115.5) = 116 quadros
        assert row[3] == "116", row
    finally:
        shutil.rmtree(paths.work_dir(project_id), ignore_errors=True)


def test_clone_falls_back_to_copy_with_notice(tmp_path, monkeypatch, capsys):
    source = tmp_path / "src"
    (source / "a").mkdir(parents=True)
    (source / "a" / "f.txt").write_text("x", encoding="utf-8")
    monkeypatch.setattr(engine.subprocess, "run",
                        lambda *a, **k: subprocess.CompletedProcess(a[0], 1, "", "cp: clonefile failed"))
    engine._clone(source, tmp_path / "dst")
    assert (tmp_path / "dst" / "a" / "f.txt").read_text(encoding="utf-8") == "x"
    assert "copia normal" in capsys.readouterr().err


def test_prepare_copies_workspace_kit_into_project_media(fake_cache, tmp_path, monkeypatch):
    # a pasta de trabalho costuma estar no Google Drive: durante o render nada do engine aponta para ela
    from ss_lib import workspace

    ws = workspace.init_workspace(tmp_path / "user")
    kit = ws / "kit-de-som"
    (kit / "music" / "bed-dark.mp3").write_bytes(b"dark")
    (kit / "sfx" / "whoosh.mp3").write_bytes(b"w1")
    (kit / "sfx" / "old.mp3").write_bytes(b"o")
    monkeypatch.chdir(tmp_path / "user")
    target = engine.prepare("p1", TEMPLATE_BRAND, {})
    music, sfx = paths.media_dir("p1", "music"), paths.media_dir("p1", "sfx")
    assert (target / "public" / "music").resolve() == music.resolve()
    assert (target / "public" / "sfx").resolve() == sfx.resolve()
    assert (music / "bed-dark.mp3").read_bytes() == b"dark"
    assert not (music / "bed-dark.mp3").is_symlink()
    assert (sfx / "whoosh.mp3").read_bytes() == b"w1"

    # no proximo prepare: novo arquivo entra, alterado e atualizado, apagado sai
    (kit / "sfx" / "pop-soft.mp3").write_bytes(b"p")
    (kit / "sfx" / "whoosh.mp3").write_bytes(b"w2-longer")
    (kit / "sfx" / "old.mp3").unlink()
    assert not (sfx / "pop-soft.mp3").exists()  # copia, nao link: so chega no prepare seguinte
    engine.prepare("p1", TEMPLATE_BRAND, {})
    assert (sfx / "pop-soft.mp3").read_bytes() == b"p"
    assert (sfx / "whoosh.mp3").read_bytes() == b"w2-longer"
    assert not (sfx / "old.mp3").exists()
    assert (music / "bed-dark.mp3").is_file()

    # midia do proprio projeto vence o kit (e nao e tocada)
    own = paths.media_dir("p2", "music")
    own.mkdir(parents=True)
    (own / "minha.mp3").write_bytes(b"m")
    other = engine.prepare("p2", TEMPLATE_BRAND, {})
    assert (other / "public" / "music").resolve() == own.resolve()
    assert sorted(f.name for f in own.iterdir()) == ["minha.mp3"]
    assert (paths.media_dir("p2", "sfx") / "pop-soft.mp3").is_file()


def test_prepare_records_brand_of_project(fake_cache, tmp_path):
    engine.prepare("p1", TEMPLATE_BRAND, {})
    saved = paths.work_dir("p1") / "brand-path.txt"
    assert Path(saved.read_text(encoding="utf-8").strip()) == TEMPLATE_BRAND.resolve()
    assert engine.project_brand("p1") == TEMPLATE_BRAND.resolve()
    assert engine.project_brand("nunca-preparado") is None


def test_recorded_brand_missing_is_loud(fake_cache, tmp_path):
    import shutil as _sh

    brand = tmp_path / "marca-temp"
    _sh.copytree(TEMPLATE_BRAND, brand)
    engine.prepare("p1", brand, {})
    _sh.rmtree(brand)
    with pytest.raises(engine.RecordedBrandMissing):
        engine.project_brand("p1")
    from ss_lib import render

    with pytest.raises(SystemExit) as exc:
        render._brand_arg(None, "p1")
    assert "nao existe mais" in str(exc.value)


def test_prepare_remembers_workspace_kit_outside_cwd(fake_cache, tmp_path, monkeypatch):
    from ss_lib import workspace

    ws = workspace.init_workspace(tmp_path / "user")
    monkeypatch.chdir(tmp_path / "user")
    engine.prepare("p1", TEMPLATE_BRAND, {})
    outside = tmp_path / "elsewhere"
    outside.mkdir()
    monkeypatch.chdir(outside)
    (ws / "kit-de-som" / "music" / "bed-light.mp3").write_bytes(b"x")
    target = engine.prepare("p1", TEMPLATE_BRAND, {})
    assert (target / "public" / "music" / "bed-light.mp3").is_file()  # kit lembrado, novo arquivo copiado


def test_prepare_clone_keeps_node_modules_linked_to_shared_deps(fake_cache):
    target = engine.prepare("p1", TEMPLATE_BRAND, {})
    deps = paths.engine_deps_dir(paths.engine_lock_hash(ENGINE_SRC)) / "node_modules"
    assert (target / "node_modules").is_symlink()
    assert (target / "node_modules").resolve() == deps.resolve()


def test_prepare_repoints_dangling_node_modules_and_keeps_project_work(fake_cache):
    # dependencias antigas removidas pelo ss setup: o link do projeto quebra; o prepare re-aponta sem apagar src/ads
    target = engine.prepare("p1", TEMPLATE_BRAND, {})
    (target / "src" / "ads" / "Custom.tsx").write_text("export {};\n", encoding="utf-8")
    (target / "node_modules").unlink()
    (target / "node_modules").symlink_to(fake_cache / "engine-deps" / "gone" / "node_modules", target_is_directory=True)
    again = engine.prepare("p1", TEMPLATE_BRAND, {})
    assert again == target
    assert (target / "src" / "ads" / "Custom.tsx").is_file()
    assert (target / "node_modules").resolve() == (paths.engine_dir(paths.plugin_version()) / "node_modules").resolve()


def test_prepare_stamps_engine_version_and_warns_when_outdated(fake_cache, capsys):
    engine.prepare("p1", TEMPLATE_BRAND, {})
    stamp = paths.work_dir("p1") / "engine-version.txt"
    assert stamp.read_text(encoding="utf-8").strip() == paths.plugin_version()
    assert "[!!]" not in capsys.readouterr().err

    stamp.write_text("0.0.9\n", encoding="utf-8")
    engine.prepare("p1", TEMPLATE_BRAND, {})
    err = [ln for ln in capsys.readouterr().err.splitlines() if ln.startswith("[!!]")]
    assert len(err) == 1
    assert "0.0.9" in err[0] and str(paths.work_dir("p1") / "engine") in err[0]

    stamp.unlink()  # copia de antes do carimbo: conta como 0.1.0
    engine.prepare("p1", TEMPLATE_BRAND, {})
    warned = "[!!]" in capsys.readouterr().err
    assert warned == (paths.plugin_version() != "0.1.0")
