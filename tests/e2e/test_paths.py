"""Smoke de ponta a ponta dos tres caminhos pelo CLI real (`bin/ss` em subprocesso), na ordem das skills.

    A  corte + apresentador-com-motion: transcribe -> corte.json -> cut -> prepare-presenter -> brand use ->
       composicao <id>-m copiada do PresenterTemplate -> draft -> render (-14 LUFS)
    B  motion-narrado: align (sem roteiro) -> brand use -> composicao <id>-m copiada do Template -> render (-15 LUFS)
    C  cortes-de-video-longo: transcribe -> clips windows -> candidatos.json -> clips validate ->
       clips render --ids 1,2 --style simples --dest (-14 LUFS, 15-60 s cada)

Rodar: pytest -m e2e -v -s   (detalhes em tests/e2e/README.md)
"""
import json
import math
import re
import sys
import time
import unicodedata
from pathlib import Path

import pytest

from ss_lib import paths
from tests.fixtures import make_media

pytestmark = pytest.mark.e2e

ROOT = Path(__file__).resolve().parents[2]
ADS = ROOT / "engine" / "src" / "ads"
BRAND = "marca-teste"

# Paragrafos neutros para o video longo do caminho C (falados pelo `say`, repetidos ate passar de 6 min)
LONG_TALK = [
    "Quem estuda sozinho costuma travar no mesmo ponto. A pessoa abre o material, lê duas páginas e sente que "
    "não guardou nada. Isso acontece porque ler não é o mesmo que lembrar. O que funciona é fechar o livro e "
    "tentar explicar o assunto com as próprias palavras. Se a explicação trava, você achou exatamente o trecho "
    "que precisa rever. Parece mais lento, mas economiza horas de releitura.",
    "Organizar a semana não precisa de aplicativo nenhum. Uma folha de papel resolve. Escreva as três tarefas "
    "que mais importam e deixe o resto para depois. Quando tudo parece urgente, nada anda. Ao escolher só três, "
    "você aceita que algumas coisas vão esperar, e tudo bem. No fim da semana, olhe a folha e veja o que de fato "
    "saiu do lugar.",
    "Muita gente desiste da caminhada porque começa forte demais. No primeiro dia anda uma hora, no segundo dia "
    "está com dor e no terceiro já parou. O caminho mais simples é começar com dez minutos e aumentar aos "
    "poucos. O corpo se acostuma e o hábito fica. A regra é sair de casa mesmo nos dias de preguiça, ainda que "
    "seja só para dar uma volta no quarteirão.",
    "Cozinhar em casa parece trabalhoso, mas o segredo está no preparo. Separe uma hora no domingo para lavar e "
    "cortar os legumes da semana. Guarde tudo em potes fechados na geladeira. Durante a semana, montar um prato "
    "leva poucos minutos, porque a parte chata já está pronta. Quem faz isso uma vez percebe que o problema "
    "nunca foi o tempo, e sim a organização.",
    "Plantas de apartamento morrem mais por excesso de cuidado do que por falta dele. A pessoa rega todo dia e "
    "a raiz apodrece. Antes de regar, coloque o dedo na terra. Se estiver úmida, espere mais um pouco. Observe "
    "também a luz: cada planta gosta de um canto diferente da casa. Com essas duas atenções, a maioria das "
    "plantas vive muito bem.",
    "Dormir bem começa bem antes de deitar. A luz forte da tela avisa o corpo que ainda é dia. Uma hora antes de "
    "dormir, diminua as luzes da casa e deixe o celular longe da cama. Tente acordar sempre no mesmo horário, "
    "inclusive no fim de semana. Em poucos dias o sono fica mais regular e acordar deixa de ser uma briga.",
    "Ler mais livros não depende de ler mais rápido. Depende de ter o livro por perto. Deixe um na bolsa, outro "
    "na mesa de cabeceira e leia nas pequenas esperas do dia. Dez páginas na fila, mais dez antes de dormir. No "
    "fim do mês, essas sobras de tempo somam um livro inteiro, sem você precisar reservar uma tarde só para isso.",
    "Beber água ao longo do dia é mais fácil quando a garrafa está à vista. Quem depende de lembrar acaba "
    "esquecendo. Encha uma garrafa pela manhã e deixe na mesa de trabalho. Quando ela esvaziar, encha de novo. "
    "Não precisa de meta complicada nem de aplicativo. O simples fato de ver a garrafa já resolve a maior parte "
    "do problema.",
]


