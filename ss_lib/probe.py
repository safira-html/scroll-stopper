"""Descreve um arquivo de midia sem processar: duracao, se tem imagem e som, resolucao e rotacao.

Uso:
    ss probe <arquivo>      imprime um JSON (para decidir o caminho antes de qualquer trabalho)
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path


def probe(path: Path) -> dict:
    path = Path(path).expanduser()
    if not path.is_file():
        raise SystemExit(f"[!!] arquivo nao encontrado: {path}")
    try:
        proc = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                               "stream=codec_type,width,height:stream_side_data=rotation:format=duration",
                               "-of", "json", str(path)], capture_output=True, text=True)
    except FileNotFoundError:
        raise SystemExit("[!!] ffprobe nao encontrado. Rode: ss setup")
    if proc.returncode != 0:
        raise SystemExit(f"[!!] nao consegui ler {path}: {proc.stderr.strip()[-200:]}")
    data = json.loads(proc.stdout or "{}")
    streams = data.get("streams") or []
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    info = {"file": str(path), "duration": None, "video": video is not None,
            "audio": any(s.get("codec_type") == "audio" for s in streams),
            "width": None, "height": None, "rotation": 0}
    try:
        info["duration"] = round(float(data["format"]["duration"]), 3)
    except (KeyError, TypeError, ValueError):
        pass
    if video:
        rotation = next((int(sd["rotation"]) for sd in video.get("side_data_list", []) if "rotation" in sd), 0)
        w, h = video.get("width"), video.get("height")
        if w and h and abs(rotation) % 180 == 90:
            w, h = h, w  # tamanho de exibicao, ja em pe
        info.update({"width": w, "height": h, "rotation": rotation})
    return info


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="ss probe", description="Descreve um arquivo de midia (JSON).")
    ap.add_argument("file")
    args = ap.parse_args(argv)
    print(json.dumps(probe(Path(args.file)), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
