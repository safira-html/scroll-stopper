import re
import subprocess

import pytest

from ss_lib import kit, sound


def _ffmpeg(*args):
    subprocess.run(["ffmpeg", "-y", "-v", "error", *args], check=True)


def _measure(path, af):
    return subprocess.run(["ffmpeg", "-hide_banner", "-i", str(path), "-af", af, "-f", "null", "-"],
                          capture_output=True, text=True).stderr


def test_normalize_music_loudness(tmp_path):
    src = tmp_path / "raw.mp3"
    _ffmpeg("-f", "lavfi", "-i", "anoisesrc=d=10:c=pink:a=0.3:r=44100", str(src))
    kit_dir = tmp_path / "kit"
    out = sound.normalize_music(src, "light", kit_dir)
    assert out == kit_dir / "music" / "bed-light.mp3"
    err = _measure(out, "ebur128=peak=true")
    summary = err[err.rfind("Summary:"):]
    lufs = float(re.search(r"I:\s+(-?[\d.]+) LUFS", summary).group(1))
    assert lufs == pytest.approx(-20, abs=0.5)


def test_normalize_music_rejects_unknown_name(tmp_path):
    src = tmp_path / "raw.mp3"
    src.write_bytes(b"x")
    with pytest.raises(ValueError, match="light"):
        sound.normalize_music(src, "pink", tmp_path / "kit")


def test_trim_sfx_peak_and_silence(tmp_path):
    src = tmp_path / "Pop Soft.mp3"
    _ffmpeg("-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", "0.5", str(tmp_path / "a.wav"))
    _ffmpeg("-f", "lavfi", "-i", "sine=f=800:d=0.2:r=44100", "-af", "volume=0.5", str(tmp_path / "b.wav"))
    _ffmpeg("-i", str(tmp_path / "a.wav"), "-i", str(tmp_path / "b.wav"), "-i", str(tmp_path / "a.wav"),
            "-filter_complex", "[0][1][2]concat=n=3:v=0:a=1", str(src))
    out = sound.trim_sfx(src, tmp_path / "kit")
    assert out == tmp_path / "kit" / "sfx" / "pop-soft.mp3"
    dur = sound.media_duration(out)
    assert 0.1 < dur <= 0.4
    peak = float(re.search(r"max_volume: (-?[\d.]+) dB", _measure(out, "volumedetect")).group(1))
    assert peak == pytest.approx(-3, abs=0.3)


def test_trim_sfx_name_override(tmp_path):
    src = tmp_path / "x.wav"
    _ffmpeg("-f", "lavfi", "-i", "sine=f=500:d=0.3:r=44100", str(src))
    out = sound.trim_sfx(src, tmp_path / "kit", name="ui-click")
    assert out.name == "ui-click.mp3"


def test_trim_sfx_silent_source_fails(tmp_path):
    src = tmp_path / "s.wav"
    _ffmpeg("-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", "0.5", str(src))
    with pytest.raises(SystemExit, match="silencio"):
        sound.trim_sfx(src, tmp_path / "kit")


def test_slugify():
    assert sound.slugify("Whoosh Short (v2)") == "whoosh-short-v2"


def test_kit_status_lists_missing(tmp_path):
    kit_dir = tmp_path / "kit"
    (kit_dir / "sfx").mkdir(parents=True)
    (kit_dir / "music").mkdir()
    (kit_dir / "sfx" / "pop-soft.mp3").write_bytes(b"x")
    (kit_dir / "music" / "bed-dark.mp3").write_bytes(b"x")
    status = kit.kit_status(kit_dir)
    assert status["sfx"]["pop-soft"] is True
    assert status["sfx"]["whoosh-short"] is False
    assert len(status["sfx"]) == 13
    assert status["music"] == {"light": False, "dark": True}


