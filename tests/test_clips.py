import json
import os
import shutil
import subprocess
import time
import uuid
from pathlib import Path

import pytest

from ss_lib import clip_render, paths, qa, render
from ss_lib import clips
from ss_lib.clips import (CLIP_DURATIONS, clip_count, sentence_bounds, split_transcript, validate_candidates,
                          windows)
from ss_lib.setup import engine_installed
from tests.fixtures import make_media

ROOT = Path(__file__).resolve().parent.parent
NODE_ENV = {**os.environ, "PATH": f"{Path.home() / '.local' / 'bin'}:/opt/homebrew/bin:/usr/local/bin:"
            f"{os.environ.get('PATH', '')}"}


# ---------- janelas e quantidade de cortes ----------

def test_windows_long_video():
    ws = windows(30 * 60)
    assert [a for a, _ in ws] == [0, 600, 1200]
    assert all(b - a <= 720 for a, b in ws)
    assert ws[-1][1] == 1800


def test_windows_single_up_to_15_minutes():
    assert windows(15 * 60) == [(0, 900)]
    assert windows(42.5) == [(0, 42.5)]


def test_windows_folds_short_tail():
    # 15,5 min: a janela final teria 5,5 min (< 6 min) e e absorvida pela anterior
    assert windows(930) == [(0, 930)]


def test_clip_count():
    assert clip_count(600) == 5
    assert clip_count(3600) == 12
    assert clip_count(7 * 3600) == 20


def test_presets_match_supoclip_durations():
    assert {k: (v.minimum, v.maximum, v.ideal_minimum, v.ideal_maximum) for k, v in CLIP_DURATIONS.items()} == {
        "auto": (15, 60, 25, 50), "short": (15, 30, 18, 25), "medium": (30, 60, 35, 55), "long": (60, 120, 75, 110)}


def test_split_transcript_by_window():
    lines = [f"[{t:6.2f}-{t + 5:6.2f}] frase {t}" for t in range(0, 1800, 60)]
    parts = split_transcript("\n".join(lines), 1800)
    assert [(a, b) for a, b, _ in parts] == [(0, 720), (600, 1320), (1200, 1800)]
    assert parts[0][2].splitlines()[0].endswith("frase 0")
    assert parts[1][2].splitlines()[0].endswith("frase 600")
    assert parts[2][2].splitlines()[-1].endswith("frase 1740")


# ---------- validacao dos candidatos ----------

def sentence_words(total_s: float = 200, sentence_s: float = 5) -> list:
    """Uma palavra por segundo; cada frase dura sentence_s e termina em ponto."""
    words, t = [], 0.0
    per = int(sentence_s)
    while t < total_s:
        for k in range(per):
            text = "palavra." if k == per - 1 else "palavra"
            words.append({"t": text, "s": round(t + k, 2), "e": round(t + k + 0.8, 2), "p": 0.9})
        t += sentence_s
    return words


def cand(start, end, hook=15, engagement=15, value=15, shareability=15, title="t"):
    return {"start": start, "end": end, "title": title, "hook_type": "question",
            "scores": {"hook": hook, "engagement": engagement, "value": value, "shareability": shareability},
            "total": 0, "reasoning": "r"}


def test_validate_candidates_drops_and_dedupes():
    words = sentence_words()
    out = validate_candidates([
        cand(50, 100),                                   # 49,8 s: longo demais para short
        cand(10, 30, hook=20),                           # [10, 29.8], total 65
        cand(15, 35, hook=10),                           # [15, 34.8]: 75 % sobre o anterior, total menor
        cand(100, 120, hook=30, value=24),               # hook 30 -> 25
    ], words, "short")
    assert [(c["start"], c["end"]) for c in out] == [(100, 119.8), (10, 29.8)]
    assert out[0]["scores"]["hook"] == 25
    assert out[0]["total"] == 25 + 15 + 24 + 15
    assert out[1]["total"] == 65


