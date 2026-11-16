---
name: incorporar-aprendizados
description: Uso de quem mantém o Scroll Stopper - lê um ou mais arquivos aprendizados.md recebidos do time, propõe mudanças concretas nas regras (knowledge/*.md) ou no código do plugin, aplica só as aprovadas uma a uma, sobe a versão de patch nos dois manifests, atualiza o CHANGELOG.md, roda os testes, faz commit e publica no repositório do plugin depois do OK. Use quando a pessoa mantenedora disser "incorpora esses aprendizados", "revisa os aprendizados do time" ou "publica uma nova versão com essas melhorias".
---

# Incorporar aprendizados (mantenedor)

Esta skill é a única que mexe no repositório do plugin. Quem usa o plugin no dia a dia nunca publica nada; as correções dele ficam em `.scroll-stopper/aprendizados.md` na pasta de trabalho e chegam aqui quando a pessoa mantenedora decide.

## Antes de começar

1. Trabalhe num **clone git do repositório do plugin** (não na pasta instalada `${CLAUDE_PLUGIN_ROOT}`, que é substituída a cada atualização). Pergunte o caminho do clone se não estiver claro; confira com `git status` que a árvore está limpa e em qual branch está.
2. Peça os arquivos `aprendizados.md` (um ou mais). Cada linha tem o formato `- AAAA-MM-DD · <skill> · <texto>`.

## Passo a passo

1. **Leia todas as linhas** e agrupe por tema (corte, legenda, tela, voz, som, roteiro, processo). Junte repetidas e anote quantas pessoas trouxeram a mesma correção.
2. **Classifique cada grupo:**
   - **já coberto** por uma regra em `knowledge/` → só cite onde;
   - **regra geral nova ou ajuste de regra** → edição em `knowledge/<arquivo>.md` (normalmente `regras-de-gosto.md`, `cortes.md`, `motion.md`, `apresentador-com-motion.md`, `voz.md` ou `qa-e-entrega.md`) ou em `skills/<skill>/SKILL.md`;
   - **mudança de código** (CLI em `ss_lib/`, engine em `engine/src/`) → descreva a mudança e o teste que a prova;
   - **específico de uma marca** → não entra no plugin; sugira que fique no `BRAND.md` da marca, em "Exceções às regras de gosto";
   - **descartar**: contradiz uma regra vigente sem motivo novo, ou só tem sentido com dado privado.
3. **Neutralize.** Nada que entra no repositório pode ter marca de empresa, nome de pessoa, métrica, caso de cliente, preço, oferta, link interno, ID de anúncio, ID ou amostra de voz clonada, mídia ou segredo. Reescreva com exemplo neutro ("uma marca fictícia", "num caso real") mantendo a regra e os números da regra. Fato sobre plataforma, licença ou custo precisa de link de fonte verificável ou entra como "regra prática"; preço de ferramenta nunca entra (escreva "confira o preço atual em <link>").
4. **Proponha uma mudança por vez:** mostre o texto atual, o texto novo (diff curto), de qual linha de aprendizado veio e por quê. **Aplique só o que for aprovado**, um item de cada vez. O que for recusado não entra.
5. **Teste:** `python -m pytest -q` no venv de desenvolvimento do plugin. O teste de manifests barra marcas e referências proibidas; o de skills confere frontmatter, comandos `ss` e conteúdo neutro. Corrija até passar.
6. **Versão:** suba o **patch** (`0.1.0` → `0.1.1`) em `.claude-plugin/plugin.json` (a entrada do marketplace não repete a versão; o `plugin.json` é a fonte única).
7. **CHANGELOG.md:** acrescente no topo a seção da nova versão, com a data e uma linha por mudança aprovada (o quê e por quê, sem nomes nem marcas).
8. **Commit:** mostre o `git diff --stat` e a mensagem proposta (`chore: incorpora aprendizados (v<versão>)` ou `feat:`/`fix:` quando couber), espere o OK e faça o commit.
9. **Publicar:** só depois de um OK explícito para publicar, rode `git push` na branch combinada. O time recebe a nova versão quando atualizar o plugin no Claude Code.
10. **Resumo final:** versão publicada, o que entrou, o que ficou de fora (e por quê) e o que foi sugerido para `BRAND.md` de alguma marca.

## Regras

- Nenhuma edição sem aprovação; nenhum commit sem mostrar o diff; nenhum push sem OK explícito.
- Nunca grave segredos nem leia variáveis de ambiente que possam ter segredo.
- Não altere os arquivos `aprendizados.md` recebidos; eles são da pessoa.