def test_cli_requires_workspace(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(kit, "find_workspace", lambda start: None)
    assert kit.main(["status"]) == 1
    assert "ss workspace init" in capsys.readouterr().err


def test_cli_add_sfx_warns_on_nonstandard_name(tmp_path, monkeypatch, capsys):
    ws = tmp_path / ".scroll-stopper"
    (ws / "kit-de-som" / "sfx").mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    src = tmp_path / "Funky Boom.wav"
    _ffmpeg("-f", "lavfi", "-i", "sine=f=300:d=0.3:r=44100", str(src))
    assert kit.main(["add-sfx", str(src)]) == 0
    captured = capsys.readouterr()
    assert (ws / "kit-de-som" / "sfx" / "funky-boom.mp3").is_file()
    assert "funky-boom" in captured.err and "padrao" in captured.err


@pytest.mark.parametrize("args", [["--name", "!!!"], ["--name", "日本"]])
def test_cli_add_sfx_rejects_name_that_slugifies_to_empty(tmp_path, monkeypatch, capsys, args):
    ws = tmp_path / ".scroll-stopper"
    (ws / "kit-de-som" / "sfx").mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    src = tmp_path / "boom.wav"
    _ffmpeg("-f", "lavfi", "-i", "sine=f=300:d=0.3:r=44100", str(src))
    assert kit.main(["add-sfx", str(src), *args]) == 1
    assert "[!!]" in capsys.readouterr().err
    assert list((ws / "kit-de-som" / "sfx").iterdir()) == []


def test_cli_add_sfx_rejects_file_name_that_slugifies_to_empty(tmp_path, monkeypatch, capsys):
    ws = tmp_path / ".scroll-stopper"
    (ws / "kit-de-som" / "sfx").mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    src = tmp_path / "___.wav"
    _ffmpeg("-f", "lavfi", "-i", "sine=f=300:d=0.3:r=44100", str(src))
    assert kit.main(["add-sfx", str(src)]) == 1
    assert "--name" in capsys.readouterr().err
    assert list((ws / "kit-de-som" / "sfx").iterdir()) == []


def _peak(path):
    return float(re.search(r"max_volume: (-?[\d.]+) dB", _measure(path, "volumedetect")).group(1))


# sementes fixas (ruido deterministico): 17, 25 e 59 nao convergiam com a correcao antiga (-2,6 / -3,5 / -2,2 dBFS);
# 42 e 63 nao convergiam com so 3 correcoes
@pytest.mark.parametrize("seed", [17, 25, 42, 59, 63])
def test_trim_sfx_white_noise_peak_after_mp3(tmp_path, seed):
    src = tmp_path / "noise.wav"
    _ffmpeg("-f", "lavfi", "-i", f"anoisesrc=d=0.4:c=white:a=0.5:r=44100:seed={seed}", str(src))
    out = sound.trim_sfx(src, tmp_path / "kit", name="impact-low")
    assert _peak(out) == pytest.approx(-3, abs=0.3)
    assert sorted(p.name for p in (tmp_path / "kit" / "sfx").iterdir()) == ["impact-low.mp3"]  # sem temporarios


def test_trim_sfx_short_file_keeps_click_near_tail(tmp_path):
    src = tmp_path / "click.wav"
    # 110 ms no total, clique em 40-50 ms: a regra da cauda nao pode descartar tudo
    _ffmpeg("-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", "0.04", str(tmp_path / "a.wav"))
    _ffmpeg("-f", "lavfi", "-i", "sine=f=1000:d=0.01:r=44100", str(tmp_path / "b.wav"))
    _ffmpeg("-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", "0.06", str(tmp_path / "c.wav"))
    _ffmpeg("-i", str(tmp_path / "a.wav"), "-i", str(tmp_path / "b.wav"), "-i", str(tmp_path / "c.wav"),
            "-filter_complex", "[0][1][2]concat=n=3:v=0:a=1", str(src))
    out = sound.trim_sfx(src, tmp_path / "kit", name="ui-click")
    assert out.is_file()


def test_slugify_folds_accents():
    assert sound.slugify("Pop Sóft") == "pop-soft"


def test_normalize_music_rejects_short_and_silent(tmp_path):
    short = tmp_path / "short.wav"
    _ffmpeg("-f", "lavfi", "-i", "sine=f=440:d=0.2:r=44100", str(short))
    with pytest.raises(SystemExit, match="curto demais"):
        sound.normalize_music(short, "dark", tmp_path / "kit")
    silent = tmp_path / "silent.wav"
    _ffmpeg("-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", "3", str(silent))
    with pytest.raises(SystemExit, match="silencio"):
        sound.normalize_music(silent, "dark", tmp_path / "kit")


def test_normalize_music_fades_out(tmp_path):
    src = tmp_path / "raw.wav"
    _ffmpeg("-f", "lavfi", "-i", "anoisesrc=d=10:c=pink:a=0.3:r=44100", str(src))
    out = sound.normalize_music(src, "dark", tmp_path / "kit")

    def level(start, end):
        return max(sound.rms_windows(out, start, end, 0.1))

    assert level(9.5, 9.95) < level(6.9, 7.2) - 10
