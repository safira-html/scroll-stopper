# Kit de som: onde conseguir e como preparar

O kit de som é seu: fica em `.scroll-stopper/kit-de-som/` na sua pasta de trabalho e nunca vai para o repositório do plugin. Sem ele o vídeo sai só com a voz; nada quebra. Nenhuma ferramenta paga é obrigatória.

## O que o engine usa

- Trilhas de fundo: `music/bed-light.mp3` e `music/bed-dark.mp3` (o apresentador usa a `dark`).
- 13 efeitos com nome fixo em `sfx/`: `whoosh-short`, `whoosh-riser`, `pop-soft`, `bubble-pop`, `ui-click`, `keyboard-typing`, `error-buzz`, `success-chime`, `clock-tick`, `zoom-swish`, `card-slide`, `impact-low`, `page-flip`.
- O engine só toca esses nomes. Outro nome é salvo, mas fica sem uso (o `ss kit add-sfx` avisa).

Comandos (rode na pasta do projeto, depois do `ss workspace init`):

```
ss kit add-music <arquivo> <light|dark>
ss kit add-sfx <arquivo> --name pop-soft
ss kit status
```

`add-music` normaliza para -20 LUFS (pico real -2 dBTP) com fade-in de 0,3 s e fade-out de 2 s. `add-sfx` corta o silêncio das pontas, aplica fades curtos e deixa o pico em -3 dBFS. Sem `--name`, o nome do arquivo (em minúsculas, com hifens) vira o nome do efeito.

## Bancos gratuitos (licenças conferidas em 2026-11-12)

Só estão aqui os bancos cuja página de licença abri e li nesta data. Licenças mudam: confira a página de novo antes de usar em campanha grande.

### Pixabay (música e efeitos)

- Licença: https://pixabay.com/service/license-summary/ ("Content License Summary", sem data na página).
- O que diz: o conteúdo (imagens, vídeo, áudio e outras mídias) pode ser usado de graça e modificado em novas obras, sem atribuição obrigatória (dar crédito é apreciado). Não pode ser vendido ou distribuído sozinho, sem esforço criativo seu; conteúdo com marca ou logo reconhecível não pode ser usado comercialmente ligado a produtos ou serviços; não pode ser usado de forma ilegal, enganosa ou como parte de marca registrada.
- O que a página NÃO diz: ela não menciona uso comercial nem anúncio de forma explícita (nem Content ID). Antes de usar uma trilha em anúncio pago, leia a licença completa, que a própria página linka: https://pixabay.com/service/terms/ (confirmado na página em 2026-11-12).

### Freesound (efeitos, com filtro de licença)

- Licenças: https://freesound.org/help/faq/#licenses e, para a CC0, https://creativecommons.org/publicdomain/zero/1.0/.
- CC0: pode copiar, modificar e usar, inclusive comercialmente, sem pedir permissão e sem atribuição; a CC0 não cobre direitos de marca, privacidade ou imagem de terceiros.
- CC BY: exige crédito ao autor (título, autor, link e licença). A página de FAQ não diz de forma explícita que o uso comercial é permitido nessa licença; ela só marca a CC BY-NC como a que proíbe.
- CC BY-NC: a FAQ diz que ela exige crédito e que você não pode "ganhar dinheiro" com a obra que criar (ou seja, não pode render dinheiro). Que anúncio entra nisso é inferência minha, não está escrito na FAQ; trate como proibido.
- Sampling+ (antiga): a FAQ diz que, além do que a BY-NC proíbe, ela proíbe uso em publicidade comercial. Mantenha fora de anúncio.
- Na busca, o filtro de licenças tem a opção "Free Cultural Works", que a FAQ descreve como CC BY ou CC0. Para não ter que creditar ninguém, escolha só a licença **CC0** (opção "Creative Commons 0" no filtro de licença da busca; confira o rótulo na tela).

## Bancos que não recomendo (por enquanto)

