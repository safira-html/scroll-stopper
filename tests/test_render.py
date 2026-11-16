import importlib.util
import json
import shutil
import subprocess
import time
import uuid
from pathlib import Path

import pytest

from ss_lib import paths
from ss_lib.setup import engine_installed
from tests.fixtures import make_media

requires_media = pytest.mark.skipif(not make_media.tools_available(), reason="ffmpeg/ffprobe/say indisponiveis")
requires_engine = pytest.mark.skipif(not engine_installed(paths.engine_dir(paths.plugin_version())),
                                     reason="engine nao instalado no cache; rode bin/ss setup")

requires_whisper = pytest.mark.skipif(importlib.util.find_spec("faster_whisper") is None,
                                      reason="faster-whisper ausente neste venv (alinhamento real da narracao)")

# Roteiro do Template (engine/src/ads/Template.tsx); as cenas se amarram a estas frases.
SCRIPT = ("Seu cliente decide em três segundos. Mostre o problema, a solução e o resultado. "
          "É isso que faz alguém parar de rolar. Toque em Saiba Mais.")
COMPOSITION = "Template-m"
TIMINGS: dict = {}


def _probe_duration(path: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True, check=True).stdout
    return float(out.strip())


@pytest.fixture(scope="module")
def rendered(tmp_path_factory):
    """Renderiza Template-m em 1080x1920 com narracao do `say` alinhada pelo ss_lib.align (Whisper real)."""
    from ss_lib import align, render

    project_id = f"test-render-{uuid.uuid4().hex[:8]}"
    try:  # cobre tudo que escreve em work_dir: falha no align ou no render nao deixa sobra no cache
        gen = tmp_path_factory.mktemp("gen")
        raw = gen / "voice.aiff"
        subprocess.run(["say", "-v", make_media.VOICE, "-r", "250", "-o", str(raw), SCRIPT], check=True)
        audio_dir = paths.media_dir(project_id, "audio")
        started = time.monotonic()
        align.align(raw, "Template-m", SCRIPT, audio_dir)
        TIMINGS["align"] = time.monotonic() - started
        dest = tmp_path_factory.mktemp("sync") / "GoogleDrive-x"
        dest.mkdir()
        started = time.monotonic()
        final = render.render(project_id, COMPOSITION, dest, "ad-test", render.LUFS_MOTION)
        TIMINGS["render"] = time.monotonic() - started
        yield project_id, dest, final
    finally:
        shutil.rmtree(paths.work_dir(project_id), ignore_errors=True)


@requires_media
@requires_engine
@requires_whisper
def test_render_workdir_outside_sync_folder(rendered):
    project_id, dest, final = rendered
    assert final == dest / "ad-test.mp4"
    assert [p.name for p in dest.iterdir()] == ["ad-test.mp4"]
    work = paths.work_dir(project_id)
    assert str(work).startswith(str(Path.home() / ".cache" / "scroll-stopper" / "work"))
    assert (work / "out" / "final-ad-test.mp4").is_file()  # intermediarios ficam no work_dir
    assert not list(dest.glob(".*.part"))
    assert not list(dest.rglob("*.json"))


@requires_media
@requires_engine
@requires_whisper
def test_qa_reports_loudness(rendered):
    from ss_lib import qa, render

    _, _, final = rendered
    report = qa.qa(final, target_lufs=render.LUFS_MOTION)
    print(f"qa({final.name}) = {json.dumps(report)}; timings = {json.dumps(TIMINGS)}")
    assert set(report) == {"width", "height", "fps", "duration", "lufs", "true_peak", "ok", "target_lufs"}
    assert (report["width"], report["height"], report["fps"]) == (1080, 1920, 30)
    assert report["duration"] == pytest.approx(_probe_duration(final), abs=0.05)
    assert abs(report["lufs"] - (-15.0)) <= 0.5
    assert report["true_peak"] <= -1.0
    assert report["ok"] is True


def test_default_lufs_by_composition():
    from ss_lib import render

    assert render.default_lufs("PresenterTemplate-m") == -14.0
    assert render.default_lufs("SimpleClip-m") == -14.0
    assert render.default_lufs("Template-m") == -15.0
    assert render.default_lufs("MyAd-f") == -15.0


@requires_media
def test_qa_requires_target(tmp_path, media_fixtures):
    from ss_lib import qa

    report = qa.qa(media_fixtures["speech_with_pause"])
    assert report["target_lufs"] is None and report["ok"] is False
    assert (report["width"], report["height"]) == (1080, 1920)


