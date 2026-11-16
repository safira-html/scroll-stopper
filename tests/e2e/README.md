# Testes de ponta a ponta (e2e)

Smoke dos três caminhos pelo CLI de verdade (cada teste confere também que a pasta de entrega só tem os arquivos esperados e que nenhum `.mp4` novo apareceu na pasta de trabalho): cada passo roda `bin/ss ...` em subprocesso, na mesma ordem que as
skills mandam, a partir de uma pasta de trabalho temporária (`ss workspace init`) e entregando numa pasta com
espaço e acento no caminho (`Meu Drive/Vídeos finais`).

| teste | caminho | o que roda |
|---|---|---|
| `test_path_a` | A, apresentador + motion (skills `corte` e `apresentador-com-motion`) | `setup --check`, marca e kit de som da pasta de trabalho, `workspace learn`, `probe`, `transcribe`, `corte.json` com o último take, `cut` (confere a duração do corte em 1x e retranscreve: o falso início não pode aparecer), `prepare-presenter`, `brand use`, composição `<id>-m` copiada do `PresenterTemplate` e registrada no engine do projeto, `draft`, `render` (−14 LUFS), `qa` |
| `test_path_b` | B, motion + narração (skill `motion-narrado`) | `align` sem roteiro, `brand use`, composição `<id>-m` copiada do `Template`, `render` (−15 LUFS), `qa` |
| `test_path_c` | C, vídeo longo em cortes (skill `cortes-de-video-longo`) | vídeo de 6 min, `transcribe`, `clips windows`, `candidatos.json` fixo, `clips validate`, `clips render --ids 1,2 --style simples --dest`, `qa` de cada clipe (−14 LUFS, 15–60 s) |

A mídia é gerada na hora com `say` e `ffmpeg` (voz do sistema sobre `testsrc2`), fica no tmp do pytest e nunca
entra no repositório. As pastas `~/.cache/scroll-stopper/work/e2e-*` criadas pelos testes são apagadas no fim,
passando ou falhando.

## Pré-requisitos

- macOS com a voz `Luciana` (português do Brasil) do `say`.
- Ambiente pronto: `bin/ss setup` (venv, modelo de transcrição, engine com `node_modules` e navegador).
- Engine em cache igual ao do repositório. Os renders usam a cópia em `~/.cache/scroll-stopper/engine/<versão>/`;
  depois de mudar `engine/`, rode `bin/ss setup` de novo. O e2e confere (`diff -rq` de `engine/` inteiro, menos
  `node_modules` e `out`) e falha com essa instrução se estiver diferente.

## Como rodar

```bash
export PATH="$HOME/.local/bin:/opt/homebrew/bin:$PATH"
bin/ss setup
~/.cache/scroll-stopper/venv/bin/python -m pytest -m e2e -v -s
```

Um caminho só: acrescente `-k path_a`, `-k path_b` ou `-k path_c`. O `-s` mostra cada comando com o tempo que
levou. O `pytest` sem `-m e2e` não roda estes testes (o `pyproject.toml` tira o marcador `e2e` do padrão).

## Tempo esperado

Numa máquina Apple Silicon, com o modelo e o engine já instalados:

- caminho A: cerca de 1,5 min;
- caminho B: cerca de 1 min;
- caminho C: alguns minutos (a transcrição do vídeo de 6 min e o render de dois clipes dominam o tempo).
