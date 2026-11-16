# Scroll Stopper (Para o Scroll)

Plugin do Claude Code que cria vídeos verticais (1080×1920, 30 fps) para anúncios e redes sociais, conversando em português com quem não sabe editar. Você manda o material, ele propõe o caminho e a marca, espera a sua confirmação e entrega o `.mp4` final na pasta que você escolher: corte, legenda karaokê, telas de motion com as cores e fontes da sua marca, trilha, efeitos e volume no padrão das plataformas. Somente macOS na v0.1.

## Os três caminhos

- **A. Apresentador + motion.** Uma gravação de alguém falando para a câmera vira um vídeo cortado (sem falso início, take repetido nem pausa longa) e dinâmico, com telas do apresentador alternadas com motion e legenda. Também dá para pedir só o corte limpo.
- **B. Motion + narração.** Uma voz (gravada por você ou gerada numa ferramenta que você já tenha) vira um vídeo 100% motion sincronizado palavra a palavra. O roteiro pode vir pronto ou ser escrito na conversa.
- **C. Vídeo longo em cortes curtos.** Uma aula, live, podcast ou entrevista, por arquivo ou link, vira vários cortes curtos com os trechos mais fortes. Você escolhe quais renderizar, no estilo simples (corte e legenda) ou dinâmico (como o caminho A).

## Requisitos

O `ss setup` confere cada item e diz como instalar o que faltar:

- macOS;
- [Homebrew](https://brew.sh), para instalar o resto;
- ffmpeg e ffprobe (`brew install ffmpeg`);
- Node 18 ou mais novo (`brew install node`);
- Python 3.11 (`brew install python@3.11`);
- internet e uns 3 GB livres na primeira execução.

Nenhuma conta paga é necessária. Geração de voz, música ou imagem em ferramentas pagas só acontece se você tiver a ferramenta e aprovar o custo antes.

## Instalação

No Claude Code:

```
/plugin marketplace add safira-html/scroll-stopper
/plugin install scroll-stopper@scroll-stopper
```

## Primeira execução

Na primeira vez em que você pedir um vídeo, o plugin roda `ss setup --check` e, com o seu OK, `ss setup`. O setup pode rodar de novo a qualquer momento (o que já está instalado fica) e guarda tudo em `~/.cache/scroll-stopper/` e no cache do Hugging Face, nunca numa pasta sincronizada. Tamanhos medidos numa instalação em Apple Silicon:

| O que | Para que serve | Espaço em disco |
| :- | :- | :- |
| Ambiente Python (`venv`) com faster-whisper, numpy, pillow e yt-dlp | transcrição, corte, download por link | ~0,3 GB |
| Modelo de transcrição `faster-whisper-large-v3-turbo` | tempo de cada palavra falada | ~1,6 GB |
| Dependências do motor de vídeo (Remotion), incluindo o navegador que renderiza (download de ~140 MB, ~470 MB instalado) | render das telas de motion | ~1,0 GB |

Depois disso, cada projeto ocupa só os arquivos dele no cache; o vídeo final é copiado para a pasta de entrega.

## Atualizações

> A forma de atualizar abaixo segue a documentação do Claude Code ([marketplaces](https://code.claude.com/docs/en/plugin-marketplaces) e [instalar e gerenciar plugins](https://code.claude.com/docs/en/discover-plugins)) e foi conferida na prática na publicação da 0.1.1.

Cada versão nova sobe o número em `.claude-plugin/plugin.json` e ganha uma entrada no [CHANGELOG.md](CHANGELOG.md). Em marketplaces de terceiros, como este, a atualização automática vem desligada. Você pode:

- ligar a atualização automática: `/plugin` → aba **Marketplaces** → `scroll-stopper` → **Enable auto-update**;
- atualizar na hora, numa sessão: `/plugin` → aba **Installed** → `scroll-stopper` → **Update now** (o comando `/plugin marketplace update scroll-stopper` só atualiza a lista do marketplace);
- ou, no terminal, em dois passos (o primeiro busca a versão nova no GitHub; sem ele o segundo responde que já está na última versão):

  ```bash
  claude plugin marketplace update scroll-stopper
  claude plugin update scroll-stopper@scroll-stopper
  ```

A sessão aberta continua com a versão antiga; rode `/reload-plugins` ou abra uma sessão nova. No primeiro vídeo depois da atualização, o plugin confere o ambiente e roda `ss setup` de novo: quando as dependências do motor não mudaram, ele só copia o código novo (alguns KB) e reaproveita o que já está instalado. Versões antigas do motor saem do cache no fim.

## Pasta de trabalho

Na primeira vez, o plugin cria `.scroll-stopper/` na pasta em que você está trabalhando (pode ser uma pasta do Google Drive ou Dropbox):

```
.scroll-stopper/
  marcas/<marca>/        brand.json, BRAND.md e assets/ (logo, símbolo)
  kit-de-som/music/      trilhas de fundo (bed-light.mp3, bed-dark.mp3)
  kit-de-som/sfx/        efeitos sonoros com os nomes que o motor toca
  aprendizados.md        correções que você fez, para o plugin não repetir o erro
  projetos/<id>/         decisões de cada vídeo (corte, roteiro, candidatos)
```

Suas marcas, seu kit de som e seus aprendizados ficam só no seu computador. O plugin nunca os envia para o GitHub nem para lugar nenhum. Se você usa o plugin num time, a pessoa que mantém o plugin pode receber o seu `aprendizados.md` (quando você mandar) e transformar o que for geral em regra numa versão nova, sem marca nem dado de cliente.

## Como usar

Abra o Claude Code na pasta do seu projeto e peça em português, por exemplo:

- "edita esse vídeo" (e mande o arquivo da gravação);
- "corta esse vídeo, só tira os erros";
- "faz um anúncio em motion com essa narração";
- "transforma essa live em reels" (arquivo ou link);
- "cadastra a minha marca".

Ele pergunta uma coisa por vez: confirma o caminho e a marca, pergunta o objetivo e a pasta de entrega, confere um rascunho antes do render final e termina dizendo o caminho de cada arquivo entregue. O plugin nunca publica vídeos nem manda mensagens por você.

## Direitos sobre o conteúdo

Você é responsável por ter o direito de usar o que entra no vídeo: gravações, vídeos baixados por link, músicas, efeitos e imagens. Antes de baixar um vídeo por link, o plugin pede que você confirme que tem esse direito. Para trilhas e efeitos, [knowledge/som.md](knowledge/som.md) resume as licenças de alguns bancos gratuitos, com o link de cada uma.

## Licenças

- O Scroll Stopper é software livre sob a [AGPL-3.0](LICENSE). Avisos de copyright e atribuição estão em [NOTICE](NOTICE): parte do método e do código dos cortes de vídeo longo foi adaptada do [SupoClip](https://github.com/FujiwaraChoki/supoclip), também AGPL-3.0.
- O motor de vídeo usa o [Remotion](https://www.remotion.dev), que tem licença própria. Segundo a [página de licença](https://www.remotion.dev/license), o Remotion "is free to use for individuals and companies up to three people"; quem não se encaixa nessa licença gratuita precisa de uma licença de empresa (Company License). Confira na página se o seu caso se encaixa.
