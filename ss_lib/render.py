"""Render final (com loudness normalizado) e rascunho com folha de contatos.

Uso:
    ss render <id> <composicao> --dest <pasta> --name <nome> [--lufs -15] [--brand <slug>]
    ss draft <id> <composicao> [--brand <slug>]

Todo intermediario fica em paths.work_dir(<id>)/out; so o .mp4 final e copiado para a pasta de destino
(que pode ser uma pasta sincronizada: nunca se renderiza dentro dela).
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from ss_lib import engine, paths, qa as qa_mod
from ss_lib.presenter import loudnorm_two_pass, media_duration

LUFS_PRESENTER = -14.0  # apresentador (caminho A) e clipes (caminho C)
LUFS_MOTION = -15.0     # anuncios de motion com narracao (caminho B)
TRUE_PEAK = -1.5
TRUE_PEAK_RETRY = -2.5  # segunda tentativa quando o pico medido passa de -1,0 dBTP
CRF = 18
DRAFT_SCALE = 0.5
SHEET_FPS = 1 / 1.5
SHEET_TILES = 11 * 4
SHEET_FILTER = "fps={fps:.6f},scale=180:-1,tile=11x4"
RENDER_TIMEOUT_S = 3600
PRESENTER_PREFIXES = ("Presenter", "SimpleClip")


def default_lufs(composition: str, project_id: str | None = None) -> float:
    """-14 para apresentador e clipe (pelo nome da composicao ou pelo presenter.mp4 do projeto); -15 no resto."""
    if composition.startswith(PRESENTER_PREFIXES):
        return LUFS_PRESENTER
    if project_id and (paths.media_dir(project_id, "video") / "presenter.mp4").is_file():
        return LUFS_PRESENTER  # projeto preparado pelo `ss prepare-presenter` (caminho A ou corte dinamico)
    return LUFS_MOTION


def _node_env() -> dict:
    extra = [str(Path.home() / ".local" / "bin"), "/opt/homebrew/bin", "/usr/local/bin"]
    return {**os.environ, "PATH": os.pathsep.join(extra + [os.environ.get("PATH", "")])}


def _default_brand() -> Path:
    return paths.PLUGIN_ROOT / "templates" / "marca"


def out_dir(project_id: str) -> Path:
    d = paths.work_dir(project_id) / "out"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _render_error(composition: str, output: str) -> str:
    """Mensagem curta em portugues a partir da saida do Remotion (sem o despejo de bundling e fontes)."""
    if "Could not find composition" in output:
        match = re.search(r"Available compositions:\s*([^\n]+)", output)
        available = match.group(1).strip() if match else "(nao consegui listar)"
        return (f"[!!] composicao '{composition}' nao existe no engine. Disponiveis: {available}")
    lines = [ln.strip() for ln in output.splitlines() if "error" in ln.lower() and "network requests" not in ln]
    detail = "\n".join(lines[:6]) if lines else output.strip()[-800:]
    return f"[!!] render de {composition} falhou:\n{detail}"


def remotion_render(engine_dir: Path, composition: str, target: Path, extra: list) -> None:
    cmd = ["npx", "--no-install", "remotion", "render", "src/index.ts", composition, str(target), *extra]
    try:
        proc = subprocess.run(cmd, cwd=engine_dir, env=_node_env(), capture_output=True, text=True,
                              timeout=RENDER_TIMEOUT_S)
    except FileNotFoundError:
        raise SystemExit("[!!] Node nao encontrado (npx). Instale o Node: brew install node, depois rode: ss setup")
    except subprocess.TimeoutExpired:
        raise SystemExit(f"[!!] render de {composition} passou de {RENDER_TIMEOUT_S // 60} min e foi interrompido")
    if proc.returncode != 0:
        raise SystemExit(_render_error(composition, f"{proc.stderr}\n{proc.stdout}"))


def finalize(src: Path, dst: Path, lufs: float, tp: float = TRUE_PEAK) -> Path:
    """Normaliza o audio de src para lufs/tp (duas passadas) e remuxa com o video copiado, em dst."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    audio = dst.with_name(dst.stem + ".norm.m4a")
    try:
        loudnorm_two_pass(src, audio, lufs=lufs, tp=tp)
        proc = subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-i", str(audio), "-map", "0:v",
                               "-map", "1:a", "-c", "copy", "-movflags", "+faststart", str(dst)],
                              capture_output=True, text=True)
        if proc.returncode != 0:
            raise SystemExit(f"[!!] ffmpeg falhou ao juntar video e audio: {proc.stderr.strip()[-400:]}")
    finally:
        audio.unlink(missing_ok=True)
    return dst


