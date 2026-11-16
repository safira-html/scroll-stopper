import importlib.util
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from ss_lib import paths
from ss_lib.cut import build_segments, cut, detect_silences, snap_to_silence

ROOT = Path(__file__).resolve().parent.parent
BIN = ROOT / "bin" / "ss"
requires_whisper = pytest.mark.skipif(importlib.util.find_spec("faster_whisper") is None,
                                      reason="faster_whisper ausente neste venv (use ~/.cache/scroll-stopper/venv)")


def _probe(path, entries):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", entries, "-of", "json", str(path)],
                         capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def _duration(path) -> float:
    return float(_probe(path, "format=duration")["format"]["duration"])


@pytest.fixture
def isolated_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "CACHE", tmp_path / "cache")
    return tmp_path / "cache"


def write_plan(tmp_path, project_id, source, keep, **extra) -> Path:
    plan = {"source": str(source), "keep": keep, "_keep": "teste", "silence_db": -35, "max_pause": 0.45,
            "pad_before": 0.10, "pad_after": 0.15, "output_size": [1440, 2560], **extra}
    path = tmp_path / "projetos" / project_id / "corte.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(plan), encoding="utf-8")
    return path


# ---------- helpers puros ----------

def test_snap_to_silence_moves_edges_within_reach():
    silences = [(0.0, 0.50), (2.00, 2.40)]
    assert snap_to_silence(0.60, silences, "start", 0.10) == pytest.approx(0.40)
    assert snap_to_silence(1.80, silences, "end", 0.15) == pytest.approx(2.15)
    # longe demais (> 0,35 s): fica onde esta
    assert snap_to_silence(1.20, silences, "end", 0.15) == 1.20


def test_build_segments_shortens_long_pauses_to_quarter_second():
    plan = {"keep": [[0.0, 5.0]], "max_pause": 0.45, "pad_before": 0.10, "pad_after": 0.15}
    segs = build_segments(plan, [(2.0, 3.5), (4.0, 4.3)])
    assert segs == [(0.0, 2.15), (3.4, 5.0)]
    kept_pause = (2.15 - 2.0) + (3.5 - 3.4)  # 0,15 depois da fala + 0,10 antes da proxima
    assert kept_pause == pytest.approx(0.25)


def test_build_segments_rejects_tiny_take():
    with pytest.raises(SystemExit, match="curto demais"):
        build_segments({"keep": [[1.0, 1.1]]}, [])


def test_build_segments_clamps_end_to_duration():
    plan = {"keep": [[0.0, 2.0], [3.0, 9.0]]}
    segs = build_segments(plan, [], duration=5.0)
    assert segs == [(0.0, 2.0), (3.0, 5.0)]


def test_build_segments_clamps_snapped_end_to_duration():
    # o fim encosta num silencio perto do fim do arquivo; o pad nao pode passar da duracao
    segs = build_segments({"keep": [[0.0, 4.8]]}, [(4.9, 5.0)], duration=5.0)
    assert segs[-1][1] == 5.0


def test_build_segments_rejects_take_past_the_end():
    with pytest.raises(SystemExit, match=r"take \[6.0, 8.0\] comeca depois do fim do video \(5.00 s\)"):
        build_segments({"keep": [[0.0, 2.0], [6.0, 8.0]]}, [], duration=5.0)


def test_build_segments_rejects_take_too_short_after_clamping():
    with pytest.raises(SystemExit, match="curto demais"):
        build_segments({"keep": [[4.9, 8.0]]}, [], duration=5.0)


def test_detect_silences_failure_is_clear_error(tmp_path):
    bogus = tmp_path / "not_media.mp4"
    bogus.write_text("isto nao e video")
    with pytest.raises(SystemExit, match="nao conseguiu medir o silencio"):
        detect_silences(bogus, -35)


# ---------- corte real (ffmpeg + say) ----------

def test_cut_shortens_pause(media_fixtures, tmp_path, isolated_cache):
    src = media_fixtures["speech_with_pause"]
    plan = write_plan(tmp_path, "pause", src, [[0, round(_duration(src), 3)]])
    out = cut(plan)
    assert out == paths.work_dir("pause") / "cut_1x.mp4"
    assert _duration(out) <= _duration(src) - 1.0
    streams = _probe(out, "stream=codec_name,codec_type,width,height,sample_rate,r_frame_rate")["streams"]
    video = next(s for s in streams if s["codec_type"] == "video")
    audio = next(s for s in streams if s["codec_type"] == "audio")
    assert (video["codec_name"], video["width"], video["height"], video["r_frame_rate"]) == ("h264", 1440, 2560, "30/1")
    assert (audio["codec_name"], audio["sample_rate"]) == ("aac", "48000")
    report = json.loads((paths.work_dir("pause") / "cut_segments.json").read_text(encoding="utf-8"))
    assert report["duration"] == pytest.approx(_duration(out), abs=0.001)


def test_cut_keep_past_end_is_clamped(media_fixtures, tmp_path, isolated_cache):
    src = media_fixtures["rotated_4k"]  # 2,0 s de tom continuo (sem silencio para encostar)
    plan = write_plan(tmp_path, "clamp", src, [[0.5, 30.0]])
    out = cut(plan)
    assert _duration(out) == pytest.approx(1.5, abs=0.1)
    report = json.loads((paths.work_dir("clamp") / "cut_segments.json").read_text(encoding="utf-8"))
    assert report["segments"][-1][1] <= 2.0


def test_cut_take_past_end_is_clear_error(media_fixtures, tmp_path, isolated_cache):
    plan = write_plan(tmp_path, "past", media_fixtures["rotated_4k"], [[0, 1.0], [10.0, 12.0]])
    with pytest.raises(SystemExit, match=r"take \[10.0, 12.0\] comeca depois do fim"):
        cut(plan)
    assert not (paths.work_dir("past") / "cut_1x.mp4").exists()


