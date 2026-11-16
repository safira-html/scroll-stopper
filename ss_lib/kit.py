"""Kit de som da pessoa: trilhas de fundo e efeitos, em .scroll-stopper/kit-de-som/.

Uso:
    ss kit add-music <arquivo> <light|dark>          normaliza para -20 LUFS -> music/bed-<light|dark>.mp3
    ss kit add-sfx <arquivo> [--name <nome-padrao>]   apara e normaliza -> sfx/<nome>.mp3
    ss kit status                                     o que ja existe e o que falta

O engine so toca os nomes padrao (veja `ss kit status`). Onde conseguir os sons: knowledge/som.md.
"""
import argparse
import sys
from pathlib import Path

from ss_lib import sound
from ss_lib.workspace import find_workspace, kit_dir


def kit_status(kit: Path) -> dict:
    """{'music': {nome: existe}, 'sfx': {nome: existe}} para os nomes que o engine usa."""
    kit = Path(kit)
    return {
        "music": {n: (kit / "music" / f"bed-{n}.mp3").is_file() for n in sound.MUSIC_NAMES},
        "sfx": {n: (kit / "sfx" / f"{n}.mp3").is_file() for n in sound.STANDARD_SFX},
    }


def _print_status(kit: Path) -> None:
    status = kit_status(kit)
    print(f"Kit de som em {kit}")
    print("Trilhas de fundo (music/bed-<nome>.mp3):")
    for name, ok in status["music"].items():
        print(f"  [{'ok' if ok else '--'}] {name}")
    have = sum(status["sfx"].values())
    print(f"Efeitos (sfx/<nome>.mp3): {have}/{len(status['sfx'])}")
    for name, ok in status["sfx"].items():
        print(f"  [{'ok' if ok else '--'}] {name}")
    missing = [n for n, ok in status["sfx"].items() if not ok]
    if missing:
        print("Faltam: " + ", ".join(missing) + " (o video fica sem esses sons; nada quebra)")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="ss kit", description="Kit de som do Scroll Stopper.")
    sub = parser.add_subparsers(dest="command", required=True)
    music = sub.add_parser("add-music", help="adiciona uma trilha de fundo")
    music.add_argument("file")
    music.add_argument("variant", choices=sound.MUSIC_NAMES)
    sfx = sub.add_parser("add-sfx", help="adiciona um efeito sonoro")
    sfx.add_argument("file")
    sfx.add_argument("--name", help="nome padrao do efeito (padrao: nome do arquivo)")
    sub.add_parser("status", help="mostra o que existe e o que falta")
    args = parser.parse_args(argv)

    ws = find_workspace(Path.cwd())
    if ws is None:
        print("[!!] Nenhuma pasta de trabalho encontrada. Rode `ss workspace init` na pasta do projeto.",
              file=sys.stderr)
        return 1
    kit = kit_dir(ws)

    if args.command == "status":
        _print_status(kit)
        return 0
    if args.command == "add-music":
        out = sound.normalize_music(Path(args.file), args.variant, kit)
        print(f"[ok] Trilha '{args.variant}' pronta em {out}")
        return 0
    name = sound.slugify(args.name or Path(args.file).expanduser().stem)
    if not name:
        print(f"[!!] '{args.name or Path(args.file).name}' nao vira um nome valido (letras, numeros e hifen). "
              "Passe --name, por exemplo --name pop-soft.", file=sys.stderr)
        return 1
    if name not in sound.STANDARD_SFX:
        print(f"[!!] '{name}' nao e um nome padrao; o engine so toca: {', '.join(sound.STANDARD_SFX)}. "
              "O arquivo foi salvo mesmo assim.", file=sys.stderr)
    out = sound.trim_sfx(Path(args.file), kit, name=name)
    print(f"[ok] Efeito '{name}' pronto em {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
