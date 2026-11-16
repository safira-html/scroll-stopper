---
name: cortes-de-video-longo
description: Caminho C do Scroll Stopper - transforma um vídeo longo (aula, live, podcast, entrevista), por arquivo ou link, em vários cortes curtos para Reels com os trechos mais fortes. Transcreve, lê a transcrição em janelas, escolhe candidatos com nota de 0 a 100, valida, mostra a tabela para a pessoa escolher e renderiza só os escolhidos, no estilo simples (corte e legenda) ou dinâmico (como o caminho A). Use depois que o caminho C e a marca foram confirmados na skill editar-video.
---

# Cortes de vídeo longo (caminho C)

**Antes de tudo:** se o caminho e a marca ainda não foram confirmados nesta conversa pela skill `scroll-stopper:editar-video`, chame-a primeiro e só volte aqui depois da confirmação.

Método completo, critérios e formato do `candidatos.json`: `${CLAUDE_PLUGIN_ROOT}/knowledge/cortes-de-video-longo.md` (leia inteiro antes de escolher trechos). Leia também `.scroll-stopper/aprendizados.md`: as correções de escolha de trecho que esta pessoa já fez valem aqui.

O CLI é `"${CLAUDE_PLUGIN_ROOT}/bin/ss"` (abaixo, `ss`; também fica no PATH do Bash com o plugin ativo). Rode a partir da pasta de trabalho e use aspas em caminhos com espaço. `<id>` é o id do projeto; `<marca>` é o slug confirmado (ou a pasta da marca efêmera).

## Passo a passo

1. **Vídeo.**
   - **Link:** antes de baixar, lembre a pessoa de que ela precisa ter direito de usar aquele conteúdo e espere a confirmação. Então `ss download "<link>" <id>`. O vídeo fica em `~/.cache/scroll-stopper/work/<id>/media/video/source.mp4` (é esse caminho que vai no `ss transcribe` e que o `ss clips render` usa sozinho). Se falhar, peça o arquivo.
   - **Arquivo:** use o caminho dele; no passo 4, ponha `"source": "<caminho absoluto>"` no `candidatos.json`.
2. **Duração dos cortes:** pergunte o preset — `short` (15–30 s), `medium` (30–60 s), `long` (60–120 s) ou `auto` (15–60 s, padrão) — e o estilo de cada corte: **simples** (corte + legenda karaokê + logo opcional) ou **dinâmico** (como o caminho A).
3. **Transcreva e divida:**
   ```bash
   ss transcribe "<video: o arquivo da pessoa ou ~/.cache/scroll-stopper/work/<id>/media/video/source.mp4>" <id>
   ss clips windows <id>
   ```
   O `windows` diz quantas janelas há (12 min com 2 min de sobreposição; até 15 min, uma só) e quantos cortes entregar (um a cada 5 min, entre 5 e 20).
4. **Escolha candidatos janela por janela:** leia **cada** `~/.cache/scroll-stopper/work/<id>/transcript/window-NN.txt` inteira e anote de 3 a 5 candidatos por janela, com os critérios do guia (gancho forte, exemplo concreto, contraste, erro e lição, antes e depois, resposta completa; fora: abertura, patrocínio, CTA, preparação vaga, trecho que depende de contexto). Para cada um: `start`, `end`, `title` fiel ao trecho, `hook_type`, as 4 notas de 0 a 25 e `reasoning`. Escreva todos em `.scroll-stopper/projetos/<id>/candidatos.json`, com o `preset`.
5. **Valide:** `ss clips validate <id>` (ou com `--preset <preset>`). O comando encaixa nas frases, descarta e explica o porquê, remove repetidos, ordena pela nota e numera. Se algum bom trecho foi descartado, ajuste e valide de novo.
6. **Mostre a tabela e espere a escolha:** id, título, nota (0–100), duração e a primeira frase de cada candidato válido. Pergunte quais cortes renderizar e, se ainda não decidido, o estilo. Não renderize nada antes da resposta.
7. **Renderize os escolhidos:**
   - simples: `ss clips render <id> --ids 1,3,5 --style simples --brand <marca> --dest "<pasta de entrega>"` (acrescente `--logo` para o logo da marca no topo). A pasta de entrega é a combinada na skill de entrada; cada corte sai em `<pasta de entrega>/<id>-clip-<n>.mp4`, 1080×1920, −14 LUFS;
   - dinâmico: `ss clips render <id> --ids 2,4 --style dinamico`. O comando só corta e mostra, para cada corte, o `ss prepare-presenter` a rodar com o id `<id>-c<n>`. Rode-o e siga a skill `scroll-stopper:apresentador-com-motion` com esse id (a composição será `<id>-c<n>-m`; o render dela sai em −14 LUFS sozinho).
8. **Confira** cada clipe simples: duração, primeira e última frase (o corte começa e termina em frase inteira) e o resultado da conferência que o comando imprime. Se aparecer `[!!] Conferência falhou`, explique e corrija.
9. **Entregue:** liste o caminho completo de cada arquivo final e o que cada corte fala (não só o número).

## Regras

- Leia cada janela inteira; não escolha trechos só pela busca de palavras.
- Título nunca promete o que o trecho não entrega nem inventa número.
- Nada é renderizado antes da escolha da pessoa.
- Download só depois do lembrete de direito de uso. Nunca publique os cortes e nunca envie nada para o GitHub.

## Aprendizados

Quando a pessoa corrigir uma escolha (um trecho que não deveria entrar, um começo ruim, um título), anote na hora:

```bash
ss workspace learn "<o que foi corrigido e a regra que fica>" --source cortes-de-video-longo
```
