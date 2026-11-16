# Onboarding de uma marca nova

O engine é o mesmo para qualquer marca. O que muda mora **na pasta de trabalho da pessoa**, em `.scroll-stopper/marcas/<slug>/`: `brand.json`, `BRAND.md` e `assets/`. Nenhuma marca nova herda a identidade de outra, e nenhuma marca entra no repositório do plugin.

Para o time não refazer o onboarding da mesma marca em cada computador, a pasta `.scroll-stopper/marcas/` pode ficar numa pasta compartilhada do time (sugestão, não exigência).

## Quando rodar

Sempre que o pedido for para uma marca que ainda não tem pasta em `.scroll-stopper/marcas/` (`ss workspace brands` lista as existentes). Mesmo quando a marca existe, confirme com a pessoa que é ela.

## Perguntas (uma de cada vez, nesta ordem)

1. **Qual é a marca e o produto?** Peça o link do site ou da página de vendas.
2. **Já existe um design system?** Figma, arquivo de tokens ou CSS, brandbook em PDF ou repositório.
3. **Se não existe:** quais são as cores (principal, de destaque, fundos) e as fontes? Se a pessoa não souber, extraia do site (abaixo) e mostre o que achou para ela confirmar.
4. **Logo:** tem SVG ou PNG transparente? Precisa de versão para fundo escuro?
5. **Imagens da marca:** fotos, ícones, mockups ou telas do produto que possam entrar nos vídeos?
6. **Referências visuais:** anúncios ou perfis de que gosta (e de que não gosta)? Se não tiver, mostre a síntese em [referencias/motion-reference-breakdown.md](referencias/motion-reference-breakdown.md) e pergunte o que manter.
7. **Público e voz:** quem compra (idade, gênero, momento de vida, e de onde vem esse dado)? Voz masculina, feminina ou as duas? Tom (direto, mentor, amigo, autoridade)?
8. **Pronúncia:** como se pronuncia o nome da marca e dos produtos? (vira o ajuste no texto do TTS)
9. **Oferta para a tela final:** título, 2–4 itens do que a pessoa recebe, preço exatamente como na página, garantia e texto do CTA. Para conteúdo orgânico, só o CTA e uma frase curta.
10. **O que não pode:** promessas proibidas, concorrentes que não podem aparecer, regras de compliance que já derrubaram anúncio.
11. **Guardar a marca?** Na pasta de trabalho (padrão) ou não guardar (marca efêmera, refeita a cada uso).

## Extrair cores e fontes de um site

```bash
ss brand extract https://site-da-marca.com.br
```

Aceita uma URL, um arquivo `.html` ou uma pasta com `index.html`. Imprime um JSON com as variáveis CSS (`--cor-…`), as cores mais usadas, as famílias de fonte e os links do Google Fonts.

É um ponto de partida, não a resposta. Mostre os resultados e confirme com a pessoa quais cores são fundo, texto e destaque. Se o site carrega as cores por JavaScript ou atrás de login, abra no navegador e leia os estilos calculados. Se a pessoa mandou um Figma e há conector do Figma na sessão, leia as variáveis por ele.

## Montar a marca

1. Crie a marca a partir do modelo neutro do plugin (o comando imprime a pasta criada):
   - marca guardada: `ss brand new <slug>` → `.scroll-stopper/marcas/<slug>/`;
   - marca efêmera: `ss brand new <slug> --ephemeral` → `~/.cache/scroll-stopper/tmp-brands/<slug>/` (nada é escrito na pasta da pessoa). Nos comandos seguintes, passe essa pasta em `--brand`.
2. Preencha o `brand.json`:
   - `slug` e `name`;
   - `colors.accent`: o único acento do vídeo (pill, destaque, CTA). Escolha a cor mais viva da marca;
   - `colors.accentInk`: o texto sobre o acento (contraste de pelo menos 4,5:1, critério WCAG AA para texto: https://www.w3.org/TR/WCAG21/#contrast-minimum);
   - `colors.accentDisplay`: o acento em versão escura, para texto de destaque sobre fundo claro (mesmo contraste);
   - `colors.light` e `colors.dark`: fundos e textos dos dois temas. O escuro é o da tela final; se a página da marca tem topo escuro, copie as cores dele;
   - `fonts.sans` (legenda e UI), `fonts.mono` (só interface de código e números) e `fonts.display` (serifada para gancho e vídeo de banco). Nomes exatos do Google Fonts: o engine recusa fonte que não existe lá;
   - `logos.header`: arquivo do logo para fundo escuro, dentro de `assets/`;
   - `captions.keepTogether`: nomes que nunca quebram entre linhas (marca, produto, ferramentas, CTA);
   - `endCard`: textos exatamente como na página. `tiles` são opcionais (logos em `assets/`); `backdrop` é `"none"` ou `"dashboard"`; `seconds` é a duração da tela final (11);
   - `voice`: provedor e vozes escolhidas na rodada de amostras, **sem ID de clone**.
3. Escreva o `BRAND.md`: fonte de cada token (arquivo, URL, data e quem conferiu), referências aprovadas e rejeitadas, pronúncia, público (com a fonte do dado), vozes, tom, proibições, fatos da oferta com fonte e exceções às regras de gosto.
4. Confira a marca num rascunho do anúncio-modelo (usa tempos de demonstração, sem gastar nada):
   ```bash
   ss draft teste-<slug> Template-m --brand <slug ou pasta da marca>
   ```
   Olhe a folha de contatos (`~/.cache/scroll-stopper/work/teste-<slug>/out/sheet.jpg`) e um quadro da tela final. Confira contraste, fontes e se o logo aparece no fundo escuro.
5. Mostre as imagens à pessoa e só siga depois do OK.

## O que não muda entre marcas

A linguagem de motion ([motion.md](motion.md)), o método de roteiro ([roteiro-publico-frio.md](roteiro-publico-frio.md)), as regras de gosto ([regras-de-gosto.md](regras-de-gosto.md)) e o QA ([qa-e-entrega.md](qa-e-entrega.md)).

As regras de gosto valem como padrão. Se a marca pedir outra coisa (por exemplo peso 800 ou vídeo acelerado), registre no `BRAND.md` como exceção daquela marca.
