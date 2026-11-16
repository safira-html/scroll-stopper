# Copyright (C) 2025  Sami Hindi
# Adapted for scroll-stopper; licensed AGPL-3.0.
# Origem: SupoClip (https://github.com/FujiwaraChoki/supoclip), backend/src/clip_duration.py (presets de
# duracao) e backend/src/ai.py (janelas de analise, encaixe nos limites do texto com tolerancia de 8 s,
# remocao de candidatos sobrepostos, nota de 4 criterios de 0-25 e quantidade de cortes pela duracao).
"""Video longo -> cortes curtos (caminho C): janelas da transcricao, validacao e nota dos candidatos.

Uso:
    ss clips windows <id>                         divide transcript.txt em janelas de 12 min
    ss clips validate <id> [--preset short]       valida projetos/<id>/candidatos.json
    ss clips render <id> --ids 1,3,5 [--style simples|dinamico] [--brand <slug|pasta>] [--logo] [--scale 1.0]
                     [--dest <pasta>]

Fluxo: `ss download` (ou o arquivo do usuario em media/video/source.mp4) -> `ss transcribe` -> `ss clips windows`
-> o Claude le cada janela e escreve candidatos.json -> `ss clips validate` -> `ss clips render`.
Criterios e formato do candidatos.json: knowledge/cortes-de-video-longo.md.
"""
import argparse
import json
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from ss_lib import paths


@dataclass(frozen=True)
class ClipDuration:
    minimum: int
    maximum: int
    ideal_minimum: int
    ideal_maximum: int


CLIP_DURATIONS = {
    "auto": ClipDuration(15, 60, 25, 50),
    "short": ClipDuration(15, 30, 18, 25),
    "medium": ClipDuration(30, 60, 35, 55),
    "long": ClipDuration(60, 120, 75, 110),
}

ANALYSIS_WINDOW_SECONDS = 12 * 60
ANALYSIS_WINDOW_OVERLAP_SECONDS = 2 * 60
ANALYSIS_SINGLE_WINDOW_MAX_SECONDS = 15 * 60
CANDIDATE_DEDUPE_OVERLAP_RATIO = 0.5
SEGMENT_SNAP_TOLERANCE_SECONDS = 8
MIN_FINAL_CLIPS = 5
MAX_FINAL_CLIPS = 20
SECONDS_PER_FINAL_CLIP = 5 * 60
SCORE_KEYS = ("hook", "engagement", "value", "shareability")
SCORE_MAX = 25
HOOK_TYPES = ("question", "statement", "statistic", "story", "contrast", "none")
SENTENCE_END = (".", "?", "!", "…")
CLOSERS = "\"'”’)]»"  # aspas e parenteses que fecham depois do ponto: 'disse "pare."'
DROP_REASONS_PT = {
    "invalid": "inicio/fim ausente ou invalido",
    "no_boundary": "nenhum comeco ou fim de frase a ate 8 s do inicio/fim informado",
    "duration_out_of_preset": "duracao fora da faixa do preset depois do encaixe nas frases",
}
TRANSCRIPT_LINE = re.compile(r"^\[\s*([\d.]+)\s*-\s*([\d.]+)\]\s*(.*)$")


def clip_duration(preset: str) -> ClipDuration:
    if preset not in CLIP_DURATIONS:
        raise ValueError(f"invalid preset: {preset!r} (expected one of {', '.join(CLIP_DURATIONS)})")
    return CLIP_DURATIONS[preset]


# ---------- janelas de analise ----------

def windows(duration: float) -> list[tuple[float, float]]:
    """Janelas de 12 min com 2 min de sobreposicao; ate 15 min fica uma janela so.

    Uma janela final com menos de 6 min e absorvida pela anterior.
    """
    if duration <= ANALYSIS_SINGLE_WINDOW_MAX_SECONDS:
        return [(0, duration)]
    step = ANALYSIS_WINDOW_SECONDS - ANALYSIS_WINDOW_OVERLAP_SECONDS
    bounds, start = [], 0
    while True:
        end = start + ANALYSIS_WINDOW_SECONDS
        if end >= duration:
            bounds.append([start, duration])
            break
        bounds.append([start, end])
        start += step
    if len(bounds) > 1 and bounds[-1][1] - bounds[-1][0] < ANALYSIS_WINDOW_SECONDS // 2:
        bounds.pop()
        bounds[-1][1] = duration
    return [(a, b) for a, b in bounds]


