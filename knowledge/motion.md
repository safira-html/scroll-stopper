# Motion: linguagem visual, legenda e animação

O que faz um vídeo em motion parecer premium e como o engine do plugin implementa isso. A análise quadro a quadro das referências que deram origem a estas regras está em [referencias/motion-reference-breakdown.md](referencias/motion-reference-breakdown.md). Estas são regras de prática (o que funcionou e o que foi rejeitado), não dados de plataforma.

## Por que as referências parecem premium (e uma primeira versão só de texto não)

Uma primeira versão só com texto cinético sobre grade de pontos foi julgada "muito fraca". A qualidade subiu nesta ordem:

1. **Sempre há um objeto concreto na tela:** card de UI, celular, render 3D ou personagem. O texto é a legenda do objeto, não o protagonista.
2. **Volume:** sombras longas e macias ("clay"), pills em relevo e renders 3D recortados.
3. **Profundidade de campo:** formas gigantes desfocadas nos cantos, que mudam de lugar a cada corte (parece que a câmera andou), e desfoque nas transições.
4. **Microeventos a cada 0,3–0,6 s;** a cena troca a cada 1,5–4 s.
5. **Continuidade:** zoom-through, morph e pan, em vez de corte seco entre telas de texto.
6. **Prova visual concreta:** telas reais do produto, números com fonte, logos reconhecíveis (com direito de uso).
7. **Cor contida:** neutros e **um único acento** (o da marca).

## O que o engine já faz

Os caminhos abaixo são relativos à pasta `src/` do engine do projeto (veja "Onde editar" no fim).

| Recurso | Onde está |
|---|---|
| Legenda karaokê: cinza fino → texto bold, palavra por palavra, no tempo da fala | `kit.tsx` `Captions`; `lib/ui.tsx` `SyncedLine` |
| Palavra-chave em pill sólida (escuro: tinta sobre acento; claro: acento sobre escuro) | `Captions` com `key` no trecho |
| Formas gigantes desfocadas nos cantos, um conjunto diferente por cena | `lib/ui.tsx` `CornerShapes`, `Scene set={n}` |
| Grade de pontos só em volta do objeto (máscara radial) | `MaskedGrid`, `Scene gridAt` |
| Vinheta e grão por quadro | `Vignette`, `Grain` (automáticos no `AdShell`) |
| Câmera com push-in contínuo de +6% por cena | `Scene push` |
| Entrada com escala 0,94 → 1; saída com zoom-through (+0,35) e blur até 14 px | `lib/anim.ts` `sceneEnvelope` |
| Pop "carimbado" com leve overshoot | `lib/anim.ts` `pop` |
| Sombras clay (claro) e dark (escuro) | `clayShadow`, `darkShadow` |
| Janela de app, dashboard, editor de código, chat, calendário | `lib/ui.tsx`, `lib/illustrations.tsx` |
| Card do produto, CTA com dedo tocando, chips de fato, carimbo, contador | `kit.tsx` `ProductCard`, `CtaTap`, `FactChip`, `Stamp`, `countUp` |
| Tela final escura com logo, título, itens, preço e CTA pulsando | `engine/EndCard.tsx`, alimentada por `brand.endCard` (duração em `endCard.seconds`, padrão 11 s) |
| Narração, trilha sob a voz, efeitos e whoosh na tela final | `engine/AdShell.tsx` (a trilha só toca com `music="light"` ou `music="dark"` no `AdShell`) |

Outros recursos que funcionaram em peças específicas e podem ser criados quando o roteiro pedir: pilha de pills de ferramentas caindo, ícones em círculos brancos com pop em sequência, diagrama de nós com linha se desenhando e um "pacote" viajando, contador com brilho, barras crescendo com linha de tendência, caixa tracejada com alças, cursor clicando "Publicar" → "✓ Publicado", pilha de cards bagunçados que se organiza.

## Regras de composição

- **Uma âncora grande por cena,** ocupando 40–60% da largura, com no máximo 5 ou 6 elementos no quadro.
- **Zona segura (1080×1920):** nenhum texto acima de y=270 nem abaixo de y=1250. Objetos podem passar. É a faixa que ficou livre da interface do Reels nas peças de origem; confira no app antes de publicar.
- **Frame 0 já mostra o objeto principal.** Nada de quadro vazio ou fade a partir do nada no começo.
- Cena com mais de 4 s só se algo se mover a cada 0,5–1,5 s.
- **Claro e escuro:** a peça pode começar clara, mas **produto, CTA e tela final são escuros** e repetem o topo da página de destino. A virada acontece quando o produto entra (problema → solução). Cenas escuras seguidas precisam de um fundo escuro contínuo por baixo; senão o fundo claro pisca 4–6 quadros em cada corte.
- **Transição padrão:** zoom-through com blur. Varie com morph (um card vira outro), pan horizontal, wipe com máscara e círculo abrindo na tela final.

## Tempo amarrado à fala

**Nunca use segundos fixos.** Cada cena e cada microevento ancora numa frase da narração:

```ts
const c = makeCues(words);              // cursor que só anda para frente: declare na ordem da fala
const s2 = c.s('Mostre o problema');    // início da frase, em segundos
c.w('Mostre o problema', 2);            // início da 3ª palavra da frase
<Scene from={s2} to={c.s('É isso que faz')} theme="light" set={1}>…</Scene>
```

O mesmo layout serve para as duas vozes e para qualquer velocidade. Se remover uma frase do roteiro, remova também o cue dela, senão os seguintes se deslocam.

## Legenda (a protagonista)

