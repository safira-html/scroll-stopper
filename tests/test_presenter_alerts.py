import importlib.util
import json
import re
import subprocess

import pytest

from ss_lib import paths
from ss_lib.presenter import find_long_short, find_noise, find_stretched, pick_speed

requires_whisper = pytest.mark.skipif(importlib.util.find_spec("faster_whisper") is None,
                                      reason="faster_whisper ausente neste venv (use ~/.cache/scroll-stopper/venv)")


def test_pick_speed():
    assert pick_speed(158, 60) == 1.16
    assert pick_speed(200, 60) == 1.0
    assert pick_speed(100, 60) == 1.3


def test_pick_speed_without_words_keeps_1x():
    assert pick_speed(0, 60) == 1.0
    assert pick_speed(10, 0) == 1.0


WORDS = [{"w": "da", "s": 33.8, "e": 36.18}, {"w": "E", "s": 57.36, "e": 58.2}, {"w": "62", "s": 45.5, "e": 46.14}]


def test_find_stretched_and_long_short():
    stretched = find_stretched(WORDS)
    long_short = find_long_short(WORDS)
    assert [a["kind"] for a in stretched] == ["STRETCHED"]
    assert [a["at"] for a in stretched] == [33.8]
    assert "'da'" in stretched[0]["detail"]
    # "da" ja e STRETCHED; "62" tem 0,64 s e nao entra
    assert [a["kind"] for a in long_short] == ["LONG_SHORT_WORD"]
    assert [a["at"] for a in long_short] == [57.36]
    assert "'E'" in long_short[0]["detail"]


def test_find_noise():
    words = [{"w": "portfólio.", "s": 29.3, "e": 29.92}, {"w": "E", "s": 30.86, "e": 31.0}]
    calls = []

    def rms_fn(start, end):
        calls.append((start, end))
        return [-60.0] * 4 + [-18.0] * 8 + [-60.0] * 6

    alerts = find_noise(words, rms_fn)
    assert [(a["kind"], a["at"]) for a in alerts] == [("NOISE", 29.92)]
    assert calls == [(pytest.approx(29.97), pytest.approx(31.11))]


def test_find_noise_ignores_quiet_short_or_mid_sentence_gaps():
    loud = lambda start, end: [-18.0] * 10  # noqa: E731
    quiet = lambda start, end: [-40.0] * 10  # noqa: E731
    sentence_gap = [{"w": "fim.", "s": 1.0, "e": 2.0}, {"w": "Depois", "s": 3.0, "e": 3.4}]
    short_gap = [{"w": "fim.", "s": 1.0, "e": 2.0}, {"w": "Depois", "s": 2.3, "e": 2.6}]
    mid_sentence = [{"w": "meio", "s": 1.0, "e": 2.0}, {"w": "depois", "s": 3.0, "e": 3.4}]
    assert find_noise(sentence_gap, quiet) == []
    assert find_noise(short_gap, loud) == []
    assert find_noise(mid_sentence, loud) == []


def _probe(path, entries):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", entries, "-of", "json", str(path)],
                         capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def _integrated_lufs(path):
    err = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(path), "-af", "ebur128", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", err)[-1])


def test_prepare_presenter_auto_speed_transcribes_once(media_fixtures, tmp_path, monkeypatch):
    from ss_lib import presenter

    monkeypatch.setattr(paths, "CACHE", tmp_path / "cache")
    src = media_fixtures["speech_with_pause"]
    fake = [{"w": "primeira", "s": 0.2, "e": 0.6}, {"w": "frase.", "s": 0.6, "e": 1.0},
            {"w": "segunda", "s": 2.6, "e": 3.0}, {"w": "frase.", "s": 3.0, "e": 3.4}]
    calls = []

    def fake_transcribe(path):
        calls.append(path)
        return fake

    monkeypatch.setattr(presenter, "transcribe_words", fake_transcribe)
    result = presenter.prepare_presenter(src, "auto", speed="auto")

    # 4 palavras em ~3,7 s = ~65 palavras/min -> limite de 1,3x
    assert result["speed"] == 1.3
    assert calls == [src]
    words = json.loads((paths.media_dir("auto", "audio") / "auto-m.words.json").read_text(encoding="utf-8"))
    assert words == [{"w": w["w"], "s": round(w["s"] / 1.3, 2), "e": round(w["e"] / 1.3, 2)} for w in fake]
    assert result["duration"] == pytest.approx(float(_probe(src, "format=duration")["format"]["duration"]) / 1.3,
                                               abs=0.15)


def test_media_duration_failure_is_clear_error(tmp_path):
    from ss_lib.presenter import media_duration

    bogus = tmp_path / "not_media.mp4"
    bogus.write_text("isto nao e video")
    with pytest.raises(SystemExit, match="nao conseguiu ler a duracao"):
        media_duration(bogus)


@requires_whisper
def test_prepare_presenter_stages_media(media_fixtures, tmp_path, monkeypatch):
    from ss_lib.presenter import prepare_presenter

    monkeypatch.setattr(paths, "CACHE", tmp_path / "cache")
    src = media_fixtures["speech_with_pause"]
    result = prepare_presenter(src, "demo", speed="1.2")

    assert result["speed"] == 1.2
    src_duration = float(_probe(src, "format=duration")["format"]["duration"])
    assert result["duration"] == pytest.approx(src_duration / 1.2, abs=0.15)
    assert isinstance(result["alerts"], list)

    video = paths.media_dir("demo", "video") / "presenter.mp4"
    voice = paths.media_dir("demo", "audio") / "demo-m.mp3"
    words_path = paths.media_dir("demo", "audio") / "demo-m.words.json"
    assert video.is_file() and voice.is_file() and words_path.is_file()
    stream = _probe(video, "stream=codec_type,r_frame_rate")["streams"]
    assert {"codec_type": "video", "r_frame_rate": "30/1"} in stream
    assert _integrated_lufs(voice) == pytest.approx(-16, abs=1.0)
    words = json.loads(words_path.read_text(encoding="utf-8"))
    assert words and all(set(w) == {"w", "s", "e"} for w in words)
    spoken = " ".join(w["w"].lower() for w in words)
    assert "primeira" in spoken and "segunda" in spoken
