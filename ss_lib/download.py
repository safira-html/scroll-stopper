"""Baixa um video por link (yt-dlp do venv do plugin), no melhor formato mp4 de ate 1080p.

Uso:
    ss download <link> <project_id>

Saida: paths.media_dir(<id>, "video")/source.mp4 (fonte do caminho C). Proximo passo: ss transcribe.
"""
import argparse
import shutil
import sys
import tempfile
from pathlib import Path

from ss_lib import paths

FAILURE_MESSAGE = ("Não consegui baixar esse link. Envie o arquivo do vídeo, ou confira se ele é público "
                   "e se você tem direito de usar esse conteúdo.")
# mp4 com video ate 1080p; junta video+audio separados quando o site entrega assim
FORMAT = ("bv*[height<=1080][ext=mp4]+ba[ext=m4a]/b[height<=1080][ext=mp4]/"
          "bv*[height<=1080]+ba/b[height<=1080]")
SOCKET_TIMEOUT_S = 20


class DownloadError(RuntimeError):
    pass


class _QuietLogger:
    """O yt-dlp escreve os proprios erros em ingles no stderr; a mensagem ao usuario e FAILURE_MESSAGE."""

    def debug(self, msg):
        pass

    info = warning = error = debug


def download(url: str, dest: Path) -> Path:
    """Baixa `url` para `dest` (.mp4). Qualquer falha vira DownloadError(FAILURE_MESSAGE)."""
    import yt_dlp

    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=dest.parent, prefix=".download-") as tmp:
        opts = {
            "format": FORMAT,
            "merge_output_format": "mp4",
            "outtmpl": str(Path(tmp) / "source.%(ext)s"),
            "noplaylist": True,
            "default_search": "error",  # texto que nao e link falha na hora, sem pesquisar na rede
            "socket_timeout": SOCKET_TIMEOUT_S,
            "retries": 1,
            "quiet": True,
            "no_warnings": True,
            "noprogress": True,
            "logger": _QuietLogger(),
        }
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])
        except Exception as exc:  # o yt-dlp levanta erros variados (DownloadError, ExtractorError, rede)
            raise DownloadError(FAILURE_MESSAGE) from exc
        got = sorted(Path(tmp).glob("source.*"))
        mp4 = [p for p in got if p.suffix == ".mp4"]
        if not mp4:
            raise DownloadError(FAILURE_MESSAGE)
        shutil.move(str(mp4[0]), dest)
    return dest


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="ss download", description="Baixa um video por link (ate 1080p, mp4).")
    ap.add_argument("url")
    ap.add_argument("project_id")
    args = ap.parse_args(argv)
    try:
        dest = paths.media_dir(args.project_id, "video") / "source.mp4"
    except ValueError as exc:
        raise SystemExit(f"[!!] id de projeto invalido: {exc}")
    try:
        out = download(args.url, dest)
    except DownloadError as exc:
        print(f"[!!] {exc}", file=sys.stderr)
        return 1
    print(f"[ok] video baixado: {out}")
    print(f"     proximo passo: ss transcribe {out} {args.project_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