def finalize_checked(src: Path, dst: Path, lufs: float) -> dict:
    """finalize + QA; se o true peak passar de -1,0 dBTP (loudnorm linear estourou), refaz com TP -2,5.

    Devolve o dict do qa() do arquivo final.
    """
    finalize(src, dst, lufs)
    report = qa_mod.qa(dst, target_lufs=lufs)
    if report["true_peak"] > qa_mod.TRUE_PEAK_MAX:
        finalize(src, dst, lufs, tp=TRUE_PEAK_RETRY)
        report = qa_mod.qa(dst, target_lufs=lufs)
    return report


def deliver(src: Path, dest_dir: Path, name: str) -> Path:
    """Copia src para dest_dir/<name>.mp4 de forma atomica e sem sobrescrever.

    Reserva o nome com open(O_CREAT|O_EXCL) (se <name>.mp4 existe, tenta <name>_v2.mp4, _v3...; nao usa
    hard link porque pastas sincronizadas podem nao suportar), copia para .<nome>.part e troca com
    os.replace. Se algo falhar, nem o .part nem o arquivo reservado vazio ficam para tras.
    Devolve o caminho final.
    """
    dest_dir = Path(dest_dir)
    n = 1
    while True:
        final = dest_dir / (f"{name}.mp4" if n == 1 else f"{name}_v{n}.mp4")
        try:
            os.close(os.open(final, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644))
            break
        except FileExistsError:
            n += 1
    part = dest_dir / f".{final.name}.part"
    try:
        shutil.copy2(src, part)
        os.replace(part, final)
    except BaseException:
        final.unlink(missing_ok=True)  # reservado por nos e ainda vazio
        raise
    finally:
        part.unlink(missing_ok=True)
    return final


def report_line(report: dict, final: Path, label: str) -> str:
    """Linha de resultado: [ok] quando o QA passou; senao aviso com os motivos e o caminho com [!!]."""
    reasons = qa_mod.problems(report)
    if not reasons:
        return f"[ok] {label}: {final}"
    return f"[!!] Conferência falhou: {'; '.join(reasons)}\n[!!] {label} (confira antes de usar): {final}"


def render(project_id: str, composition: str, dest_dir: Path, name: str, lufs: float,
           brand_dir: Path | None = None) -> Path:
    """Renderiza em work_dir (h264 crf 18), normaliza para lufs e copia so o .mp4 final para dest_dir."""
    return render_checked(project_id, composition, dest_dir, name, lufs, brand_dir)[0]


def render_checked(project_id: str, composition: str, dest_dir: Path, name: str, lufs: float,
                   brand_dir: Path | None = None) -> tuple[Path, dict]:
    """Como render(), mas devolve tambem o dict do qa() do arquivo final."""
    if not name or "/" in name or "\\" in name or name.startswith("."):
        raise SystemExit(f"[!!] nome de arquivo invalido: {name!r}")
    name = name[:-4] if name.lower().endswith(".mp4") else name
    dest_dir = Path(dest_dir).expanduser()
    if not dest_dir.parent.is_dir():
        raise SystemExit(f"[!!] a pasta {dest_dir.parent} nao existe; crie-a ou escolha outro destino")
    target = engine.prepare(project_id, Path(brand_dir) if brand_dir else _default_brand())
    work = out_dir(project_id)
    raw = work / f"raw-{name}.mp4"
    remotion_render(target, composition, raw, ["--codec=h264", f"--crf={CRF}"])
    normalized = work / f"final-{name}.mp4"
    report = finalize_checked(raw, normalized, lufs)
    dest_dir.mkdir(exist_ok=True)
    final = deliver(normalized, dest_dir, name)
    print(f"qa: {json.dumps(report)}")
    return final, report


def sheet_fps(duration: float) -> float:
    """Quadros por segundo da folha: 1 a cada 1,5 s, ou menos para os 44 quadros cobrirem o video inteiro."""
    return min(SHEET_FPS, SHEET_TILES / max(duration, 0.1))


