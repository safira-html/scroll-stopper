---
name: corte
description: Corta o bruto de alguém falando para a câmera (caminho A do Scroll Stopper e limpeza de gravações) - transcreve, decide o que sai (claquete, falso início, take repetido ficando o último completo, conversa de set, pausa longa, ruído de voz), escreve o corte.json, corta encostado no silêncio e prepara o corte para o motion resolvendo os avisos antes do render. Use depois que o caminho e a marca foram confirmados na skill editar-video.
---

# Corte do bruto

**Antes de tudo:** se o caminho e a marca ainda não foram confirmados nesta conversa pela skill `scroll-stopper:editar-video`, chame-a primeiro e só volte aqui depois da confirmação.

Regras e porquês: `${CLAUDE_PLUGIN_ROOT}/knowledge/cortes.md` (leia inteiro antes de decidir o corte). Leia também `.scroll-stopper/aprendizados.md`: as correções de corte que esta pessoa já fez valem aqui.

O CLI é `"${CLAUDE_PLUGIN_ROOT}/bin/ss"` (abaixo, `ss`; também fica no PATH do Bash com o plugin ativo). Rode a partir da pasta de trabalho e use aspas em caminhos com espaço. `<id>` é o id do projeto definido na entrada (letras minúsculas, números, hífen).

## Passo a passo

1. **Transcreva:** `ss transcribe "<bruto>" <id>`. Saem `words.json` e `transcript.txt` em `~/.cache/scroll-stopper/work/<id>/transcript/`.
2. **Leia o `transcript.txt` inteiro** e decida o que sai, pelas regras de `cortes.md`:
   - claquete e conversa de set saem; leitura incerta antes do roteiro (palavra com `p` < ~0,9 ou nome solto) é claquete até prova em contrário: **pergunte**;
   - falso início sai;
   - take repetido: **fica o último take completo**;
   - comentário no meio e sobra depois da última fala saem;
   - pausas longas são encurtadas sozinhas.
   Na dúvida sobre uma fala, pergunte à pessoa citando o tempo ("aos 41 s você repete a frase; fico com a segunda?").
3. **Escreva** `.scroll-stopper/projetos/<id>/corte.json` com `source` (caminho absoluto do bruto), `keep` (trechos em segundos, na ordem do vídeo), `_keep` (o porquê de cada trecho que ficou ou saiu) e, se a sala tem ruído, `"silence_db": -28`. Para tirar algo do meio de um take, quebre o take em dois.
4. **Corte:** `ss cut ".scroll-stopper/projetos/<id>/corte.json"`. Sai `~/.cache/scroll-stopper/work/<id>/cut_1x.mp4`.
5. **Prepare para o motion:** `ss prepare-presenter ~/.cache/scroll-stopper/work/<id>/cut_1x.mp4 <id>` (velocidade automática pelo ritmo de fala, ~184 palavras/min, entre 1,0x e 1,3x; para forçar, `--speed 1.0`).
6. **Resolva todos os avisos antes de seguir** (tabela em `cortes.md`):
   - `STRETCHED`: retranscreva só aquele trecho do bruto como clipe curto (receita em `cortes.md`, com `ss transcribe` num id `<id>-trecho`); achando take repetido, refaça o `keep` a partir do último take completo;
   - `LONG SHORT WORD` e `NOISE`: diga o tempo à pessoa, peça para ela ouvir e, confirmado, quebre o take no `keep` para tirar o trecho;
   - depois de mudar o `corte.json`, rode de novo `ss cut` e `ss prepare-presenter` até não sobrar aviso sem decisão.
7. **Mostre o resultado:** duração final, quantos trechos ficaram e o que saiu (resuma o `_keep`). Ofereça o arquivo `cut_1x.mp4` para ela assistir.
8. **Siga:** no caminho A, chame `scroll-stopper:apresentador-com-motion` com o id. Se a pessoa quiser **só o corte**, sem motion, entregue com o volume normalizado (−14 LUFS) na pasta que ela escolheu (o `ss finalize` converte o corte de 1440×2560 para 1080×1920 a 30 fps antes de normalizar):
   ```bash
   ss finalize ~/.cache/scroll-stopper/work/<id>/cut_1x.mp4 --dest "<pasta de entrega>" --name <nome>
   ```
   O comando imprime o caminho final; diga esse caminho à pessoa.

## Regras

- Corte só depois de ler a transcrição inteira; nunca no escuro.
- Nunca corte no tempo do Whisper sem o `ss cut` (ele encosta a borda no silêncio medido).
- Jump cut na emenda é aceito; não invente transição para escondê-lo no corte puro.
- O bruto nunca é alterado; tudo pesado fica em `~/.cache/scroll-stopper/`.
- Nunca envie nada para o GitHub e nunca publique o vídeo.

## Aprendizados

Quando a pessoa corrigir uma decisão de corte (o que saiu, o que ficou, um ruído que passou), anote na hora:

```bash
ss workspace learn "<o que foi corrigido e a regra que fica>" --source corte
```
