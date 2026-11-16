"""Corta e renderiza os candidatos escolhidos de um video longo (caminho C).

Para cada candidato escolhido (id do candidatos.json validado):
  1. escreve um plano de corte em work_dir(<id>-c<n>)/corte.json (keep=[[inicio, fim]]) e chama o `ss cut`
     (o id do projeto do corte vem da pasta do plano, por isso cada clipe tem a sua: <id>-c<n>);
  2. leva as palavras da transcricao do video longo para a linha do tempo do corte (sem transcrever de novo);
  3. estilo simples: renderiza SimpleClip-m (video + legenda karaoke + logo opcional, audio do proprio corte)
     e copia o resultado para .scroll-stopper/projetos/<id>/clips/clip-<n>.mp4;
     estilo dinamico: nao renderiza; mostra como seguir pelo caminho A com o corte.
"""
import json
import math
import shutil
from pathlib import Path

from ss_lib import engine, paths
from ss_lib.clips import finite_number, load_words
from ss_lib.cut import cut
from ss_lib.render import LUFS_PRESENTER, deliver, finalize_checked, remotion_render, report_line
from ss_lib.words import enforce_monotonic

COMPOSITION = "SimpleClip-m"
WORDS_FILE = "SimpleClip-m.words.json"
CLIP_VIDEO = "clip.mp4"
CLIP_TAIL_S = 0.6  # igual a CLIP_TAIL em engine/src/ads/SimpleClip.tsx
DEFAULT_FRAMES = 1200  # duracao da composicao sem palavras (Root.tsx)
FPS = 30
RENDER_TIMEOUT_S = 3600


def clip_project_id(project_id: str, n: int) -> str:
    return f"{project_id}-c{n}"


def remap_words(words: list, segments: list) -> list:
    """Palavras do video longo -> tempo do corte ([{w, s, e}]).

    segments sao os trechos mantidos pelo `ss cut` (tempo do video de origem), na ordem em que foram
    emendados. Palavra cujo meio cai fora de todos os trechos (pausa cortada) sai.
    """
    out, offset, spans = [], 0.0, []
    for a, b in segments:
        spans.append((float(a), float(b), offset))
        offset += float(b) - float(a)
    for w in words:
        s, e = float(w["s"]), float(w["e"])
        mid = (s + e) / 2
        for a, b, off in spans:
            if a <= mid <= b:
                text = str(w.get("w", w.get("t", ""))).strip()
                out.append({"w": text, "s": off + max(s, a) - a, "e": off + min(e, b) - a})
                break
    return [{"w": w["w"], "s": w["s"], "e": w["e"]} for w in enforce_monotonic(out)]


