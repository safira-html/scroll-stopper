"""Caminhos compartilhados do plugin. Todo trabalho pesado fica em ~/.cache/scroll-stopper."""
import hashlib
import json
import re
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
CACHE = Path.home() / ".cache" / "scroll-stopper"
MEDIA_KINDS = ("video", "audio", "music", "sfx", "stock")
PROJECT_ID = re.compile(r"[a-z0-9][a-z0-9-]*")  # vira nome de pasta e de composicao do Remotion


def plugin_version() -> str:
    """Versao lida de .claude-plugin/plugin.json (define CACHE/engine/<versao>/)."""
    manifest = PLUGIN_ROOT / ".claude-plugin" / "plugin.json"
    return json.loads(manifest.read_text(encoding="utf-8"))["version"]


def venv_dir() -> Path:
    return CACHE / "venv"


def venv_python() -> Path:
    return venv_dir() / "bin" / "python"


def engine_dir(version: str) -> Path:
    """Codigo do engine desta versao (src, scripts...); node_modules e um link para engine_deps_dir."""
    return CACHE / "engine" / version


def engine_lock_hash(engine_src: Path) -> str:
    """16 primeiros hex do sha256 do package-lock.json do engine: identifica as dependencias instaladas."""
    return hashlib.sha256((Path(engine_src) / "package-lock.json").read_bytes()).hexdigest()[:16]


def engine_deps_dir(lock_hash: str) -> Path:
    """Dependencias do engine (node_modules + navegador do Remotion), compartilhadas por versoes com o mesmo lock."""
    return CACHE / "engine-deps" / lock_hash


def work_dir(project_id: str) -> Path:
    """Pasta de trabalho de um projeto: CACHE/work/<id>. Nao cria nada em disco."""
    if not isinstance(project_id, str) or not PROJECT_ID.fullmatch(project_id):
        raise ValueError(f"invalid project id: {project_id!r} (use lowercase letters, digits and hyphens, "
                         f"starting with a letter or digit, e.g. video-01)")
    return CACHE / "work" / project_id


def media_dir(project_id: str, kind: str) -> Path:
    """Staging de midia de um projeto: work_dir(id)/media/<kind>, kind em MEDIA_KINDS.

    Nao cria o diretorio; quem escreve nele faz mkdir(parents=True, exist_ok=True).
    """
    if kind not in MEDIA_KINDS:
        raise ValueError(f"invalid media kind: {kind!r} (expected one of {', '.join(MEDIA_KINDS)})")
    return work_dir(project_id) / "media" / kind
