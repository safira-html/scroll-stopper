# Portions adapted from earlier MIT-licensed work. Copyright (c) 2026 Safira Mendes.
"""Transcreve um video com tempo por palavra (faster-whisper large-v3-turbo, pt).

Uso:
    ss transcribe <video> <project_id>

Escreve em work_dir(<id>)/transcript/: audio16k.wav (usado para medir silencio), words.json
([{t: palavra, s: inicio, e: fim, p: probabilidade}]) e transcript.txt (uma linha por segmento).
VAD desligado de proposito: queremos ver as pausas e as falas fora do roteiro para decidir o corte.
"""
import argparse
import functools
import json
import subprocess
import sys
from pathlib import Path

from ss_lib import paths
from ss_lib.setup import WHISPER_MODEL


@functools.lru_cache(maxsize=1)
def load_model():
    """Modelo do cache do Hugging Face (baixado pelo `ss setup`); nao acessa a rede."""
    from faster_whisper import WhisperModel

    try:
        return WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8", local_files_only=True)
    except Exception as exc:  # o faster-whisper levanta erros variados quando o modelo falta
        raise SystemExit(f"[!!] Modelo de transcricao indisponivel ({WHISPER_MODEL}). Rode: bin/ss setup\n{exc}")


def transcribe_segments(audio: Path):
    """Segmentos do Whisper (pt, tempo por palavra, VAD desligado), ja materializados em lista."""
    segs, _info = load_model().transcribe(str(audio), language="pt", word_timestamps=True, vad_filter=False,
                                          condition_on_previous_text=False)
    return list(segs)


def transcribe(src: Path, out_dir: Path) -> Path:
    """Escreve audio16k.wav, words.json e transcript.txt em out_dir; devolve o caminho do words.json."""
    src, out_dir = Path(src).expanduser(), Path(out_dir)
    if not src.is_file():
        raise SystemExit(f"[!!] video nao encontrado: {src}")
    out_dir.mkdir(parents=True, exist_ok=True)
    audio = out_dir / "audio16k.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-vn", "-ac", "1", "-ar", "16000", str(audio)],
                   check=True)
    words, lines = [], []
    for seg in transcribe_segments(audio):
        for w in seg.words:
            words.append({"t": w.word.strip(), "s": round(w.start, 3), "e": round(w.end, 3),
                          "p": round(w.probability, 2)})
        lines.append(f"[{seg.start:6.2f}-{seg.end:6.2f}] {seg.text.strip()}")
    words_path = out_dir / "words.json"
    words_path.write_text(json.dumps(words, ensure_ascii=False, indent=0), encoding="utf-8")
    (out_dir / "transcript.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return words_path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="ss transcribe", description="Transcreve um video com tempo por palavra.")
    ap.add_argument("src", help="video gravado")
    ap.add_argument("project_id", help="id do projeto (pasta em projetos/<id>)")
    args = ap.parse_args(argv)
    try:
        out_dir = paths.work_dir(args.project_id) / "transcript"
    except ValueError as exc:
        raise SystemExit(f"[!!] id de projeto invalido: {exc}")
    words_path = transcribe(Path(args.src), out_dir)
    count = len(json.loads(words_path.read_text(encoding="utf-8")))
    print(f"[ok] {count} palavras transcritas")
    print(f"     palavras:   {words_path}")
    print(f"     transcricao: {out_dir / 'transcript.txt'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