def test_validate_candidates_snaps_to_sentences_within_tolerance():
    words = sentence_words()
    out = validate_candidates([cand(11.3, 28.1), cand(300, 320)], words, "short")
    assert [(c["start"], c["end"]) for c in out] == [(10, 29.8)]  # o segundo esta longe de qualquer frase
    assert out[0]["duration"] == pytest.approx(19.8)


def test_validate_candidates_rejects_unknown_preset():
    with pytest.raises(ValueError, match="preset"):
        validate_candidates([], [], "gigante")


def test_validate_candidates_bad_hook_type_and_missing_scores():
    out = validate_candidates([{"start": 10, "end": 30, "hook_type": "meme", "scores": {"hook": "x"}}],
                              sentence_words(), "short")
    assert out[0]["hook_type"] == "none"
    assert out[0]["scores"] == {"hook": 0, "engagement": 0, "value": 0, "shareability": 0}
    assert out[0]["total"] == 0


def test_validate_rejects_bool_overflow_and_non_finite():
    words = sentence_words()
    weird = cand(10, 30)
    weird["scores"] = {"hook": True, "engagement": float("inf"), "value": float("nan"), "shareability": 1e400}
    out = validate_candidates([weird, cand(float("nan"), 60), cand(40, float("inf")), cand(True, 70)], words, "short")
    assert len(out) == 1
    assert out[0]["scores"] == {"hook": 0, "engagement": 0, "value": 0, "shareability": 0}


def test_sentence_bounds_strip_closing_quotes_and_brackets():
    words = [{"w": w, "s": i, "e": i + 0.5} for i, w in enumerate(
        ["Ele", 'disse "pare."', "Depois", "(saiu.)", "E", "voltou.”", "Fim", "«ja?»", "ok"])]
    starts, ends = sentence_bounds(words)
    assert starts == [0, 2, 4, 6, 8]
    assert ends == [1.5, 3.5, 5.5, 7.5, 8.5]


def test_validate_reports_drop_reasons():
    words = sentence_words()
    drops = []
    out = validate_candidates([cand(10, 30, hook=20, title="bom"), cand(15, 35, title="repetido"),
                               cand(50, 100, title="longo"), cand(300, 320, title="longe"), "lixo",
                               {"start": "x", "end": 20}], words, "short", drops=drops)
    assert [c["title"] for c in out] == ["bom"]
    assert [(d["index"], d["reason"]) for d in drops] == [
        (2, "duplicate_of #1"), (3, "duration_out_of_preset"), (4, "no_boundary"), (5, "invalid"), (6, "invalid")]


@pytest.fixture
def validate_env(tmp_path, monkeypatch):
    """Pasta de trabalho + palavras num cache isolado; o cwd fica na pasta do usuario."""
    monkeypatch.setattr(paths, "CACHE", tmp_path / "cache")
    transcript = paths.work_dir("p1") / "transcript"
    transcript.mkdir(parents=True)
    (transcript / "words.json").write_text(json.dumps(sentence_words(1800)), encoding="utf-8")
    project = tmp_path / "user" / ".scroll-stopper" / "projetos" / "p1"
    project.mkdir(parents=True)
    monkeypatch.chdir(tmp_path / "user")
    return project / "candidatos.json"


def test_validate_keeps_existing_ids(validate_env, capsys):
    first = {**cand(100, 120, hook=5), "id": 7}
    validate_env.write_text(json.dumps({"preset": "short", "candidates": [
        first, cand(10, 30, hook=25), cand(15, 35), cand(200, 220, hook=20)]}), encoding="utf-8")
    assert clips.main(["validate", "p1"]) == 0
    data = json.loads(validate_env.read_text(encoding="utf-8"))
    assert [(c["start"], c["id"]) for c in data["candidates"]] == [(10, 8), (200, 9), (100, 7)]
    printed = capsys.readouterr().out
    assert "descartado" in printed and "repete" in printed
    # validar de novo nao muda os ids ja escolhidos
    assert clips.main(["validate", "p1"]) == 0
    again = json.loads(validate_env.read_text(encoding="utf-8"))
    assert [(c["start"], c["id"]) for c in again["candidates"]] == [(10, 8), (200, 9), (100, 7)]


