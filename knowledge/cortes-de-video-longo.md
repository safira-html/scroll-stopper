# Cortes de vídeo longo (caminho C)

Como transformar um vídeo longo (aula, live, podcast, entrevista) em cortes curtos que funcionam sozinhos no feed.
O método de seleção e a nota vêm do SupoClip (https://github.com/FujiwaraChoki/supoclip, licença AGPL-3.0),
adaptados para o Scroll Stopper. Os arquivos citados abaixo são do repositório do SupoClip (commit `5c99c18`).
Copyright (C) 2025  Sami Hindi (AGPL-3.0).

## Passo a passo

1. Vídeo: o arquivo do usuário em `media/video/source.mp4` do projeto, ou `ss download <link> <id>`.
   Se o download falhar, peça o arquivo e lembre de conferir se o vídeo é público e se há direito de uso.
2. `ss transcribe <source.mp4> <id>`: palavras com tempo e `transcript.txt` (uma linha por trecho, `[ini-fim] texto`).
3. `ss clips windows <id>`: divide a transcrição em janelas (`transcript/window-01.txt`, ...) e diz quantos cortes entregar.
4. O Claude lê **cada janela inteira** e escreve `projetos/<id>/candidatos.json` (formato abaixo).
5. `ss clips validate <id> [--preset short|medium|long|auto]`: encaixa nas frases, descarta, recalcula a nota, remove repetidos e numera.
6. Mostre a lista ao usuário (título, nota, duração, trecho falado) e pergunte quais cortes ele quer.
7. `ss clips render <id> --ids 1,3,5 --style simples --dest <pasta>` (vídeo + legenda karaokê + logo opcional com `--logo`;
   com `--dest`, cada corte vai para `<pasta>/<id>-clip-<n>.mp4`)
   ou `--style dinamico` (só corta; cada corte segue pelo caminho A com `ss prepare-presenter`).

## Janelas e quantidade de cortes

- Até 15 min de vídeo: uma janela só, com a transcrição inteira.
- Acima disso: janelas de 12 min que se sobrepõem 2 min (começam em 0, 10, 20 min, ...). Uma janela final com
  menos de 6 min é juntada à anterior. Fonte: `backend/src/ai.py` (`ANALYSIS_WINDOW_SECONDS`,
  `ANALYSIS_WINDOW_OVERLAP_SECONDS`, `ANALYSIS_SINGLE_WINDOW_MAX_SECONDS`, `split_transcript_into_windows`).
  Justificativa deste plugin (não do SupoClip): assim nenhum trecho fica sem atenção e um momento na emenda
  aparece inteiro em pelo menos uma janela.
- Em cada janela, procure de 3 a 5 candidatos (`ANALYSIS_WINDOW_SEGMENT_TARGET = "3-5"` em `backend/src/ai.py`).
  Menos e melhores é melhor do que encher cota.
- Quantidade final: um corte a cada 5 min de vídeo, no mínimo 5 e no máximo 20 (`round(duração_s / 300)`, limitado
  a 5–20). O SupoClip usa a mesma regra com arredondamento para cima (`max_final_clips_for_duration`, constantes
  `MIN_FINAL_CLIPS`, `MAX_FINAL_CLIPS`, `SECONDS_PER_FINAL_CLIP` em `backend/src/ai.py`); aqui o arredondamento é
  para o inteiro mais próximo.

## Durações por preset

Fonte: `CLIP_DURATIONS` em `backend/src/clip_duration.py`.

| preset | aceito | ideal |
|---|---|---|
| `short` | 15–30 s | 18–25 s |
| `medium` | 30–60 s | 35–55 s |
| `long` | 60–120 s | 75–110 s |
| `auto` | 15–60 s | 25–50 s |

Mire no ideal: a validação ainda move as bordas até a frase mais próxima, e isso pode alongar o corte.

## O que escolher

Bons cortes (critérios do prompt de seleção em `backend/src/ai.py`):
- afirmação contrária ao senso comum, erro ou lição, exemplo concreto, antes e depois, passo a passo, resultado
  surpreendente, reação com emoção, resposta completa a uma pergunta interessante;
- o trecho se entende sozinho: tem a preparação mínima e o fecho (payoff);
- se o momento bom é uma frase só, inclua a preparação e o fecho em volta; pare quando o assunto muda ou o
  falante se repete.

Evite: abertura e apresentação, patrocínio ou chamada para ação, preparação vaga, citação solta sem contexto,
ponto repetido, definição sem consequência, rodeio, resposta que depende de algo que o espectador não viu, e
trechos em que a imagem está quebrada ou parada ("a imagem caiu", "voltamos já").

### Começo e fim do corte

- Começa na primeira palavra de uma frase que alguém sem contexto entende. Não comece no meio da frase, em
  muleta ("tipo", "né", "então"), em concordância solta ("isso", "exato"), em pronome que aponta para alguém que
  o espectador não conhece, em referência ao que veio antes ("como eu falei") nem em conjunção que continua outro
  ponto ("mas o principal motivo...").
- Termina na última palavra da frase que fecha o ponto, sem pegar o começo do próximo assunto.
- A primeira frase é o gancho: julgue os primeiros segundos sozinhos. Abertura que depende de contexto perdido
  baixa a nota de gancho.

## Nota: 4 critérios de 0 a 25 (total 0–100)

Fonte: `VIRALITY SCORING` no prompt e `ViralityAnalysis` em `backend/src/ai.py`. A validação limita cada nota
a 0–25 e recalcula `total` como a soma das quatro (o total escrito pelo Claude é ignorado).

**Gancho (`hook`)**: os primeiros segundos fazem quem está rolando o feed parar?
- 20–25: prende na hora (fato surpreendente, afirmação forte, pergunta intrigante)
- 15–19: boa abertura, cria curiosidade
- 10–14: começo razoável, poderia ser mais forte
- 0–9: gancho fraco ou ausente

**Envolvimento (`engagement`)**: o trecho segura a atenção até o fim?
- 20–25: muito envolvente, com emoção ou tensão
- 15–19: interessante, segura a atenção
- 10–14: moderadamente envolvente
- 0–9: entrega sem energia

**Valor (`value`)**: o que a pessoa leva?
- 20–25: ideia aplicável, conhecimento raro ou que muda a forma de ver
- 15–19: informação útil que a maioria não sabe
- 10–14: um pouco informativo
- 0–9: senso comum ou enchimento

**Compartilhamento (`shareability`)**: alguém mandaria para outra pessoa?
- 20–25: "preciso mandar isso para alguém"
- 15–19: vale salvar
- 10–14: legal, mas ninguém compartilha
- 0–9: genérico

Tipo de gancho (`hook_type`), da lista em `backend/src/ai.py`: `question` (pergunta que cria curiosidade),
`statement` (afirmação forte), `statistic` (número que chama atenção), `story` (começa contando uma história),
`contrast` (antes e depois, problema e solução), `none` (sem padrão claro). Valor fora da lista vira `none`.

Seja honesto na nota: espalhe os valores para que os melhores fiquem claramente acima (do prompt de
reordenação em `backend/src/ai.py`, linha 636). A justificativa (`reasoning`) cita o que está de fato no trecho
escolhido.

## O que a validação faz (`ss clips validate`)

Baseado em `backend/src/ai.py`:
- **Encaixe nas frases** (`_snap_bounds_to_transcript_lines`, `SEGMENT_SNAP_TOLERANCE_SECONDS = 8`): o início vai
  para o começo de frase mais próximo e o fim para o final de frase mais próximo, se estiverem a até 8 s. Mais
  longe que isso, o candidato sai. No SupoClip o encaixe é na linha da transcrição; aqui é na frase, pela
  pontuação final das palavras do Whisper.
- **Duração**: depois do encaixe, fora da faixa aceita do preset, o candidato sai.
- **Repetidos** (`dedupe_overlapping_segments`, `CANDIDATE_DEDUPE_OVERLAP_RATIO = 0.5`): janelas que se sobrepõem
  podem achar o mesmo momento duas vezes. Se dois candidatos dividem mais de 50% do mais curto, fica o de maior total.
- Ordena do maior para o menor total e guarda só a quantidade final de cortes. Candidato que já tem `id` mantém o
  número (validar de novo não muda o que o usuário escolheu); os novos ganham números depois do maior.
- Mostra cada descartado com o motivo (início/fim inválido, nenhum limite de frase a até 8 s, duração fora do
  preset, repete outro candidato, acima do limite). Use isso para escolher outro trecho e validar de novo.

## Formato do `candidatos.json`

O Claude escreve em `.scroll-stopper/projetos/<id>/candidatos.json` (tempos em segundos do vídeo longo,
tirados das linhas `[ini-fim]` da janela; títulos e justificativas em português):

```json
{
  "preset": "short",
  "candidates": [
    {
      "start": 754.2,
      "end": 781.9,
      "title": "O erro que trava quem está começando",
      "hook_type": "statement",
      "scores": {"hook": 21, "engagement": 17, "value": 19, "shareability": 16},
      "total": 73,
      "reasoning": "Abre com uma afirmação forte e fecha com o exemplo que comprova o ponto."
    }
  ]
}
```

- `title`: manchete curta (3 a 9 palavras) fiel ao trecho, sem hashtag, emoji ou aspas; nunca prometa o que o
  trecho não entrega nem invente número.
- `"source": "<caminho>"` (opcional) usa outro vídeo em vez de `media/video/source.mp4`; caminho relativo é
  contado a partir da pasta que contém `.scroll-stopper/`.
- Depois do `ss clips validate`, o arquivo ganha `validated: true`, `id` e `duration` em cada candidato; o
  `ss clips render` só aceita o arquivo validado.

## Render

- `simples`: cada corte vira `<pasta de --dest>/<id>-clip-<n>.mp4` (sem `--dest`, `projetos/<id>/clips/clip-<n>.mp4`; 1080×1920, 30 fps), com o plano médio do vídeo,
  legenda karaokê em blocos de 2 a 4 palavras montados automaticamente e logo da marca no topo com `--logo`
  (`--brand <slug|pasta>` escolhe a marca; sem ele, a última usada no projeto ou a neutra). O áudio é o do próprio corte; a loudness de entrega
  (−14 LUFS) é aplicada na finalização.
- `dinamico`: só corta; o comando mostra o `ss prepare-presenter` de cada corte para seguir pelo caminho A.
- Os cortes intermediários ficam no cache (`~/.cache/scroll-stopper/work/<id>-c<n>/`), nunca na pasta sincronizada.
