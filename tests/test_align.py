import importlib.util
import json
import shutil
import subprocess

import pytest

from ss_lib import align as align_mod
from ss_lib.align import align

requires_whisper = pytest.mark.skipif(importlib.util.find_spec("faster_whisper") is None,
                                      reason="faster_whisper ausente neste venv (use ~/.cache/scroll-stopper/venv)")


def stub(words):
    return lambda _path: [{"w": w, "s": round(0.5 * i, 2), "e": round(0.5 * i + 0.4, 2)} for i, w in enumerate(words)]


@pytest.fixture
def tone(tmp_path):
    if shutil.which("ffmpeg") is None:
        pytest.skip("ffmpeg indisponivel")
    path = tmp_path / "raw.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "sine=frequency=220:duration=2", str(path)],
                   check=True)
    return path


def test_script_spelling_wins(tone, tmp_path):
    words = align(tone, "Ad-m", "Scroll", tmp_path / "audio", transcriber=stub(["Escrol"]))
    assert words == [{"w": "Scroll", "s": 0.0, "e": 0.4}]
    assert json.loads((tmp_path / "audio" / "Ad-m.words.json").read_text()) == words
    assert (tmp_path / "audio" / "Ad-m.mp3").stat().st_size > 0


def test_missing_word_spread_in_gap(tone, tmp_path):
    heard = [{"w": "um", "s": 0.0, "e": 0.4}, {"w": "tres", "s": 2.0, "e": 2.4}]
    words = align(tone, "Ad-m", "um dois tres", tmp_path, transcriber=lambda _p: heard)
    assert [w["w"] for w in words] == ["um", "dois", "tres"]
    assert 0.4 <= words[1]["s"] < words[1]["e"] <= 2.0


def test_no_script_glues_percent(tone, tmp_path):
    words = align(tone, "Ad-m", None, tmp_path, transcriber=stub(["62", "%", "maiores"]))
    assert [w["w"] for w in words] == ["62%", "maiores"]
    assert words[0]["e"] == 0.9  # % estica o fim da palavra anterior


def test_dash_attaches_to_previous_word():
    heard = [{"w": "a", "s": 0, "e": 0.3}, {"w": "b", "s": 0.4, "e": 0.7}]
    words = align_mod.align_words(heard, "a — b")
    assert [w["w"] for w in words] == ["a —", "b"]


def test_missing_raw_exits(tmp_path):
    with pytest.raises(SystemExit):
        align(tmp_path / "nope.mp3", "k", None, tmp_path)


@requires_whisper
def test_integration_say_with_whisper(tmp_path):
    if shutil.which("say") is None or shutil.which("ffmpeg") is None:
        pytest.skip("say/ffmpeg indisponiveis")
    aiff = tmp_path / "raw.aiff"
    subprocess.run(["say", "-v", "Luciana", "-o", str(aiff), "O mercado precisa de dados"], check=True)
    out = tmp_path / "audio"
    words = align(aiff, "Demo-m", "O mercado precisa de dados.", out)
    assert [w["w"] for w in words] == ["O", "mercado", "precisa", "de", "dados."]
    assert all(a["s"] <= a["e"] for a in words)
    assert (out / "Demo-m.mp3").is_file()


def _assert_monotonic(words):
    prev = 0.0
    for w in words:
        assert w["s"] < w["e"], w
        assert w["s"] >= prev, w
        prev = w["e"]


def _h(*items):
    return [{"w": w, "s": s, "e": e} for w, s, e in items]


def test_tiny_gap_no_overlap():
    words = align_mod.align_words(_h(("b", 0.0, 0.4)), "a b")
    assert [w["w"] for w in words] == ["a", "b"]
    _assert_monotonic(words)


def test_zero_gap_no_empty_word():
    words = align_mod.align_words(_h(("x", 0.0, 0.4), ("y", 0.42, 0.8)), "x um dois tres y")
    assert [w["w"] for w in words] == ["x", "um", "dois", "tres", "y"]
    _assert_monotonic(words)


def test_gap_heavy_invariant():
    heard = _h(("c", 0.0, 0.1), ("g", 0.1, 0.2), ("k", 0.21, 0.3))
    words = align_mod.align_words(heard, "a b c d e f g h i j k l")
    assert len(words) == 12
    _assert_monotonic(words)


def test_enforce_monotonic_direct():
    from ss_lib.words import enforce_monotonic
    _assert_monotonic(enforce_monotonic(_h(("a", 0.5, 0.5), ("b", 0.4, 0.45), ("c", 0.3, 0.9))))


def test_scale_words_tiny_word():
    from ss_lib.presenter import scale_words
    words = scale_words(_h(("a", 1.0, 1.002), ("b", 1.002, 1.5)), 1.2)
    _assert_monotonic(words)


def test_replace_one_to_one():
    words = align_mod.align_words(_h(("pra", 0.0, 0.3)), "para")
    assert words == [{"w": "para", "s": 0.0, "e": 0.3}]


def test_span_many_script_words_to_one_heard():
    words = align_mod.align_words(_h(("62%", 1.0, 2.0)), "sessenta e dois por cento")
    assert [w["w"] for w in words] == ["sessenta", "e", "dois", "por", "cento"]
    assert words[0]["s"] == 1.0 and words[-1]["e"] == 2.0
    _assert_monotonic(words)


def test_missing_first_word():
    words = align_mod.align_words(_h(("mundo", 0.5, 0.9)), "olá mundo")
    assert [w["w"] for w in words] == ["olá", "mundo"]
    assert words[0]["s"] == 0.0 and words[0]["e"] <= words[1]["s"]


def test_accents_match():
    words = align_mod.align_words(_h(("voce", 0.0, 0.3), ("ve", 0.3, 0.6)), "você vê")
    assert words == [{"w": "você", "s": 0.0, "e": 0.3}, {"w": "vê", "s": 0.3, "e": 0.6}]


def test_no_script_rounds_and_drops_leading_punctuation():
    words = align_mod.align_words(_h((",", 0.0, 0.1), ("oi", 0.123456, 0.4567)), None)
    assert words == [{"w": "oi", "s": 0.12, "e": 0.46}]