@requires_media
@requires_engine
@requires_whisper
def test_draft_writes_half_scale_video_and_sheet(rendered):
    from ss_lib import render

    project_id, dest, _ = rendered
    started = time.monotonic()
    sheet = render.draft(project_id, COMPOSITION)
    TIMINGS["draft"] = time.monotonic() - started
    work = paths.work_dir(project_id) / "out"
    assert sheet == work / "sheet.jpg" and sheet.stat().st_size > 1000
    info = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                      "stream=width,height", "-of", "json", str(work / "draft.mp4")],
                                     capture_output=True, text=True, check=True).stdout)["streams"][0]
    assert (info["width"], info["height"]) == (540, 960)
    assert sorted(p.name for p in dest.iterdir()) == ["ad-test.mp4"]  # rascunho nunca vai para o destino


# ---------- entrega atomica, erros claros e seguranca de pico ----------

def test_deliver_is_atomic_and_never_overwrites(tmp_path):
    from ss_lib import render

    src = tmp_path / "src.mp4"
    src.write_bytes(b"new")
    dest = tmp_path / "dest"
    dest.mkdir()
    (dest / "ad.mp4").write_bytes(b"old")
    first = render.deliver(src, dest, "ad")
    second = render.deliver(src, dest, "ad")
    assert (first, second) == (dest / "ad_v2.mp4", dest / "ad_v3.mp4")
    assert (dest / "ad.mp4").read_bytes() == b"old"
    assert first.read_bytes() == b"new"
    assert sorted(p.name for p in dest.iterdir()) == ["ad.mp4", "ad_v2.mp4", "ad_v3.mp4"]  # nenhum .part sobra


def test_deliver_reserves_name_before_copying(tmp_path, monkeypatch):
    from ss_lib import render

    src = tmp_path / "src.mp4"
    src.write_bytes(b"new")
    seen = {}
    real_copy = render.shutil.copy2

    def spy(a, b):
        seen["reserved"] = (tmp_path / "ad.mp4").exists()  # nome ja reservado durante a copia
        return real_copy(a, b)

    monkeypatch.setattr(render.shutil, "copy2", spy)
    assert render.deliver(src, tmp_path, "ad") == tmp_path / "ad.mp4"
    assert seen["reserved"] is True
    assert (tmp_path / "ad.mp4").read_bytes() == b"new"


def test_deliver_failure_leaves_no_part_nor_reserved_file(tmp_path, monkeypatch):
    from ss_lib import render

    src = tmp_path / "src.mp4"
    src.write_bytes(b"x")

    def boom(*_):
        raise OSError("disk full")

    monkeypatch.setattr(render.shutil, "copy2", boom)
    with pytest.raises(OSError):
        render.deliver(src, tmp_path, "ad")
    assert sorted(p.name for p in tmp_path.iterdir()) == ["src.mp4"]


def test_deliver_cleans_part_file_on_failure(tmp_path, monkeypatch):
    from ss_lib import render

    src = tmp_path / "src.mp4"
    src.write_bytes(b"x")

    def boom(*_):
        raise OSError("disk full")

    monkeypatch.setattr(render.os, "replace", boom)
    with pytest.raises(OSError):
        render.deliver(src, tmp_path, "ad")
    assert not list(tmp_path.glob(".*.part")) and not (tmp_path / "ad.mp4").exists()


def test_render_requires_existing_dest_parent(tmp_path):
    from ss_lib import render

    with pytest.raises(SystemExit, match="nao existe"):
        render.render("p1", "Template-m", tmp_path / "missing" / "out", "ad", -15.0)


def test_cli_engine_not_installed_is_portuguese(tmp_path, monkeypatch):
    from ss_lib import engine, render

    def missing(*_a, **_k):
        raise engine.EngineNotInstalled("engine nao instalado em /x")

    monkeypatch.setattr(render.engine, "prepare", missing)
    with pytest.raises(SystemExit, match="ss setup"):
        render.main_render(["p1", "Template-m", "--dest", str(tmp_path), "--name", "ad"])
    with pytest.raises(SystemExit, match="ss setup"):
        render.main_draft(["p1", "Template-m"])


def test_render_error_message_lists_compositions():
    from ss_lib import render

    out = ("Bundling 100%\n[Tab 0] Made 63 network requests to load fonts\n"
           "Error  Error: Could not find composition with ID Bogus-x. Available compositions: A-f, B-m\n")
    msg = render._render_error("Bogus-x", out)
    assert "Bogus-x" in msg and "A-f, B-m" in msg and "Bundling" not in msg
    other = render._render_error("X-m", "Bundling 1%\nsome noise\nError: boom\n  at stack")
    assert "boom" in other and "Bundling" not in other


