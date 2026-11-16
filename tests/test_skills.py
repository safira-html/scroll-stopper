"""Skills e base de conhecimento: frontmatter, comandos `ss` que existem e conteúdo neutro."""
import hashlib
import re
from pathlib import Path

import pytest

from conftest import ROOT
from test_manifests import FORBIDDEN

SKILLS_DIR = ROOT / "skills"
KNOWLEDGE_DIR = ROOT / "knowledge"
EXPECTED_SKILLS = {
    "editar-video", "onboarding-de-marca", "corte", "apresentador-com-motion",
    "motion-narrado", "cortes-de-video-longo", "incorporar-aprendizados",
}
# skills de caminho: anotam correções localmente e nunca publicam nada
PATH_SKILLS = EXPECTED_SKILLS - {"incorporar-aprendizados"}
DESCRIPTION_MAX = 1024
# conteúdo do caso de origem que não pode aparecer nos textos genéricos
CASE_SPECIFIC = re.compile(
    r"\bc2\d{3}\b|\bad0\d\d\b|pinterest\.com|safira|slack|caso de origem|\bvagas\b")
# nomes de pessoas e empresas do caso de origem: guardados só como hash para não publicá-los
CASE_SPECIFIC_WORD_HASHES = {"1ba4c99ebf974ed2", "61bab03dc44bdbc5", "e4ffb7bd879b89da"}
WORD = re.compile(r"[a-z0-9]+")


def case_specific_word(text: str) -> str | None:
    for word in WORD.findall(text):
        if hashlib.sha256(word.encode()).hexdigest()[:16] in CASE_SPECIFIC_WORD_HASHES:
            return word
    return None
SS_TOKEN = re.compile(r"(?<![\w/-])ss ([a-z][a-z0-9-]*)(?: ([a-z][a-z0-9-]*))?")
SUBCOMMAND_MODULES = {"workspace", "brand", "kit", "clips"}


def skill_files() -> list[Path]:
    return sorted(SKILLS_DIR.glob("*/SKILL.md"))


def text_files() -> list[Path]:
    return skill_files() + sorted(KNOWLEDGE_DIR.rglob("*.md"))


def frontmatter(path: Path) -> dict:
    """Frontmatter YAML simples (chave: valor numa linha), sem dependências."""
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n"), f"{path}: sem frontmatter"
    end = text.index("\n---\n", 4)
    data = {}
    for line in text[4:end].splitlines():
        if not line.strip():
            continue
        key, sep, value = line.partition(":")
        assert sep and key.strip() and not key.startswith(" "), f"{path}: linha de frontmatter inválida: {line!r}"
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        data[key.strip()] = value
    return data


def dispatchable_commands() -> set[str]:
    """Allowlist do bin/ss (linha do `case "$CMD" in`), cada um com modulo ss_lib e ponto de entrada."""
    source = (ROOT / "bin" / "ss").read_text(encoding="utf-8")
    line = re.search(r'case "\$CMD" in\n\s*([a-z|-]+)\)', source).group(1)
    commands = set(line.split("|"))
    for cmd in commands:
        module = ROOT / "ss_lib" / f"{cmd.replace('-', '_')}.py"
        assert module.is_file() and '__name__ == "__main__"' in module.read_text(encoding="utf-8"), cmd
    return commands


def subcommands(command: str) -> set[str]:
    source = (ROOT / "ss_lib" / f"{command}.py").read_text(encoding="utf-8")
    return set(re.findall(r'add_parser\("([a-z-]+)"', source))


def test_expected_skills_exist():
    assert {p.parent.name for p in skill_files()} == EXPECTED_SKILLS


@pytest.mark.parametrize("path", skill_files(), ids=lambda p: p.parent.name)
def test_frontmatter_name_and_description(path):
    meta = frontmatter(path)
    assert meta.get("name") == path.parent.name
    assert meta.get("description"), f"{path}: description vazia"
    assert len(meta["description"]) <= DESCRIPTION_MAX
    # valor YAML sem aspas: ": " ou " #" no meio quebraria o parser de quem carrega a skill
    raw = next(ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.startswith("description:"))
    value = raw.split(":", 1)[1].strip()
    if value[:1] not in "\"'":
        assert ": " not in value and " #" not in value, f"{path}: description precisa de aspas"