@pytest.mark.parametrize("content", ["[]", "{}", '{"candidates": {}}'])
def test_validate_malformed_file_fails_in_portuguese(validate_env, content):
    validate_env.write_text(content, encoding="utf-8")
    with pytest.raises(SystemExit, match="candidatos.json"):
        clips.main(["validate", "p1"])


def test_load_candidates_missing_bounds_fails_clearly(tmp_path):
    project = tmp_path / ".scroll-stopper" / "projetos" / "p1"
    project.mkdir(parents=True)
    (project / "candidatos.json").write_text(json.dumps({"validated": True, "candidates": [{"id": 1, "end": 30}]}),
                                             encoding="utf-8")
    with pytest.raises(SystemExit, match="candidato 1.*start"):
        clip_render.load_candidates(tmp_path / ".scroll-stopper", "p1")


def test_relative_source_resolves_against_workspace_root(tmp_path):
    ws = tmp_path / "pasta" / ".scroll-stopper"
    ws.mkdir(parents=True)
    video = tmp_path / "pasta" / "videos" / "longo.mp4"
    video.parent.mkdir()
    video.write_bytes(b"x")
    assert clip_render.source_video({"source": "videos/longo.mp4"}, "p1", ws) == video


# ---------- palavras do corte ----------

def test_remap_words_to_cut_timeline():
    words = [{"t": "a", "s": 10.0, "e": 10.4}, {"t": "b", "s": 10.5, "e": 11.0},
             {"t": "pausa", "s": 11.6, "e": 11.7}, {"t": "c", "s": 12.3, "e": 12.8}]
    out = clip_render.remap_words(words, [[9.9, 11.15], [12.2, 13.0]])
    assert out == [{"w": "a", "s": 0.1, "e": 0.5}, {"w": "b", "s": 0.6, "e": 1.1},
                   {"w": "c", "s": 1.35, "e": 1.85}]


# ---------- blocos de legenda automaticos (helper do engine) ----------

def run_auto_chunks(tmp_path, words) -> list:
    shutil.copy(ROOT / "engine" / "src" / "lib" / "autoChunks.ts", tmp_path / "autoChunks.mts")
    script = tmp_path / "run.mjs"
    script.write_text("import {autoChunks} from './autoChunks.mts';\n"
                      f"console.log(JSON.stringify(autoChunks({json.dumps(words)})));\n", encoding="utf-8")
    proc = subprocess.run(["node", "--experimental-strip-types", "--no-warnings", str(script)], cwd=tmp_path,
                          env=NODE_ENV, capture_output=True, text=True, timeout=60)
    assert proc.returncode == 0, proc.stderr
    return [c["p"] for c in json.loads(proc.stdout)]


def ws_(text: str) -> list:
    return [{"w": w, "s": i, "e": i + 0.5} for i, w in enumerate(text.split())]


@pytest.mark.skipif(shutil.which("node", path=NODE_ENV["PATH"]) is None, reason="node indisponivel")
def test_auto_chunks_two_to_four_words_breaking_at_punctuation(tmp_path):
    chunks = run_auto_chunks(tmp_path, ws_("Oi, tudo bem? Hoje eu vou mostrar um jeito simples de cortar video."))
    assert chunks == ["Oi, tudo bem?", "Hoje eu vou mostrar", "um jeito simples de", "cortar video."]
    for text in ("Uma frase com cinco palavras.", "a b c d e f g h i", "Oi.", "Tchau, Oi."):
        sizes = [len(c.split()) for c in run_auto_chunks(tmp_path, ws_(text))]
        assert sum(sizes) == len(text.split())
        assert all(2 <= n <= 4 for n in sizes) or sizes == [1], (text, sizes)


