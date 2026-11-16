---
name: motion-narrado
description: Caminho B do Scroll Stopper - vídeo 100% motion sincronizado com uma voz (enviada pela pessoa ou gerada numa ferramenta de terceiros que ela tenha), com legenda karaokê, trilha, efeitos e tela final quando for anúncio. Escreve ou confere o roteiro para público frio e só gera voz depois do roteiro aprovado e do custo confirmado. Use depois que o caminho B e a marca foram confirmados na skill editar-video.
---

# Motion narrado (caminho B)

**Antes de tudo:** se o caminho e a marca ainda não foram confirmados nesta conversa pela skill `scroll-stopper:editar-video`, chame-a primeiro e só volte aqui depois da confirmação.

Leia antes: `${CLAUDE_PLUGIN_ROOT}/knowledge/voz.md`, `${CLAUDE_PLUGIN_ROOT}/knowledge/roteiro-publico-frio.md`, `${CLAUDE_PLUGIN_ROOT}/knowledge/motion.md` (gramática e "Onde editar"), `${CLAUDE_PLUGIN_ROOT}/knowledge/regras-de-gosto.md` e as linhas de `.scroll-stopper/aprendizados.md`.

O CLI é `"${CLAUDE_PLUGIN_ROOT}/bin/ss"` (abaixo, `ss`; também fica no PATH do Bash com o plugin ativo). Rode a partir da pasta de trabalho e use aspas em caminhos com espaço. `<id>` é o id do projeto; `<marca>` é o slug confirmado (ou a pasta da marca efêmera).

## Passo a passo

1. **De onde vem a voz** (pergunte e espere):
   - a pessoa já tem o áudio gravado → peça o arquivo;
   - a pessoa tem uma ferramenta de voz → veja quais conectores de geração de voz existem nesta sessão e ofereça só os que ela tem; sem conector, ela pode gerar no site da ferramenta e enviar o arquivo;
   - nenhuma das duas → peça para ela gravar (celular serve) e enviar. Nunca exija conta paga.
2. **Roteiro** (pergunte se ela traz pronto ou quer que você escreva):
   - **pronto:** confira cada fato contra uma fonte (página, `BRAND.md`, arquivo dela) e ajuste só a pronúncia para a voz;
   - **escrever:** levante os fatos, escreva pelo método gancho → conteúdo → produto → CTA e passe pelo checklist de `roteiro-publico-frio.md`, respeitando as proibições do `BRAND.md`.
   Grave a versão da legenda em `.scroll-stopper/projetos/<id>/roteiro.txt` e, se precisar de ajuste de pronúncia, a versão do TTS em `roteiro-tts.txt`. **Mostre o roteiro e espere a aprovação antes de gerar qualquer voz.** Se a voz já foi gravada, o roteiro é o que foi falado.
3. **Gerar voz (só se for por ferramenta):**
   - diga o que vai gerar e o custo aproximado (confira o preço atual na ferramenta) e espere o sim;
   - primeiro uma **amostra curta** (o gancho) em 3–4 vozes, para a pessoa escolher; sem tags de emoção; tudo em 1x;
   - depois da escolha, novo aviso de custo e a narração inteira a partir de `roteiro-tts.txt`;
   - salve como `.scroll-stopper/projetos/<id>/narracao.mp3`. Clone de voz só com consentimento explícito e registrado da pessoa dona da voz.
4. **Alinhe a voz às palavras:**
   ```bash
   ss align ".scroll-stopper/projetos/<id>/narracao.mp3" <id>-m --project <id> --script ".scroll-stopper/projetos/<id>/roteiro.txt"
   ```
   Use `<id>-f` para voz feminina (e `f` nos passos seguintes). Sem roteiro, omita `--script` e revise os nomes de marca na legenda.
5. **Kit de som (opcional):** rode `ss kit status`. O kit da pasta de trabalho entra no projeto sozinho (a cada `ss brand use`, `ss draft` e `ss render`). Sem kit, o vídeo sai só com a voz. Para montar um kit: `${CLAUDE_PLUGIN_ROOT}/knowledge/som.md`.
6. **Engine do projeto:** `ss brand use <marca> --project <id>` (imprime a pasta `~/.cache/scroll-stopper/work/<id>/engine`). Edite só nessa pasta.
7. **Composição:**
   - copie `src/ads/Template.tsx` para `src/ads/<Nome>.tsx` e troque os nomes exportados (`Template` → `<Nome>`, `SCRIPT` → `<NOME>_SCRIPT`), com o roteiro da legenda no script;
   - registre em `src/ads/index.ts`: `{id: '<id>', component: <Nome>, demoScript: <NOME>_SCRIPT, voices: ['m']}`;
   - a composição se chama `<id>-m`.
8. **Escreva as cenas:** uma cena por bloco do roteiro, cada uma ancorada numa frase (`makeCues`, na ordem da fala); objeto concreto em toda cena e no frame 0; microeventos a cada 0,3–0,6 s; trechos de legenda de 2–4 palavras com a palavra-chave em pill; produto, CTA e tela final no tema escuro; `music="light"` ou `music="dark"` no `AdShell` se houver trilha; efeitos acompanhando eventos visuais. Anúncio termina na tela final da marca (`brand.endCard`, 11 s); confira que o CTA falado é igual a `endCard.cta`.
9. **Rascunho:** `ss draft <id> <id>-m --brand <marca>`. Olhe a folha de contatos (`~/.cache/scroll-stopper/work/<id>/out/sheet.jpg`) e quadros soltos (gancho, troca para o escuro, CTA, tela final, último quadro); passe pelo checklist de `${CLAUDE_PLUGIN_ROOT}/knowledge/qa-e-entrega.md` e corrija antes de mostrar.
10. **Mostre o rascunho** (`draft.mp4`) e aplique os ajustes pedidos, com novo `ss draft` a cada mudança visível.
11. **Render final** (depois do OK):
    ```bash
    ss render <id> <id>-m --dest "<pasta de entrega>" --name <nome> --brand <marca>
    ```
    Sai em −15 LUFS, TP −1,5. Se aparecer `[!!] Conferência falhou`, explique e corrija antes de entregar.
12. **Entregue:** diga o caminho completo do `.mp4` final e liste o que uma pessoa precisa ouvir (pronúncia da marca, siglas, trilha, efeitos) e as pendências de licença (voz, banco de imagem).

## Regras

- Nenhuma voz é gerada antes do roteiro aprovado e do custo confirmado. Amostra curta antes do roteiro inteiro.
- Nunca acelere o vídeo pronto; ritmo vem do roteiro e da voz.
- Todo fato falado ou mostrado tem fonte; sem fonte, sai.
- Nunca edite o plugin instalado; só a cópia do engine do projeto.
- Nunca publique o vídeo e nunca envie nada para o GitHub.

## Aprendizados

Quando a pessoa corrigir algo (roteiro, voz, cena, legenda, som), anote na hora:

```bash
ss workspace learn "<o que foi corrigido e a regra que fica>" --source motion-narrado
```
