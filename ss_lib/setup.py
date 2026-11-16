"""Prepara (ou confere) a maquina para rodar o Scroll Stopper.

Uso (so biblioteca padrao, roda com o python3 do sistema):
    ss setup                 cria o venv, instala dependencias, baixa o modelo, instala o engine
    ss setup --check         so verifica, nao instala nem cria nada
    ss setup --json          imprime o estado final como JSON (logs vao para stderr)

E idempotente: pode rodar de novo a qualquer momento.
"""
import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path

from ss_lib import paths

PACKAGES = ["faster-whisper", "numpy", "pillow", "yt-dlp", "pytest"]
IMPORT_NAMES = {"faster-whisper": "faster_whisper", "numpy": "numpy", "pillow": "PIL",
                "yt-dlp": "yt_dlp", "pytest": "pytest"}
WHISPER_MODEL = "mobiuslabsgmbh/faster-whisper-large-v3-turbo"
MIN_NODE_MAJOR = 18
STATUS_KEYS = ("ffmpeg", "node", "python311", "venv", "whisper_model", "yt_dlp", "engine")

_log_stream = sys.stdout


def say(message: str = "") -> None:
    print(message, file=_log_stream, flush=True)


def line(ok: bool, label: str, detail: str = "") -> None:
    say(f"{'[ok]' if ok else '[!!]'} {label:<14}" + (f" {detail}" if detail else ""))


def run(cmd, **kwargs):
    return subprocess.run(cmd, capture_output=True, text=True, **kwargs)


# ---------- verificacoes (sem efeito colateral) ----------

def ffmpeg_ok() -> bool:
    return all(shutil.which(tool) for tool in ("ffmpeg", "ffprobe"))


def node_major():
    node = shutil.which("node")
    if not node:
        return None
    match = re.match(r"v(\d+)", run([node, "--version"]).stdout.strip())
    return int(match.group(1)) if match else None


def node_ok() -> bool:
    major = node_major()
    return major is not None and major >= MIN_NODE_MAJOR


def find_python311():
    """Caminho de um Python 3.11 que roda (python3.11 no PATH ou ~/.local/bin), ou None."""
    candidates = [shutil.which("python3.11"), str(Path.home() / ".local" / "bin" / "python3.11")]
    for candidate in candidates:
        if not candidate or not os.path.exists(candidate):
            continue
        out = run([candidate, "-c", "import sys;print('%d.%d' % sys.version_info[:2])"])
        if out.returncode == 0 and out.stdout.strip() == "3.11":
            return candidate
    return None


def venv_ok() -> bool:
    return paths.venv_python().exists() and run([str(paths.venv_python()), "-c", "pass"]).returncode == 0


def missing_packages():
    """Pacotes que nao importam no venv."""
    python = str(paths.venv_python())
    return [pkg for pkg in PACKAGES if run([python, "-c", f"import {IMPORT_NAMES[pkg]}"]).returncode != 0]


def yt_dlp_ok() -> bool:
    return venv_ok() and run([str(paths.venv_python()), "-c", "import yt_dlp"]).returncode == 0


def whisper_model_ok() -> bool:
    """O modelo esta no cache local? (nao baixa nada)"""
    if not venv_ok():
        return False
    code = ("import sys\n"
            "from faster_whisper.utils import download_model\n"
            "try:\n"
            "    download_model(sys.argv[1], local_files_only=True)\n"
            "except Exception:\n"
            "    sys.exit(1)\n")
    return run([str(paths.venv_python()), "-c", code, WHISPER_MODEL]).returncode == 0


# npm ci grava este arquivo no fim; node_modules/ sem ele e instalacao interrompida
ENGINE_SENTINEL = Path("node_modules") / ".package-lock.json"
# navegador do Remotion; fica no cache para as copias por projeto ja nascerem com ele
ENGINE_BROWSER = Path("node_modules") / ".remotion" / "chrome-headless-shell"


def engine_installed(target: Path) -> bool:
    return (target / ENGINE_SENTINEL).is_file() and (target / ENGINE_BROWSER).is_dir()


def engine_ok() -> bool:
    return engine_installed(paths.engine_dir(paths.plugin_version()))


def collect_status() -> dict:
    status = {
        "ffmpeg": ffmpeg_ok(),
        "node": node_ok(),
        "python311": find_python311() is not None,
        "venv": venv_ok(),
        "whisper_model": whisper_model_ok(),
        "yt_dlp": yt_dlp_ok(),
        "engine": engine_ok(),
    }
    status["ok"] = all(status[key] for key in STATUS_KEYS)
    return status


# ---------- mensagens ----------