def clip_count(duration: float) -> int:
    """Quantos cortes entregar: um a cada 5 min, entre 5 e 20."""
    return max(MIN_FINAL_CLIPS, min(MAX_FINAL_CLIPS, round(max(0.0, duration) / SECONDS_PER_FINAL_CLIP)))


def split_transcript(transcript: str, duration: float) -> list[tuple[float, float, str]]:
    """Linhas do transcript.txt ("[ini-fim] texto") de cada janela, pelo inicio da linha."""
    timed = []
    for raw in transcript.splitlines():
        match = TRANSCRIPT_LINE.match(raw.strip())
        if match:
            timed.append((float(match.group(1)), raw.strip()))
    parts = []
    bounds = windows(duration)
    for i, (a, b) in enumerate(bounds):
        last = i == len(bounds) - 1
        lines = [ln for s, ln in timed if a <= s and (s < b or (last and s <= b))]
        parts.append((a, b, "\n".join(lines)))
    return parts


# ---------- validacao dos candidatos ----------

def _text(word: dict) -> str:
    return str(word.get("w", word.get("t", ""))).strip()


def _ends_sentence(text: str) -> bool:
    return text.rstrip(CLOSERS).endswith(SENTENCE_END)


def sentence_bounds(words: list) -> tuple[list[float], list[float]]:
    """Inicios e fins de frase (pontuacao final do Whisper); a primeira e a ultima palavra tambem contam."""
    starts, ends = [], []
    for i, w in enumerate(words):
        if i == 0 or _ends_sentence(_text(words[i - 1])):
            starts.append(float(w["s"]))
        if _ends_sentence(_text(w)) or i == len(words) - 1:
            ends.append(float(w["e"]))
    return starts, ends


def snap_to_sentences(start: float, end: float, starts: list, ends: list,
                      tolerance: float = SEGMENT_SNAP_TOLERANCE_SECONDS) -> tuple[float, float] | None:
    """Leva inicio e fim ao limite de frase mais proximo (ate `tolerance` s); fora disso, None."""
    if not starts or not ends:
        return None
    s = min(starts, key=lambda x: (abs(x - start), x))
    if abs(s - start) > tolerance:
        return None
    later = [x for x in ends if x > s]
    if not later:
        return None
    e = min(later, key=lambda x: (abs(x - end), -x))
    if abs(e - end) > tolerance:
        return None
    return s, e


def finite_number(value) -> float | None:
    """Numero finito, ou None (bool, texto, NaN e infinito nao valem)."""
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) else None


def _score(value) -> int:
    number = finite_number(value)
    return 0 if number is None else max(0, min(SCORE_MAX, int(round(number))))


def _ref(cand: dict, index: int) -> str:
    """Como citar um candidato: pelo id, se ja tiver, ou pela posicao no arquivo (#n)."""
    return str(cand["id"]) if cand.get("id") is not None else f"#{index}"


def overlap_ratio(first: tuple[float, float], second: tuple[float, float]) -> float:
    """Sobreposicao como fracao do trecho mais curto (1.0 = um contem o outro)."""
    shorter = min(first[1] - first[0], second[1] - second[0])
    if shorter <= 0:
        return 0.0
    return max(0.0, min(first[1], second[1]) - max(first[0], second[0])) / shorter


