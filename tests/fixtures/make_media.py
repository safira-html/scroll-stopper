"""Gera midia de teste neutra com ffmpeg + `say` do macOS (nunca versionada; vai para um tmp do pytest).

    speech_with_pause.mp4  "primeira frase." + 1,5 s de silencio + "segunda frase." sobre testsrc2 1080x1920
    rotated_4k.mp4         testsrc2 3840x2160 com metadado de rotacao -90 (celular gravando em pe)

Para os testes e2e (tests/e2e):
    make_presenter_takes   falso inicio + pausa + take completo (com uma pausa longa no meio) sobre testsrc2
    make_narration         narracao em mp3 (so audio)
    make_long_talk         paragrafos falados em sequencia ate passar de N segundos, com o tempo de cada um
    make_tone              tom senoidal (trilha ou efeito neutro para o kit de som)
"""
import shutil
import subprocess
from pathlib import Path

VOICE = "Luciana"
PAUSE_S = 1.5


def tools_available() -> bool:
    return all(shutil.which(tool) for tool in ("ffmpeg", "ffprobe", "say"))


def _ffmpeg(*args: str) -> None:
    subprocess.run(["ffmpeg", "-y", "-v", "error", *args], check=True)


def _say(text: str, dest: Path) -> Path:
    subprocess.run(["say", "-v", VOICE, "-o", str(dest), text], check=True)
    return dest


def make_speech_with_pause(out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    first = _say("primeira frase.", out_dir / "first.aiff")
    second = _say("segunda frase.", out_dir / "second.aiff")
    voice = out_dir / "voice.wav"
    _ffmpeg("-i", str(first), "-f", "lavfi", "-t", str(PAUSE_S), "-i", "anullsrc=r=48000:cl=mono",
            "-i", str(second), "-filter_complex",
            "[0:a]aresample=48000,aformat=channel_layouts=mono[a0];"
            "[2:a]aresample=48000,aformat=channel_layouts=mono[a2];"
            "[a0][1:a][a2]concat=n=3:v=0:a=1[a]",
            "-map", "[a]", str(voice))
    out = out_dir / "speech_with_pause.mp4"
    _ffmpeg("-f", "lavfi", "-i", "testsrc2=size=1080x1920:rate=30", "-i", str(voice),
            "-map", "0:v", "-map", "1:a", "-shortest", "-c:v", "libx264", "-preset", "ultrafast",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-ar", "48000", str(out))
    return out


def make_rotated_4k(out_dir: Path, seconds: float = 2.0) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    plain = out_dir / "landscape_4k.mp4"
    _ffmpeg("-f", "lavfi", "-i", f"testsrc2=size=3840x2160:rate=30:duration={seconds}",
            "-f", "lavfi", "-i", f"sine=frequency=440:sample_rate=48000:duration={seconds}",
            "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-shortest", str(plain))
    out = out_dir / "rotated_4k.mp4"
    _ffmpeg("-display_rotation", "-90", "-i", str(plain), "-c", "copy", str(out))
    return out


def _speech_wav(text: str, dest: Path) -> Path:
    """Fala do `say` em wav 48 kHz mono (formato comum para emendar)."""
    aiff = _say(text, dest.with_suffix(".aiff"))
    _ffmpeg("-i", str(aiff), "-ar", "48000", "-ac", "1", str(dest))
    aiff.unlink()
    return dest


def _silence_wav(seconds: float, dest: Path) -> Path:
    _ffmpeg("-f", "lavfi", "-t", str(seconds), "-i", "anullsrc=r=48000:cl=mono", str(dest))
    return dest


def _concat_wavs(parts: list, dest: Path) -> Path:
    """Emenda wavs 48 kHz mono na ordem (concat demuxer, sem reencode)."""
    listing = dest.with_suffix(".txt")
    listing.write_text("".join(f"file '{p.as_posix()}'\n" for p in parts), encoding="utf-8")
    _ffmpeg("-f", "concat", "-safe", "0", "-i", str(listing), "-c", "copy", str(dest))
    listing.unlink()
    return dest


def wav_duration(path: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                          str(path)], capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


def _over_testsrc(audio: Path, out: Path, size: str) -> Path:
    _ffmpeg("-f", "lavfi", "-i", f"testsrc2=size={size}:rate=30", "-i", str(audio),
            "-map", "0:v", "-map", "1:a", "-shortest", "-c:v", "libx264", "-preset", "ultrafast",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-ar", "48000", str(out))
    return out


def make_presenter_takes(out_dir: Path, false_start: str, first_half: str, second_half: str,
                         pause_s: float = PAUSE_S) -> tuple[Path, dict]:
    """Bruto de apresentador: falso inicio, pausa, take completo com uma pausa longa entre as duas metades.

    Devolve o video e a duracao (s) de cada parte: false_start, gap, first_half, pause, second_half.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    parts = {"false_start": _speech_wav(false_start, out_dir / "take1.wav"),
             "gap": _silence_wav(pause_s, out_dir / "gap1.wav"),
             "first_half": _speech_wav(first_half, out_dir / "take2a.wav"),
             "pause": _silence_wav(pause_s, out_dir / "gap2.wav"),
             "second_half": _speech_wav(second_half, out_dir / "take2b.wav")}
    voice = _concat_wavs(list(parts.values()), out_dir / "presenter_voice.wav")
    durations = {name: wav_duration(wav) for name, wav in parts.items()}
    return _over_testsrc(voice, out_dir / "presenter_takes.mp4", "1080x1920"), durations


def make_narration(out_dir: Path, text: str) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    wav = _speech_wav(text, out_dir / "narration.wav")
    out = out_dir / "narration.mp3"
    _ffmpeg("-i", str(wav), "-c:a", "libmp3lame", "-b:a", "192k", str(out))
    return out


def make_long_talk(out_dir: Path, paragraphs: list[str], min_seconds: float = 360.0,
                   gap_s: float = 0.8) -> tuple[Path, list[tuple[float, float]]]:
    """Fala os paragrafos em sequencia (repetindo a lista se preciso) ate passar de min_seconds.

    Devolve o video (testsrc2 720x1280) e o (inicio, fim) de cada paragrafo falado, em segundos.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    spoken = [_speech_wav(text, out_dir / f"par{i:02d}.wav") for i, text in enumerate(paragraphs)]
    gap = _silence_wav(gap_s, out_dir / "gap.wav")
    parts, spans, t, i = [], [], 0.0, 0
    while t < min_seconds:
        wav = spoken[i % len(spoken)]
        d = wav_duration(wav)
        parts += [wav, gap]
        spans.append((round(t, 3), round(t + d, 3)))
        t += d + wav_duration(gap)
        i += 1
    voice = _concat_wavs(parts, out_dir / "long_voice.wav")
    return _over_testsrc(voice, out_dir / "long_talk.mp4", "720x1280"), spans


def make_tone(out_dir: Path, name: str, seconds: float, freq: int, volume: float = 0.3) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{name}.wav"
    _ffmpeg("-f", "lavfi", "-i", f"sine=frequency={freq}:sample_rate=48000:duration={seconds}",
            "-af", f"volume={volume}", str(out))
    return out


if __name__ == "__main__":
    import sys

    target = Path(sys.argv[1] if len(sys.argv) > 1 else "fixtures-out")
    print(make_speech_with_pause(target))
    print(make_rotated_4k(target))