def test_missing_node_is_portuguese(tmp_path, monkeypatch):
    from ss_lib import render

    def no_npx(*_a, **_k):
        raise FileNotFoundError("npx")

    monkeypatch.setattr(render.subprocess, "run", no_npx)
    with pytest.raises(SystemExit, match="brew install node"):
        render.remotion_render(tmp_path, "Template-m", tmp_path / "o.mp4", [])


@requires_engine
def test_unknown_composition_lists_available(tmp_path):
    from ss_lib import render

    project_id = f"test-render-{uuid.uuid4().hex[:8]}"
    try:
        with pytest.raises(SystemExit) as exc:
            render.render(project_id, "Bogus-x", tmp_path, "ad", -15.0)
    finally:
        shutil.rmtree(paths.work_dir(project_id), ignore_errors=True)
    message = str(exc.value)
    assert "Bogus-x" in message and "Template-m" in message
    assert "Bundling" not in message and "network requests" not in message


def test_sheet_fps_covers_long_videos():
    from ss_lib import render

    assert render.sheet_fps(20) == pytest.approx(1 / 1.5)
    assert render.sheet_fps(120) == pytest.approx(44 / 120)


@requires_media
def test_finalize_checked_keeps_true_peak_safe(tmp_path):
    """Ruido rosa baixo + cliques: o loudnorm cai no modo dinamico e estoura -1,0 dBTP com TP -1,5; o retry com -2,5 corrige."""
    from ss_lib import qa, render

    raw = tmp_path / "clicks.mp4"
    graph = ("anoisesrc=color=pink:amplitude=0.03:sample_rate=48000:duration=8:seed=3[n];"
             "aevalsrc='if(lt(mod(t,1),0.002),0.95,0)':s=48000:d=8[c];[n][c]amix=inputs=2:normalize=0[a]")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "testsrc2=size=1080x1920:rate=30:duration=8",
                    "-filter_complex", graph, "-map", "0:v", "-map", "[a]", "-c:v", "libx264", "-preset", "ultrafast",
                    "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", str(raw)], check=True)
    first_peak = qa.measure_loudness(render.finalize(raw, tmp_path / "first.mp4", render.LUFS_PRESENTER))[1]
    assert first_peak > qa.TRUE_PEAK_MAX  # sem o retry o arquivo sairia fora do padrao
    report = render.finalize_checked(raw, tmp_path / "final.mp4", render.LUFS_PRESENTER)
    print(f"peak without retry {first_peak:.2f} dBTP; after finalize_checked {report}")
    assert report["true_peak"] <= qa.TRUE_PEAK_MAX


def test_qa_problems_and_report_line_in_portuguese():
    from ss_lib import qa, render

    good = {"width": 1080, "height": 1920, "fps": 30.0, "duration": 5, "lufs": -15.0, "true_peak": -3.0,
            "ok": True, "target_lufs": -15.0}
    bad = {**good, "lufs": -17.6, "true_peak": -1.13, "ok": False}
    assert qa.problems(good) == []
    reasons = qa.problems(bad)
    assert reasons == ["loudness -17.6 LUFS (alvo -15)"]  # -1.13 dBTP ainda esta dentro de -1,0
    worse = {**bad, "true_peak": -0.5, "width": 540, "height": 960}
    assert "pico -0.5 dBTP" in "; ".join(qa.problems(worse)) and "540x960" in "; ".join(qa.problems(worse))
    assert render.report_line(good, Path("/x/a.mp4"), "video final").startswith("[ok] video final: /x/a.mp4")
    line = render.report_line(bad, Path("/x/a.mp4"), "video final")
    assert line.startswith("[!!] Conferência falhou: loudness -17.6 LUFS (alvo -15)")
    assert line.splitlines()[1].startswith("[!!] video final") and line.endswith("/x/a.mp4")


def test_main_render_prints_warning_when_qa_fails(tmp_path, monkeypatch, capsys):
    from ss_lib import render

    bad = {"width": 1080, "height": 1920, "fps": 30.0, "duration": 5, "lufs": -17.6, "true_peak": -1.13,
           "ok": False, "target_lufs": -15.0}
    monkeypatch.setattr(render, "render_checked", lambda *a, **k: (tmp_path / "ad.mp4", bad))
    render.main_render(["p1", "Template-m", "--dest", str(tmp_path), "--name", "ad"])
    out = capsys.readouterr().out
    assert "[!!] Conferência falhou: loudness -17.6 LUFS (alvo -15)" in out and "[ok]" not in out


