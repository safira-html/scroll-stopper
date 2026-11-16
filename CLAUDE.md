# Scroll Stopper: regras para agentes neste repositório

Plugin do Claude Code "Scroll Stopper" (`scroll-stopper`; em português, "Para o Scroll"). Estas regras valem para quem desenvolve o plugin. As regras de uso ficam nas skills (`skills/`) e na base de conhecimento (`knowledge/`).

## Restrições globais

- Nome do plugin `scroll-stopper`; nome de exibição "Scroll Stopper"; nome de apresentação em português "Para o Scroll".
- Licença AGPL-3.0 em todo o repositório (há código copiado do SupoClip). Mantenha o aviso de copyright do SupoClip em cada arquivo copiado dele e o aviso MIT nos arquivos copiados de trabalhos anteriores sob MIT.
- O repositório nunca contém: marca de empresa, métricas, casos de clientes, IDs ou amostras de voz clonada, mídia (áudio, vídeo, imagens além de fixtures neutras), segredos, nem referência ou link aos repositórios de origem do código e do conhecimento.
- Código, nomes de arquivos, identificadores e mensagens de CLI em inglês; comentários podem ser em português. Skills, docs de conhecimento e conversa com o usuário em português do Brasil.
- Pasta de trabalho do usuário (criada pelo plugin, nunca versionada): `.scroll-stopper/marcas/<slug>/{brand.json,BRAND.md,assets/}`, `.scroll-stopper/kit-de-som/{music,sfx}/`, `.scroll-stopper/aprendizados.md`, `.scroll-stopper/projetos/<id>/`.
- Trabalho pesado (`node_modules` do engine, venv, renders) fica em `~/.cache/scroll-stopper/`, nunca numa pasta sincronizada; só o `.mp4` final é copiado para onde o usuário quiser.
- Geração paga (voz, música, efeitos, imagens) só depois de dizer o que será gerado e o custo estimado e receber um sim. O plugin precisa funcionar sem nenhum conector pago.
- Caminho e marca são sempre confirmados com o usuário antes de começar, mesmo quando detectados.
- Loudness: vídeos com apresentador e clipes −14 LUFS, TP −1,5 dBTP; anúncios de motion narrado −15 LUFS, TP −1,5; narração −16 LUFS; trilhas −20 LUFS; efeitos com pico −3 dBFS.
- Vídeo: 1080×1920, 30 fps, H.264 + AAC 48 kHz.
- Ritmo de fala nos cortes de apresentador: ≈184 palavras/min, velocidade limitada a 1,0–1,3×.
- Duração dos cortes (caminho C): `short` 15–30 s (ideal 18–25), `medium` 30–60 s (ideal 35–55), `long` 60–120 s, `auto` 15–60 s (ideal 25–50); janelas de análise de 12 min com 2 min de sobreposição; quantidade final de cortes = clamp(round(duração_s / 300), 5, 20).
- O plugin nunca publica vídeos nem envia mensagens por ninguém; a entrega é o caminho (ou link) do arquivo final mostrado ao usuário.
- Só macOS na v0.1.

## Trabalho no repositório

- Nunca grave segredos em arquivos, logs ou commits. Não leia nem imprima variáveis de ambiente que possam carregar segredo.
- Todo fato em `knowledge/` (estatística, comportamento de plataforma, licença, custo) tem link de fonte verificável ou é marcado como regra prática. Preço de ferramenta não entra: escreva "confira o preço atual em <link>".
- Skills só citam comandos `ss` que existem (`tests/test_skills.py` confere).
- Ao mudar regras ou código para uma nova versão, suba o patch em `.claude-plugin/plugin.json` (fonte única da versão; a entrada do marketplace não repete) e atualize o `CHANGELOG.md` (skill `incorporar-aprendizados`).
- Testes: `python -m pytest`.
