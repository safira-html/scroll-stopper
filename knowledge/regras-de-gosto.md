# Regras de gosto: o que foi corrigido e virou regra

O arquivo mais importante do plugin. Cada regra saiu de uma correção real feita por quem pediu os vídeos durante a produção de anúncios em motion e de vídeos com apresentador. Formato: o que foi dito (resumido), o que mudou e a regra que fica. São **regras de prática**, não dados de plataforma: valem como padrão até uma marca pedir outra coisa (a exceção vai no `BRAND.md` da marca).

Antes de mostrar qualquer coisa para quem pediu, passe por esta lista. A barra de qualidade da primeira leva foi "não está perfeito, mas para uma v1 está bem bom". O objetivo é começar acima disso.

Os aprendizados locais da pessoa (`.scroll-stopper/aprendizados.md` na pasta de trabalho) somam-se a estas regras e valem para os vídeos dela.

## Visual

| # | O que foi dito | O que mudou | Regra |
|---|---|---|---|
| V1 | "cada tela precisa chamar atenção… está fraco" (sobre uma v1 só de tipografia) | A v2 ganhou um objeto ilustrado por cena; a v3, a gramática das referências | **Texto sozinho na tela nunca basta.** Toda cena tem um objeto-âncora concreto e detalhado (UI em SVG, render 3D ou ilustração rica), com entrada animada, zoom e profundidade. Ornamento girando não conta como visual. |
| V2 | A primeira imagem "tem que ser a mais legal" (o gancho era uma linha fina emaranhada) | A linha virou uma pilha 3D de cards bagunçados que treme e se organiza | **O primeiro quadro é a imagem mais forte do vídeo** e já está composto no frame 0. Nada de desenho de linha fina como gancho. |
| V3 | Texto "bem na cara da pessoa" é ruim | Os textos foram reposicionados depois de checar onde estão os rostos com grade | **Nunca ponha texto sobre rosto.** |
| V4 | "parece balaio de gato" (planos de vídeo de banco de lugares diferentes) | Mesmo ator de uma única série do banco, uma correção de cor e uma tinta únicas | **Vídeo de banco precisa parecer uma filmagem só:** mesma pessoa, mesmo tipo de lugar, uma correção de cor. |
| V5 | "deixou muito escuro o que botou por cima" | Escurecimento por plano ×0,45, grade e tinta mais leves, degradê do topo mais curto | **Overlay leve.** No máximo uma tinta leve mais um degradê curto atrás da legenda. Nunca empilhe escurecimento por plano, grade e degradê pesados. |
| V6 | "horrível esse jeito de elipse… bota só a tipografia normal" (bulge feito com mapa de deslocamento SVG) | Voltou para a serifada limpa, na cor de destaque, sem distorção | **Nunca distorça texto de gancho** para imitar 3D: fica barato. Se não der para reproduzir fielmente o efeito da referência, use a fonte limpa. |
| V7 | "cuidado para não ficar um carnaval" (mono + sans + serif) | Família unificada por peça | **No máximo 2 famílias tipográficas por vídeo**: uma de display/legenda e uma de UI. |
| V8 | "um pouquinho mais para cima… está pegando na cabeça" | Gancho subiu | O texto do gancho não encosta em cabeça nem rosto. |
| V9 | "remove o texto… conflita com a legenda… isso não está na locução" | O título sem fala saiu | **Não ponha título que não é falado.** Ele compete com a legenda karaokê, a protagonista do motion. |

## Legenda e tipografia

| # | O que foi dito | O que mudou | Regra |
|---|---|---|---|
| L1 | Gosta do destaque "mudando o peso da fonte" | Mantido | **Destaque karaokê por peso**: cada palavra vai de cinza e fina (300) a cor de texto e bold (700) quando é falada. |
| L2 | "uma palavra da primeira linha desce para a segunda; o ideal é a frase já começar com as linhas quebradas" | Quebras calculadas antes, com a largura final (bold) de cada palavra | **A quebra de linha é fixa desde o primeiro quadro.** Nunca deixe reflow durante a animação. |
| L3 | "não é legal uma palavra sozinha numa linha… evitar viúvas e órfãs" | Penalidade de viúva, palavra fraca não termina linha, nomes inseparáveis | **Nenhuma linha com uma palavra só.** Linha não termina em artigo ou preposição. Nomes de marca, produto e CTA não se quebram (`captions.keepTogether` no `brand.json`). |
| L4 | "retângulo preto, texto colorido e sombra branca… dificulta o contraste" | Sem sombra nem brilho no texto das pills | **Sem sombra nem brilho no texto dentro de pill ou caixa de destaque.** |
| L5 | "diminui em 100 o peso, só da mais pesada" | 800 → 700 | **Peso máximo 700.** |
| L6 | "no máximo 3 a 4 palavras por linha… deixa maior a legenda" | Trechos de 3–4 palavras em uma linha, tamanho 112, redução automática até 72% para caber | **Vídeo de banco ou vlog: legenda grande, 3–4 palavras por trecho, uma linha.** No motion: 2–4 palavras por trecho, grande, ilustração sem encostar. |

## Voz e áudio

