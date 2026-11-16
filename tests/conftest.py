import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
# Este arquivo e o teste de manifests citam as palavras proibidas; ficam fora da varredura.
SELF_EXCLUDED = {"tests/test_manifests.py", "tests/conftest.py"}


def _is_text(path: Path) -> bool:
    try:
        return b"\0" not in path.read_bytes()[:8192]
    except OSError:
        return False


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return ROOT


def git_tracked_text_files() -> list[Path]:
    out = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT, capture_output=True, check=True,
    ).stdout.decode("utf-8")
    files = []
    for rel in filter(None, out.split("\0")):
        if rel in SELF_EXCLUDED or rel.startswith("docs/superpowers/"):
            continue
        path = ROOT / rel
        if path.is_file() and _is_text(path):
            files.append(path)
    return files


@pytest.fixture(scope="session")
def media_fixtures(tmp_path_factory) -> dict:
    """Midia neutra gerada uma vez por sessao (ffmpeg + say), fora do repositorio."""
    from tests.fixtures import make_media

    if not make_media.tools_available():
        pytest.skip("ffmpeg/ffprobe/say indisponiveis: nao da para gerar a midia de teste")
    out = tmp_path_factory.mktemp("media")
    return {"speech_with_pause": make_media.make_speech_with_pause(out),
            "rotated_4k": make_media.make_rotated_4k(out)}
