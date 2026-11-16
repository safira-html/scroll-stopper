"""Onboarding de marca.

Uso:
    ss brand extract <url|arquivo|pasta>      imprime JSON com cores, fontes e variaveis CSS do site
    ss brand new <slug> [--ephemeral]         cria a marca a partir do modelo neutro e imprime a pasta dela
    ss brand use <slug|pasta> --project <id>  ativa a marca no engine do projeto e imprime a pasta do engine
"""
import argparse
import json
import sys
from pathlib import Path

from ss_lib import brand_extract, engine, workspace


class BrandNotFound(LookupError):
    pass


def resolve_brand(ref: str, cwd: Path | None = None) -> Path:
    """Pasta com brand.json: caminho existente ou slug da pasta de trabalho."""
    candidate = Path(ref).expanduser()
    if candidate.is_dir() and (candidate / "brand.json").is_file():
        return candidate.resolve()
    ws = workspace.find_workspace(cwd or Path.cwd())
    if ws is None:
        raise BrandNotFound(f"Marca '{ref}' nao encontrada e nao ha pasta de trabalho. "
                            "Passe a pasta da marca ou rode `ss workspace init`.")
    try:
        target = workspace.brand_dir(ws, ref)
    except ValueError as exc:
        raise BrandNotFound(f"Marca '{ref}' invalida: nao e uma pasta com brand.json nem um slug valido.") from exc
    if not (target / "brand.json").is_file():
        known = ", ".join(workspace.list_brands(ws)) or "nenhuma"
        raise BrandNotFound(f"Marca '{ref}' nao encontrada em {ws / 'marcas'}. Marcas existentes: {known}.")
    return target


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="ss brand", description="Onboarding de marca.")
    sub = parser.add_subparsers(dest="command", required=True)
    ext = sub.add_parser("extract", help="extrai cores, fontes e variaveis CSS de um site")
    ext.add_argument("source", help="URL, arquivo .html ou pasta com index.html")
    new = sub.add_parser("new", help="cria a marca a partir do modelo neutro")
    new.add_argument("slug", help="nome curto da marca (minusculas e hifens)")
    new.add_argument("--ephemeral", action="store_true",
                     help="nao guarda na pasta de trabalho: cria em ~/.cache/scroll-stopper/tmp-brands/<slug>")
    use = sub.add_parser("use", help="ativa uma marca no engine de um projeto")
    use.add_argument("brand", help="slug da marca ou pasta com brand.json")
    use.add_argument("--project", required=True, help="id do projeto")
    args = parser.parse_args(argv)

    if args.command == "extract":
        try:
            result = brand_extract.extract(args.source)
        except brand_extract.ExtractionError as exc:
            print(f"[!!] Nao consegui extrair os tokens: {exc}", file=sys.stderr)
            return 1
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if args.command == "new":
        ws = None
        if not args.ephemeral:
            ws = workspace.find_workspace(Path.cwd())
            if ws is None:
                print("[!!] Nenhuma pasta de trabalho encontrada. Rode `ss workspace init` na pasta do projeto "
                      "ou use --ephemeral para nao guardar a marca.", file=sys.stderr)
                return 1
        try:
            target = workspace.new_brand_from_template(ws, args.slug)
        except FileExistsError:
            print(f"[!!] A marca '{args.slug}' ja existe em {ws / 'marcas'}. Escolha outro nome ou edite a existente.",
                  file=sys.stderr)
            return 1
        except ValueError:
            print(f"[!!] Nome de marca invalido: {args.slug!r} (use minusculas, numeros e hifens).", file=sys.stderr)
            return 1
        print(target.resolve())
        return 0

    try:
        brand_dir = resolve_brand(args.brand)
        engine_path = engine.prepare(args.project, brand_dir, media={})
    except BrandNotFound as exc:
        print(f"[!!] {exc}", file=sys.stderr)
        return 1
    except (engine.EngineNotInstalled, engine.BrandActivationError, ValueError) as exc:
        print(f"[!!] {exc}", file=sys.stderr)
        return 1
    print(engine_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