def install_hint(tool: str) -> str:
    if platform.system() != "Darwin":
        return "Este plugin so suporta macOS na versao 0.1."
    return {
        "ffmpeg": "Instale com: brew install ffmpeg",
        "node": f"Instale o Node {MIN_NODE_MAJOR} ou mais novo com: brew install node",
        "python311": "Instale com: brew install python@3.11",
    }[tool]


def print_report(status: dict) -> None:
    say("\n--- checklist ---")
    detail = {
        "ffmpeg": "ffmpeg e ffprobe no PATH",
        "node": f"Node {MIN_NODE_MAJOR}+" + (f" (encontrado: {node_major()})" if node_major() else ""),
        "python311": "Python 3.11 para o venv",
        "venv": str(paths.venv_dir()),
        "whisper_model": WHISPER_MODEL,
        "yt_dlp": "yt-dlp no venv",
        "engine": str(paths.engine_dir(paths.plugin_version())),
    }
    for key in STATUS_KEYS:
        line(status[key], key, detail[key])
        if not status[key]:
            if key in ("ffmpeg", "node", "python311"):
                say(f"       {install_hint(key)}")
            elif key == "engine" and not (paths.PLUGIN_ROOT / "engine").is_dir():
                say("       A pasta engine/ ainda nao existe nesta versao do plugin; a instalacao e pulada.")
            else:
                say("       Rode: ss setup")
    say("\n" + ("Tudo pronto." if status["ok"] else "Ha itens pendentes (veja os [!!] acima)."))


# ---------- instalacao ----------

def create_venv(python311: str) -> bool:
    if venv_ok():
        line(True, "venv", f"ja existe em {paths.venv_dir()}")
        return True
    say(f"Criando venv com {python311} em {paths.venv_dir()} ...")
    paths.venv_dir().parent.mkdir(parents=True, exist_ok=True)
    out = run([python311, "-m", "venv", str(paths.venv_dir())])
    if out.returncode != 0:
        line(False, "venv", f"nao foi possivel criar: {out.stderr.strip()[-300:]}")
        return False
    line(True, "venv", f"criado em {paths.venv_dir()}")
    return True


def install_packages() -> bool:
    missing = missing_packages()
    if not missing:
        line(True, "pacotes", ", ".join(PACKAGES) + " ja instalados")
        return True
    say(f"Instalando {', '.join(missing)} (pode levar alguns minutos) ...")
    proc = subprocess.run([str(paths.venv_python()), "-m", "pip", "install", "--disable-pip-version-check", *missing],
                          stdout=_log_stream, stderr=_log_stream)
    still = missing_packages()
    if proc.returncode != 0 or still:
        line(False, "pacotes", f"falhou: {', '.join(still or missing)}")
        return False
    line(True, "pacotes", "instalados")
    return True


def download_model() -> bool:
    if whisper_model_ok():
        line(True, "whisper_model", f"{WHISPER_MODEL} ja esta no cache")
        return True
    say(f"Baixando o modelo {WHISPER_MODEL} (~1,6 GB). Acontece uma vez e precisa de internet ...")
    env = {k: v for k, v in os.environ.items() if k != "HF_HUB_OFFLINE"}  # rede ligada so nesta execucao
    code = ("import sys\n"
            "from faster_whisper.utils import download_model\n"
            "print(download_model(sys.argv[1]))\n")
    proc = subprocess.run([str(paths.venv_python()), "-c", code, WHISPER_MODEL], env=env,
                          stdout=_log_stream, stderr=_log_stream)
    ok = proc.returncode == 0
    line(ok, "whisper_model", "baixado" if ok else "download falhou (confira a conexao e o espaco em disco)")
    return ok


def _link_node_modules(target: Path, deps: Path) -> None:
    """target/node_modules vira link absoluto para deps/node_modules (substitui pasta ou link antigo)."""
    link = target / "node_modules"
    if link.is_symlink() or link.is_file():
        link.unlink()
    elif link.is_dir():
        shutil.rmtree(link)  # layout antigo: dependencias dentro da pasta da versao
    link.symlink_to(deps / "node_modules", target_is_directory=True)


def remove_stale_engines(version: str) -> None:
    """Apaga as pastas de outras versoes e as dependencias que nenhuma versao restante usa."""
    engines = paths.CACHE / "engine"
    for entry in engines.iterdir():
        if entry.name != version:
            say(f"Removendo engine antigo {entry} ...")
            if entry.is_dir() and not entry.is_symlink():
                shutil.rmtree(entry)
            else:
                entry.unlink()
    used = {(entry / "node_modules").resolve().parent for entry in engines.iterdir()
            if (entry / "node_modules").is_symlink()}
    deps_root = paths.CACHE / "engine-deps"
    if deps_root.is_dir():
        for entry in deps_root.iterdir():
            if entry.resolve() not in used:
                say(f"Removendo dependencias sem uso {entry} ...")
                shutil.rmtree(entry, ignore_errors=True)