| # | O que foi dito | O que mudou | Regra |
|---|---|---|---|
| A1 | "parece que está gemendo e do nada muda a voz… a de antes estava melhor" (tags de emoção no TTS) | Narração sem tags | **Sem tags de emoção no TTS.** O tom vem da pontuação: reticências, dois-pontos, vírgulas. |
| A2 | Quer voz que combine com quem compra | Voz escolhida pelo perfil de compra | **Escolha a voz pelo perfil de quem compra** (gênero e idade, com fonte no `BRAND.md`). |
| A3 | "fala o nome da marca errado" | Acento só no texto enviado ao TTS | **Ajuste a pronúncia no texto do TTS** (acento, número por extenso) e mantenha a grafia correta na legenda. Registre a pronúncia da marca no onboarding. |
| A4 | "uma voz por texto para não ficar repetido" | Uma voz por roteiro na leva final | **Uma voz por roteiro na leva final**, alternando masculina e feminina. Gere as duas só para escolher. |
| A5 | "odiei as versões aceleradas… fica em 1x" | Descartadas as versões em 1,15x | **No motion narrado, nunca acelere o vídeo pronto.** O ritmo vem do roteiro e da voz. (No apresentador, a velocidade segue o ritmo de fala: [cortes.md](cortes.md).) |
| A6 | Voz naturalmente rápida não precisa acelerar | Ficou em 1x | Voz rápida fica em 1x. |
| A7 | Consentimento do clone dado por escrito | O consentimento na ferramenta só foi marcado depois disso | **Clone de voz só com consentimento explícito** da pessoa dona da voz, registrado. Clone, ID ou amostra de voz de pessoa real nunca entra no repositório do plugin. |

## Roteiro, oferta e fatos

| # | O que foi dito | O que mudou | Regra |
|---|---|---|---|
| R1 | Quer tensão (ansiedade) em boa parte das peças | Ansiedade sempre como voz interna ou cenário | Ansiedade **nunca atribuída à pessoa** ("você está ansioso?"). A política de anúncios da Meta proíbe conteúdo que afirme ou insinue atributos pessoais, inclusive saúde mental: https://transparency.meta.com/policies/ad-standards/objectionable-content/privacy-violations-personal-attributes/ |
| R2 | "metade com o que já deu certo… sem deixar de testar ângulos novos" | Parte da leva derivada de vencedores | **Pelo menos metade da leva vem de anúncios que já venderam** (ordenados por vendas e custo por venda, depois CTR); o resto testa ângulos novos. |
| R3 | "esse roteiro foi feito baseado em quê? parece igual aos anteriores" | Reescrito pelo método de porte | **Quando pedirem "um igual ao X", porte o esqueleto do X literalmente** (conectivos, ordem, tempo verbal) e troque só o conteúdo, com fonte. Parafrasear com o conteúdo antigo não é portar. |
| R4 | A dona do produto corrigiu um número da página | Corrigido em todas as peças | Fato dito pela dona do produto vale mais que a página; registre a fonte e a data e avise onde a página está desatualizada. |
| R5 | Âncora de preço só onde foi autorizada | Âncora só nas peças autorizadas | **Âncora de preço só com OK explícito** e igual à página. Registre onde foi usada. |
| R6 | Pediu para conferir contra o checklist de público frio | Checklist aplicado a todo roteiro | Todo roteiro passa pelo checklist de [roteiro-publico-frio.md](roteiro-publico-frio.md) antes de produzir. |
| R7 | Misturar fundo claro e escuro "porque o topo da página de vendas é escuro… conectar criativo e página" | Peças claras viram escuras quando o produto entra; a tela final copia o topo da página | **Ponte com a página:** o fim do vídeo reproduz o primeiro quadro da página de destino, e o vídeo fala uma frase que a pessoa vai reler lá. |

## Corte e apresentador

| # | O que foi dito | Regra |
|---|---|---|
| C1 | Sigla de claquete virou nome de pessoa na legenda | Leitura incerta antes do roteiro é claquete: corte e pergunte ([cortes.md](cortes.md)). |
| C2 | "tira esse 'uuuu' aos 29 s" | Ruído de voz entre frases sai. Resolva todos os avisos do `ss prepare-presenter` antes do render final. |
| C3 | "enquadra melhor, rosto mais para cima, e mais devagar (avaliando 1x ou 1,1x)" | Velocidade pelo ritmo de fala (~184 palavras/min, 1,0–1,3x); rosto medido com grade antes de fixar o enquadramento. |
| C4 | Conteúdo orgânico com CTA de comentário | Não leva a tela de oferta de 11 s: saída curta de 2–3 s com o logo. |

## Processo e comunicação

| # | Situação | Regra |
|---|---|---|
| P1 | "tem algo meio pronto para eu já olhar?" | Mostre rascunho em meia resolução (`ss draft`) enquanto itera; não espere o render final. |
| P2 | Pedidos de ajuste em frases curtas | Aceite ajustes como "tira esse 'uuuu' aos 29 s" e aplique só aquilo; depois mostre de novo. |
| P3 | Resumo de vários vídeos | Descreva **o que cada vídeo fala**, não o número do arquivo. |
| P4 | Antes de gastar crédito | Diga o que vai gerar e o custo estimado e espere o sim. Gere uma amostra curta antes do roteiro inteiro. Se passar do aprovado, avise na hora. |
| P5 | Entrega | A entrega é o vídeo pronto e o caminho onde ele está. O plugin nunca publica, nunca sobe anúncio e nunca manda mensagem por ninguém. |
| P6 | Correção feita durante o uso | Anote na mesma sessão com `ss workspace learn "<texto>" --source <skill>`: correção que fica só na conversa volta na próxima sessão. |