- YouTube Audio Library: a página de ajuda (https://support.google.com/youtube/answer/3376882) trata de uso no YouTube e diz que o YouTube não dá orientação jurídica para uso fora da plataforma. Anúncio em outras redes não está coberto no que li.
- Mixkit: a página https://mixkit.co/license/ só lista a "Sound Effects Free License" e a "Stock Music Free License" com links; não consegui abrir o texto de nenhuma das duas (a URL tentada para efeitos devolveu 404). Sem o texto, não afirmo o que permitem.

## Como confirmar a licença arquivo por arquivo

1. Abra a página do arquivo (não só a do banco) e leia a licença mostrada nela; no Freesound ela aparece em cada som e pode ser diferente de um som para outro.
2. Tire um print da página, com a licença, a data e o link, e guarde junto do arquivo original (por exemplo numa pasta `origem/` ao lado do kit).
3. Se exige crédito, anote já o texto do crédito para a descrição do anúncio.
4. Desconfie de trilha que reconhece como música conhecida e de som com marca ou voz de pessoa identificável: a licença do banco não cobre direitos de terceiros.
5. Na dúvida, use outro arquivo. Não é conselho jurídico; para campanha grande, peça a quem cuida do jurídico.

## Gerar com uma ferramenta de terceiros

Qualquer ferramenta de geração de som que você já tenha serve: via conector (MCP), via API ou direto no site dela. Um exemplo entre vários é o gerador de efeitos sonoros da ElevenLabs; nada no plugin depende dele. Antes de gerar, o plugin diz o que vai gerar e o custo aproximado e espera o seu sim. Confira nos termos da ferramenta se o que ela gera pode ser usado em anúncio.

Dicas gerais: peça uma coisa só por arquivo, diga a duração e o caráter do som, gere 2 ou 3 versões e fique com a mais limpa. O `ss kit add-sfx` apara o silêncio e acerta o nível, então não precisa ser perfeito.

### Prompts de partida (não testados)

São sugestões para começar; ajuste de ouvido depois de gerar.

| Nome | Prompt |
|---|---|
| `whoosh-short` | short airy whoosh, 0.4 seconds, soft swoosh passing left to right, no tail |
| `whoosh-riser` | rising whoosh, 1.2 seconds, building air sweep ending on a clean cut |
| `pop-soft` | soft bubble pop, 0.2 seconds, round and gentle, dry |
| `bubble-pop` | single water bubble pop, 0.25 seconds, bright and clean |
| `ui-click` | clean interface button click, 0.1 seconds, crisp and dry, no reverb |
| `keyboard-typing` | laptop keyboard typing, 1.5 seconds, fast soft keys, no room noise |
| `error-buzz` | short error buzz, 0.4 seconds, low soft digital buzzer, not harsh |
| `success-chime` | success chime, 0.8 seconds, two ascending bell notes, warm and bright |
| `clock-tick` | single clock tick, 0.15 seconds, dry wooden click, no ambience |
| `zoom-swish` | quick camera zoom swish, 0.3 seconds, fast airy sweep with a soft end |
| `card-slide` | card sliding on a table, 0.4 seconds, smooth paper slide, soft |
| `impact-low` | low cinematic impact, 0.8 seconds, deep thud with short decay, no reverb tail |
| `page-flip` | single paper page flip, 0.4 seconds, light and crisp |

Trilhas de fundo: descreva clima e andamento, sem voz e sem letra. Exemplo para `light`: "light upbeat instrumental background music, soft pads and gentle plucks, no vocals, steady mid tempo, 60 seconds". Para `dark`: "dark minimal instrumental background music, deep pulse and subtle texture, no vocals, steady slow tempo, 60 seconds". Prefira trilhas de 30 a 90 s; o motor repete em laço.

## Níveis e regras de uso

- Trilha de fundo: -20 LUFS no arquivo (o `add-music` faz isso) e tocada em volume por volta de 0,09 sob a voz.
- Efeitos: pico em -3 dBFS no arquivo (o `add-sfx` faz isso).
- No máximo 1 efeito a cada 0,5 s, com volume entre 0,25 e 0,5. Efeito demais vira poluição e compete com a fala.