def load_candidates(ws: Path, project_id: str) -> dict:
    path = Path(ws) / "projetos" / project_id / "candidatos.json"
    if not path.is_file():
        raise SystemExit(f"[!!] candidatos.json nao encontrado: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"[!!] candidatos.json invalido ({path}): {exc}")
    cands = data.get("candidates") if isinstance(data, dict) else None
    if (not isinstance(cands, list) or not data.get("validated")
            or any(not isinstance(c, dict) or "id" not in c for c in cands)):
        raise SystemExit(f"[!!] candidatos ainda nao validados. Rode antes: ss clips validate {project_id}")
    for c in cands:
        for key in ("start", "end"):
            if finite_number(c.get(key)) is None:
                raise SystemExit(f"[!!] candidato {c['id']} sem '{key}' valido no candidatos.json. "
                                 f"Rode de novo: ss clips validate {project_id}")
    return data


def source_video(data: dict, project_id: str, ws: Path) -> Path:
    """Video longo: "source" do candidatos.json (relativo a pasta que contem .scroll-stopper/) ou media/video."""
    if data.get("source"):
        src = Path(data["source"]).expanduser()
        if not src.is_absolute():
            src = Path(ws).resolve().parent / src
    else:
        src = paths.media_dir(project_id, "video") / "source.mp4"
    if not src.is_file():
        raise SystemExit(f"[!!] video longo nao encontrado: {src}. Rode `ss download <link> {project_id}` "
                         "ou informe \"source\" no candidatos.json")
    return src


def cut_clip(project_id: str, n: int, cand: dict, source: Path) -> Path:
    """Corta o trecho do candidato; devolve work_dir(<id>-c<n>)/cut_1x.mp4."""
    clip_id = clip_project_id(project_id, n)
    work = paths.work_dir(clip_id)
    work.mkdir(parents=True, exist_ok=True)
    plan = work / "corte.json"
    plan.write_text(json.dumps({"source": str(source), "keep": [[cand["start"], cand["end"]]],
                                "_keep": f"candidato {n} de {project_id}: {cand.get('title', '')}"},
                               ensure_ascii=False, indent=1), encoding="utf-8")
    return cut(plan)


def render_simple(clip_id: str, cut_path: Path, words: list, brand_dir: Path, out: Path,
                  scale: float = 1.0, logo: bool = False) -> tuple[Path, dict]:
    """Renderiza SimpleClip-m com o corte em public/video/clip.mp4 e as palavras em public/audio/."""
    video_dir = paths.media_dir(clip_id, "video")
    audio_dir = paths.media_dir(clip_id, "audio")
    video_dir.mkdir(parents=True, exist_ok=True)
    audio_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(cut_path, video_dir / CLIP_VIDEO)
    (audio_dir / WORDS_FILE).write_text(json.dumps(words, ensure_ascii=False), encoding="utf-8")
    target = engine.prepare(clip_id, brand_dir)

    segments = json.loads((paths.work_dir(clip_id) / "cut_segments.json").read_text(encoding="utf-8"))
    # a composicao dura fala + CLIP_TAIL_S; o video do corte pode acabar antes: corta no ultimo quadro dele
    comp_frames = math.ceil((words[-1]["e"] + CLIP_TAIL_S) * FPS) if words else DEFAULT_FRAMES
    last_frame = max(0, min(comp_frames, math.floor(segments["duration"] * FPS)) - 1)
    rendered = paths.work_dir(clip_id) / "out" / "clip.mp4"
    rendered.parent.mkdir(parents=True, exist_ok=True)
    props = {"id": "SimpleClip", "voice": "m", "words": [], "logo": logo}
    remotion_render(target, COMPOSITION, rendered,
                    [f"--scale={scale}", f"--frames=0-{last_frame}", f"--props={json.dumps(props)}"])
    # clipes saem em -14 LUFS (mesmo alvo do apresentador); o intermediario fica no work_dir
    normalized = rendered.with_name("final-clip.mp4")
    report = finalize_checked(rendered, normalized, LUFS_PRESENTER)
    out.parent.mkdir(parents=True, exist_ok=True)
    return deliver(normalized, out.parent, out.stem), report


def render_clips(ws: Path, project_id: str, ids: list[int], style: str = "simples", brand_dir: Path | None = None,
                 scale: float = 1.0, logo: bool = False, dest: Path | None = None) -> list[Path]:
    """Corta cada candidato escolhido e (estilo simples) renderiza; devolve os arquivos gerados.

    dest: pasta de entrega (cada clipe vira <dest>/<id>-clip-<n>.mp4, sem sobrescrever); sem ela,
    .scroll-stopper/projetos/<id>/clips/clip-<n>.mp4.
    """
    if style not in ("simples", "dinamico"):
        raise ValueError(f"invalid style: {style!r}")
    data = load_candidates(ws, project_id)
    by_id = {int(c["id"]): c for c in data["candidates"]}
    missing = [n for n in ids if n not in by_id]
    if missing:
        raise SystemExit(f"[!!] id(s) fora do candidatos.json: {', '.join(map(str, missing))} "
                         f"(existem: {', '.join(map(str, sorted(by_id))) or 'nenhum'})")
    source = source_video(data, project_id, ws)
    words = load_words(project_id) if style == "simples" else []
    brand_dir = Path(brand_dir) if brand_dir else paths.PLUGIN_ROOT / "templates" / "marca"
    outputs = []
    for n in ids:
        clip_id = clip_project_id(project_id, n)
        cut_path = cut_clip(project_id, n, by_id[n], source)
        if style == "dinamico":
            print(f"[->] Corte {n} pronto: {cut_path}")
            print("     Estilo dinamico: siga pelo caminho A (apresentador + motion) com este corte:")
            print(f"     ss prepare-presenter {cut_path} {clip_id}")
            outputs.append(cut_path)
            continue
        segments = json.loads((paths.work_dir(clip_id) / "cut_segments.json").read_text(encoding="utf-8"))["segments"]
        clip_words = remap_words(words, segments)
        if not clip_words:
            raise SystemExit(f"[!!] nenhuma fala transcrita no trecho do candidato {n} "
                             f"({by_id[n]['start']}-{by_id[n]['end']} s): confira a transcricao ou escolha outro trecho")
        if dest is not None:
            final = Path(dest) / f"{project_id}-clip-{n}.mp4"
        else:
            final = Path(ws) / "projetos" / project_id / "clips" / f"clip-{n}.mp4"
        final, report = render_simple(clip_id, cut_path, clip_words, brand_dir, final, scale=scale, logo=logo)
        print(report_line(report, final, f"Clipe {n}"))
        outputs.append(final)
    return outputs
