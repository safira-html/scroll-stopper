# Portions adapted from earlier MIT-licensed work. Copyright (c) 2026 Safira Mendes.
"""Corte de video gravado (caminho A, e limpeza da fonte no caminho C): so corte, sem legenda/logo/look.

Uso:
    ss cut <projetos/<id>/corte.json>

O corte.json diz o que manter (decisao editorial, lida da transcricao):
    {"source": "~/Videos/bruto.mov", "keep": [[s, e], ...], "_keep": "nota livre",
     "silence_db": -35, "max_pause": 0.45, "pad_before": 0.10, "pad_after": 0.15,
     "output_size": [1440, 2560]}
O script mede o silencio no audio para achar os pontos exatos de corte: a transcricao diz O QUE
foi falado, o silencio medido diz ONDE cortar. Saida: work_dir(<id>)/cut_1x.mp4 (velocidade 1x).
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

from ss_lib import paths

DEFAULTS = {"silence_db": -35, "max_pause": 0.45, "pad_before": 0.10, "pad_after": 0.15,
            "output_size": [1440, 2560]}
MIN_SILENCE_S = 0.18   # silencio mais curto que isso nao e pausa, e respiracao entre silabas
SNAP_REACH_S = 0.35    # borda marcada na transcricao so encosta num silencio ate essa distancia
MIN_TAKE_S = 0.3
MIN_SEGMENT_S = 0.08
FADE_S = 0.012         # fade curto em cada emenda para nao estalar
FPS = 30


def detect_silences(src: Path, noise_db: float, min_dur: float = MIN_SILENCE_S) -> list:
    proc = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", str(src), "-vn", "-af", f"silencedetect=noise={noise_db}dB:d={min_dur}",
         "-f", "null", "-"],
        capture_output=True, text=True)
    if proc.returncode != 0:
        raise SystemExit(f"[!!] ffmpeg nao conseguiu medir o silencio de {src}: {proc.stderr.strip()[-400:]}")
    out = proc.stderr
    starts = [float(x) for x in re.findall(r"silence_start: (-?[\d.]+)", out)]
    ends = [float(x) for x in re.findall(r"silence_end: (-?[\d.]+)", out)]
    return list(zip(starts, ends))


def snap_to_silence(t: float, silences: list, side: str, pad: float, reach: float = SNAP_REACH_S) -> float:
    """Borda de take marcada pela transcricao -> borda medida no silencio mais proximo.

    O Whisper erra a borda da palavra em ate ~0,2 s; cortar no tempo dele decapita a silaba.
    side="start": encosta no fim do silencio anterior; side="end": no comeco do silencio seguinte.
    """
    best = None
    for s, e in silences:
        edge = e if side == "start" else s
        if abs(edge - t) <= reach and (best is None or abs(edge - t) < abs(best - t)):
            best = edge
    if best is None:
        return t
    return best - pad if side == "start" else best + pad


def window_segments(win_start: float, win_end: float, silences: list, max_pause: float,
                    pad_before: float, pad_after: float) -> list:
    """Trechos de um take com as pausas longas encurtadas para pad_after + pad_before (~0,25 s)."""
    cuts = []
    for s, e in silences:
        if e - s > max_pause and s > win_start and e < win_end:
            a, b = s + pad_after, e - pad_before
            if b > a:
                cuts.append((a, b))
    cuts.sort()
    segs, cur = [], win_start
    for a, b in cuts:
        a, b = max(a, win_start), min(b, win_end)
        if b <= cur:
            continue
        if a > cur:
            segs.append((round(cur, 3), round(a, 3)))
        cur = max(cur, b)
    if cur < win_end:
        segs.append((round(cur, 3), round(win_end, 3)))
    return [s for s in segs if s[1] - s[0] > MIN_SEGMENT_S]


def build_segments(plan: dict, silences: list, duration: float | None = None) -> list:
    """Trechos mantidos = takes do plano com bordas no silencio medido e pausas longas encurtadas.

    duration (s) e a duracao do video de origem: take que comeca depois do fim e erro; o fim de cada
    take e limitado a ela antes de encostar no silencio (o fade de saida cai dentro do trecho real).
    """
    plan = {**DEFAULTS, **plan}
    ranges = [tuple(r) for r in plan.get("keep") or []]
    if not ranges:
        raise SystemExit("[!!] nenhum take em 'keep' no corte.json")
    clamped = []
    for a, b in ranges:
        if duration is not None:
            if a >= duration:
                raise SystemExit(f"[!!] take [{a}, {b}] comeca depois do fim do video ({duration:.2f} s): "
                                 "confira 'keep' no corte.json")
            b = min(b, duration)
        if b - a < MIN_TAKE_S:
            raise SystemExit(f"[!!] take [{a}, {b}] vazio ou curto demais: confira 'keep' no corte.json")
        clamped.append((a, b))
    segs = []
    for a, b in clamped:
        a = max(0.0, snap_to_silence(a, silences, "start", plan["pad_before"]))
        b = snap_to_silence(b, silences, "end", plan["pad_after"])
        if duration is not None:
            b = min(b, duration)
        segs += window_segments(a, b, silences, plan["max_pause"], plan["pad_before"], plan["pad_after"])
    return segs


def probe_video(src: Path) -> dict:
    """Largura/altura de exibicao (ja considerando o metadado de rotacao), rotacao em graus e duracao (s)."""
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height:stream_side_data=rotation:format=duration", "-of", "json", str(src)],
                         capture_output=True, text=True)
    if out.returncode != 0:
        raise SystemExit(f"[!!] ffprobe nao conseguiu ler {src}: {out.stderr.strip()[-200:]}")
    data = json.loads(out.stdout)
    streams = data.get("streams") or []
    if not streams:
        raise SystemExit(f"[!!] {src} nao tem faixa de video")
    info = streams[0]
    rotation = next((int(sd["rotation"]) for sd in info.get("side_data_list", []) if "rotation" in sd), 0)
    w, h = info["width"], info["height"]
    if abs(rotation) % 180 == 90:
        w, h = h, w
    try:
        duration = float(data["format"]["duration"])
    except (KeyError, TypeError, ValueError):
        raise SystemExit(f"[!!] nao foi possivel ler a duracao de {src}")
    return {"width": w, "height": h, "rotation": rotation, "duration": duration}


def output_duration(path: Path) -> float:
    proc = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                          capture_output=True, text=True)
    try:
        return float(proc.stdout.strip())
    except ValueError:
        raise SystemExit(f"[!!] ffprobe nao conseguiu ler a duracao de {path}: {proc.stderr.strip()[-200:]}")


def filter_graph(segs: list, width: int, height: int) -> str:
    parts, labels = [], ""
    for i, (a, b) in enumerate(segs):
        d = b - a
        parts.append(f"[0:v]trim={a}:{b},setpts=PTS-STARTPTS[v{i}]")
        parts.append(f"[0:a]atrim={a}:{b},asetpts=PTS-STARTPTS,afade=t=in:d={FADE_S},"
                     f"afade=t=out:st={d - FADE_S:.3f}:d={FADE_S}[a{i}]")
        labels += f"[v{i}][a{i}]"
    parts.append(f"{labels}concat=n={len(segs)}:v=1:a=1[vc][ac]")
    # preenche o quadro de saida sem esticar (corta o excesso no centro)
    parts.append(f"[vc]fps={FPS},scale={width}:{height}:force_original_aspect_ratio=increase:flags=lanczos,"
                 f"crop={width}:{height},setsar=1,format=yuv420p[v]")
    parts.append("[ac]aresample=48000[a]")
    return ";".join(parts)


def load_plan(plan_path: Path) -> dict:
    try:
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"[!!] corte.json nao encontrado: {plan_path}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"[!!] corte.json invalido ({plan_path}): {exc}")
    if not plan.get("source"):
        raise SystemExit("[!!] corte.json sem 'source' (caminho do video gravado)")
    return {**DEFAULTS, **plan}


def cut(plan_path: Path) -> Path:
    """Corta o video do corte.json; devolve work_dir(<id>)/cut_1x.mp4 (id = pasta do corte.json)."""
    plan_path = Path(plan_path).expanduser().resolve()
    plan = load_plan(plan_path)
    try:
        work = paths.work_dir(plan_path.parent.name)
    except ValueError as exc:
        raise SystemExit(f"[!!] pasta do projeto invalida: {exc}")
    src = Path(plan["source"]).expanduser()
    if not src.is_file():
        raise SystemExit(f"[!!] video de origem nao encontrado: {src}")
    width, height = (int(v) for v in plan["output_size"])

    video = probe_video(src)
    segs = build_segments(plan, detect_silences(src, plan["silence_db"]), video["duration"])
    if not segs:
        raise SystemExit("[!!] nenhum trecho mantido: confira 'keep' no corte.json")

    work.mkdir(parents=True, exist_ok=True)
    out = work / "cut_1x.mp4"
    # -autorotate (padrao do ffmpeg, explicito aqui): o decodificador aplica o metadado de rotacao do
    # celular antes dos filtros, e a saida sai em pe sem metadado de rotacao (nao gira duas vezes).
    cmd = ["ffmpeg", "-y", "-v", "error", "-autorotate", "-i", str(src),
           "-filter_complex", filter_graph(segs, width, height), "-map", "[v]", "-map", "[a]",
           "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-profile:v", "high",
           "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", str(out)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise SystemExit(f"[!!] ffmpeg falhou ao cortar: {proc.stderr.strip()[-400:]}")

    total = output_duration(out)
    (work / "cut_segments.json").write_text(json.dumps({"segments": segs, "duration": round(total, 3),
                                                        "source": str(src), "rotation": video["rotation"]},
                                                       ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[ok] {len(segs)} trechos mantidos, {total:.2f} s (origem {video['width']}x{video['height']}"
          + (f", rotacao {video['rotation']} corrigida" if video["rotation"] else "") + ")")
    for a, b in segs:
        print(f"     {a:7.2f} -> {b:7.2f}  ({b - a:.2f} s)")
    print(f"     saida: {out}")
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="ss cut", description="Corta o video gravado conforme o corte.json.")
    ap.add_argument("plan", help="caminho de projetos/<id>/corte.json")
    args = ap.parse_args(argv)
    cut(Path(args.plan))
    return 0


if __name__ == "__main__":
    sys.exit(main())