# ---------- ajudantes ----------

def norm(text: str) -> str:
    text = unicodedata.normalize("NFD", text.lower())
    return re.sub(r"[^a-z0-9]", "", "".join(ch for ch in text if not unicodedata.combining(ch)))


def template_string(tsx: str, const: str) -> str:
    """Texto de `export const <const> = '...'` de um arquivo do engine (o roteiro dos modelos)."""
    match = re.search(rf"export const {const} =\s*'([^']*)'", (ADS / tsx).read_text(encoding="utf-8"))
    assert match, f"{const} nao encontrado em {tsx}"
    return match.group(1)


def last_json(stdout: str) -> dict:
    return json.loads(next(ln for ln in reversed(stdout.splitlines()) if ln.startswith("{")))


def render_qa(stdout: str) -> dict:
    """Dict do qa() impresso pelo `ss render` (linha 'qa: {...}')."""
    return json.loads(next(ln for ln in stdout.splitlines() if ln.startswith("qa: "))[4:])


def delivered(stdout: str, label: str) -> list[Path]:
    """Caminhos entregues nas linhas '[ok] <label>...: <caminho>.mp4' (falha se a conferencia falhou)."""
    assert "[!!]" not in stdout, stdout
    return [Path(m) for m in re.findall(rf"^\[ok\] {label}[^:]*: (.+\.mp4)$", stdout, re.M)]


def register_composition(engine: Path, template: str, name: str, renames: dict, entry: str) -> None:
    """Passo 'Composicao' das skills: copia src/ads/<template>.tsx para <name>.tsx e registra em index.ts."""
    ads = engine / "src" / "ads"
    text = (ads / f"{template}.tsx").read_text(encoding="utf-8")
    for old, new in renames.items():
        text = re.sub(rf"\b{old}\b", new, text)
    (ads / f"{name}.tsx").write_text(text, encoding="utf-8")
    index = (ads / "index.ts").read_text(encoding="utf-8")
    imported = ", ".join(sorted(set(renames.values())))
    index = index.replace("\nexport type AdEntry", f"import {{{imported}}} from './{name}';\n\nexport type AdEntry", 1)
    head, sep, tail = index.rpartition("];")
    (ads / "index.ts").write_text(f"{head}  {entry}\n{sep}{tail}", encoding="utf-8")


def setup_brand_and_kit(cli, media: Path) -> None:
    """Marca da pasta de trabalho (copia do modelo neutro) e kit de som com uma trilha e um efeito neutros."""
    cli("brand", "new", BRAND)
    assert BRAND in cli("workspace", "brands").stdout.split()
    cli("kit", "add-music", make_media.make_tone(media, "bed", 20, 220, volume=0.2), "dark")
    cli("kit", "add-sfx", make_media.make_tone(media, "whoosh", 0.5, 880), "--name", "whoosh-short")
    status = cli("kit", "status").stdout
    assert "[ok] dark" in status and "[ok] whoosh-short" in status, status


def assert_only_outputs(dest: Path, expected: list[str], root: Path, inputs: list[Path]) -> None:
    """Entrega exata na pasta de destino (nada de .part nem extra) e nenhum .mp4 novo na pasta de trabalho."""
    assert sorted(p.name for p in dest.iterdir()) == sorted(expected)
    found = sorted(p.resolve() for p in root.rglob("*.mp4"))
    assert found == sorted(p.resolve() for p in inputs), found


