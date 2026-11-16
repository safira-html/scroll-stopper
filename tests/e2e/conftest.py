"""Infra dos testes e2e: confere pre-requisitos, roda `bin/ss` como subprocesso e limpa os work_dirs.

Os testes daqui so rodam com `pytest -m e2e` (o pyproject tira o marcador e2e do `pytest` padrao).
"""
import json
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path

import pytest

from ss_lib import paths
from tests.fixtures import make_media

ROOT = Path(__file__).resolve().parents[2]
SS = ROOT / "bin" / "ss"
STEP_TIMEOUT_S = 3600
# o render usa o engine do cache (paths.engine_dir): tudo, menos o que o setup instala ou gera, tem de ser igual
ENGINE_NOT_SYNCED = ("node_modules", "out")


def _fail_unless(ok: bool, message: str) -> None:
    if not ok:
        pytest.fail(message, pytrace=False)


@pytest.fixture(scope="session", autouse=True)
def e2e_prerequisites():
    """Falha cedo, com o que fazer, se a maquina nao esta pronta para o e2e."""
    _fail_unless(make_media.tools_available(), "e2e precisa de ffmpeg, ffprobe e say (macOS) no PATH")
    _fail_unless(paths.venv_python().is_file(), f"venv ausente em {paths.venv_dir()}: rode bin/ss setup")
    check = subprocess.run([str(SS), "setup", "--check", "--json"], capture_output=True, text=True)
    status = json.loads(check.stdout or "{}")
    _fail_unless(bool(status.get("ok")), f"ambiente incompleto ({status}): rode bin/ss setup")
    cached = paths.engine_dir(paths.plugin_version())
    excluded = [arg for name in ENGINE_NOT_SYNCED for arg in ("-x", name)]
    diff = subprocess.run(["diff", "-rq", *excluded, str(ROOT / "engine"), str(cached)], capture_output=True, text=True)
    _fail_unless(diff.returncode == 0,
                 f"engine/ do repositorio difere do engine em cache ({cached}); os renders usariam o codigo antigo. "
                 f"Rode bin/ss setup e confira de novo.\n{(diff.stdout + diff.stderr).strip()[:1500]}")


class Cli:
    """Roda `bin/ss` como as skills rodam: a partir da pasta de trabalho, com os argumentos em lista."""

    def __init__(self, cwd: Path):
        self.cwd = cwd
        self.log: list[dict] = []

    def __call__(self, *args, check: bool = True) -> subprocess.CompletedProcess:
        cmd = [str(SS), *map(str, args)]
        started = time.monotonic()
        proc = subprocess.run(cmd, cwd=self.cwd, capture_output=True, text=True, timeout=STEP_TIMEOUT_S)
        elapsed = round(time.monotonic() - started, 1)
        self.log.append({"cmd": "ss " + " ".join(map(str, args)), "seconds": elapsed, "code": proc.returncode})
        print(f"[e2e] {elapsed:7.1f}s  rc={proc.returncode}  ss {' '.join(map(str, args))}", file=sys.stderr)
        if check and proc.returncode != 0:
            raise AssertionError(f"ss {' '.join(map(str, args))} saiu com {proc.returncode}\n"
                                 f"--- stdout ---\n{proc.stdout[-3000:]}\n--- stderr ---\n{proc.stderr[-3000:]}")
        return proc


@pytest.fixture
def project_id(request):
    """Id unico por teste; apaga work_dir(<id>) e os derivados (<id>-c1, ...) no fim, passe ou falhe."""
    pid = f"e2e-{request.node.name.removeprefix('test_').replace('_', '-')}-{uuid.uuid4().hex[:6]}"
    yield pid
    for d in (paths.CACHE / "work").glob(f"{pid}*"):
        shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def workspace(tmp_path):
    """Pasta de trabalho e pasta de entrega com espacos e acentos no caminho, como numa pasta sincronizada."""
    drive = tmp_path / "Meu Drive"
    root = drive / "Projeto Vídeo"
    root.mkdir(parents=True)
    cli = Cli(root)
    cli("workspace", "init")
    return {"root": root, "ws": root / ".scroll-stopper", "dest": drive / "Vídeos finais", "cli": cli,
            "media": tmp_path / "midia"}