def validate_candidates(cands: list[dict], words: list[dict], preset: str, drops: list | None = None) -> list[dict]:
    """Encaixa nas frases, descarta duracao fora do preset, recalcula a nota e remove repetidos.

    Devolve os candidatos validos do maior para o menor total (0-100 = 4 notas de 0-25).
    drops (opcional) recebe um registro por candidato descartado, em ordem de posicao:
    {"index": posicao 1.., "id", "title", "reason"}, com reason em invalid, no_boundary,
    duration_out_of_preset ou "duplicate_of <id ou #posicao>".
    """
    limits = clip_duration(preset)
    starts, ends = sentence_bounds(words)
    valid, dropped = [], []

    def drop(index: int, raw, reason: str) -> None:
        info = raw if isinstance(raw, dict) else {}
        dropped.append({"index": index, "id": info.get("id"), "title": info.get("title", ""), "reason": reason})

    for index, raw in enumerate(cands, 1):
        start = finite_number(raw.get("start")) if isinstance(raw, dict) else None
        end = finite_number(raw.get("end")) if isinstance(raw, dict) else None
        if start is None or end is None or end <= start:
            drop(index, raw, "invalid")
            continue
        snapped = snap_to_sentences(start, end, starts, ends)
        if snapped is None:
            drop(index, raw, "no_boundary")
            continue
        s, e = round(snapped[0], 2), round(snapped[1], 2)
        duration = round(e - s, 2)
        if not limits.minimum <= duration <= limits.maximum:
            drop(index, raw, "duration_out_of_preset")
            continue
        given = raw.get("scores") if isinstance(raw.get("scores"), dict) else {}
        scores = {k: _score(given.get(k)) for k in SCORE_KEYS}
        hook_type = raw.get("hook_type") if raw.get("hook_type") in HOOK_TYPES else "none"
        valid.append((index, {**raw, "start": s, "end": e, "duration": duration, "hook_type": hook_type,
                              "scores": scores, "total": sum(scores.values())}))
    kept = []
    for index, c in sorted(valid, key=lambda item: item[1]["total"], reverse=True):
        twin = next(((ki, k) for ki, k in kept if overlap_ratio((c["start"], c["end"]), (k["start"], k["end"]))
                     > CANDIDATE_DEDUPE_OVERLAP_RATIO), None)
        if twin is not None:
            drop(index, c, f"duplicate_of {_ref(twin[1], twin[0])}")
            continue
        kept.append((index, c))
    if drops is not None:
        drops.extend(sorted(dropped, key=lambda d: d["index"]))
    return [c for _, c in kept]


def drop_reason_pt(reason: str) -> str:
    if reason.startswith("duplicate_of "):
        return f"repete o candidato {reason.split(' ', 1)[1]} (mais de 50% do trecho), que tem nota maior"
    return DROP_REASONS_PT.get(reason, reason)


def assign_ids(cands: list[dict]) -> None:
    """Mantem o id de quem ja tem (o usuario pode ter escolhido por ele); numera os novos depois do maior."""
    used = [c["id"] for c in cands if isinstance(c.get("id"), int) and not isinstance(c.get("id"), bool)]
    next_id = max(used, default=0) + 1
    for c in cands:
        if not (isinstance(c.get("id"), int) and not isinstance(c.get("id"), bool)):
            c["id"] = next_id
            next_id += 1


# ---------- CLI ----------

def load_words(project_id: str) -> list:
    words_path = paths.work_dir(project_id) / "transcript" / "words.json"
    if not words_path.is_file():
        raise SystemExit(f"[!!] transcricao nao encontrada: {words_path}. "
                         f"Rode antes: ss transcribe <video> {project_id}")
    return json.loads(words_path.read_text(encoding="utf-8"))


def _workspace() -> Path:
    from ss_lib.workspace import find_workspace

    ws = find_workspace(Path.cwd())
    if ws is None:
        raise SystemExit("[!!] Nenhuma pasta de trabalho encontrada. Rode `ss workspace init` na pasta do projeto.")
    return ws


def candidates_path(ws: Path, project_id: str) -> Path:
    paths.work_dir(project_id)  # valida o id
    return ws / "projetos" / project_id / "candidatos.json"


def cmd_windows(project_id: str) -> int:
    words = load_words(project_id)
    transcript_dir = paths.work_dir(project_id) / "transcript"
    transcript = (transcript_dir / "transcript.txt").read_text(encoding="utf-8")
    duration = float(words[-1]["e"]) if words else 0.0
    parts = split_transcript(transcript, duration)
    for old in transcript_dir.glob("window-*.txt"):
        old.unlink()
    print(f"[ok] {duration / 60:.1f} min de fala, {len(parts)} janela(s); entregar ate {clip_count(duration)} cortes")
    for i, (a, b, text) in enumerate(parts, 1):
        out = transcript_dir / f"window-{i:02d}.txt"
        out.write_text(text + "\n", encoding="utf-8")
        print(f"     janela {i}: {a / 60:5.1f}-{b / 60:5.1f} min  {out}")
    return 0


