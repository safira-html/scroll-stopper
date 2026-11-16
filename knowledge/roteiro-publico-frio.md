# Roteiro para público frio

Como escolher ângulos e escrever narrações de vídeo para **público frio**, ou seja, quem ainda não conhece a marca. Usado no caminho B quando a pessoa pede para o plugin escrever o roteiro. Se ela traz o roteiro pronto, só confira os fatos (seção 6) e ajuste a pronúncia para a voz ([voz.md](voz.md)).

**O roteiro é mostrado e aprovado antes de qualquer voz ser gerada.**

## 1. Antes de escrever: levante o que já se sabe

Pergunte e leia; cada fato vira uma linha com a fonte.

1. **Página de vendas ou de destino:** preço, parcelas, garantia, carga horária, bônus pelo nome e o que a página promete ou não promete. Anote o trecho de cada fato. Se a página tem variantes em teste A/B, anote as frases que mudam.
2. **Anúncios que já rodaram** (se a pessoa tiver): transcreva com `ss transcribe <video> <id>`, registre gancho, o que aparece na tela, mecanismo, CTA e resultados. Separe os que venderam dos que não venderam e procure o que têm em comum.
3. **Estáticos e carrosséis:** o mesmo, com título e argumento.
4. **Pesquisa com compradores** (se houver): idade, área de origem, medos e frases nas palavras deles. Confira o resumo contra os dados brutos.
5. O `BRAND.md` da marca: público, tom, proibições e fatos da oferta.

Cuidado com métricas: checkout pode vir inflado por atribuição, e anúncio de outro produto pode aparecer no mesmo painel (num caso real, um anúncio com muitos checkouts e nenhuma venda era de outro produto). Ordene os vencedores por **vendas e custo por venda primeiro, depois CTR**.

## 2. Estrutura de público frio

Método de prática, anotado de um curso de criativos para público frio (sem fonte pública verificável; os números abaixo são referência, não meta):

- **Frio = Gancho → Conteúdo → Produto → CTA.** Para público quente basta gancho → oferta → CTA: vende, mas não escala.
- O **conteúdo** faz pelo menos uma de três coisas:
  1. **mostrar o possível**, algo que a pessoa não sabia que dava;
  2. **desmistificar** algo que ela quer mas não acredita que consegue;
  3. **trazer urgência** para algo que ela já acha que precisa.
- **Gancho:** parada visual no primeiro segundo. Referência de prática para a taxa de retenção em 3 s: 30% é muito bom, 12% ou menos é ruim. Formato nativo segura mais que produção polida.
- **Curiosidade sem desejo derruba a conversão.** Fale do produto e do porquê, não só ensine.
- **Tela final de 10–14 s sem fala**, com o resumo da oferta. Na referência de prática, deu +0,2 p.p. de CTR; com 5–6 s não fez diferença. O plugin usa 11 s (`endCard.seconds` no `brand.json`).
- **Promessa:** o momento (timing) pesa mais do que tudo. Prefira "faça / construa / crie" a "descubra / aprenda / segredos".
- **Casting:** a voz e a pessoa na tela têm a idade de quem compra.
- **Ressalvas:** os números do curso vêm de outro nicho; são referência. Escassez só se for real. Vídeo de uma cena só é remarketing, não frio.

### Checklist (rode em todo roteiro antes de produzir)

| Critério | Pergunta |
|---|---|
| Estrutura | Tem gancho → conteúdo → produto → CTA? |
| Conteúdo | Mostra o possível, desmistifica ou traz urgência? A leva tem os três tipos? |
| Gancho | O primeiro quadro tem um objeto concreto que para o dedo? |
| Desejo | O produto entra com o porquê, e não só no fim? |
| Grade | Ao falar do produto, aparece um item concreto do que se recebe? |
| Autoridade | Existe um fato real de autoridade? Se não existe, não invente. |
| Timing | Algum roteiro usa o momento (tecnologia, mercado) como alavanca? |
| Tela final | Tem 10–14 s e repete exatamente a oferta da página? |
| Escassez | Só se for real. |
| Casting | A voz combina com a idade e o gênero de quem compra? |

## 3. Composição da leva (quando são vários vídeos)

- **Pelo menos 50% derivados de vencedores.** Mantenha o miolo que vendeu e varie o gancho. O resto testa ângulos novos.
- **Tensão em cerca de metade das peças,** sempre como voz interna ("Eu não sei por onde começar.") ou como cenário ("o cliente pede o orçamento para amanhã"). Nunca atribuída à pessoa ("você está ansioso?"): a política de anúncios da Meta proíbe afirmar ou insinuar atributos pessoais, inclusive saúde mental (https://transparency.meta.com/policies/ad-standards/objectionable-content/privacy-violations-personal-attributes/). A tensão é leve e se resolve logo.
- **Tecnologia nova como oportunidade,** não como ameaça. Numa produção anterior, o anúncio que tratou a tecnologia como ameaça não vendeu (um caso só; trate como hipótese).
- **Ponte com a página:** cada vídeo fala uma frase que a pessoa vai reler na página. Se a página tem variantes A/B, aponte cada anúncio para a variante que ele ecoa.

## 4. Formato da narração

- **Gancho** (1–2 frases): uma tensão ou objeção concreta.
- **Conteúdo** (3–5 frases): o mecanismo explicado, por exemplo a ordem de um método (passo 1 → passo 2 → passo 3).
- **Produto** (2–3 frases): nome, o que a pessoa recebe e o ritmo.
- **CTA falado** e simples: o mesmo texto de `endCard.cta` no `brand.json` (por exemplo "Toque em Saiba Mais").
- Depois, 11 s de tela final sem fala (anúncio). Conteúdo orgânico não leva tela de oferta.

Total entre 35 e 60 s. Escreva para o ouvido: frases curtas, vírgula onde se respira e números por extenso no texto enviado ao TTS.

## 5. Portar um anúncio de referência

Quando pedirem "um igual ao X" (de concorrente ou referência):

1. Transcreva o X (e outros vídeos do mesmo anunciante, se houver) para entender o padrão.
2. Monte uma tabela **frase a frase**: esqueleto do X → nossa versão.
3. **O esqueleto fica literal:** conectivos, ordem e tempo verbal. Só muda o conteúdo entre colchetes, e cada fato trocado tem fonte.
4. **Declare cada divergência.** Mais de 3 divergências significa que você reescreveu, não portou.
5. O erro mais comum é copiar só a ordem dos blocos e parafrasear cada frase com o conteúdo que você já tinha. Parece fiel e não é; foi rejeitado numa produção anterior.

## 6. Fatos: nada inventado

- **Todo fato sobre produto, público ou oferta precisa de fonte:** arquivo da pessoa, página no ar ou o `BRAND.md`. Fato dito pela pessoa dona do produto vale, com data.
- **O visual também precisa ser verdadeiro.** Se a narração diz que o produto faz X, a tela mostra o produto fazendo X.
- Dashboards e gráficos dentro do vídeo são ilustrativos e não podem parecer resultado de cliente.
- Texto de interface inventado (nome de aba, carimbo) é apontado na entrega.
- **Promessas proibidas por padrão:** resultado garantido, ganho financeiro ("ganhe até R$ X"), estatística de mercado sem fonte primária, escassez falsa, "a IA faz por você", nome ou logo de empresa real em print (mascare) e nome de ferramenta de terceiros sem autorização (use um termo genérico, como "assistente de IA"). O `BRAND.md` de cada marca pode listar proibições próprias.
- Âncora de preço ("de R$ X por R$ Y") só com OK explícito e igual à página.
