# Changelog

Mudanças de cada versão publicada do Scroll Stopper. A versão fica só em `.claude-plugin/plugin.json`.

## 0.1.1 — 2026-11-16

- README: o caminho de atualização foi conferido instalando a 0.1.0 e atualizando para esta versão.

## 0.1.0 — 2026-11-12

Primeira versão.

- Três caminhos para vídeos verticais 1080×1920 a 30 fps: A (apresentador + motion, ou só o corte limpo), B (motion + narração sincronizada palavra a palavra) e C (vídeo longo, por arquivo ou link, em cortes curtos com nota de 0 a 100, no estilo simples ou dinâmico).
- Sete skills em português: `editar-video` (porta de entrada), `onboarding-de-marca`, `corte`, `apresentador-com-motion`, `motion-narrado`, `cortes-de-video-longo` e `incorporar-aprendizados`, com a base de conhecimento em `knowledge/`.
- CLI `ss`: `setup`, `workspace`, `brand`, `kit`, `transcribe`, `cut`, `prepare-presenter`, `align`, `download`, `clips`, `draft`, `render`, `finalize`, `probe` e `qa`. Só os comandos da ajuda rodam.
- Motor de vídeo em Remotion por marca (cores, fontes, logo), com modelos de anúncio narrado, de apresentador e de clipe simples. As dependências ficam em `~/.cache/scroll-stopper/engine-deps/`, compartilhadas entre versões com o mesmo `package-lock.json`; versões antigas saem do cache no `ss setup`.
- Pasta de trabalho `.scroll-stopper/` com marcas, kit de som, aprendizados e projetos, que nunca vão para o GitHub. O kit de som é copiado para o cache do projeto a cada preparo; o render nunca lê de pasta sincronizada.
- Entrega com volume normalizado (−14 LUFS apresentador e cortes, −15 LUFS motion narrado, pico −1,5 dBTP), conferência técnica (`ss qa`) e cópia sem sobrescrever. `ss finalize` converte o corte para 1080×1920 a 30 fps antes de entregar.
- Licença AGPL-3.0, com atribuição ao SupoClip e o aviso de licença do Remotion em `NOTICE`.