def test_cut_source_with_spaces_and_accents(media_fixtures, tmp_path, isolated_cache):
    folder = tmp_path / "Meu Drive" / "Formação ã"
    folder.mkdir(parents=True)
    src = folder / "gravação bruta.mp4"
    shutil.copyfile(media_fixtures["rotated_4k"], src)
    plan = write_plan(tmp_path, "accents", src, [[0, 1.0]])
    assert cut(plan).is_file()


def test_rotated_source_outputs_portrait(media_fixtures, tmp_path, isolated_cache):
    src = media_fixtures["rotated_4k"]
    plan = write_plan(tmp_path, "rotated", src, [[0, 1.5]])
    out = cut(plan)
    info = _probe(out, "stream=width,height:stream_side_data=rotation")["streams"][0]
    assert info["width"] < info["height"]
    assert not any("rotation" in sd for sd in info.get("side_data_list", []))


def test_cut_expands_home_in_source(media_fixtures, tmp_path, isolated_cache, monkeypatch):
    home = tmp_path / "home"
    (home / "videos").mkdir(parents=True)
    os.symlink(media_fixtures["rotated_4k"], home / "videos" / "raw.mp4")
    monkeypatch.setenv("HOME", str(home))
    plan = write_plan(tmp_path, "tilde", "~/videos/raw.mp4", [[0, 1.0]])
    assert cut(plan).is_file()


def test_cut_missing_source_is_clear_error(tmp_path, isolated_cache):
    plan = write_plan(tmp_path, "missing", tmp_path / "nope.mp4", [[0, 2]])
    with pytest.raises(SystemExit, match="video de origem nao encontrado"):
        cut(plan)


# ---------- transcricao (precisa do faster_whisper) ----------

@requires_whisper
def test_transcribe_writes_words(media_fixtures, tmp_path):
    from ss_lib.transcribe import transcribe

    out_dir = tmp_path / "transcript"
    words_path = transcribe(media_fixtures["speech_with_pause"], out_dir)
    assert words_path == out_dir / "words.json"
    assert (out_dir / "audio16k.wav").is_file()
    assert (out_dir / "transcript.txt").read_text(encoding="utf-8").strip()
    words = json.loads(words_path.read_text(encoding="utf-8"))
    assert words and all(set(w) == {"t", "s", "e", "p"} for w in words)
    spoken = " ".join(w["t"].lower() for w in words)
    assert "primeira" in spoken and "segunda" in spoken
    # a pausa de 1,5 s aparece entre as duas frases (VAD desligado nao a esconde)
    gaps = [b["s"] - a["e"] for a, b in zip(words, words[1:])]
    assert max(gaps) >= 1.0


# ---------- CLI ----------

def test_cli_maps_hyphenated_command_to_module(tmp_path):
    if not paths.venv_python().exists():
        pytest.skip("venv do plugin ausente; rode bin/ss setup")
    proc = subprocess.run([str(BIN), "prepare-presenter", "--help"], cwd=tmp_path, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    assert "--speed" in proc.stdout


def test_cli_rejects_unsafe_command_names(tmp_path):
    for bad in ("-x", "Cut", "../setup", "cut;ls", "a--"):
        proc = subprocess.run([str(BIN), bad], cwd=tmp_path, capture_output=True, text=True)
        assert proc.returncode == 2, bad


def test_cut_then_finalize_delivers_1080x1920_and_passes_qa(media_fixtures, tmp_path, isolated_cache):
    # caminho A "so o corte": o corte sai em 1440x2560; o finalize precisa entregar 1080x1920 e passar no QA
    from ss_lib import finalize, qa

    src = media_fixtures["speech_with_pause"]
    plan = write_plan(tmp_path, "only-cut", src, [[0, round(_duration(src), 3)]])
    cut_file = cut(plan)
    final, report = finalize.finalize_video(cut_file, tmp_path / "entrega", "so-corte")
    assert final == tmp_path / "entrega" / "so-corte.mp4"
    streams = _probe(final, "stream=codec_name,codec_type,width,height,sample_rate,r_frame_rate")["streams"]
    video = next(s for s in streams if s["codec_type"] == "video")
    audio = next(s for s in streams if s["codec_type"] == "audio")
    assert (video["codec_name"], video["width"], video["height"], video["r_frame_rate"]) == ("h264", 1080, 1920, "30/1")
    assert (audio["codec_name"], audio["sample_rate"]) == ("aac", "48000")
    assert report["ok"], qa.problems(report)
    assert not list((isolated_cache / "tmp").glob("*"))  # intermediarios apagados


ALLOWED_COMMANDS = ("setup", "workspace", "brand", "transcribe", "cut", "prepare-presenter", "kit", "align",
                    "download", "clips", "render", "draft", "finalize", "probe", "qa")


def test_cli_allows_only_documented_commands(tmp_path):
    # modulos internos (paths, engine, sound...) existem em ss_lib mas nao sao comandos
    for internal in ("paths", "engine", "sound", "words", "presenter", "clip-render", "brand-extract", "init"):
        proc = subprocess.run([str(BIN), internal], cwd=tmp_path, capture_output=True, text=True)
        assert proc.returncode == 2, internal
        assert "desconhecido" in proc.stderr, internal
    if not paths.venv_python().exists():
        pytest.skip("venv do plugin ausente; rode bin/ss setup")
    for command in ALLOWED_COMMANDS:
        proc = subprocess.run([str(BIN), command, "--help"], cwd=tmp_path, capture_output=True, text=True)
        assert proc.returncode == 0, (command, proc.stderr)
        assert command in subprocess.run([str(BIN)], capture_output=True, text=True).stderr
