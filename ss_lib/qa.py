"""QA de maquina de um video final: formato, duracao e loudness.

Uso:
    ss qa <video> [--lufs -15]

ok = 1080x1920, 30 fps, loudness integrado a +-0,5 LU do alvo e true peak <= -1,0 dBTP.
Sem alvo (target_lufs=None) o loudness nao pode ser conferido e ok fica False.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

WIDTH, HEIGHT, FPS = 1080, 1920, 30
LUFS_TOLERANCE = 0.5
TRUE_PEAK_MAX = -1.0


def probe(video: Path) -> dict:
    proc = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                           "stream=width,height,r_frame_rate:format=duration", "-of", "json", str(video)],
                          capture_output=True, text=True)
    try:
        data = json.loads(proc.stdout)
        stream = data["streams"][0]
        num, _, den = stream["r_frame_rate"].partition("/")
        return {"width": int(stream["width"]), "height": int(stream["height"]),
                "fps": float(num) / float(den or 1), "duration": float(data["format"]["duration"])}
    except (ValueError, KeyError, IndexError, ZeroDivisionError):
        raise SystemExit(f"[!!] ffprobe nao conseguiu ler {video}: {proc.stderr.strip()[-200:]}")


def measure_loudness(video: Path) -> tuple[float, float]:
    """(LUFS integrado, true peak dBTP) do audio, medidos pelo loudnorm do ffmpeg."""
    proc = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(video), "-vn", "-af",
                           "loudnorm=I=-15:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"],
                          capture_output=True, text=True)
    match = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", proc.stderr)
    if not match:
        raise SystemExit(f"[!!] nao consegui medir o loudness de {video} (sem audio?)")
    data = json.loads(match.group(0))
    return float(data["input_i"]), float(data["input_tp"])


def qa(video: Path, target_lufs: float | None = None) -> dict:
    video = Path(video).expanduser()
    if not video.is_file():
        raise SystemExit(f"[!!] video nao encontrado: {video}")
    info = probe(video)
    lufs, true_peak = measure_loudness(video)
    ok = (target_lufs is not None
          and (info["width"], info["height"]) == (WIDTH, HEIGHT)
          and abs(info["fps"] - FPS) < 0.01
          and abs(lufs - target_lufs) <= LUFS_TOLERANCE
          and true_peak <= TRUE_PEAK_MAX)
    return {"width": info["width"], "height": info["height"], "fps": round(info["fps"], 3),
            "duration": round(info["duration"], 3), "lufs": round(lufs, 2), "true_peak": round(true_peak, 2),
            "ok": bool(ok), "target_lufs": target_lufs}


def problems(report: dict) -> list[str]:
    """Motivos (em portugues) pelos quais um qa() deu ok=False; lista vazia quando esta tudo certo."""
    out = []
    if (report["width"], report["height"]) != (WIDTH, HEIGHT):
        out.append(f"resolucao {report['width']}x{report['height']} (esperado {WIDTH}x{HEIGHT})")
    if abs(report["fps"] - FPS) >= 0.01:
        out.append(f"{report['fps']:g} fps (esperado {FPS})")
    target = report.get("target_lufs")
    if target is None:
        out.append("sem alvo de loudness para conferir")
    elif abs(report["lufs"] - target) > LUFS_TOLERANCE:
        out.append(f"loudness {report['lufs']:g} LUFS (alvo {target:g})")
    if report["true_peak"] > TRUE_PEAK_MAX:
        out.append(f"pico {report['true_peak']:g} dBTP (maximo {TRUE_PEAK_MAX:g})")
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="ss qa", description="Confere formato e loudness do video final.")
    ap.add_argument("video")
    ap.add_argument("--lufs", type=float, default=-15.0, help="alvo de loudness (-15 motion, -14 apresentador/clipe)")
    args = ap.parse_args(argv)
    report = qa(Path(args.video), args.lufs)
    print(json.dumps(report, ensure_ascii=False))
    if report["ok"]:
        print("[ok] video dentro do padrao")
    else:
        print(f"[!!] fora do padrao (esperado {WIDTH}x{HEIGHT}, {FPS} fps, {args.lufs} LUFS +-{LUFS_TOLERANCE}, "
              f"pico <= {TRUE_PEAK_MAX} dBTP)")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