def cmd_validate(project_id: str, preset: str | None) -> int:
    path = candidates_path(_workspace(), project_id)
    if not path.is_file():
        raise SystemExit(f"[!!] candidatos.json nao encontrado: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"[!!] candidatos.json invalido ({path}): {exc}")
    if not isinstance(data, dict) or not isinstance(data.get("candidates"), list):
        raise SystemExit(f"[!!] candidatos.json fora do formato ({path}): esperado um objeto com a lista "
                         "\"candidates\" (veja knowledge/cortes-de-video-longo.md)")
    preset = preset or data.get("preset") or "auto"
    if preset not in CLIP_DURATIONS:
        raise SystemExit(f"[!!] preset invalido no candidatos.json: {preset!r} (use {', '.join(CLIP_DURATIONS)})")
    words = load_words(project_id)
    duration = float(words[-1]["e"]) if words else 0.0
    raw = data["candidates"]
    drops = []
    limit = clip_count(duration)
    valid = validate_candidates(raw, words, preset, drops=drops)
    assign_ids(valid)
    for c in valid[limit:]:
        drops.append({"index": None, "id": c["id"], "title": c.get("title", ""), "reason": "over_limit"})
    valid = valid[:limit]
    path.write_text(json.dumps({**data, "preset": preset, "validated": True, "candidates": valid},
                               ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[ok] {len(valid)} de {len(raw)} candidatos validos (preset {preset})")
    for c in valid:
        print(f"     {c['id']:2d}. {c['total']:3d}/100  {c['start']:8.2f}-{c['end']:8.2f}  ({c['duration']:.1f} s)  "
              f"{c.get('title', '')}")
    for d in drops:
        who = f"id {d['id']}" if d["index"] is None else f"#{d['index']}"
        why = (f"acima do limite de {limit} cortes para esta duracao" if d["reason"] == "over_limit"
               else drop_reason_pt(d["reason"]))
        print(f"     descartado {who} {d['title']!r}: {why}")
    return 0


def _ids(text: str) -> list[int]:
    try:
        return [int(x) for x in text.split(",") if x.strip()]
    except ValueError:
        raise SystemExit(f"[!!] --ids invalido: {text!r} (use numeros separados por virgula, ex.: 1,3,5)")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="ss clips", description="Cortes curtos de um video longo.")
    sub = ap.add_subparsers(dest="command", required=True)
    w = sub.add_parser("windows", help="divide a transcricao em janelas de analise")
    w.add_argument("project_id")
    v = sub.add_parser("validate", help="valida e numera os candidatos")
    v.add_argument("project_id")
    v.add_argument("--preset", choices=sorted(CLIP_DURATIONS))
    r = sub.add_parser("render", help="corta e renderiza os candidatos escolhidos")
    r.add_argument("project_id")
    r.add_argument("--ids", required=True, help="ids do candidatos.json, ex.: 1,3,5")
    r.add_argument("--style", choices=("simples", "dinamico"), default="simples")
    r.add_argument("--brand", help="slug da marca em .scroll-stopper/marcas ou pasta com brand.json "
                   "(padrao: marca neutra)")
    r.add_argument("--logo", action="store_true", help="logo da marca no topo")
    r.add_argument("--scale", type=float, default=1.0, help="escala do render (1.0 = 1080x1920)")
    r.add_argument("--dest", help="pasta de entrega dos clipes (padrao: .scroll-stopper/projetos/<id>/clips)")
    args = ap.parse_args(argv)
    try:
        paths.work_dir(args.project_id)
    except ValueError as exc:
        raise SystemExit(f"[!!] id de projeto invalido: {exc}")

    if args.command == "windows":
        return cmd_windows(args.project_id)
    if args.command == "validate":
        return cmd_validate(args.project_id, args.preset)
    from ss_lib import clip_render

    ws = _workspace()
    from ss_lib.render import _brand_arg, guard

    brand = _brand_arg(args.brand, args.project_id)
    dest = Path(args.dest).expanduser() if args.dest else None
    if dest is not None and not dest.parent.is_dir():
        raise SystemExit(f"[!!] a pasta {dest.parent} nao existe; crie-a ou escolha outro destino")

    guard(lambda: clip_render.render_clips(ws, args.project_id, _ids(args.ids), style=args.style, brand_dir=brand,
                                           scale=args.scale, logo=args.logo, dest=dest))
    return 0


if __name__ == "__main__":
    sys.exit(main())
