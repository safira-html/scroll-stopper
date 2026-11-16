# Portions adapted from earlier MIT-licensed work. Copyright (c) 2026 Safira Mendes.
"""Ferramentas do kit de som: normaliza trilhas de fundo e apara efeitos sonoros.

Funcoes (a CLI fica em `ss kit`, ver ss_lib/kit.py):
    normalize_music(src, name, kit)  ->  kit/music/bed-<name>.mp3  (-20 LUFS, TP -2, fade-in 0,3 s, fade-out 2 s)
    trim_sfx(src, kit, name=None)    ->  kit/sfx/<name>.mp3        (apara silencio, fades curtos, pico -3 dBFS)

So ffmpeg/ffprobe e biblioteca padrao: a envoltoria de RMS vem do filtro astats, sem numpy.
"""
import re
import subprocess
import unicodedata
from pathlib import Path

from ss_lib.presenter import _run, loudnorm_two_pass, media_duration, rms_windows

__all__ = ["MUSIC_NAMES", "STANDARD_SFX", "media_duration", "normalize_music", "slugify", "trim_sfx"]

# Nomes que o engine procura (music/bed-<name>.mp3 e sfx/<name>.mp3).
MUSIC_NAMES = ("light", "dark")
STANDARD_SFX = ("whoosh-short", "whoosh-riser", "pop-soft", "bubble-pop", "ui-click", "keyboard-typing",
                "error-buzz", "success-chime", "clock-tick", "zoom-swish", "card-slide", "impact-low",
                "page-flip")

MUSIC_LUFS, MUSIC_TP, MUSIC_LRA = -20, -2, 11
MUSIC_FADE_IN_S, MUSIC_FADE_OUT_S = 0.3, 2.0
SFX_PEAK_DB = -3.0
SFX_SILENCE_DB = -50.0
SFX_WINDOW_S = 0.01      # janela do RMS
SFX_TAIL_IGNORED = 12    # ultimas 12 janelas (120 ms): estalo de borda dos geradores
SFX_PAD_BEFORE = 1       # janelas mantidas antes do primeiro som
SFX_PAD_AFTER = 6        # janelas mantidas depois do ultimo som
SFX_FADE_IN_S, SFX_FADE_OUT_MAX_S = 0.003, 0.06
SFX_SAMPLE_RATE = 44100
SFX_TAIL_MIN_FILE_S = 0.5   # so ignora a cauda em arquivos maiores que isso
SFX_PEAK_TOLERANCE_DB = 0.1
SFX_PEAK_PASSES = 5      # correcoes medidas no mp3 depois da primeira codificacao (3 nao bastavam: 6 em 120 ruidos)
MUSIC_MIN_S = 0.5


def slugify(text: str) -> str:
    """Minusculas, digitos e hifens: 'Whoosh Short (v2)' -> 'whoosh-short-v2'."""
    folded = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", folded.lower()).strip("-")


def normalize_music(src: Path, name: str, kit: Path) -> Path:
    """Trilha de fundo em -20 LUFS (duas passadas), fade-in 0,3 s e fade-out 2 s -> kit/music/bed-<name>.mp3."""
    if name not in MUSIC_NAMES:
        raise ValueError(f"music name must be one of {', '.join(MUSIC_NAMES)} (got {name!r})")
    src = Path(src).expanduser()
    if not src.is_file():
        raise SystemExit(f"[!!] arquivo nao encontrado: {src}")
    duration = media_duration(src)
    if duration < MUSIC_MIN_S:
        raise SystemExit(f"[!!] {src.name} e curto demais para ser uma trilha ({duration:.2f} s)")
    if max(rms_windows(src, 0.0, duration, 0.1), default=-120.0) <= SFX_SILENCE_DB:
        raise SystemExit(f"[!!] {src.name} e so silencio; escolha outra trilha")
    fade_out_at = max(0.0, duration - MUSIC_FADE_OUT_S)
    pre = f"afade=t=in:d={MUSIC_FADE_IN_S},afade=t=out:st={fade_out_at:.3f}:d={MUSIC_FADE_OUT_S}"
    dst = Path(kit) / "music" / f"bed-{name}.mp3"
    dst.parent.mkdir(parents=True, exist_ok=True)
    loudnorm_two_pass(src, dst, lufs=MUSIC_LUFS, tp=MUSIC_TP, lra=MUSIC_LRA, pre=pre)
    return dst


