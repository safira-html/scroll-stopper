"""Entrega um video pronto (por exemplo, so o corte do `ss cut`) com o volume normalizado.

Uso:
    ss finalize <video> --dest <pasta> --name <nome> [--lufs -14]

Se o video nao estiver em 1080x1920 a 30 fps (o `ss cut` entrega 1440x2560), primeiro converte para
1080x1920/30 fps (preenche e corta o centro, lanczos, H.264 crf 18, audio copiado).
Normaliza o audio em duas passadas (TP -1,5 dBTP; refaz com -2,5 se o pico passar de -1,0), confere com o QA
e copia so o .mp4 final para a pasta de entrega, sem sobrescrever. O intermediario fica no cache.
"""
import argparse
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

from ss_lib import paths, qa as qa_mod
from ss_lib.render import LUFS_PRESENTER, deliver, finalize_checked, report_line


CONFORM_FILTER = (f"scale={qa_mod.WIDTH}:{qa_mod.HEIGHT}:force_original_aspect_ratio=increase:flags=lanczos,"
                  f"crop={qa_mod.WIDTH}:{qa_mod.HEIGHT},fps={qa_mod.FPS}")


def conform(src: Path, work: Path) -> Path:
    """Devolve src se ja estiver em 1080x1920 a 30 fps; senao converte para work/conformed.mp4."""
    info = qa_mod.probe(src)
    if (info["width"], info["height"]) == (qa_mod.WIDTH, qa_mod.HEIGHT) and abs(info["fps"] - qa_mod.FPS) < 0.01:
        return src
    out = work / "conformed.mp4"
    proc = subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-map", "0:v:0", "-map", "0:a?",
                           "-vf", CONFORM_FILTER, "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                           "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart", str(out)],
                          capture_output=True, text=True)
    if proc.returncode != 0:
        raise SystemExit(f"[!!] ffmpeg falhou ao converter para {qa_mod.WIDTH}x{qa_mod.HEIGHT}: "
                         f"{proc.stderr.strip()[-400:]}")
    return out


def finalize_video(src: Path, dest_dir: Path, name: str, lufs: float = LUFS_PRESENTER) -> tuple[Path, dict]:
    src = Path(src).expanduser()
    if not src.is_file():
        raise SystemExit(f"[!!] video nao encontrado: {src}")
    if not name or "/" in name or "\\" in name or name.startswith("."):
        raise SystemExit(f"[!!] nome de arquivo invalido: {name!r}")
    name = name[:-4] if name.lower().endswith(".mp4") else name
    dest_dir = Path(dest_dir).expanduser()
    if not dest_dir.parent.is_dir():
        raise SystemExit(f"[!!] a pasta {dest_dir.parent} nao existe; crie-a ou escolha outro destino")
    work = paths.CACHE / "tmp" / f"finalize-{uuid.uuid4().hex[:8]}"
    work.mkdir(parents=True, exist_ok=True)
    try:
        normalized = work / f"{name}.mp4"
        report = finalize_checked(conform(src, work), normalized, lufs)
        dest_dir.mkdir(exist_ok=True)
        return deliver(normalized, dest_dir, name), report
    finally:
        shutil.rmtree(work, ignore_errors=True)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="ss finalize", description="Normaliza o volume e entrega um video pronto.")
    ap.add_argument("video")
    ap.add_argument("--dest", required=True, help="pasta onde o .mp4 final sera salvo")
    ap.add_argument("--name", required=True, help="nome do arquivo (sem .mp4)")
    ap.add_argument("--lufs", type=float, default=LUFS_PRESENTER, help="alvo de loudness (padrao: -14)")
    args = ap.parse_args(argv)
    final, report = finalize_video(Path(args.video), Path(args.dest), args.name, args.lufs)
    print(report_line(report, final, f"video final ({args.lufs:g} LUFS)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