def engine_number(tsx: str, const: str) -> float:
    match = re.search(rf"export const {const} = ([\d.]+)", (ROOT / "engine" / "src" / tsx).read_text(encoding="utf-8"))
    assert match, f"{const} nao encontrado em {tsx}"
    return float(match.group(1))


def report(path: str, started: float, cli) -> None:
    """Tempo total do caminho (cada passo ja foi impresso pelo Cli)."""
    print(f"[e2e] caminho {path}: {time.monotonic() - started:.1f} s no total, {len(cli.log)} comandos ss",
          file=sys.stderr)


# ---------- caminho A: apresentador + motion ----------

def test_path_a(workspace, project_id):
    started = time.monotonic()
    cli, root, ws, dest = workspace["cli"], workspace["root"], workspace["ws"], workspace["dest"]
    pid = project_id
    cli("setup", "--check")
    setup_brand_and_kit(cli, workspace["media"])
    cli("workspace", "learn", "e2e: corte com take repetido fica com o ultimo take completo", "--source", "e2e")
    assert "e2e: corte com take repetido" in (ws / "aprendizados.md").read_text(encoding="utf-8")

    # bruto: falso inicio + 1,5 s + o roteiro do modelo inteiro, com 1,5 s de pausa no meio
    script = template_string("PresenterTemplate.tsx", "PRESENTER_SCRIPT")
    split = script.index("Quem segura")
    raw, parts = make_media.make_presenter_takes(root / "bruto", "Seu anúncio pode estar perdendo gente",
                                                 script[:split].strip(), script[split:].strip())
    source = json.loads(cli("probe", raw).stdout)
    source_duration = float(source["duration"])

    cli("transcribe", raw, pid)
    words = json.loads((paths.work_dir(pid) / "transcript" / "words.json").read_text(encoding="utf-8"))
    takes = [w for w in words if norm(w["t"]) == "seu"]
    assert len(takes) >= 2, f"esperava dois takes comecando em 'Seu': {[w['t'] for w in words[:12]]}"
    second = takes[1]
    plan = ws / "projetos" / pid / "corte.json"
    plan.parent.mkdir(parents=True, exist_ok=True)
    plan.write_text(json.dumps({
        "source": str(raw.resolve()),
        "keep": [[round(second["s"] - 0.1, 2), round(words[-1]["e"] + 0.2, 2)]],
        "_keep": "falso inicio sai; fica o ultimo take completo (a pausa longa do meio e encurtada pelo ss cut)",
    }, ensure_ascii=False, indent=1), encoding="utf-8")

    cli("cut", f".scroll-stopper/projetos/{pid}/corte.json")
    cut_path = paths.work_dir(pid) / "cut_1x.mp4"
    # o corte em 1x (antes da aceleracao) perde o falso inicio com a pausa dele e ~1 s da pausa longa do meio
    cut_duration = float(json.loads(cli("probe", cut_path).stdout)["duration"])
    limit = source_duration - (parts["false_start"] + parts["gap"]) - 1.0
    print(f"[e2e] A corte 1x: {cut_duration:.2f} s (origem {source_duration:.2f} s, limite {limit:.2f} s, "
          f"partes {parts})", file=sys.stderr)
    assert cut_duration <= limit, (cut_duration, limit)
    # e o que ficou comeca no take completo: a primeira frase aparece uma vez so, no comeco
    cli("transcribe", cut_path, f"{pid}-cut")
    cut_words = [norm(w["t"]) for w in json.loads(
        (paths.work_dir(f"{pid}-cut") / "transcript" / "words.json").read_text(encoding="utf-8"))]
    first_sentence = [norm(t) for t in script[:script.index(".")].split()]
    assert cut_words[:len(first_sentence)] == first_sentence, cut_words[:12]
    assert cut_words.count("seu") == 1, cut_words
    prep = last_json(cli("prepare-presenter", cut_path, pid).stdout)
    print(f"[e2e] prepare-presenter: {prep}", file=sys.stderr)
    assert 1.0 <= prep["speed"] <= 1.3

    engine = Path(cli("brand", "use", BRAND, "--project", pid).stdout.strip().splitlines()[-1])
    assert engine == paths.work_dir(pid) / "engine"
    # o kit da pasta de trabalho entra no projeto sozinho, copiado para o cache (o render nao le da pasta sincronizada)
    assert (engine / "public" / "music").resolve() == paths.media_dir(pid, "music").resolve()
    for kind, name in (("music", "bed-dark.mp3"), ("sfx", "whoosh-short.mp3")):
        staged = engine / "public" / kind / name
        assert staged.read_bytes() == (ws / "kit-de-som" / kind / name).read_bytes()
        assert paths.CACHE in staged.resolve().parents
    register_composition(engine, "PresenterTemplate", "SmokePresenter",
                         {"PresenterTemplate": "SmokePresenter", "PRESENTER_SCRIPT": "SMOKEPRESENTER_SCRIPT"},
                         f"{{id: '{pid}', component: SmokePresenter, voices: ['m'], tail: 0.35 + OUTRO_SECONDS}},")

    cli("draft", pid, f"{pid}-m", "--brand", BRAND)
    out = paths.work_dir(pid) / "out"
    assert (out / "draft.mp4").is_file() and (out / "sheet.jpg").is_file()

    rendered = cli("render", pid, f"{pid}-m", "--dest", dest, "--name", "apresentador", "--brand", BRAND).stdout
    qa_render = render_qa(rendered)
    [final] = delivered(rendered, "video final")
    assert final == dest / "apresentador.mp4" and final.is_file()
    qa = last_json(cli("qa", final, "--lufs", "-14").stdout)
    print(f"[e2e] A qa render: {qa_render}\n[e2e] A qa: {qa}", file=sys.stderr)
    assert qa_render["target_lufs"] == -14.0 and qa_render["ok"]
    assert qa["ok"], qa
    assert qa["duration"] < source_duration, (qa["duration"], source_duration)
    assert_only_outputs(dest, ["apresentador.mp4"], root, [raw])
    report("A", started, cli)


