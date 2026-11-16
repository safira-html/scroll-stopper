# Vídeo com apresentador alternado com motion (caminho A)

Use quando existe uma **gravação de uma pessoa falando para a câmera** e o pedido é um vídeo vertical dinâmico: telas do apresentador alternadas com telas de motion, transições, legenda karaokê e efeitos sonoros.

Se não existe gravação, só uma voz, o caminho é o B ([voz.md](voz.md), modelo `Template.tsx`).

## 1. Cortar (só o corte)

Siga [cortes.md](cortes.md): `ss transcribe`, `corte.json`, `ss cut`. O corte sai sem legenda, sem logo e sem trilha, em 1440×2560 (margem para os punch-ins); legenda, logo e som entram na montagem.

## 2. Preparar o corte para o motion

```bash
ss prepare-presenter ~/.cache/scroll-stopper/work/<id>/cut_1x.mp4 <id>
```

1. **Velocidade:** mede o ritmo de fala e acelera até ≈184 palavras/min, com teto de 1,3x (uma gravação a 158 palavras/min foi para 1,17x).
2. **Vídeo:** grava `media/video/presenter.mp4` (30 fps) no cache do projeto.
3. **Voz e palavras:** grava `media/audio/<id>-m.mp3` (−16 LUFS) e `<id>-m.words.json`, que ancoram a legenda e as telas.
4. **Avisos** (`STRETCHED`, `LONG SHORT WORD`, `NOISE`): resolva **antes** do render final, como em [cortes.md](cortes.md). Depois de mudar o `keep`, rode `ss cut` e `ss prepare-presenter` de novo.

Escreva as frases dos `chunks` da legenda **exatamente como o Whisper escreveu** ("pra", "tá", "por que"). Revise nomes de marca.

## 3. Montar: alternar apresentador e motion

Crie a composição na cópia do engine do projeto a partir de `src/ads/PresenterTemplate.tsx` e registre com `voices: ['m']` (passo a passo em [motion.md](motion.md), "Onde editar"). Os componentes de tela estão em `src/presenter.tsx`.

**Meça o rosto** num quadro do corte com grade e ajuste `face` (0–1) no `SOURCE` da composição:

```bash
ffmpeg -v error -ss 3 -i ~/.cache/scroll-stopper/work/<id>/media/video/presenter.mp4 -frames:v 1 -vf "drawgrid=w=iw/10:h=ih/10:t=2:c=yellow@0.7" ~/.cache/scroll-stopper/work/<id>/face.jpg
```

(O `ffmpeg` é instalado junto com o plugin; `ss setup --check` confere que ele está no PATH.)

Olhe a imagem (cada célula = 0,1) e anote x e y do centro do rosto. Faça em 2 ou 3 momentos do vídeo.

### Os quatro tipos de tela

| Tela | Quando usar | Componente |
|---|---|---|
| **Apresentador em close**, com punch-in (+14% em 4 quadros) na palavra forte | gancho, opinião, alerta ("presta atenção"), pergunta, CTA | `PresenterShot` (zoom 1,4–2,1; rosto em ~30% da altura) |
| **Tela dividida:** motion em cima e o apresentador num card embaixo | quando ele explica algo que dá para mostrar ao mesmo tempo | `SplitScreen` |
| **Só motion**, sem pessoa | dado, lista, antes × depois, exemplo concreto | `BrandStage` + cena (de `kit.tsx`, `lib/illustrations.tsx` ou nova) |
| **Flash de palavra** sobre a cor de destaque | número ou palavra curta ("3 coisas"), 0,6–1,2 s | `WordFlash` |

### Ritmo e variação

- Troque de tela a cada 2–5 s, sempre numa frase falada (`makeCues`), nunca em segundos fixos.
- Nunca repita duas vezes seguidas o mesmo tipo de tela nem a mesma transição.
- **Transições** (`Shot enter`): `whipL` / `whipR` (desliza com blur), `zoom` (chega grande e assenta), `up` (sobe) e `cut`. No corte seco de uma fala de alerta, use `WhiteHit` (flash branco de 2 quadros). A tela que sai fica mais 8 quadros por baixo, para a seguinte entrar sem quadro vazio.
- Misture **cenas claras e escuras** da marca.
- **Som:** um efeito em cada troca de tela (whoosh, swish, card-slide, impact no flash) e nos microeventos (pop, clique, check). A trilha (`music/bed-dark.mp3`) fica baixa, com volume 0,09 sob a voz. Sem kit de som, o vídeo sai só com a voz; nada quebra ([som.md](som.md)).

### Legenda

Use `SegmentCaptions`: um bloco de legenda por tela, que sai junto com ela.

| Tela | Posição (`CAPTION_TOP`) |
|---|---|
| Sobre o apresentador | 1140, com `CaptionScrim` (degradê escuro; nunca sombra no texto) |
| Só motion | 1110, com a cena ocupando até y ≈ 1080 |
| Tela dividida | 830, na emenda entre o motion e o card |

- 2–4 palavras por trecho e uma pill por trecho.
- Nunca ponha texto sobre o rosto.
- Fique dentro da zona segura: y entre 270 e 1250.

### Conteúdo

- **Mostre o que ele fala.** Se ele fala de planilha, a tela mostra uma planilha se preenchendo. Se cita um número, entra um contador com a fonte na tela, num chip ("Fonte · Nome do estudo, ano").
- Dado falado precisa de fonte verificável. Sem fonte, não mostre o número na tela e avise a pessoa.
- Exemplos em UI são fictícios (nomes, e-mails, pedidos "exemplo") e precisam parecer exemplo.
- **Conteúdo orgânico com CTA de comentário não leva a tela de oferta de 11 s.** A saída tem 2–3 s, com o logo (`OUTRO_SECONDS` no modelo), e pode ter um comentário sendo digitado.

## 4. Rascunho, render e QA

```bash
ss draft <id> <id>-m --brand <marca>
ss render <id> <id>-m --dest "<pasta de entrega>" --name <nome> --brand <marca>
```

- O rascunho sai em meia escala com uma folha de contatos (`sheet.jpg`, um quadro a cada 1,5 s). **Olhe a folha** e quadros do começo, do CTA e da saída. Confira se algum contador fica parado em zero, se alguma cena tem espaço vazio, se algum texto encosta no rosto, se o CTA fica tempo suficiente e se algum quadro fica vazio numa transição.
- O `ss render` sai em **−14 LUFS** sozinho quando o projeto tem `media/video/presenter.mp4` (gravado pelo `ss prepare-presenter`); `--lufs` só é preciso para forçar outro alvo.
- O render já normaliza o áudio (duas passadas, TP −1,5) e roda a conferência técnica. Checklist completo: [qa-e-entrega.md](qa-e-entrega.md).

O agente não ouve o áudio: peça para uma pessoa ouvir as emendas antes de entregar.
