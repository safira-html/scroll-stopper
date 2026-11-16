# Armadilhas conhecidas

Problemas que já aconteceram e a solução de cada um.

## Segurança

- **Nunca rode `pgrep -fl`, `ps eww` ou qualquer comando que imprima o ambiente de um processo.** Um desses comandos jogou um token de API no histórico da conversa e o token teve de ser trocado. Para testar se um processo existe, use `pgrep -f "<padrão>" >/dev/null`; para encerrar, `pkill -f`.
- Não leia nem imprima variáveis de ambiente que possam ter segredo. Para checar se uma existe: `[ -n "${VAR:-}" ] && echo definida || echo ausente`.
- Links assinados (download de ferramenta de voz, de pasta compartilhada) expiram e dão acesso: não grave em log nem em arquivo.

## Pastas

- **Render dentro de pasta sincronizada trava.** Todo trabalho pesado fica em `~/.cache/scroll-stopper/`; só o `.mp4` final vai para a pasta da pessoa.
- **Caminho com espaço** (pastas sincronizadas costumam ter): sempre entre aspas nos comandos.
- **`public/` pesado** → o Remotion copia tudo em cada bundle; deixe extrações fora dele.
- **Nunca edite o plugin instalado.** Composições novas vão na cópia do engine do projeto (`~/.cache/scroll-stopper/work/<id>/engine/`; ver [motion.md](motion.md)).

## Engine e render

- **Composição não encontrada** → o `ss render` lista as disponíveis. Confira o `id` registrado em `src/ads/index.ts` e a voz (`<id>-m` ou `<id>-f`).
- **Erro de sintaxe num arquivo de `src/ads/` quebra o bundle de todas as composições do projeto.** Corrija antes de renderizar qualquer outra.
- **Quadro claro piscando entre cenas escuras** → fundo escuro contínuo sob as cenas escuras.
- **Legenda pulando de linha quando o peso cresce** → quebra calculada no peso final (já é assim no engine). Travar a largura de cada palavra deixou buracos e foi revertido.
- **Linha com uma palavra só** → fallback de menos linhas e redução automática da fonte (já no engine).
- **Nome quebrado entre linhas** → `captions.keepTogether` no `brand.json`.
- **Legenda de 3 linhas encostando num card** → encurte o trecho ou a pill.
- **`makeCues` só anda para frente** → declare os cues na ordem da fala e remova o cue quando remover a frase.
- **Último quadro preto** → sempre confira o último quadro.
- **Apresentador saiu em −15 LUFS** → o projeto não tem `media/video/presenter.mp4` (rode o `ss prepare-presenter`) ou um `--lufs` explícito foi passado.
- **Trilha não toca no motion narrado** → o `AdShell` só toca a trilha com `music="light"` ou `music="dark"`.

## Áudio

- **O Whisper erra o nome da marca** → no motion narrado, a legenda vem do roteiro (`ss align --script`), nunca da transcrição.
- **Acelerar a narração exige reescalar as palavras** (`s/vel`, `e/vel`). No motion narrado, não acelere: foi rejeitado. No apresentador, o `ss prepare-presenter` já reescala.
- **Tag de emoção no TTS** soa artificial → não use.
- **Fila cheia ou "atividade incomum" na ferramenta de voz** → tente mais tarde.
- **Som gerado veio mudo ou com voz** (aconteceu com 4 de 20 efeitos e com uma trilha marcada como instrumental que precisou ser conferida) → o `ss kit add-sfx` apara e normaliza, mas confira o arquivo antes de usar e peça para alguém ouvir.
- **Trilha pedida com uma duração veio com outra** (pediu 31 s, veio 40 s) → meça sempre.
- **O agente não escuta** → peça para uma pessoa ouvir.

## Corte

- **Whisper alucina nos falsos inícios** e esconde takes dentro de palavras esticadas → retranscreva o trecho como clipe curto ([cortes.md](cortes.md)).
- **Sala com ruído** → `silence_db: -28` no `corte.json`.
- **Sigla de claquete virando nome na legenda** → leitura incerta antes do roteiro é claquete; pergunte.

## Banco de imagem

- **Prévia com xadrez e texto queimados** → recorte do PSD ([banco-de-imagem.md](banco-de-imagem.md)).
- **Custo por download pouco claro** → confira o saldo antes e depois e avise a pessoa.

## Navegador e downloads

- **Tabela de painel dentro de iframe sem texto legível** → screenshot + zoom.
- **Download grande de pasta compartilhada para na tela de antivírus** → é preciso confirmar o download na página.
- **Navegador bloqueia vários downloads automáticos** → peça à pessoa para liberar para o site.
- **Planilha de outra conta sem acesso** → peça um CSV exportado.
- **Link de vídeo privado, com bloqueio regional ou sem direito de uso** → o `ss download` falha com uma mensagem em português; peça o arquivo.

## Conteúdo

- **Narração afirmando o que a tela não mostra** → confira cada afirmação contra o visual.
- **"Porte" que virou paráfrase** → método literal ([roteiro-publico-frio.md](roteiro-publico-frio.md)).
- **Distorção de texto SVG imitando 3D** → fica barata; use a fonte limpa.

## Ferramentas do Claude

- **Edit falha com "string not found"** depois de outras edições → releia o arquivo. Em substituição por script, confira antes que o trecho aparece exatamente 1 vez.
- **`rm` com variável é bloqueado pelo sandbox** → use `${VAR:?}` ou o caminho literal.