# ---------- caminho B: motion + narracao ----------

def test_path_b(workspace, project_id):
    started = time.monotonic()
    cli, root, ws, dest = workspace["cli"], workspace["root"], workspace["ws"], workspace["dest"]
    pid = project_id
    cli("brand", "new", BRAND)

    project = ws / "projetos" / pid
    project.mkdir(parents=True, exist_ok=True)
    narration = make_media.make_narration(workspace["media"], template_string("Template.tsx", "SCRIPT"))
    (project / "narracao.mp3").write_bytes(narration.read_bytes())
    # sem roteiro: a legenda usa o texto do Whisper
    cli("align", f".scroll-stopper/projetos/{pid}/narracao.mp3", f"{pid}-m", "--project", pid)
    assert (paths.media_dir(pid, "audio") / f"{pid}-m.words.json").is_file()

    engine = Path(cli("brand", "use", BRAND, "--project", pid).stdout.strip().splitlines()[-1])
    register_composition(engine, "Template", "SmokeNarrated", {"Template": "SmokeNarrated", "SCRIPT": "SMOKENARRATED_SCRIPT"},
                         f"{{id: '{pid}', component: SmokeNarrated, demoScript: SMOKENARRATED_SCRIPT, voices: ['m']}},")

    rendered = cli("render", pid, f"{pid}-m", "--dest", dest, "--name", "narrado", "--brand", BRAND).stdout
    qa_render = render_qa(rendered)
    [final] = delivered(rendered, "video final")
    assert final == dest / "narrado.mp4" and final.is_file()
    qa = last_json(cli("qa", final, "--lufs", "-15").stdout)
    print(f"[e2e] B qa render: {qa_render}\n[e2e] B qa: {qa}", file=sys.stderr)
    assert qa_render["target_lufs"] == -15.0 and qa_render["ok"]
    assert qa["ok"], qa
    # duracao = fim da fala alinhada + respiro + tela final da marca (AdShell.tsx: TAIL + endCard.seconds)
    speech_end = json.loads((paths.media_dir(pid, "audio") / f"{pid}-m.words.json").read_text(encoding="utf-8"))[-1]["e"]
    brand = json.loads((ws / "marcas" / BRAND / "brand.json").read_text(encoding="utf-8"))
    tail = engine_number("engine/AdShell.tsx", "TAIL") + brand["endCard"].get("seconds", 11)
    expected = math.ceil((speech_end + tail) * 30) / 30
    assert abs(qa["duration"] - expected) <= 0.1, (qa["duration"], expected, speech_end, tail)
    assert_only_outputs(dest, ["narrado.mp4"], root, [])
    report("B", started, cli)