def draft(project_id: str, composition: str, brand_dir: Path | None = None) -> Path:
    """Rascunho em meia escala (draft.mp4) + folha de contatos (sheet.jpg), ambos em work_dir/out. Devolve a folha."""
    target = engine.prepare(project_id, Path(brand_dir) if brand_dir else _default_brand())
    work = out_dir(project_id)
    video, sheet = work / "draft.mp4", work / "sheet.jpg"
    remotion_render(target, composition, video, [f"--scale={DRAFT_SCALE}", "--codec=h264"])
    # amostra 1 quadro a cada 1,5 s; videos longos espalham os 44 quadros da folha 11x4 pela duracao toda
    fps = sheet_fps(media_duration(video))
    proc = subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(video), "-vf", SHEET_FILTER.format(fps=fps),
                           "-frames:v", "1",
                           "-q:v", "3", str(sheet)], capture_output=True, text=True)
    if proc.returncode != 0 or not sheet.is_file():
        raise SystemExit(f"[!!] nao consegui montar a folha de contatos: {proc.stderr.strip()[-400:]}")
    return sheet


def _brand_arg(ref: str | None, project_id: str | None = None) -> Path | None:
    """--brand: slug de .scroll-stopper/marcas ou pasta com brand.json (marca efemera, fora da pasta de trabalho).

    Sem --brand, usa a marca do ultimo `ss brand use`/render deste projeto (engine.project_brand), se houver.
    """
    if not ref:
        if not project_id:
            return None
        try:
            return engine.project_brand(project_id)
        except engine.RecordedBrandMissing as exc:
            raise SystemExit(f"[!!] {exc}")
    from ss_lib.brand import BrandNotFound, resolve_brand

    try:
        return resolve_brand(ref)
    except BrandNotFound as exc:
        raise SystemExit(f"[!!] {exc}")


def _check_id(project_id: str) -> None:
    try:
        paths.work_dir(project_id)
    except ValueError as exc:
        raise SystemExit(f"[!!] id de projeto invalido: {exc}")


def guard(fn):
    """Roda fn e troca erros do engine por mensagens curtas em portugues."""
    try:
        return fn()
    except engine.EngineNotInstalled as exc:
        raise SystemExit(f"[!!] {exc}. Rode: ss setup")
    except engine.BrandActivationError as exc:
        raise SystemExit(f"[!!] nao consegui ativar a marca: {exc}")


def main_render(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="ss render", description="Render final com loudness normalizado.")
    ap.add_argument("project_id")
    ap.add_argument("composition", help="ex.: Template-m, PresenterTemplate-m, SimpleClip-m")
    ap.add_argument("--dest", required=True, help="pasta onde o .mp4 final sera salvo")
    ap.add_argument("--name", required=True, help="nome do arquivo (sem .mp4)")
    ap.add_argument("--lufs", type=float, help="alvo de loudness (padrao: -14 apresentador/clipe, inclusive projeto com "
                    "media/video/presenter.mp4; -15 motion)")
    ap.add_argument("--brand", help="slug da marca em .scroll-stopper/marcas ou pasta com brand.json "
                    "(padrao: a ultima usada no projeto, senao a neutra)")
    args = ap.parse_args(argv)
    _check_id(args.project_id)
    lufs = args.lufs if args.lufs is not None else default_lufs(args.composition, args.project_id)
    brand = _brand_arg(args.brand, args.project_id)
    final, report = guard(lambda: render_checked(args.project_id, args.composition, Path(args.dest), args.name,
                                                 lufs, brand))
    print(report_line(report, final, f"video final ({lufs:g} LUFS)"))
    return 0  # o arquivo foi entregue; o aviso acima diz o que conferir


def main_draft(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="ss draft", description="Rascunho em meia escala com folha de contatos.")
    ap.add_argument("project_id")
    ap.add_argument("composition")
    ap.add_argument("--brand", help="slug da marca ou pasta com brand.json (padrao: a ultima usada no projeto)")
    args = ap.parse_args(argv)
    _check_id(args.project_id)
    brand = _brand_arg(args.brand, args.project_id)
    sheet = guard(lambda: draft(args.project_id, args.composition, brand))
    print(f"[ok] rascunho:        {sheet.with_name('draft.mp4')}")
    print(f"     folha de contato: {sheet}")
    return 0


if __name__ == "__main__":
    sys.exit(main_render())