def install_deps(deps: Path, source: Path) -> bool:
    """npm ci + navegador do Remotion em deps (uma vez por package-lock.json)."""
    if engine_installed(deps):
        line(True, "engine", f"dependencias ja instaladas em {deps}")
        return True
    npm, npx = shutil.which("npm"), shutil.which("npx")
    if not (npm and npx):
        line(False, "engine", f"npm/npx nao encontrados. {install_hint('node')}")
        return False
    deps.mkdir(parents=True, exist_ok=True)
    for name in ("package.json", "package-lock.json"):
        shutil.copy2(source / name, deps / name)
    if not (deps / ENGINE_SENTINEL).is_file():
        say("Rodando npm ci (pode levar alguns minutos) ...")
        proc = subprocess.run([npm, "ci"], cwd=deps, stdout=_log_stream, stderr=_log_stream)
        if proc.returncode != 0:
            line(False, "engine", "npm ci falhou")
            return False
    if not (deps / ENGINE_BROWSER).is_dir():
        say("Baixando o navegador do Remotion (~140 MB, uma vez so) ...")
        proc = subprocess.run([npx, "--no-install", "remotion", "browser", "ensure"], cwd=deps,
                              stdout=_log_stream, stderr=_log_stream)
        if proc.returncode != 0:
            line(False, "engine", "download do navegador do Remotion falhou (confira a conexao)")
            return False
    return engine_installed(deps)


def install_engine() -> bool:
    """Espelha engine/ em CACHE/engine/<versao> e liga node_modules a CACHE/engine-deps/<hash do lock>.

    Subir a versao sem mexer no package-lock.json so copia o codigo (dezenas de KB); as dependencias
    (~1 GB) sao reaproveitadas. No fim, versoes e dependencias que ninguem usa saem do cache.
    """
    source = paths.PLUGIN_ROOT / "engine"
    if not source.is_dir():
        line(True, "engine", "pasta engine/ ausente nesta versao; instalacao pulada")
        return True
    version = paths.plugin_version()
    target = paths.engine_dir(version)
    say(f"Copiando o engine para {target} ...")
    target.mkdir(parents=True, exist_ok=True)
    # espelha o plugin: arquivo apagado do engine/ nao pode sobreviver no cache (o render usa o cache);
    # node_modules (link para as dependencias) e out ficam
    kept = {"node_modules", "out"}
    for entry in target.iterdir():
        if entry.name in kept:
            continue
        if entry.is_dir() and not entry.is_symlink():
            shutil.rmtree(entry)
        else:
            entry.unlink()
    shutil.copytree(source, target, dirs_exist_ok=True, ignore=shutil.ignore_patterns(*kept))
    deps = paths.engine_deps_dir(paths.engine_lock_hash(source))
    if not install_deps(deps, source):
        return False
    _link_node_modules(target, deps)
    ok = engine_installed(target)
    line(ok, "engine", f"instalado em {target} (dependencias em {deps})" if ok else "instalacao incompleta")
    if ok:
        remove_stale_engines(version)
    return ok


def do_setup() -> None:
    if not ffmpeg_ok():
        line(False, "ffmpeg", f"ffmpeg/ffprobe nao encontrados. {install_hint('ffmpeg')}")
    if not node_ok():
        line(False, "node", f"Node {MIN_NODE_MAJOR}+ nao encontrado. {install_hint('node')}")
    python311 = find_python311()
    if not python311:
        line(False, "python311", f"Python 3.11 nao encontrado. {install_hint('python311')}")
        return
    if not (ffmpeg_ok() and node_ok()):
        say("\nInstale o que falta (veja acima) e rode ss setup de novo.")
        return
    line(True, "python311", python311)
    if create_venv(python311) and install_packages():
        download_model()
    install_engine()


def main(argv=None) -> int:
    global _log_stream
    parser = argparse.ArgumentParser(prog="ss setup", description="Prepara ou confere o ambiente do Scroll Stopper.")
    parser.add_argument("--check", action="store_true", help="so verifica; nao instala nem cria nada")
    parser.add_argument("--json", action="store_true", help="imprime o estado final como JSON no stdout")
    args = parser.parse_args(argv)
    if args.json:
        _log_stream = sys.stderr  # stdout fica so com o JSON

    if platform.system() != "Darwin":
        say("[!!] Este plugin so suporta macOS na versao 0.1.")
    say(f"Scroll Stopper setup (versao {paths.plugin_version()}, cache {paths.CACHE})")
    if not args.check:
        do_setup()
    status = collect_status()
    print_report(status)
    if args.json:
        print(json.dumps(status))
    return 0 if status["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