# ---------- caminho C: video longo -> cortes ----------

def test_path_c(workspace, project_id):
    started = time.monotonic()
    cli, root, ws, dest = workspace["cli"], workspace["root"], workspace["ws"], workspace["dest"]
    pid = project_id
    cli("brand", "new", BRAND)

    video, spans = make_media.make_long_talk(root / "aula longa", LONG_TALK, min_seconds=360)
    assert spans[-1][1] >= 360
    cli("transcribe", video, pid)
    windows = cli("clips", "windows", pid).stdout
    assert "1 janela(s)" in windows and "entregar ate 5 cortes" in windows, windows

    # candidatos fixos: paragrafos inteiros do video (cada um e uma ideia completa de 20-40 s)
    picks = [(0, "Explicar com as proprias palavras", 22), (2, "Comecar a caminhada devagar", 20),
             (4, "Plantas morrem por excesso de cuidado", 18)]
    candidates = [{"start": spans[i][0], "end": spans[i][1], "title": title, "hook_type": "statement",
                   "scores": {"hook": score, "engagement": score, "value": score, "shareability": score},
                   "reasoning": "paragrafo completo do teste"} for i, title, score in picks]
    plan = ws / "projetos" / pid / "candidatos.json"
    plan.parent.mkdir(parents=True, exist_ok=True)
    plan.write_text(json.dumps({"preset": "auto", "source": str(video.resolve()), "candidates": candidates},
                               ensure_ascii=False, indent=2), encoding="utf-8")
    validated = cli("clips", "validate", pid).stdout
    assert "3 de 3 candidatos validos" in validated, validated

    chosen = {c["id"]: c for c in json.loads(plan.read_text(encoding="utf-8"))["candidates"]}
    # validados pela nota: id 1 = paragrafo 0, id 2 = paragrafo 2; o encaixe nas frases mexe pouco nas bordas
    for n, (par, _title, _score) in zip((1, 2), picks):
        assert abs(chosen[n]["start"] - spans[par][0]) <= 1.0 and abs(chosen[n]["end"] - spans[par][1]) <= 1.0, \
            (n, chosen[n], spans[par])
    rendered = cli("clips", "render", pid, "--ids", "1,2", "--style", "simples", "--brand", BRAND,
                   "--dest", dest).stdout
    finals = delivered(rendered, "Clipe")
    assert finals == [dest / f"{pid}-clip-1.mp4", dest / f"{pid}-clip-2.mp4"], rendered
    for n, final in zip((1, 2), finals):
        qa = last_json(cli("qa", final, "--lufs", "-14").stdout)
        print(f"[e2e] C qa {final.name}: {qa} (candidato {chosen[n]['start']}-{chosen[n]['end']}, "
              f"{chosen[n]['duration']} s)", file=sys.stderr)
        assert qa["ok"], qa
        assert 15 <= qa["duration"] <= 60, qa
        # o clipe e o trecho escolhido (bordas encostadas no silencio + respiro final mexem menos de 1 s)
        assert abs(qa["duration"] - chosen[n]["duration"]) <= 1.0, (qa, chosen[n])
    assert_only_outputs(dest, [f.name for f in finals], root, [video])
    report("C", started, cli)
