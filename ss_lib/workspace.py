"""Pasta de trabalho do usuario: marcas, kit de som e aprendizados (nunca vao para o GitHub).

Uso:
    ss workspace init             cria .scroll-stopper/ na pasta atual
    ss workspace brands           lista as marcas da pasta de trabalho
    ss workspace learn "<texto>"  anota um aprendizado em aprendizados.md

Layout (nomes em portugues de proposito, e o formato dos dados do usuario):
    .scroll-stopper/marcas/<slug>/{brand.json,BRAND.md,assets/}
    .scroll-stopper/kit-de-som/{music,sfx}/
    .scroll-stopper/aprendizados.md
    .scroll-stopper/projetos/<id>/
"""
import argparse
import json
import shutil
import sys
from datetime import date
from pathlib import Path

from ss_lib import paths

WORKSPACE_DIRNAME = ".scroll-stopper"
LEARNINGS_FILE = "aprendizados.md"
LEARNINGS_HEADER = "# Aprendizados\n\n"


def template_dir() -> Path:
    return paths.PLUGIN_ROOT / "templates" / "marca"


def _check_slug(slug: str) -> str:
    if not slug or slug.startswith(".") or "/" in slug or "\\" in slug:
        raise ValueError(f"invalid brand slug: {slug!r}")
    return slug


def find_workspace(start: Path) -> Path | None:
    """Pasta .scroll-stopper/ do ancestral mais proximo de `start` (inclusive), ou None."""
    start = Path(start).resolve()
    for folder in (start, *start.parents):
        candidate = folder / WORKSPACE_DIRNAME
        if candidate.is_dir():
            return candidate
    return None


def init_workspace(root: Path) -> Path:
    """Cria o layout em root/.scroll-stopper. Idempotente: nao sobrescreve nada existente."""
    ws = Path(root) / WORKSPACE_DIRNAME
    for sub in ("marcas", "kit-de-som/music", "kit-de-som/sfx", "projetos"):
        (ws / sub).mkdir(parents=True, exist_ok=True)
    learnings = ws / LEARNINGS_FILE
    if not learnings.exists():
        learnings.write_text(LEARNINGS_HEADER, encoding="utf-8")
    return ws


def brand_dir(ws: Path, slug: str) -> Path:
    return ws / "marcas" / _check_slug(slug)


def list_brands(ws: Path) -> list[str]:
    marcas = ws / "marcas"
    if not marcas.is_dir():
        return []
    return sorted(p.name for p in marcas.iterdir() if (p / "brand.json").is_file())


def new_brand_from_template(ws: Path | None, slug: str) -> Path:
    """Copia o template neutro (brand.json, BRAND.md, assets/) para a marca `slug`.

    Com ws=None a marca e efemera: vai para CACHE/tmp-brands/<slug> e nada e criado na pasta do usuario.
    """
    _check_slug(slug)
    target = brand_dir(ws, slug) if ws is not None else paths.CACHE / "tmp-brands" / slug
    if target.exists():
        if ws is not None:
            raise FileExistsError(f"brand already exists: {target}")
        shutil.rmtree(target)  # efemera: sempre recomeca do template
    shutil.copytree(template_dir(), target)
    brand_json = target / "brand.json"
    data = json.loads(brand_json.read_text(encoding="utf-8"))
    data["slug"] = slug
    data["name"] = slug
    brand_json.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return target


def kit_dir(ws: Path) -> Path:
    return ws / "kit-de-som"


def append_learning(ws: Path, text: str, source: str, today: str | None = None) -> None:
    """Acrescenta '- AAAA-MM-DD · <source> · <text>' (data local; `today` so para testes)."""
    entry = " ".join(text.split())  # uma linha por aprendizado
    if not entry:
        raise ValueError("aprendizado vazio")
    source = " ".join(source.split()) or "manual"
    stamp = today or date.today().isoformat()
    learnings = ws / LEARNINGS_FILE
    if not learnings.exists():
        learnings.write_text(LEARNINGS_HEADER, encoding="utf-8")
    existing = learnings.read_text(encoding="utf-8")
    prefix = "" if existing.endswith("\n") or not existing else "\n"
    with learnings.open("a", encoding="utf-8") as handle:
        handle.write(f"{prefix}- {stamp} · {source} · {entry}\n")


def read_learnings(ws: Path) -> list[str]:
    learnings = ws / LEARNINGS_FILE
    if not learnings.exists():
        return []
    return [ln for ln in learnings.read_text(encoding="utf-8").splitlines() if ln.startswith("- ")]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="ss workspace", description="Pasta de trabalho do Scroll Stopper.")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init", help="cria .scroll-stopper/ na pasta atual")
    sub.add_parser("brands", help="lista as marcas")
    learn = sub.add_parser("learn", help="anota um aprendizado")
    learn.add_argument("text")
    learn.add_argument("--source", default="manual")
    args = parser.parse_args(argv)

    if args.command == "init":
        ws = init_workspace(Path.cwd())
        print(f"[ok] Pasta de trabalho pronta em {ws}")
        return 0

    ws = find_workspace(Path.cwd())
    if ws is None:
        print("[!!] Nenhuma pasta de trabalho encontrada. Rode `ss workspace init` na pasta do projeto.",
              file=sys.stderr)
        return 1
    if args.command == "brands":
        brands = list_brands(ws)
        if not brands:
            print("(nenhuma marca ainda)")
        for slug in brands:
            print(slug)
        return 0
    append_learning(ws, args.text, args.source)
    print("[ok] Aprendizado anotado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
