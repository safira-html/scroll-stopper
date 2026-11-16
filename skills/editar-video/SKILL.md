---
name: editar-video
description: Porta de entrada do Scroll Stopper (Para o Scroll) para criar ou editar vídeos verticais. Use quando a pessoa disser "edita esse vídeo", "faz um vídeo", "corta esse vídeo", "faz cortes desse vídeo", "transforma essa live em reels", mandar um arquivo de vídeo ou áudio, ou mandar um link de vídeo para virar cortes. Confere o ambiente, acha a pasta de trabalho, propõe o caminho (A apresentador + motion, B motion + narração, C vídeo longo em cortes) e a marca, espera a confirmação e chama a skill do caminho.
---

# Editar vídeo (porta de entrada)

Você conduz uma pessoa sem formação em edição, motion ou programação, por perguntas curtas, até o vídeo pronto. Fale em português do Brasil, uma pergunta por vez, sem jargão (nada de Remotion, ffmpeg, Whisper na conversa, a não ser que ela pergunte).

## Como chamar o CLI

O CLI do plugin é `"${CLAUDE_PLUGIN_ROOT}/bin/ss"`; abaixo ele aparece abreviado como `ss`. A pasta `bin/` do plugin também fica no PATH do Bash enquanto o plugin está ativo, então `ss` sozinho costuma funcionar; se não funcionar, use o caminho completo. Rode os comandos **a partir da pasta de trabalho** (a que tem ou vai ter `.scroll-stopper/`) e ponha entre aspas todo caminho com espaço.

## Passo a passo

1. **Ambiente.** Rode `ss setup --check`. Se faltar algo, explique em uma frase que a primeira instalação baixa ferramentas (alguns GB, alguns minutos), peça o OK e rode `ss setup`. Só macOS nesta versão. Na primeira instalação, avise também em uma frase: o motor de vídeo usa o Remotion, que é gratuito para pessoas físicas e para empresas de até 3 pessoas; quem não se encaixa precisa de uma licença de empresa (https://www.remotion.dev/license).
2. **Pasta de trabalho.** Procure `.scroll-stopper/` na pasta atual ou acima. Se não existir, diga onde vai criar (a pasta atual) e, com o OK, rode `ss workspace init`.
3. **Aprendizados.** Leia `.scroll-stopper/aprendizados.md` inteiro antes de qualquer decisão. Cada linha é uma correção que esta pessoa já fez; ela vale junto com as regras de `${CLAUDE_PLUGIN_ROOT}/knowledge/regras-de-gosto.md`.
4. **Olhe o material** (sem processar ainda): `ss probe "<arquivo>"` diz a duração, se tem imagem e som e a resolução. Veja também se é link e, se precisar ver a imagem para saber se é alguém falando para a câmera, extraia um quadro (receita em `${CLAUDE_PLUGIN_ROOT}/knowledge/qa-e-entrega.md`).
5. **Proponha o caminho e espere a confirmação.** Mesmo quando parecer óbvio, pergunte e só siga depois do sim:
   - **A. Com apresentador:** bruto de alguém falando para a câmera → vídeo cortado e dinâmico (telas do apresentador alternadas com motion, legenda karaokê, efeitos).
   - **B. Sem apresentador:** uma voz (gravada pela pessoa ou gerada numa ferramenta que ela tenha) → vídeo 100% motion sincronizado com a voz. O roteiro pode vir pronto ou ser escrito aqui.
   - **C. Vídeo longo → cortes curtos:** aula, live, podcast, por arquivo ou link → vários cortes curtos com os trechos mais fortes.
   Exemplo: "Pelo que vi, é uma gravação sua falando para a câmera, de 3 min. Sugiro o caminho A (apresentador + motion). Confirma o caminho A?"
6. **Proponha a marca e espere a confirmação.** Rode `ss workspace brands`.
   - Achou uma ou mais: diga qual parece ser e peça para confirmar a marca ("Uso a marca `minha-marca`? Confirma?"). Nunca escolha sozinha.
   - Não achou, ou a pessoa diz que é outra: chame a skill `scroll-stopper:onboarding-de-marca`.
   - A pessoa não quer guardar a marca: o onboarding cria uma marca efêmera no cache; nada é escrito na pasta dela.
7. **Pergunte só o essencial,** uma coisa por vez: objetivo (anúncio ou conteúdo orgânico), oferta e CTA (anúncio), a **pasta de entrega** onde o vídeo final (ou os cortes, no caminho C) vai ficar, e no caminho B de onde vem a voz.
8. **Id do projeto.** Escolha um id curto só com letras minúsculas, números e hífen (por exemplo `video-01`): ele vira o nome da composição. Crie `.scroll-stopper/projetos/<id>/`.
9. **Chame a skill do caminho** (ferramenta Skill), passando o que já foi decidido (caminho, marca, id, arquivo ou link, objetivo, pasta de entrega):
   - A: `scroll-stopper:corte` e depois `scroll-stopper:apresentador-com-motion`;
   - B: `scroll-stopper:motion-narrado`;
   - C: `scroll-stopper:cortes-de-video-longo`.
10. **Entrega.** Termine dizendo o caminho completo de cada arquivo final (o `ss render` e o `ss clips render` imprimem). O que a pessoa faz depois é decisão dela.

## Regras que valem em qualquer caminho

- **Custo antes de gastar.** Antes de qualquer geração paga (voz, música, efeito, imagem), diga o que vai gerar e o custo aproximado e espere o sim. Voz: amostra curta antes do roteiro inteiro. O plugin funciona sem nenhuma conta paga.
- **Fatos com fonte.** Nada de número ou promessa inventados no que é falado ou mostrado.
- **Rascunho cedo.** Mostre um rascunho em baixa resolução assim que der e aplique ajustes pedidos em frases curtas ("tira esse 'uuuu' aos 29 s").
- **Nunca publique** vídeo, nunca suba anúncio e nunca mande mensagem por ninguém. Nunca envie nada para o GitHub.
- **Segredos:** nunca leia nem imprima variáveis de ambiente que possam ter chave ou token.

## Aprendizados

Quando a pessoa corrigir algo (uma regra de gosto, um ajuste de corte, uma preferência), anote na hora, em uma linha, o que mudou e a regra que fica:

```bash
ss workspace learn "<o que foi corrigido e a regra que fica>" --source editar-video
```

Isso grava só em `.scroll-stopper/aprendizados.md` da pasta de trabalho. Para virar regra do plugin, a pessoa manda esse arquivo para quem mantém o plugin.