- **Karaokê por peso:** a frase entra 6 quadros antes da primeira palavra (blur 8 → 0, sobe 30 px). Cada palavra leva 6 quadros: opacidade 0,35 → 1, peso 300 → 700 e cinza → cor do texto. **Peso máximo 700.**
- **Quebra de linha calculada antes,** com a largura no peso final (`lib/textLayout.tsx` `breakLines`):
  - tenta 2, 3 e 4 linhas;
  - custo: viúva ×1000, palavra fraca no fim da linha ×50, diferença de largura entre linhas e leve preferência por pirâmide invertida;
  - palavras fracas (pt-BR) não terminam linha: a, o, de, do, da, em, no, na, um, uma, pra, para, por, com, que, se, ou…;
  - nomes inseparáveis vêm de `brand.captions.keepTogether`;
  - sem solução sem viúva, fica a de menos linhas.
- **Redução automática:** trecho de até 5 palavras que não cabe numa linha diminui a fonte até 72%, em vez de quebrar.
- **Trechos:** 2–4 palavras no motion e 3–4 em uma linha no vídeo de banco (tamanho 112). Defina os trechos à mão em `chunks`, seguindo a respiração da fala; o texto de cada trecho é escrito exatamente como está nas palavras (`words.json`).
- **Pills sem sombra no texto.**
- **Riscado:** barra na cor `strike` com 10 px, girada −2°, desenhada depois da frase; o texto riscado fica cinza.
- Legenda em fonte serifada de peso único: o destaque é por cor (cinza → branco), com `weights=[400, 400]`.

## Tipografia

- **No máximo 2 famílias por vídeo:** `sans` para legenda e UI; `mono` só para interface de código e números (nunca na narrativa). `display` (serifada) só para gancho ou vídeo de banco, e aí substitui a sans na legenda dessa peça.
- Tracking dos títulos e da legenda: −0,035em. Display: −0,015em, line-height 0,9.
- As fontes vêm do Google Fonts via `@remotion/google-fonts`, declaradas no `brand.json`.

## Easing e duração

- `easeOut = cubic-bezier(0.23, 1, 0.32, 1)` para entradas; `easeInOut = cubic-bezier(0.77, 0, 0.175, 1)` para movimento na tela (`lib/anim.ts`).
- Entradas de 250–400 ms (8–12 quadros). O texto sobe 30–40 px enquanto aparece.
- Stagger de cerca de 300 ms entre itens de uma lista.
- Nada de bounce exagerado; o overshoot fica só no `pop`.

## Som

Um efeito acompanha um evento visual e nunca toca sozinho: pop nos pop-ins, whoosh nas transições, tique em cronômetro, clique em botão. No máximo 1 efeito a cada 0,5 s, volume 0,25–0,5. Kit, nomes e níveis: [som.md](som.md).

## Vídeo de banco (formato vlog)

Ver [banco-de-imagem.md](banco-de-imagem.md): mesma pessoa, uma correção de cor, nenhum texto sobre rosto, overlays leves e produto/CTA numa cena escura da marca, não sobre o vídeo.

## Onde editar (engine do projeto)

O plugin instalado nunca é editado. Cada projeto tem a **sua cópia do engine** em `~/.cache/scroll-stopper/work/<id>/engine/`, criada pelo `ss brand use <marca> --project <id>` (o comando imprime o caminho). É nela que se criam e registram as composições:

1. **Arquivo novo** em `~/.cache/scroll-stopper/work/<id>/engine/src/ads/<Nome>.tsx`, copiado do modelo:
   - caminho B (motion narrado): `src/ads/Template.tsx`;
   - caminho A (apresentador): `src/ads/PresenterTemplate.tsx`.
   Troque os nomes exportados (`Template`/`SCRIPT`, `PresenterTemplate`/`PRESENTER_SCRIPT`) por nomes próprios, para não colidir com o modelo.
2. **Registro** em `src/ads/index.ts`: importe o componente e acrescente uma entrada em `ADS` com `id` igual ao **id do projeto** (é o `id` que liga a composição às palavras `audio/<id>-<voz>.words.json` gravadas pelo `ss align` e pelo `ss prepare-presenter`):
   ```ts
   import {MeuVideo, ROTEIRO} from './MeuVideo';
   // motion narrado com voz masculina (tela final pela marca):
   {id: 'video-01', component: MeuVideo, demoScript: ROTEIRO, voices: ['m']},
   // apresentador (saída curta, sem tela de oferta):
   {id: 'video-01', component: MeuVideo, voices: ['m'], tail: 0.35 + OUTRO_SECONDS},
   ```
3. A composição se chama **`<id>-<voz>`** (por exemplo `video-01-m`). Use esse nome no `ss draft` e no `ss render`. O id do projeto só pode ter letras, números e hífen (é o nome da composição no Remotion).
4. A cada `ss brand use`, `ss draft` e `ss render`, a pasta `media/{video,audio,music,sfx,stock}` do projeto é ligada em `public/` do engine. Sem `media/music` ou `media/sfx` próprios, os arquivos do kit de som da pasta de trabalho (`.scroll-stopper/kit-de-som/music` e `sfx`) são copiados para `media/music` e `media/sfx` do projeto, no cache (a pasta de trabalho costuma estar no Google Drive ou Dropbox, e o render nunca lê de pasta sincronizada). A cópia é refeita a cada um desses comandos: o que a pessoa acrescentar, trocar ou apagar no kit chega ao projeto no próximo. O que estiver em `public/video/`, `public/audio/`, `public/music/` e `public/sfx/` fica disponível por `staticFile('<pasta>/<arquivo>')`.
5. Imagens e ícones do projeto vão em `~/.cache/scroll-stopper/work/<id>/media/stock/` (viram `staticFile('stock/<arquivo>')`); os assets da marca vêm do `assets/` dela (`brandAsset(...)`).