def test_brand_arg_accepts_ephemeral_folder_or_workspace_slug(tmp_path, monkeypatch):
    """Marca efemera (pasta no cache, fora de .scroll-stopper/) ou slug da pasta de trabalho."""
    from ss_lib import render, workspace

    folder = tmp_path / "cache" / "tmp-brands" / "efemera"
    shutil.copytree(paths.PLUGIN_ROOT / "templates" / "marca", folder)
    outside = tmp_path / "sem-pasta-de-trabalho"
    outside.mkdir()
    monkeypatch.chdir(outside)
    assert render._brand_arg(str(folder)) == folder.resolve()

    ws = workspace.init_workspace(tmp_path / "user")
    workspace.new_brand_from_template(ws, "minha")
    monkeypatch.chdir(tmp_path / "user")
    assert render._brand_arg("minha").resolve() == (ws / "marcas" / "minha").resolve()
    with pytest.raises(SystemExit) as exc:
        render._brand_arg("nao-existe")
    assert "nao encontrada" in str(exc.value)


def test_default_lufs_presenter_project(tmp_path, monkeypatch):
    from ss_lib import render

    monkeypatch.setattr(paths, "CACHE", tmp_path / "cache")
    video = paths.media_dir("v1", "video")
    video.mkdir(parents=True)
    (video / "presenter.mp4").write_bytes(b"x")
    assert render.default_lufs("v1-m", "v1") == -14.0
    assert render.default_lufs("v2-m", "v2") == -15.0


def test_main_render_uses_project_brand_and_presenter_lufs(tmp_path, monkeypatch):
    from ss_lib import render

    monkeypatch.setattr(paths, "CACHE", tmp_path / "cache")
    video = paths.media_dir("v1", "video")
    video.mkdir(parents=True)
    (video / "presenter.mp4").write_bytes(b"x")
    brand = tmp_path / "marca"
    shutil.copytree(paths.PLUGIN_ROOT / "templates" / "marca", brand)
    (paths.work_dir("v1") / "brand-path.txt").write_text(str(brand), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    seen = []
    good = {"width": 1080, "height": 1920, "fps": 30.0, "duration": 5, "lufs": -14.0, "true_peak": -1.6,
            "ok": True, "target_lufs": -14.0}

    def fake(pid, comp, dest, name, lufs, brand_dir):
        seen.append((lufs, brand_dir))
        return tmp_path / "a.mp4", good

    monkeypatch.setattr(render, "render_checked", fake)
    render.main_render(["v1", "v1-m", "--dest", str(tmp_path), "--name", "a"])
    render.main_render(["v1", "v1-m", "--dest", str(tmp_path), "--name", "a", "--lufs", "-15"])
    assert seen[0] == (-14.0, brand.resolve())
    assert seen[1][0] == -15.0

    drafted = []
    monkeypatch.setattr(render, "draft", lambda pid, comp, brand_dir=None: drafted.append(brand_dir) or tmp_path / "s.jpg")
    render.main_draft(["v1", "v1-m"])
    assert drafted == [brand.resolve()]


@requires_media
def test_finalize_plain_video_delivers_normalized(tmp_path, media_fixtures, monkeypatch, capsys):
    from ss_lib import finalize, qa

    monkeypatch.setattr(paths, "CACHE", tmp_path / "cache")
    dest = tmp_path / "entrega"
    assert finalize.main([str(media_fixtures["speech_with_pause"]), "--dest", str(dest), "--name", "so-corte"]) == 0
    final = dest / "so-corte.mp4"
    assert final.is_file()
    report = qa.qa(final, target_lufs=-14.0)
    assert abs(report["lufs"] + 14.0) <= 0.5 and report["true_peak"] <= -1.0
    assert str(final) in capsys.readouterr().out


@requires_media
def test_probe_reports_streams(media_fixtures, tmp_path):
    from ss_lib import probe

    info = probe.probe(media_fixtures["speech_with_pause"])
    assert info["video"] is True and info["audio"] is True
    assert (info["width"], info["height"]) == (1080, 1920)
    assert info["duration"] > 2
    with pytest.raises(SystemExit):
        probe.probe(tmp_path / "nao-existe.mp4")