# ---------- corte e render de um clipe ----------

requires_media = pytest.mark.skipif(not make_media.tools_available(), reason="ffmpeg/ffprobe/say indisponiveis")
requires_engine = pytest.mark.skipif(not engine_installed(paths.engine_dir(paths.plugin_version())),
                                     reason="engine nao instalado no cache; rode bin/ss setup")

SPEECH = "Este video e um teste de corte. Ele tem duas frases curtas e termina aqui."


def _probe(path: Path) -> dict:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height:format=duration",
                          "-of", "json", str(path)], capture_output=True, text=True, check=True).stdout
    return json.loads(out)


@pytest.fixture
def long_video_project(tmp_path):
    """Projeto com source.mp4 (~8 s, 1920x1080, fala do `say`), palavras e candidatos.json validados."""
    project_id = f"test-clips-{uuid.uuid4().hex[:8]}"
    media = tmp_path / "gen"
    media.mkdir()
    voice = media / "voice.aiff"
    subprocess.run(["say", "-v", make_media.VOICE, "-o", str(voice), SPEECH], check=True)
    video_dir = paths.media_dir(project_id, "video")
    video_dir.mkdir(parents=True)
    source = video_dir / "source.mp4"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "testsrc2=size=1920x1080:rate=30:duration=8",
                    "-i", str(voice), "-filter_complex", "[1:a]aresample=48000,apad[a]", "-map", "0:v", "-map", "[a]",
                    "-t", "8", "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-c:a", "aac",
                    str(source)], check=True)
    speech_s = float(_probe(voice)["format"]["duration"])
    tokens = SPEECH.split()
    step = (speech_s - 0.3) / len(tokens)
    words = [{"t": w, "s": round(0.1 + i * step, 2), "e": round(0.1 + (i + 0.85) * step, 2), "p": 0.9}
             for i, w in enumerate(tokens)]
    transcript = paths.work_dir(project_id) / "transcript"
    transcript.mkdir(parents=True)
    (transcript / "words.json").write_text(json.dumps(words), encoding="utf-8")

    ws = tmp_path / ".scroll-stopper"
    project = ws / "projetos" / project_id
    project.mkdir(parents=True)
    candidate = {**cand(0.0, words[-1]["e"]), "id": 1, "duration": words[-1]["e"]}
    (project / "candidatos.json").write_text(json.dumps({"preset": "short", "validated": True,
                                                         "candidates": [candidate]}), encoding="utf-8")
    try:
        yield ws, project_id, words
    finally:
        for pid in (project_id, f"{project_id}-c1"):
            shutil.rmtree(paths.work_dir(pid), ignore_errors=True)


@requires_media
def test_render_dinamico_cuts_and_hands_off(long_video_project, capsys):
    ws, project_id, _ = long_video_project
    outputs = clip_render.render_clips(ws, project_id, [1], style="dinamico")
    cut = paths.work_dir(f"{project_id}-c1") / "cut_1x.mp4"
    assert outputs == [cut]
    assert cut.is_file()
    printed = capsys.readouterr().out
    assert "caminho A" in printed
    assert f"ss prepare-presenter {cut} {project_id}-c1" in printed
    assert not (ws / "projetos" / project_id / "clips").exists()


@requires_media
def test_render_unknown_id_fails(long_video_project):
    ws, project_id, _ = long_video_project
    with pytest.raises(SystemExit, match="7"):
        clip_render.render_clips(ws, project_id, [7], style="simples")