def test_every_ss_command_exists():
    known = dispatchable_commands()
    for path in text_files():
        for cmd, sub in SS_TOKEN.findall(path.read_text(encoding="utf-8")):
            assert cmd in known, f"{path}: `ss {cmd}` não existe no bin/ss"
            if cmd in SUBCOMMAND_MODULES and sub:
                assert sub in subcommands(cmd), f"{path}: `ss {cmd} {sub}` não existe"


def test_skills_reference_existing_knowledge_files():
    for path in skill_files():
        for rel in re.findall(r"knowledge/[\w/.-]+\.md", path.read_text(encoding="utf-8")):
            assert (ROOT / rel).is_file(), f"{path}: {rel} não existe"


def test_entry_skill_confirms_path_and_brand():
    lines = (SKILLS_DIR / "editar-video" / "SKILL.md").read_text(encoding="utf-8").lower().splitlines()
    confirm = [ln for ln in lines if "confirm" in ln]
    assert any("caminho" in ln for ln in confirm), "editar-video não confirma o caminho"
    assert any("marca" in ln for ln in confirm), "editar-video não confirma a marca"


@pytest.mark.parametrize("name", sorted(PATH_SKILLS))
def test_path_skills_record_learnings_and_never_push(name):
    text = (SKILLS_DIR / name / "SKILL.md").read_text(encoding="utf-8")
    assert f"ss workspace learn" in text and f"--source {name}" in text
    assert "git push" not in text


def test_maintainer_skill_bumps_version_and_changelog():
    text = (SKILLS_DIR / "incorporar-aprendizados" / "SKILL.md").read_text(encoding="utf-8")
    for needle in (".claude-plugin/plugin.json", "CHANGELOG.md", "git push"):
        assert needle in text
    assert (ROOT / "CHANGELOG.md").read_text(encoding="utf-8").count("0.1.0") >= 1


@pytest.mark.parametrize("path", text_files(), ids=lambda p: str(p.relative_to(ROOT)))
def test_no_brand_or_case_specific_content(path):
    text = path.read_text(encoding="utf-8").lower()
    assert not FORBIDDEN.search(text), path
    found = CASE_SPECIFIC.search(text)
    assert not found, f"{path}: conteúdo do caso de origem: {found.group(0)!r}"
    word = case_specific_word(text)
    assert not word, f"{path}: nome do caso de origem: {word!r}"


GUARDED_SKILLS = PATH_SKILLS - {"editar-video"}


@pytest.mark.parametrize("name", sorted(GUARDED_SKILLS))
def test_path_skills_send_unconfirmed_requests_to_entry_skill(name):
    """Sem caminho e marca confirmados pela skill de entrada nesta conversa, a skill de caminho chama a entrada."""
    text = (SKILLS_DIR / name / "SKILL.md").read_text(encoding="utf-8")
    guard = next((ln for ln in text.splitlines() if ln.startswith("**Antes de tudo:**")), "")
    assert "`scroll-stopper:editar-video`" in guard and "chame-a primeiro" in guard


@pytest.mark.parametrize("name", ["corte", "cortes-de-video-longo"])
def test_cut_skills_read_learnings(name):
    assert ".scroll-stopper/aprendizados.md" in (SKILLS_DIR / name / "SKILL.md").read_text(encoding="utf-8")


@pytest.mark.parametrize("path", skill_files(), ids=lambda p: p.parent.name)
def test_skills_use_cli_not_raw_media_tools(path):
    """Skills usam o CLI (`ss probe`, `ss finalize`, `ss brand new`), não ffprobe nem cópias manuais."""
    text = path.read_text(encoding="utf-8")
    for needle in ("ffprobe", "cp -R", "--lufs -14"):
        assert needle not in text, f"{path}: {needle!r}"
