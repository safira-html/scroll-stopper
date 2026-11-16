---
name: onboarding-de-marca
description: Cadastra ou confirma uma marca na pasta de trabalho do Scroll Stopper (cores, fontes, logo, público, voz, pronúncia, tela final, proibições), extrai cores e fontes do site, monta brand.json e BRAND.md e mostra um rascunho de teste para aprovação. Use quando a marca do vídeo ainda não existe em .scroll-stopper/marcas, quando a pessoa quiser revisar uma marca ou preferir usar uma marca sem guardar.
---

# Onboarding de marca

**Antes de tudo:** se esta skill não foi chamada pela `scroll-stopper:editar-video` nesta conversa, chame-a primeiro (ela confere o ambiente, a pasta de trabalho e o caminho) e só volte aqui quando ela pedir o onboarding.

Guia completo: `${CLAUDE_PLUGIN_ROOT}/knowledge/onboarding-de-marca.md` (leia antes de começar).

O CLI é `"${CLAUDE_PLUGIN_ROOT}/bin/ss"` (abaixo, `ss`; também fica no PATH do Bash com o plugin ativo). Rode a partir da pasta de trabalho e use aspas em caminhos com espaço.

## Passo a passo

1. **Veja o que já existe:** `ss workspace brands`. Se a marca existe, mostre o resumo do `BRAND.md` e confirme se é ela e se algo mudou.
2. **Pergunte uma coisa de cada vez, nesta ordem** (espere a resposta antes da próxima):
   1. marca e produto, com o link do site ou da página de vendas;
   2. design system (Figma, tokens, CSS, brandbook);
   3. cores e fontes, se não houver design system;
   4. logo (SVG ou PNG transparente; versão para fundo escuro);
   5. imagens da marca (fotos, ícones, mockups, telas do produto);
   6. referências visuais de que gosta e de que não gosta (sem referências, mostre a síntese de `${CLAUDE_PLUGIN_ROOT}/knowledge/referencias/motion-reference-breakdown.md`);
   7. público e voz (idade, gênero, momento de vida, de onde vem o dado; voz masculina, feminina ou as duas; tom);
   8. pronúncia do nome da marca e dos produtos;
   9. oferta da tela final (título, 2–4 itens, preço exatamente como na página, garantia, CTA) ou, em conteúdo orgânico, só o CTA;
   10. proibições (promessas, concorrentes, compliance);
   11. guardar a marca na pasta de trabalho ou **não guardar** (marca efêmera).
3. **Extraia do site** quando houver link: `ss brand extract "<url>"`. Mostre as cores e fontes encontradas e peça para a pessoa dizer o que é fundo, texto e destaque. Não decida sozinha.
4. **Monte a marca** a partir do modelo neutro do plugin (escolha um slug curto, minúsculo, com hífens); o comando imprime a pasta criada:
   - guardar: `ss brand new <slug>` (cria `.scroll-stopper/marcas/<slug>/`);
   - não guardar: `ss brand new <slug> --ephemeral` (cria `~/.cache/scroll-stopper/tmp-brands/<slug>/`; nada vai para a pasta da pessoa). Nos comandos seguintes, use o **caminho impresso** no lugar do slug em `--brand`.
   Preencha o `brand.json` e o `BRAND.md` seguindo o guia: fonte de cada token, contraste do acento, fontes com o nome exato do Google Fonts, logo em `assets/`, `captions.keepTogether`, `endCard` igual à página, voz sem ID de clone.
5. **Rascunho de teste** (não gasta crédito; usa o anúncio-modelo com tempos de demonstração):
   ```bash
   ss draft teste-<slug> Template-m --brand <slug ou pasta da marca efêmera>
   ```
   Abra e olhe `~/.cache/scroll-stopper/work/teste-<slug>/out/sheet.jpg`, extraia um quadro da tela final do `draft.mp4` (receita em `${CLAUDE_PLUGIN_ROOT}/knowledge/qa-e-entrega.md`) e mostre as imagens à pessoa. Confira contraste, fontes, logo no fundo escuro e textos da tela final.
6. **Ajuste até a pessoa aprovar.** Só então volte para a skill que chamou o onboarding, dizendo o slug (ou a pasta da marca efêmera).

## Regras

- Uma pergunta por vez. Nunca invente cor, fonte, preço ou público: o que a pessoa não sabe fica como pendência no `BRAND.md`.
- Nenhuma marca herda a identidade de outra; não copie tokens de uma marca para outra.
- Para o time não refazer o onboarding em cada computador, sugira (sem exigir) manter `.scroll-stopper/marcas/` numa pasta compartilhada do time.
- Nada da marca vai para o repositório do plugin. Nunca envie nada para o GitHub.

## Aprendizados

Quando a pessoa corrigir algo da marca ou do processo, anote na hora:

```bash
ss workspace learn "<o que foi corrigido e a regra que fica>" --source onboarding-de-marca
```

Correção que vale só para esta marca vai também no `BRAND.md` dela, em "Exceções às regras de gosto".
