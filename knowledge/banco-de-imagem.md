# Banco de imagem e vídeo

Imagens, ícones e vídeos de banco entram no projeto em `~/.cache/scroll-stopper/work/<id>/media/stock/` (o engine lê como `staticFile('stock/<arquivo>')`). Nunca no repositório do plugin e nunca dentro de `public/` do engine diretamente: o Remotion copia `public/` inteiro em cada bundle, e uma pasta de 1,6 GB deixou tudo lento (observado na prática).

## Fontes e licenças

Licenças mudam: abra a página de licença antes de usar em campanha e guarde um print com a data.

| Fonte | Uso | Licença (conferida em 12/11/2026) |
|---|---|---|
| **Pexels** (vídeo e foto) | Vídeo de banco para peças "vlog" | Grátis, sem atribuição obrigatória; lista anúncios e marketing de produto entre os usos permitidos. Proíbe mostrar pessoas identificáveis de forma ofensiva, sugerir que pessoas ou marcas endossam o seu produto e usar como marca. https://www.pexels.com/license/ |
| **Unsplash** (foto) | Foto | Uso comercial e não comercial grátis, sem atribuição obrigatória; não pode vender sem modificação significativa. O Unsplash+ tem licença própria. https://unsplash.com/license |
| **3dicons** | Ícones 3D | CC0, uso comercial sem atribuição. https://3dicons.co/ (a coleção é limitada: confira se tem o ícone de que você precisa) |
| **Freepik e similares** (conector ou site, se a pessoa tiver conta) | Ícones e renders 3D, fotos | Depende do plano e do item; conteúdo marcado como editorial não serve para anúncio. Confira nos termos: https://www.freepik.com/legal/terms-of-use |

Vídeo de banco em bancos pagos costuma custar caro por clipe: prefira o Pexels para vídeo. Antes de baixar qualquer coisa paga, diga o que vai baixar e o custo e espere o sim (confira o preço atual na própria ferramenta).

## Ícones 3D vindos de PSD

Em alguns bancos, a prévia vem com xadrez de transparência e texto promocional queimados nos pixels, e o pacote traz só JPG e PSD. Para recortar:

1. Baixe o pacote com o PSD (custo antes, se for pago).
2. Recorte as camadas com `psd-tools` num venv separado.
3. Confira cada recorte sobre o fundo claro e o escuro da marca, com zoom 2× nas bordas.
4. Descarte o que tiver dado falso na própria camada (gráfico com porcentagem inventada) ou cor fora da paleta.

Evite celular de marca reconhecível, print de rede social, personagens 3D genéricos de executivo e assets fora da paleta.

## Vídeo de banco (formato vlog)

1. **Uma série só:** escolha planos de **uma mesma série de um mesmo autor**, com o mesmo ator e o mesmo tipo de lugar (numa produção anterior, 6 planos de uma série bastaram).
2. Busque no site do banco pelo navegador e anote id, título e link de cada plano.
3. Baixe o arquivo do plano (o link de download do Pexels traz a resolução e o fps no nome; o fps varia entre 24, 25, 30 e 60). Confira duplicatas com `md5`.
4. **Onde estão os rostos:** tire quadros de cada plano com grade (`ffmpeg -vf "drawgrid=w=270:h=60:t=1:c=yellow@0.6"`) e posicione legenda e chips longe deles.
5. **Uma correção de cor para todos os planos** (CSS no `OffthreadVideo`). Valores aprovados numa produção anterior, para ajustar à marca:
   - filtro: `saturate(0.8) contrast(1.04) brightness(1.08) sepia(0.08)`;
   - tinta em soft-light: um degradê leve na cor escura da marca mais um toque quente, que puxa as sombras para a marca e deixa as luzes quentes;
   - degradê atrás da legenda: `.55 0% / .25 22% / 0 36% / 0 70% / .3 100%`;
   - escurecimento por plano entre 0,05 e 0,16. A primeira versão, 2× mais escura, foi rejeitada ("muito escuro").
6. Cada plano ganha um zoom lento (`[1.04, 1.1]`) e começa num ponto interessante do clipe.
7. **Produto e CTA vão numa cena escura da marca,** não sobre o vídeo.
8. Gancho em serifada limpa na cor de destaque, sem distorção, longe da cabeça da pessoa. Legendas grandes, com 3–4 palavras.

## Prints de tela reais

- Print de site ou app real só com **nome, logo da empresa e marca da rede mascarados**. Troque elementos identificáveis por genéricos (barra "Buscar", botão neutro "Continuar").
- O que a narração afirma sobre o print tem de estar no print.

## Referências de estudo

Vídeos de concorrentes e pins de referência servem **só para estudo**: nunca entram no render.
