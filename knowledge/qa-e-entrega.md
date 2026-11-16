# Render, QA e entrega

## Onde fica cada coisa

- **Trabalho pesado** (engine com `node_modules`, venv, transcrições, renders intermediários) fica em `~/.cache/scroll-stopper/`, fora de pastas sincronizadas como Google Drive e Dropbox: processos gravando muitos arquivos numa pasta sincronizada travaram com 0% de CPU (observado na prática). Só o `.mp4` final é copiado para a pasta que a pessoa escolher.
- **Na pasta de trabalho** (`.scroll-stopper/`): marcas, kit de som, aprendizados e, por projeto, `projetos/<id>/` com `corte.json`, roteiros e `candidatos.json`.
- **Nunca no repositório do plugin:** mídia, marcas, vozes, renders, métricas.

## Iterar com rascunho

```bash
ss draft <id> <composicao> --brand <marca>
```

- Gera `draft.mp4` em meia escala e `sheet.jpg` (folha de contatos, um quadro a cada 1,5 s; vídeos longos espalham os 44 quadros pela duração toda) em `~/.cache/scroll-stopper/work/<id>/out/`.
- **Olhe a folha** antes de dizer que ficou bom. Para conferir um momento exato, extraia um quadro do rascunho:
  ```bash
  ffmpeg -v error -ss <segundos> -i ~/.cache/scroll-stopper/work/<id>/out/draft.mp4 -frames:v 1 ~/.cache/scroll-stopper/work/<id>/out/q.png
  ```
  Escolha os momentos pelas palavras (`words.json`), para cair em momentos falados.
- Sempre confira o **último quadro** e a **tela final**: num caso real, o último quadro saiu preto e só a conferência pegou.
- Mostre o rascunho cedo para a pessoa ver o movimento; não espere o render final.

## Render final

```bash
ss render <id> <composicao> --dest "<pasta de entrega>" --name <nome> [--lufs -14|-15] [--brand <marca>]
```

1. Renderiza no cache em H.264 (CRF 18), 1080×1920, 30 fps.
2. Normaliza o áudio em duas passadas: **−14 LUFS** (apresentador e clipes) ou **−15 LUFS** (motion narrado), **TP −1,5 dBTP**, AAC 48 kHz, vídeo copiado sem reencode. O render cru sai abaixo do alvo, por isso o passo é obrigatório. Se o pico passar de −1,0 dBTP, refaz com TP −2,5.
3. Copia o `.mp4` para a pasta de entrega sem sobrescrever (se o nome existe, vira `<nome>_v2.mp4`, `_v3`…) e imprime o caminho final.

Padrão do `--lufs`: −14 quando o projeto tem `media/video/presenter.mp4` (caminho A e cortes dinâmicos) ou a composição começa com `Presenter` ou `SimpleClip`; −15 nas demais (motion narrado). `--lufs` explícito sempre vence.

Padrão do `--brand`: a marca usada por último neste projeto (gravada pelo `ss brand use`, `ss draft` e `ss render` em `~/.cache/scroll-stopper/work/<id>/brand-path.txt`); sem nenhuma, a marca neutra. Aceita slug de `.scroll-stopper/marcas` ou a pasta de uma marca efêmera.

**Vídeo pronto sem composição** (por exemplo, só o corte do `ss cut`): `ss finalize <video> --dest "<pasta>" --name <nome>` converte para 1080×1920 a 30 fps quando o vídeo vem em outro tamanho ou ritmo (o corte sai em 1440×2560), normaliza para −14 LUFS (ou `--lufs`), confere e entrega do mesmo jeito.

## Checklist de QA (rode em todo vídeo)

**Técnico** (o `ss render` já confere; para conferir de novo: `ss qa <arquivo> --lufs <alvo>`)
- 1080×1920, 30 fps, H.264 + AAC, com a duração esperada.
- Loudness integrada no alvo (±0,5 LU) e true peak até −1 dBTP.
- Se o render imprimir `[!!] Conferência falhou`, o arquivo foi entregue mesmo assim: diga o motivo para a pessoa e corrija antes de ela usar.

**Layout** (na folha de contatos e em quadros soltos)
- Nenhum texto fora da zona segura (y 270–1250).
- Nada cortado nem sobreposto; nenhuma legenda encostando em ilustração.
- Nenhum quadro claro piscando entre cenas escuras.
- Frame 0 já mostra o objeto principal.
- Quadros quase vazios na folha costumam ser os 2–4 quadros de transição: isso é esperado; confira no rascunho.

**Legenda**
- Confere palavra a palavra com o roteiro, incluindo nomes de marca e siglas.
- Nenhuma linha com uma palavra só, nenhum nome quebrado, peso máximo 700 e nenhuma sombra no texto de pill.
- Toda frase usada em `makeCues` existe nas palavras da voz usada.

**Fatos**
- Nenhuma promessa proibida, nem na voz nem na tela ([roteiro-publico-frio.md](roteiro-publico-frio.md)).
- A tela final bate com a página no ar.
- Números de gráfico parecem exemplo.

**Estrutura** (anúncio)
- Gancho → conteúdo → produto → CTA, com tela final de 10,9–11,1 s (`endCard.seconds` = 11).

**Escuta** (o agente não ouve; isto é aproximação)
- Retranscreva os trechos editados.
- Rode `silencedetect` (−40 dB, 0,6 s) e confira que os pontos de corte estão abaixo de −50 dB.
- Liste para a pessoa ouvir: pronúncia da marca, siglas, trilha e efeitos.

## Entrega

- **O vídeo pronto e o caminho onde ele está.** O que a pessoa faz depois (aprovar, publicar, mandar para alguém) é decisão dela.
- Ao entregar vários vídeos, resuma **pelo que cada um fala**, não pelo número do arquivo.
- Liste o que ficou pendente de conferência humana: licença da voz e do banco de imagem, consentimento de clone, pronúncia, âncora de preço usada.
- **O plugin nunca publica vídeo, nunca sobe anúncio e nunca envia mensagem** em nome de ninguém.

## Licença do Remotion

O engine usa o Remotion. Segundo a página de licença (https://www.remotion.dev/license), ele é gratuito para pessoas físicas e para empresas de até 3 pessoas; quem não se encaixa na licença gratuita precisa de uma licença de empresa (Company License). Confira a página antes de usar numa empresa maior.
