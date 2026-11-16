"""Prepara um corte de apresentador (saida do `ss cut`) para o engine de motion.

Uso:
    ss prepare-presenter <cut.mp4> <project_id> [--speed auto|1.0|1.2]

Faz:
  1. mede o ritmo de fala e, com --speed auto, escolhe a velocidade que chega perto de 184 palavras/min
     (limitada a 1,0-1,3x);
  2. escreve media/video/presenter.mp4 (30 fps) nessa velocidade;
  3. escreve media/audio/<id>-m.mp3 (-16 LUFS, loudnorm em duas passadas) e media/audio/<id>-m.words.json
     ([{w, s, e}], da transcricao do corte em 1x dividida pela velocidade: uma passada so do Whisper);
     o `engine.prepare` liga media/<kind> em public/<kind> do engine;
  4. avisa o que costuma dar errado, para corrigir antes do render final:
     - palavra "esticada" (> 1,2 s): o Whisper escondeu uma retomada ou hesitacao dentro dela;
     - palavra curta longa demais (<= 3 letras, > 0,75 s): costuma esconder um "uuuu" antes da fala;
     - som dentro da pausa entre frases (RMS > -25 dB): ruido vocal a cortar.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

from ss_lib import paths
from ss_lib.words import enforce_monotonic

TARGET_WPM = 184
MIN_SPEED, MAX_SPEED = 1.0, 1.3
STRETCHED_S = 1.2
SHORT_WORD_LETTERS = 3
LONG_SHORT_S = 0.75
SENTENCE_END = (".", "?", "!")
NOISE_DB = -25
NOISE_MIN_WINDOWS = 6
NOISE_MIN_GAP_S = 0.6
RMS_WINDOW_S = 0.05
VOICE_LUFS, VOICE_TP, VOICE_LRA = -16, -1.5, 11
SAMPLE_RATE = 48000
FPS = 30


# ---------- helpers puros (testados sem audio) ----------

def pick_speed(words: int, seconds: float) -> float:
    """Velocidade que leva o ritmo de fala a ~184 palavras/min, limitada a 1,0-1,3x."""
    if words <= 0 or seconds <= 0:
        return MIN_SPEED
    wpm = words / seconds * 60
    return round(min(MAX_SPEED, max(MIN_SPEED, TARGET_WPM / wpm)), 2)


def _alert(kind: str, at: float, detail: str) -> dict:
    return {"kind": kind, "at": at, "detail": detail}


def find_stretched(words: list) -> list:
    """Palavras com mais de 1,2 s: retomada ou hesitacao escondida pelo Whisper."""
    return [_alert("STRETCHED", w["s"], f"'{w['w']}' {w['s']:.2f}-{w['e']:.2f}s: retomada ou hesitacao escondida? "
                   "retranscreva esse trecho do bruto e ajuste o corte")
            for w in words if w["e"] - w["s"] > STRETCHED_S]


def find_long_short(words: list) -> list:
    """Palavras de ate 3 letras com mais de 0,75 s (e que nao sao ja STRETCHED)."""
    out = []
    for w in words:
        d = w["e"] - w["s"]
        if len(re.sub(r"\W", "", w["w"])) <= SHORT_WORD_LETTERS and LONG_SHORT_S < d <= STRETCHED_S:
            out.append(_alert("LONG_SHORT_WORD", w["s"], f"'{w['w']}' {w['s']:.2f}-{w['e']:.2f}s: provavel ruido "
                              "vocal antes dela; escute e corte"))
    return out


def find_noise(words: list, rms_fn) -> list:
    """Som dentro da pausa entre o fim de uma frase e o comeco da proxima.

    rms_fn(start, end) -> lista de RMS em dB por janela de 50 ms. Olha do fim da frase (+0,05 s) ate o
    comeco da proxima mais 0,25 s (a borda que o Whisper erra); pausa >= 0,6 s com >= 6 janelas acima de
    -25 dB vira alerta.
    """
    out = []
    for prev, nxt in zip(words, words[1:]):
        gap = nxt["s"] - prev["e"]
        if not prev["w"].endswith(SENTENCE_END) or gap < NOISE_MIN_GAP_S:
            continue
        loud = [v for v in rms_fn(prev["e"] + 0.05, nxt["s"] + 0.25) if v > NOISE_DB]
        if len(loud) >= NOISE_MIN_WINDOWS:
            out.append(_alert("NOISE", prev["e"], f"entre '{prev['w']}' e '{nxt['w']}' ({prev['e']:.2f}-{nxt['s']:.2f}s): "
                              "escute; ruido vocal se corta, nao fica"))
    return out


# ---------- audio/video ----------

def _run(cmd: list) -> str:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise SystemExit(f"[!!] {cmd[0]} falhou: {proc.stderr.strip()[-400:]}")
    return proc.stderr


def media_duration(path: Path) -> float:
    proc = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                          capture_output=True, text=True)
    try:
        return float(proc.stdout.strip())
    except ValueError:
        raise SystemExit(f"[!!] ffprobe nao conseguiu ler a duracao de {path}: {proc.stderr.strip()[-200:]}")


def rms_windows(path: Path, start: float, end: float, win: float = RMS_WINDOW_S) -> list:
    err = subprocess.run(
        ["ffmpeg", "-hide_banner", "-ss", f"{max(0.0, start):.3f}", "-to", f"{end:.3f}", "-i", str(path), "-af",
         f"aresample={SAMPLE_RATE},asetnsamples={int(SAMPLE_RATE * win)},astats=metadata=1:reset=1,"
         "ametadata=print:key=lavfi.astats.Overall.RMS_level", "-f", "null", "-"],
        capture_output=True, text=True).stderr
    return [float(x) if x not in ("-inf", "inf", "nan") else -120.0 for x in re.findall(r"RMS_level=(\S+)", err)]


def loudnorm_two_pass(src: Path, dst: Path, lufs: float = VOICE_LUFS, tp: float = VOICE_TP,
                      lra: float = VOICE_LRA, pre: str = "") -> None:
    """Normaliza o audio de src para lufs/tp em duas passadas (mede, depois aplica linear) e grava dst.

    `pre` e uma cadeia de filtros aplicada antes do loudnorm (ex.: fades), nas duas passadas.
    """
    target = f"loudnorm=I={lufs}:TP={tp}:LRA={lra}"
    head = f"{pre}," if pre else ""
    err = _run(["ffmpeg", "-hide_banner", "-i", str(src), "-vn", "-af", f"{head}{target}:print_format=json",
                "-f", "null", "-"])
    match = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", err)
    if not match:
        raise SystemExit("[!!] loudnorm nao devolveu as medidas da primeira passada")
    m = json.loads(match.group(0))
    measured = (f":measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
                f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    _run(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-vn", "-af", head + target + measured,
          "-ar", str(SAMPLE_RATE), "-b:a", "192k", str(dst)])


def transcribe_words(path: Path) -> list:
    """[{w, s, e}] do Whisper (pt, VAD desligado), no tempo do arquivo transcrito."""
    from ss_lib.transcribe import transcribe_segments

    return [{"w": w.word.strip(), "s": round(w.start, 3), "e": round(w.end, 3)}
            for seg in transcribe_segments(path) for w in seg.words]


def scale_words(words: list, speed: float) -> list:
    """Palavras do corte em 1x -> tempo do video acelerado (s/e divididos pela velocidade)."""
    return enforce_monotonic([{"w": w["w"], "s": w["s"] / speed, "e": w["e"] / speed} for w in words])


def parse_speed(speed) -> str | float:
    if speed == "auto":
        return "auto"
    try:
        value = float(speed)
    except (TypeError, ValueError):
        raise SystemExit(f"[!!] --speed invalido: {speed!r} (use auto ou um numero, ex.: 1.2)")
    if not 0.5 <= value <= 2.0:
        raise SystemExit(f"[!!] --speed fora do intervalo 0.5-2.0: {value}")
    return value


def prepare_presenter(cut: Path, project_id: str, speed: str = "auto") -> dict:
    cut = Path(cut).expanduser()
    if not cut.is_file():
        raise SystemExit(f"[!!] corte nao encontrado: {cut}")
    try:
        video_dir, audio_dir = paths.media_dir(project_id, "video"), paths.media_dir(project_id, "audio")
    except ValueError as exc:
        raise SystemExit(f"[!!] id de projeto invalido: {exc}")
    video_dir.mkdir(parents=True, exist_ok=True)
    audio_dir.mkdir(parents=True, exist_ok=True)

    chosen = parse_speed(speed)
    # uma passada so do Whisper: transcreve o corte em 1x e deriva o tempo no video acelerado
    words_1x = transcribe_words(cut)
    if chosen == "auto":
        count, seconds = len(words_1x), media_duration(cut)
        chosen = pick_speed(count, seconds)
        wpm = count / seconds * 60 if seconds else 0
        print(f"[ok] ritmo de fala {wpm:.0f} palavras/min em 1x -> velocidade {chosen}x")

    video = video_dir / "presenter.mp4"
    vf = f"setpts=PTS/{chosen},fps={FPS}" if chosen != 1.0 else f"fps={FPS}"
    _run(["ffmpeg", "-y", "-v", "error", "-i", str(cut), "-filter_complex",
          f"[0:v]{vf}[v];[0:a]atempo={chosen},aresample={SAMPLE_RATE}[a]", "-map", "[v]", "-map", "[a]",
          "-c:v", "libx264", "-crf", "17", "-preset", "fast", "-pix_fmt", "yuv420p",
          "-c:a", "aac", "-b:a", "192k", "-ar", str(SAMPLE_RATE), "-movflags", "+faststart", str(video)])
    voice = audio_dir / f"{project_id}-m.mp3"
    loudnorm_two_pass(video, voice)

    words = scale_words(words_1x, chosen)
    (audio_dir / f"{project_id}-m.words.json").write_text(json.dumps(words, ensure_ascii=False), encoding="utf-8")
    alerts = sorted(find_stretched(words) + find_long_short(words)
                    + find_noise(words, lambda start, end: rms_windows(voice, start, end)),
                    key=lambda a: a["at"])
    return {"speed": chosen, "duration": round(media_duration(video), 3), "alerts": alerts}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="ss prepare-presenter",
                                 description="Prepara o corte do apresentador para o engine de motion.")
    ap.add_argument("cut", help="video cortado (saida do ss cut)")
    ap.add_argument("project_id", help="id do projeto")
    ap.add_argument("--speed", default="auto", help="auto (mira 184 palavras/min) ou um numero, ex.: 1.0, 1.2")
    args = ap.parse_args(argv)
    result = prepare_presenter(Path(args.cut), args.project_id, args.speed)
    print(f"[ok] presenter.mp4 a {result['speed']}x, {result['duration']:.1f} s")
    print(f"     midia em: {paths.work_dir(args.project_id) / 'media'}")
    for a in result["alerts"]:
        print(f"  {a['kind']:<15} {a['at']:7.2f}s  {a['detail']}")
    n = len(result["alerts"])
    print("[ok] nada suspeito" if not n else f"[!!] {n} ponto(s) para conferir antes do render final")
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
