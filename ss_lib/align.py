# Portions adapted from earlier MIT-licensed work. Copyright (c) 2026 Safira Mendes.
"""Alinha uma narracao (mp3/wav/m4a de qualquer TTS ou gravada pela pessoa) a palavras com tempo.

Uso:
    ss align <raw> <key> --project <id> [--script roteiro.txt]

<key> segue o engine: "<id>-f" ou "<id>-m" (variante de voz). Escreve em
media_dir(<id>, "audio"): <key>.mp3 (-16 LUFS, loudnorm em duas passadas) e <key>.words.json
([{w, s, e}]). O `engine.prepare` liga essa pasta em public/audio do engine.

Com --script, a grafia do roteiro vence e o Whisper so da os tempos (palavra que ele nao ouviu e
encaixada no intervalo entre as vizinhas). Sem roteiro, vale o texto do Whisper: revise nomes de marca.
"""
import argparse
import difflib
import json
import re
import sys
import unicodedata
from pathlib import Path

from ss_lib import paths
from ss_lib.presenter import loudnorm_two_pass, transcribe_words
from ss_lib.words import enforce_monotonic

GLUE_CHARS = set("%,.!?")


def norm(word: str) -> str:
    """Forma comparavel: minuscula, sem acento, so letras e digitos."""
    word = unicodedata.normalize("NFKD", word.lower())
    return re.sub(r"[^a-z0-9]", "", "".join(c for c in word if not unicodedata.combining(c)))


def _is_glue(token: str) -> bool:
    return bool(token) and all(c in GLUE_CHARS for c in token)


def tokenize_script(text: str) -> list:
    """Palavras do roteiro; travessao solto vira parte da palavra anterior (legenda)."""
    out = []
    for tok in text.split():
        if out and not any(c.isalnum() for c in tok):
            out[-1] += " " + tok
        else:
            out.append(tok)
    return out


def glue_punctuation(words: list) -> list:
    """Sem roteiro: pontuacao e % soltos do Whisper colam na palavra anterior, esticando o fim dela."""
    out = []
    for w in words:
        tok = w["w"].strip()
        if not tok:
            continue
        if not any(c.isalnum() for c in tok):
            if out:  # pontuacao solta no inicio nao vira palavra
                out[-1]["w"] += tok if _is_glue(tok) else " " + tok
                out[-1]["e"] = w["e"]
        else:
            out.append({"w": tok, "s": w["s"], "e": w["e"]})
    return out


def align_words(heard: list, script: str | None) -> list:
    """[{w, s, e}] do Whisper + roteiro opcional -> [{w, s, e}] com a grafia do roteiro."""
    if script is None:
        return enforce_monotonic(glue_punctuation(heard))
    target = tokenize_script(script)
    sm = difflib.SequenceMatcher(None, [norm(w["w"]) for w in heard], [norm(w) for w in target], autojunk=False)
    out = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for i, j in zip(range(i1, i2), range(j1, j2)):
                out.append({"w": target[j], "s": round(heard[i]["s"], 2), "e": round(heard[i]["e"], 2)})
            continue
        chunk = target[j1:j2]
        if not chunk:
            continue
        if i2 > i1:
            start, end = heard[i1]["s"], heard[i2 - 1]["e"]
        else:
            # palavra que o Whisper nao ouviu: encaixa no intervalo entre as vizinhas
            start = heard[i1 - 1]["e"] if i1 > 0 else 0.0
            end = heard[i1]["s"] if i1 < len(heard) else start + 0.3
            if end <= start:
                end = start + 0.05
        # distribui o intervalo proporcional ao tamanho das palavras
        total = sum(len(x) for x in chunk)
        t = start
        for x in chunk:
            d = (end - start) * len(x) / total
            out.append({"w": x, "s": round(t, 2), "e": round(t + d, 2)})
            t += d
    return enforce_monotonic(out)


def align(raw: Path, key: str, script: str | None, out_dir: Path, transcriber=transcribe_words) -> list:
    """Alinha raw ao roteiro e grava out_dir/<key>.mp3 (-16 LUFS) e out_dir/<key>.words.json.

    transcriber(path) -> [{w, s, e}]; injetavel para testes (o padrao usa o Whisper do Task 6).
    """
    raw, out_dir = Path(raw).expanduser(), Path(out_dir)
    if not raw.is_file():
        raise SystemExit(f"[!!] narracao nao encontrada: {raw}")
    out_dir.mkdir(parents=True, exist_ok=True)
    words = align_words(transcriber(raw), script)
    (out_dir / f"{key}.words.json").write_text(json.dumps(words, ensure_ascii=False), encoding="utf-8")
    loudnorm_two_pass(raw, out_dir / f"{key}.mp3")
    return words


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="ss align", description="Alinha a narracao a palavras com tempo.")
    ap.add_argument("raw", help="narracao (mp3, wav ou m4a)")
    ap.add_argument("key", help="chave da voz no engine: <id>-f ou <id>-m")
    ap.add_argument("--project", required=True, help="id do projeto (destino: media/audio dele)")
    ap.add_argument("--script", help="arquivo .txt com o roteiro exatamente como deve aparecer na legenda")
    args = ap.parse_args(argv)
    if not re.fullmatch(r"[\w.-]+", args.key) or args.key.startswith("."):
        raise SystemExit(f"[!!] chave invalida: {args.key!r}")
    script = None
    if args.script:
        script_path = Path(args.script).expanduser()
        if not script_path.is_file():
            raise SystemExit(f"[!!] roteiro nao encontrado: {script_path}")
        script = script_path.read_text(encoding="utf-8")
    try:
        out_dir = paths.media_dir(args.project, "audio")
    except ValueError as exc:
        raise SystemExit(f"[!!] id de projeto invalido: {exc}")
    words = align(Path(args.raw), args.key, script, out_dir)
    print(f"[ok] {len(words)} palavras alinhadas" + ("" if script else " (texto do Whisper: revise nomes de marca)"))
    print(f"     audio:    {out_dir / (args.key + '.mp3')}")
    print(f"     palavras: {out_dir / (args.key + '.words.json')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
