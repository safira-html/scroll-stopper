"""Extrai pistas de design system (cores, fontes, variaveis CSS) de um site para o onboarding de marca.

Envolve tools/extract-site-tokens.mjs (so usa built-ins do Node, sem dependencias npm).
O extrator so le URLs http(s); para um arquivo ou pasta local, este modulo serve a pasta
em 127.0.0.1 numa porta livre durante a extracao e encerra o servidor no final.
"""
import contextlib
import functools
import json
import os
import subprocess
import threading
from urllib.parse import quote
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from ss_lib import paths

EXTRACTOR = "extract-site-tokens.mjs"


class ExtractionError(RuntimeError):
    pass


class _LocalOnlyHandler(SimpleHTTPRequestHandler):
    """Serve a pasta so para quem chama 127.0.0.1:<porta> ou localhost:<porta> (barra DNS rebinding)."""

    def _host_allowed(self) -> bool:
        port = self.server.server_address[1]
        return self.headers.get("Host", "") in (f"127.0.0.1:{port}", f"localhost:{port}")

    def send_head(self):
        if not self._host_allowed():
            self.send_error(403, "Forbidden host")
            return None
        return super().send_head()

    def log_message(self, format, *args):  # noqa: A002 - assinatura da stdlib
        pass


@contextlib.contextmanager
def serve_folder(root: Path):
    """Serve root em 127.0.0.1 numa porta livre enquanto o bloco roda; devolve a porta."""
    handler = functools.partial(_LocalOnlyHandler, directory=str(root))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)  # porta 0 = livre
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_address[1]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _node_env() -> dict:
    extra = [str(Path.home() / ".local" / "bin"), "/opt/homebrew/bin", "/usr/local/bin"]
    return {**os.environ, "PATH": os.pathsep.join(extra + [os.environ.get("PATH", "")])}


def _run_extractor(url: str) -> dict:
    script = paths.PLUGIN_ROOT / "tools" / EXTRACTOR
    try:
        proc = subprocess.run(["node", str(script), url, "--json"], capture_output=True, text=True,
                              env=_node_env(), timeout=120)
    except FileNotFoundError as exc:
        raise ExtractionError("node nao encontrado. Rode: ss setup") from exc
    except subprocess.TimeoutExpired as exc:
        raise ExtractionError(f"tempo esgotado lendo {url}") from exc
    if proc.returncode != 0:
        raise ExtractionError(proc.stderr.strip() or proc.stdout.strip() or f"extrator falhou ({proc.returncode})")
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise ExtractionError(f"o extrator devolveu uma resposta que nao e JSON ({proc.stdout[:80]!r})") from exc


def extract(source: str) -> dict:
    """source: URL http(s), arquivo .html local ou pasta com index.html."""
    if source.startswith(("http://", "https://")):
        return _run_extractor(source)
    path = Path(source.removeprefix("file://")).expanduser().resolve()
    if path.is_dir():
        root, page = path, "index.html"
    elif path.is_file():
        root, page = path.parent, path.name
    else:
        raise ExtractionError(f"origem nao encontrada: {source}")
    with serve_folder(root) as port:
        result = _run_extractor(f"http://127.0.0.1:{port}/{quote(page)}")
    result["url"] = str(path)
    return result
