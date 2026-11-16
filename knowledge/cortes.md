# Cortes: o que sai do bruto e onde cortar

Vale para o caminho A (apresentador) e para a limpeza de qualquer gravação de alguém falando. No caminho C a escolha dos trechos segue [cortes-de-video-longo.md](cortes-de-video-longo.md); o corte em si usa a mesma máquina.

**A transcrição diz O QUE foi falado; o silêncio medido diz ONDE cortar.** Nunca corte no tempo do Whisper sem encostar no silêncio: na prática ele erra a borda da palavra em até ~0,2 s, e o corte decapita a sílaba (medido nas gravações que deram origem a estas regras; não é especificação do Whisper).

## Fluxo

1. `ss transcribe <bruto> <id>`: palavras com tempo (`words.json`, com a probabilidade `p` de cada palavra) e `transcript.txt` em `~/.cache/scroll-stopper/work/<id>/transcript/`. A transcrição roda **sem VAD** de propósito: com VAD ligado, a claquete e os takes repetidos somem da transcrição e você não consegue decidir o corte.
2. Leia o `transcript.txt` inteiro e escreva `.scroll-stopper/projetos/<id>/corte.json` (formato abaixo).
3. `ss cut .scroll-stopper/projetos/<id>/corte.json`: corta e grava `cut_1x.mp4` no cache do projeto. O id do projeto é o nome da pasta onde está o `corte.json`.
4. `ss prepare-presenter <cut_1x.mp4> <id>`: acerta a velocidade pelo ritmo de fala e lista os pontos suspeitos (seção "Avisos").
5. Resolva cada aviso **antes** do render final.
6. Se a entrega é **só o corte** (sem motion): `ss finalize ~/.cache/scroll-stopper/work/<id>/cut_1x.mp4 --dest "<pasta>" --name <nome>` converte para 1080×1920 a 30 fps (o corte sai em 1440×2560), normaliza o volume para −14 LUFS e copia para a pasta de entrega.

## O que sai (decisão editorial)

| Sai | Exemplo (fictício) |
|---|---|
| Claquete e conversa de set | "foi câmera, foi foco… ação"; "esse aqui é o segundo vídeo, 1, 2, 3, gravando" |
| Sobra depois da última fala do roteiro | "beleza, acho que foi" depois do CTA |
| Falso início | "Responda uma rápida…" retomado dois segundos depois |
| Take repetido: **fica sempre o último take completo** | a pessoa termina, diz "deixa eu fazer de novo" e grava outra vez: fica a segunda |
| Comentário no meio | "ah, não, falta uma coisa… vou de novo" |
| Pausa longa | automático: toda pausa maior que `max_pause` (0,45 s) vira ~0,25 s (0,15 s depois da fala + 0,10 s antes da próxima) |

**Registre o porquê** no campo `_keep` do `corte.json`. É o que permite a outra pessoa (ou outra sessão) entender a edição sem assistir ao bruto.

### Claquete falada nunca vai para a legenda

Antes do roteiro, quem grava costuma dizer qual vídeo é ("vídeo 3", "ADS01"). Isso é identificação de arquivo, não roteiro. O Whisper costuma ler a sigla como um nome de pessoa (numa gravação, "ADS01" virou "Edson"). Então:

- desconfie da primeira palavra do primeiro take quando a probabilidade (`p` no `words.json`) é menor que ~0,9, ou quando é um nome próprio solto antes do começo do roteiro;
- para provar: transcreva só esse trecho como clipe curto (receita na seção "Retranscrever um trecho") e/ou **pergunte**;
- **leitura incerta antes do roteiro é claquete até prova em contrário.** Na dúvida, não legende e pergunte. Nunca transforme uma leitura incerta em texto fixo;
- comece o primeiro take no silêncio entre a claquete e a primeira palavra do roteiro.

## Formato do `corte.json`

```json
{
  "source": "~/Videos/bruto.mov",
  "keep": [[8.62, 11.96], [66.06, 72.00]],
  "_keep": "8,6–12,0: gancho (último take completo; o primeiro tinha falso início). 66–72: CTA. Fora: claquete 0–8,6 e conversa de set.",
  "silence_db": -35,
  "max_pause": 0.45,
  "pad_before": 0.10,
  "pad_after": 0.15,
  "output_size": [1440, 2560]
}
```

- `keep`: trechos mantidos, em segundos do bruto, na ordem em que entram no vídeo. Tire os tempos das palavras do `words.json`.
- Para tirar um pedaço do meio de um take, **quebre o take em dois** no `keep`. Não existe lista de "remover".
- `output_size` maior que 1080×1920 (o padrão é 1440×2560) dá margem para os punch-ins do caminho A sem perder nitidez.
- Os demais campos têm padrão; só mude quando precisar (sala com ruído, abaixo).

## Como o `ss cut` corta

1. Mede o silêncio com `ffmpeg silencedetect` a `silence_db` (padrão −35 dB), mínimo 0,18 s.
2. Cada borda de take encosta no silêncio mais próximo (até 0,35 s de distância), com 0,10 s de respiro antes da fala e 0,15 s depois.
3. Dentro de cada take, pausas maiores que 0,45 s são encurtadas.
4. Cada emenda ganha fade de 12 ms no áudio (sem estalo).
5. Endireita o vídeo pelo metadado de rotação (câmera ou celular gravando de lado sai em pé) e preenche o quadro de saída cortando o excesso no centro, sem esticar.

## Sala com ruído: `silence_db`

