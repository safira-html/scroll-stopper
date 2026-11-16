"""Prepara uma copia do engine Remotion para um projeto.

O engine instalado pelo `ss setup` fica em paths.engine_dir(<versao>), com node_modules como link para
paths.engine_deps_dir(<hash do lock>). Cada projeto ganha a sua copia em paths.work_dir(<id>)/engine, feita
com clone APFS (`cp -cR`, que mantem node_modules como link): rapida, sem gastar espaco, e isolada (o projeto
pode criar telas em src/ads sem mexer no cache).
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

from ss_lib import paths
from ss_lib.setup import engine_installed


class EngineNotInstalled(RuntimeError):
    pass


class RecordedBrandMissing(RuntimeError):
    """A marca gravada para o projeto nao existe mais (pasta apagada ou marca efemera limpa)."""


class BrandActivationError(RuntimeError):
    pass


def _node_env() -> dict:
    extra = [str(Path.home() / ".local" / "bin"), "/opt/homebrew/bin", "/usr/local/bin"]
    return {**os.environ, "PATH": os.pathsep.join(extra + [os.environ.get("PATH", "")])}


def _repoint_dangling_node_modules(target: Path, source: Path) -> None:
    """Link node_modules quebrado (dependencias antigas removidas pelo ss setup) passa a apontar para as atuais."""
    link = target / "node_modules"
    if link.is_symlink() and not link.exists():
        link.unlink()
        link.symlink_to((source / "node_modules").resolve(), target_is_directory=True)


def _clone(source: Path, target: Path) -> None:
    """Clone APFS (cp -c); se o volume nao suportar, copia normal."""
    target.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(["cp", "-cR", str(source), str(target)], capture_output=True, text=True)
    if proc.returncode != 0:
        print(f"[!!] clone APFS indisponivel ({proc.stderr.strip() or 'cp -c falhou'}); "
              f"fazendo copia normal do engine (mais lenta e ocupa espaco)", file=sys.stderr)
        shutil.rmtree(target, ignore_errors=True)
        shutil.copytree(source, target, symlinks=True)


KIT_KINDS = ("music", "sfx")
BRAND_RECORD = "brand-path.txt"
ENGINE_VERSION_RECORD = "engine-version.txt"
UNSTAMPED_ENGINE_VERSION = "0.1.0"  # copias feitas antes do carimbo
WORKSPACE_RECORD = "workspace-path.txt"


def _resolve_workspace(workspace: Path | None, project_id: str) -> Path | None:
    """Pasta de trabalho: a passada, a encontrada a partir do cwd ou a gravada no ultimo prepare do projeto."""
    if workspace is None:
        from ss_lib.workspace import find_workspace

        workspace = find_workspace(Path.cwd())
    if workspace is None:
        record = paths.work_dir(project_id) / WORKSPACE_RECORD
        if record.is_file():
            saved = Path(record.read_text(encoding="utf-8").strip())
            workspace = saved if saved.is_dir() else None
    return workspace


def _workspace_kit(workspace: Path | None) -> Path | None:
    """kit-de-som da pasta de trabalho resolvida, se existir."""
    if workspace is None:
        return None
    kit = Path(workspace) / "kit-de-som"
    return kit if kit.is_dir() else None


KIT_COPY_MARKER = ".from-kit"  # pasta media/<kind> que e copia do kit (refeita a cada prepare), nao midia propria


def _sync_kit(source: Path, dest: Path) -> Path:
    """Espelha os arquivos de source (kit de som) em dest: novo ou alterado e copiado, apagado sai."""
    dest.mkdir(parents=True, exist_ok=True)
    (dest / KIT_COPY_MARKER).touch()
    wanted = {f.relative_to(source) for f in source.rglob("*")
              if f.is_file() and not any(part.startswith(".") for part in f.relative_to(source).parts)}
    for rel in sorted(wanted):
        src, dst = source / rel, dest / rel
        stat = src.stat()
        if dst.is_file() and dst.stat().st_size == stat.st_size and int(dst.stat().st_mtime) == int(stat.st_mtime):
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    for f in sorted(dest.rglob("*"), reverse=True):
        rel = f.relative_to(dest)
        if f.is_file() and rel != Path(KIT_COPY_MARKER) and rel not in wanted:
            f.unlink()
        elif f.is_dir() and not any(f.iterdir()):
            f.rmdir()
    return dest


def _is_kit_copy(folder: Path) -> bool:
    return (folder / KIT_COPY_MARKER).is_file()


def _media_sources(project_id: str, media: dict, workspace: Path | None = None) -> dict:
    """kind -> pasta de origem. Sem entrada no dict, usa paths.media_dir(id, kind) se existir.

    music e sfx sem pasta propria no projeto vem do kit de som da pasta de trabalho, COPIADOS para
    paths.media_dir(id, kind) (a pasta de trabalho costuma ser sincronizada; o render nunca le dela).
    A copia e refeita a cada prepare: o que a pessoa acrescentar, trocar ou apagar no kit chega ao projeto.
    """
    unknown = sorted(set(media) - set(paths.MEDIA_KINDS))
    if unknown:
        raise ValueError(f"invalid media kind: {', '.join(unknown)} (expected one of {', '.join(paths.MEDIA_KINDS)})")
    sources = {}
    for kind in paths.MEDIA_KINDS:
        if kind in media:
            source = Path(media[kind]).expanduser().resolve()
            if not source.is_dir():
                raise ValueError(f"pasta de midia '{kind}' nao existe: {source}")
            sources[kind] = source
        elif paths.media_dir(project_id, kind).is_dir() and not _is_kit_copy(paths.media_dir(project_id, kind)):
            sources[kind] = paths.media_dir(project_id, kind)
    kit = _workspace_kit(_resolve_workspace(workspace, project_id))
    for kind in KIT_KINDS:
        if kind in sources:
            continue
        staged = paths.media_dir(project_id, kind)
        if kit is not None and (kit / kind).is_dir():
            sources[kind] = _sync_kit((kit / kind).resolve(), staged)
        elif _is_kit_copy(staged):
            sources[kind] = staged  # kit fora de alcance agora: fica a ultima copia
    return sources


def _link_media(public: Path, sources: dict) -> None:
    public.mkdir(parents=True, exist_ok=True)
    for kind in paths.MEDIA_KINDS:
        link = public / kind
        if link.is_symlink() or link.is_file():
            link.unlink()
        elif link.is_dir():
            shutil.rmtree(link)
        if kind in sources:
            link.symlink_to(sources[kind], target_is_directory=True)


def project_brand(project_id: str) -> Path | None:
    """Marca usada no ultimo prepare deste projeto (gravada em work_dir/brand-path.txt).

    None quando o projeto nunca foi preparado; RecordedBrandMissing quando a marca gravada sumiu
    (nunca cai em silencio na marca neutra).
    """
    record = paths.work_dir(project_id) / BRAND_RECORD
    if not record.is_file():
        return None
    brand = Path(record.read_text(encoding="utf-8").strip())
    if not (brand / "brand.json").is_file():
        raise RecordedBrandMissing(
            f"a marca usada neste projeto nao existe mais: {brand}. Passe --brand <slug ou pasta> para escolher outra."
        )
    return brand


def _warn_if_outdated(target: Path, stamp: Path) -> None:
    """Uma linha em stderr quando a copia do projeto veio de outra versao do plugin."""
    copied = stamp.read_text(encoding="utf-8").strip() if stamp.is_file() else UNSTAMPED_ENGINE_VERSION
    current = paths.plugin_version()
    if copied != current:
        print(f"[!!] o engine deste projeto veio da versao {copied} do plugin e a atual e {current}; para usar o novo, "
              f"apague {target} e refaca a composicao (o proximo ss brand use, ss draft ou ss render cria a copia nova)",
              file=sys.stderr)


def prepare(project_id: str, brand_dir: Path, media: dict | None = None, workspace: Path | None = None) -> Path:
    """Deixa work_dir(id)/engine pronto para renderizar com a marca de brand_dir.

    media: {kind: pasta} para kinds em paths.MEDIA_KINDS; cada pasta vira o link public/<kind>.
    workspace: pasta .scroll-stopper/ cujo kit de som e copiado para o projeto quando ele nao tem music/sfx
    proprios (padrao: a encontrada a partir do cwd). A marca usada fica gravada em work_dir/brand-path.txt.
    Chamar de novo no mesmo projeto reaproveita a copia e so atualiza marca e links.
    Devolve o caminho do engine do projeto.
    """
    media = media or {}
    source = paths.engine_dir(paths.plugin_version())
    if not engine_installed(source):
        raise EngineNotInstalled(f"engine nao instalado em {source}. Rode: ss setup")
    sources = _media_sources(project_id, media, workspace)

    target = paths.work_dir(project_id) / "engine"
    _repoint_dangling_node_modules(target, source)
    stamp = paths.work_dir(project_id) / ENGINE_VERSION_RECORD
    if not engine_installed(target):
        shutil.rmtree(target, ignore_errors=True)  # copia anterior incompleta
        _clone(source, target)
        stamp.write_text(paths.plugin_version() + "\n", encoding="utf-8")
    _warn_if_outdated(target, stamp)
    _link_media(target / "public", sources)

    brand_dir = Path(brand_dir).expanduser().resolve()
    proc = subprocess.run(["node", "scripts/use-brand.mjs", str(brand_dir)], cwd=target, env=_node_env(),
                          capture_output=True, text=True)
    if proc.returncode != 0:
        raise BrandActivationError(proc.stderr.strip() or proc.stdout.strip())
    (paths.work_dir(project_id) / BRAND_RECORD).write_text(str(brand_dir) + "\n", encoding="utf-8")
    ws = _resolve_workspace(workspace, project_id)
    if ws is not None:
        (paths.work_dir(project_id) / WORKSPACE_RECORD).write_text(str(Path(ws).resolve()) + "\n", encoding="utf-8")
    return target