def find_active_range(rms: list) -> tuple | None:
    """(inicio_s, fim_s) do trecho com som acima de -50 dB; None se so ha silencio.

    Em arquivos com mais de 0,5 s ignora os ultimos 120 ms (estalo de borda dos geradores).
    """
    long_enough = len(rms) * SFX_WINDOW_S > SFX_TAIL_MIN_FILE_S
    body = rms[: max(1, len(rms) - SFX_TAIL_IGNORED)] if long_enough else rms
    active = [i for i, v in enumerate(body) if v > SFX_SILENCE_DB]
    if not active:
        return None
    start = max(0, active[0] - SFX_PAD_BEFORE) * SFX_WINDOW_S
    end = min(len(rms), active[-1] + SFX_PAD_AFTER) * SFX_WINDOW_S
    return start, end


def _peak_db(path: Path, label: str) -> float:
    detect = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(path), "-af", "volumedetect", "-f", "null", "-"],
                            capture_output=True, text=True).stderr
    match = re.search(r"max_volume: (-?[\d.]+) dB", detect)
    if not match:
        raise SystemExit(f"[!!] nao consegui medir o pico de {label}")
    return float(match.group(1))


def trim_sfx(src: Path, kit: Path, name: str | None = None) -> Path:
    """Apara o silencio do efeito, aplica fades de borda e normaliza o pico em -3 dBFS -> kit/sfx/<name>.mp3.

    `name` padrao: nome do arquivo de origem sem extensao, em formato slug.
    """
    src = Path(src).expanduser()
    if not src.is_file():
        raise SystemExit(f"[!!] arquivo nao encontrado: {src}")
    name = slugify(name or src.stem)
    if not name:
        raise SystemExit("[!!] nome do efeito vazio; use --name")
    found = find_active_range(rms_windows(src, 0.0, media_duration(src), SFX_WINDOW_S))
    if found is None:
        raise SystemExit(f"[!!] {src.name} e so silencio (abaixo de {SFX_SILENCE_DB:.0f} dB); nada a aproveitar")
    start, end = found
    length = end - start
    fade_out = min(SFX_FADE_OUT_MAX_S, length * 0.25)
    dst = Path(kit) / "sfx" / f"{name}.mp3"
    dst.parent.mkdir(parents=True, exist_ok=True)
    trim = (f"atrim={start:.3f}:{end:.3f},asetpts=PTS-STARTPTS,afade=t=in:d={SFX_FADE_IN_S},"
            f"afade=t=out:st={length - fade_out:.3f}:d={fade_out:.3f}")
    # aparar para um wav temporario, medir o pico e so entao aplicar o ganho e gravar o mp3
    tmp = dst.with_suffix(".trim.wav")
    attempt = dst.with_suffix(".try.mp3")
    try:
        _run(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-af", trim, str(tmp)])
        gain = SFX_PEAK_DB - _peak_db(tmp, src.name)
        best = None
        low = high = None  # maior ganho que ficou abaixo do alvo e menor que ficou acima
        # o mp3 muda o pico (ruido, sobretudo: sobe ~3 dB e oscila +-0,4 dB de um ganho para outro).
        # Codifica, mede o mp3 e corrige; quando ja ha ganhos dos dois lados do alvo, tenta o meio deles
        # (corrigir pelo erro inteiro pode ficar indo e voltando entre os mesmos dois ganhos).
        # Fica com a tentativa mais perto de -3 dBFS.
        for _ in range(1 + SFX_PEAK_PASSES):
            _run(["ffmpeg", "-y", "-v", "error", "-i", str(tmp), "-af", f"volume={gain:.2f}dB",
                  "-ar", str(SFX_SAMPLE_RATE), "-b:a", "192k", str(attempt)])
            error = SFX_PEAK_DB - _peak_db(attempt, src.name)
            if best is None or abs(error) < best:
                best = abs(error)
                attempt.replace(dst)
            if abs(error) <= SFX_PEAK_TOLERANCE_DB:
                break
            if error > 0:
                low = gain if low is None else max(low, gain)
            else:
                high = gain if high is None else min(high, gain)
            nxt = (low + high) / 2 if low is not None and high is not None else gain + error
            if round(nxt, 2) == round(gain, 2):
                break
            gain = nxt
    finally:
        tmp.unlink(missing_ok=True)
        attempt.unlink(missing_ok=True)
    return dst