O limiar padrão (−35 dB) pressupõe estúdio. Em selfie ou escritório, o ruído de sala fica acima dele e o `silencedetect` quase não acha pausa (numa gravação de celular, achou 4 a 6 pausas no arquivo inteiro; nenhuma foi encurtada e o vídeo saiu ~6 s mais longo). Meça o piso de ruído e ponha `"silence_db": -28` (valor que funcionou nas gravações de celular) no `corte.json`.

## Velocidade pelo ritmo de fala

- `ss prepare-presenter` com `--speed auto` mede palavras por minuto do corte em 1x (pausas já encurtadas) e escolhe a velocidade que leva a **≈184 palavras/min**, limitada a **1,0–1,3x**.
- De onde vem o número (regra prática): apresentadores aprovados ficaram entre 184 e 221 palavras/min; os novos, em 1x, entre 166 e 184. Quem já fala a ~184 fica em 1x; quem fala a 166 vai para ~1,1x.
- A voz acelera sem mudar o tom (`atempo`). Para forçar, use `--speed 1.0` ou outro número.
- Isso vale para o apresentador. No motion narrado, **nunca acelere o vídeo pronto** (veja [regras-de-gosto.md](regras-de-gosto.md)).

## Avisos do `ss prepare-presenter`

| Aviso | O que costuma ser | Como corrigir |
|---|---|---|
| `STRETCHED` (palavra com mais de 1,2 s) | O Whisper escondeu um take repetido ou uma hesitação dentro da palavra. Num caso real, a pessoa repetiu a frase inteira três vezes e o Whisper registrou só uma, com palavras de 2,6 s e 4,2 s e nenhum silêncio medido no meio. | Retranscreva **só aquele trecho do bruto** como clipe curto. Achando o take repetido, refaça o `keep` a partir do último take completo. |
| `LONG SHORT WORD` (palavra de até 3 letras com mais de 0,75 s) | Ruído de voz antes da fala ("uuuu"). | Peça para a pessoa ouvir o ponto; corte quebrando o take no `keep`. |
| `NOISE` (som numa pausa entre frases) | Murmúrio, "uuuu", erro de gravação. | Quebre o take no `keep` para tirar o trecho e rode `ss cut` e `ss prepare-presenter` de novo. |

### Retranscrever um trecho (alucinação nos falsos inícios)

Transcrito no arquivo inteiro, o Whisper às vezes **alucina nos falsos inícios**: junta o primeiro take ao segundo, some com palavras do segundo e estica palavras por segundos (visto em duas gravações de celular de 1,5 a 2,5 min). O conserto é transcrever cada trecho suspeito isolado:

```bash
ffmpeg -v error -ss <inicio-1> -to <fim+1> -i "<bruto>" -c:v libx264 -c:a aac "$HOME/.cache/scroll-stopper/tmp-trecho.mp4"
ss transcribe "$HOME/.cache/scroll-stopper/tmp-trecho.mp4" <id>-trecho
```

(O `ffmpeg` é instalado junto com o plugin; `ss setup --check` confere que ele está no PATH.)

Leia o `transcript.txt` de `~/.cache/scroll-stopper/work/<id>-trecho/transcript/` e some `<inicio-1>` aos tempos para voltar ao tempo do bruto. Antes de qualquer render final, liste as palavras com mais de ~1,2 s no `words.json` e retranscreva esses trechos.

## Jump cut

Em vídeo falado, o pulo de imagem na emenda é aceito: é a linguagem do formato. No corte puro, não tente esconder com zoom ou transição. No caminho A, as trocas de tela e os punch-ins já disfarçam as emendas.

## Enquadramento do rosto (caminho A)

- A posição da legenda depende do enquadramento: em selfie de busto o queixo fica em ~50–55% da altura; em close-up, em ~69–76%. Meça o rosto em alguns quadros antes de fixar o enquadramento (receita com grade em [apresentador-com-motion.md](apresentador-com-motion.md)).
- "Rosto mais para cima" tem teto geométrico: a janela do zoom não desce abaixo do quadro. Com o rosto baixo (cabelo a 35% ou mais da altura), um zoom de 1,3 sobe o cabelo de ~38% para ~20% e o queixo de ~76% para ~68%. Simule nos piores quadros antes de renderizar.
- O topo do cabelo de quem grava em plano médio raramente passa de ~320 px (de 1920): um logo entre y 80 e 170 não encosta na cabeça. Meça no seu vídeo.

## Por que essas regras existem (aprendizados)

| O que aconteceu | Regra |
|---|---|
| O Whisper errou a borda da palavra em até ~0,2 s | Corte encostado no silêncio medido |
| VAD ligado escondeu claquete e takes repetidos | Transcrição sem VAD |
| Whisper no arquivo inteiro alucinou nos falsos inícios | Retranscrever cada trecho suspeito como clipe curto |
| Uma 3ª tentativa de frase ficou escondida dentro de palavras esticadas | Listar palavras com mais de ~1,2 s e retranscrever antes do render |
| Ruído de sala de celular acima de −35 dB | `silence_db: -28` no `corte.json` |
| Ritmo aprovado fechava em ~184 palavras/min | Velocidade pelo ritmo, limitada a 1,0–1,3x |
| Sigla falada ("ADS01") virou nome na legenda | Leitura incerta antes do roteiro = claquete; pergunte |
| Processos gravando muitos arquivos numa pasta sincronizada travaram com 0% de CPU | Render no cache (`~/.cache/scroll-stopper/`); só o `.mp4` final volta para a pasta do usuário |
| Bruto de câmera em 4K com rotação de −90° | O corte endireita pelo metadado e sai 9:16 sem crop manual |