@requires_media
@requires_engine
def test_render_simple_clip(long_video_project):
    ws, project_id, words = long_video_project
    started = time.monotonic()
    outputs = clip_render.render_clips(ws, project_id, [1], style="simples", scale=0.3, logo=True)
    elapsed = time.monotonic() - started
    final = ws / "projetos" / project_id / "clips" / "clip-1.mp4"
    assert outputs == [final]
    info = _probe(final)
    kinds = {s["codec_type"] for s in info["streams"]}
    assert kinds == {"video", "audio"}
    video = next(s for s in info["streams"] if s["codec_type"] == "video")
    assert (video["width"], video["height"]) == (324, 576)
    cut_duration = json.loads((paths.work_dir(f"{project_id}-c1") / "cut_segments.json").read_text())["duration"]
    assert float(info["format"]["duration"]) == pytest.approx(cut_duration, abs=0.25)
    assert abs(qa.measure_loudness(final)[0] - render.LUFS_PRESENTER) <= 0.5
    clip_words = json.loads((paths.media_dir(f"{project_id}-c1", "audio") / "SimpleClip-m.words.json").read_text())
    assert [w["w"] for w in clip_words] == [w["t"] for w in words]
    print(f"render SimpleClip-m (scale 0.3): {elapsed:.1f} s")


@requires_media
def test_render_span_without_speech_fails_early(long_video_project):
    ws, project_id, _ = long_video_project
    # a unica palavra fica depois do trecho do candidato: nada para legendar
    (paths.work_dir(project_id) / "transcript" / "words.json").write_text(
        json.dumps([{"t": "depois.", "s": 7.5, "e": 7.9, "p": 0.9}]), encoding="utf-8")
    with pytest.raises(SystemExit, match="nenhuma fala"):
        clip_render.render_clips(ws, project_id, [1], style="simples", scale=0.3)
    assert not (ws / "projetos" / project_id / "clips").exists()


def test_clips_render_accepts_ephemeral_brand_folder(validate_env, tmp_path, monkeypatch):
    folder = tmp_path / "cache" / "tmp-brands" / "efemera"
    shutil.copytree(ROOT / "templates" / "marca", folder)
    seen = {}
    monkeypatch.setattr(clip_render, "render_clips", lambda ws, pid, ids, **kw: seen.update(kw) or [])
    clips.main(["render", "p1", "--ids", "1", "--brand", str(folder)])
    assert seen["brand_dir"].resolve() == folder.resolve()


def test_clips_render_passes_dest(validate_env, tmp_path, monkeypatch):
    seen = {}
    monkeypatch.setattr(clip_render, "render_clips", lambda ws, pid, ids, **kw: seen.update(kw) or [])
    clips.main(["render", "p1", "--ids", "1", "--dest", str(tmp_path / "entrega")])
    assert Path(seen["dest"]) == tmp_path / "entrega"


def test_render_clips_delivers_to_dest(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "CACHE", tmp_path / "cache")
    ws = tmp_path / "user" / ".scroll-stopper"
    data = {"validated": True, "candidates": [{"id": 1, "start": 1.0, "end": 20.0, "title": "t"}]}
    monkeypatch.setattr(clip_render, "load_candidates", lambda w, p: data)
    monkeypatch.setattr(clip_render, "source_video", lambda d, p, w: tmp_path / "src.mp4")
    monkeypatch.setattr(clip_render, "load_words", lambda p: [{"w": "oi.", "s": 1.0, "e": 1.5}])
    monkeypatch.setattr(clip_render, "cut_clip", lambda p, n, c, s: tmp_path / "cut.mp4")
    seg = paths.work_dir("p1-c1")
    seg.mkdir(parents=True)
    (seg / "cut_segments.json").write_text(json.dumps({"segments": [[1.0, 20.0]], "duration": 19}), encoding="utf-8")
    outs = []

    def fake_simple(clip_id, cut_path, words, brand_dir, out, scale=1.0, logo=False):
        outs.append(out)
        return out, {"width": 1080, "height": 1920, "fps": 30.0, "duration": 19, "lufs": -14.0,
                     "true_peak": -1.6, "ok": True, "target_lufs": -14.0}

    monkeypatch.setattr(clip_render, "render_simple", fake_simple)
    clip_render.render_clips(ws, "p1", [1], dest=tmp_path / "entrega")
    assert outs == [tmp_path / "entrega" / "p1-clip-1.mp4"]
