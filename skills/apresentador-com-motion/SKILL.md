---
name: apresentador-com-motion
description: Monta o vídeo do caminho A do Scroll Stopper depois do corte - alterna telas do apresentador (close com punch-in, tela dividida) com telas de motion e flashes de palavra, com transições, legenda karaokê por tela e um efeito sonoro em cada troca, a partir do modelo PresenterTemplate; mostra rascunho, aplica ajustes e renderiza o vídeo final. Use depois da skill corte, com o corte preparado e sem avisos pendentes.
---

# Apresentador com motion (caminho A)

**Antes de tudo:** se o caminho e a marca ainda não foram confirmados nesta conversa pela skill `scroll-stopper:editar-video`, chame-a primeiro e só volte aqui depois da confirmação.

Leia antes: `${CLAUDE_PLUGIN_ROOT}/knowledge/apresentador-com-motion.md` (telas, ritmo, legenda, conteúdo), `${CLAUDE_PLUGIN_ROOT}/knowledge/motion.md` (gramática e "Onde editar"), `${CLAUDE_PLUGIN_ROOT}/knowledge/regras-de-gosto.md` e as linhas de `.scroll-stopper/aprendizados.md`.

O CLI é `"${CLAUDE_PLUGIN_ROOT}/bin/ss"` (abaixo, `ss`; também fica no PATH do Bash com o plugin ativo). Rode a partir da pasta de trabalho e use aspas em caminhos com espaço. `<id>` é o id do projeto; `<marca>` é o slug confirmado (ou a pasta da marca efêmera).

Pré-requisito: a skill `scroll-stopper:corte` já rodou `ss prepare-presenter` para este id e não há aviso sem decisão. Existem `media/video/presenter.mp4`, `media/audio/<id>-m.mp3` e `media/audio/<id>-m.words.json` em `~/.cache/scroll-stopper/work/<id>/`.

## Passo a passo

1. **Kit de som (opcional).** Rode `ss kit status`. O kit da pasta de trabalho entra no projeto sozinho (a cada `ss brand use`, `ss draft` e `ss render`). Sem kit, o vídeo sai só com a voz; nada quebra. Se a pessoa quiser montar o kit, siga `${CLAUDE_PLUGIN_ROOT}/knowledge/som.md` (bancos gratuitos primeiro; geração paga só com custo informado e o sim dela).
2. **Engine do projeto:** `ss brand use <marca> --project <id>`. O comando imprime a pasta do engine do projeto (`~/.cache/scroll-stopper/work/<id>/engine`). Todas as edições abaixo são nessa pasta, nunca no plugin instalado.
3. **Composição:**
   - copie `src/ads/PresenterTemplate.tsx` para `src/ads/<Nome>.tsx` (por exemplo `Video01.tsx`) e troque os nomes exportados (`PresenterTemplate` → `Video01`, `PRESENTER_SCRIPT` → `VIDEO01_SCRIPT`);
   - registre em `src/ads/index.ts`: importe o componente e acrescente em `ADS` a entrada `{id: '<id>', component: Video01, voices: ['m'], tail: 0.35 + OUTRO_SECONDS}`;
   - a composição se chama `<id>-m`.
4. **Meça o rosto** em 2 ou 3 quadros de `media/video/presenter.mp4` com grade (receita no guia) e ajuste `face` no `SOURCE`.
5. **Planeje as telas a partir das palavras** (`media/audio/<id>-m.words.json`): para cada frase, escolha o tipo de tela (close com punch-in, tela dividida, só motion, flash de palavra), a transição e o efeito. Troca a cada 2–5 s, sempre numa frase falada, sem repetir tipo de tela nem transição em sequência. Mostre o plano à pessoa em uma tabela curta (tempo, fala, tela) antes de codar se o vídeo passar de 30 s.
6. **Escreva a composição:** cues com `makeCues` na ordem da fala; `SegmentCaptions` por tela com trechos de 2–4 palavras escritos exatamente como no `words.json`; `CAPTION_TOP` certo para cada tela; nada de texto sobre o rosto; zona segura y 270–1250; cena de motion mostra o que ele fala; número falado só aparece com fonte; um `Sfx` em cada troca de tela. Conteúdo orgânico termina na saída curta com o logo; anúncio com oferta pode ganhar a tela final da marca.
7. **Rascunho:** `ss draft <id> <id>-m --brand <marca>`. Abra a folha de contatos (`~/.cache/scroll-stopper/work/<id>/out/sheet.jpg`) e quadros do começo, do CTA e da saída. Passe pelo checklist de `${CLAUDE_PLUGIN_ROOT}/knowledge/qa-e-entrega.md` e corrija o que achar **antes** de mostrar.
8. **Mostre o rascunho** (`~/.cache/scroll-stopper/work/<id>/out/draft.mp4`) e aplique os ajustes pedidos, um a um, com um novo `ss draft` quando mudar algo visível.
9. **Render final** (só depois do OK no rascunho):
   ```bash
   ss render <id> <id>-m --dest "<pasta de entrega>" --name <nome> --brand <marca>
   ```
   Sai em −14 LUFS sozinho (o projeto tem `presenter.mp4`). Se o comando imprimir `[!!] Conferência falhou`, explique o motivo e corrija antes de entregar.
10. **Entregue:** diga o caminho completo do `.mp4` final e liste o que uma pessoa precisa ouvir (emendas, pronúncia, trilha e efeitos), porque o agente não escuta.

## Regras

- Nunca edite arquivos do plugin instalado; só a cópia do engine em `~/.cache/scroll-stopper/work/<id>/engine/`.
- Um erro de sintaxe em `src/ads/` quebra o render; se o `ss draft` falhar, leia a mensagem, corrija e rode de novo.
- Geração paga (trilha, efeito, imagem) só com o custo informado e o sim da pessoa.
- Nunca publique o vídeo e nunca envie nada para o GitHub.

## Aprendizados

Quando a pessoa corrigir algo (posição de texto, tipo de tela, transição, volume, legenda), anote na hora:

```bash
ss workspace learn "<o que foi corrigido e a regra que fica>" --source apresentador-com-motion
```
