# Voz e narração (caminho B)

A narração pode chegar de três jeitos; depois disso o processo é o mesmo.

| Origem | O que fazer |
|---|---|
| **Voz enviada pela pessoa** (gravada no celular ou em estúdio) | Salve em `.scroll-stopper/projetos/<id>/narracao.<mp3|wav|m4a>`. Se a gravação tem claquete ou takes repetidos, corte antes como no caminho A ([cortes.md](cortes.md)) e use o áudio do corte. |
| **Ferramenta de terceiros que a pessoa já tem** (conector MCP, API ou o site da ferramenta; a ElevenLabs é um exemplo entre vários) | Fluxo abaixo: custo antes, amostra curta, sem tags de emoção. Salve o arquivo como acima. |
| **Nenhuma** | Peça para a pessoa gravar e enviar o áudio. O plugin não exige conta paga. |

Depois, para qualquer origem:

```bash
ss align .scroll-stopper/projetos/<id>/narracao.mp3 <id>-m --project <id> --script .scroll-stopper/projetos/<id>/roteiro.txt
```

- `<id>-m` para voz masculina, `<id>-f` para feminina: a letra vira o sufixo da composição (`<id>-m`).
- Com `--script`, a legenda sai com a grafia do roteiro e o Whisper só dá os tempos (palavra que ele não ouviu é encaixada entre as vizinhas). Sem roteiro, vale o texto do Whisper: revise nomes de marca, porque o Whisper costuma errá-los.
- O `ss align` normaliza a narração para **−16 LUFS, TP −1,5, LRA 11** em duas passadas e grava `<id>-m.mp3` e `<id>-m.words.json` no cache do projeto, de onde o engine lê.

Se a pessoa gravou em vídeo e quer aparecer, é o caminho A ([apresentador-com-motion.md](apresentador-com-motion.md)).

## Gerar numa ferramenta de terceiros

1. **Descubra o que a pessoa tem.** Veja quais conectores de geração de voz existem na sessão; se não houver nenhum, pergunte se ela usa alguma ferramenta pelo site. Só ofereça o que ela tem.
2. **Licença:** confira se o plano dela permite uso comercial antes de qualquer anúncio rodar (na ElevenLabs, a página de planos diz o que cada um inclui: https://elevenlabs.io/pricing). Preços e planos mudam; confira o preço atual na página da ferramenta.
3. **Custo antes de gerar.** Diga o que vai gerar (quantos caracteres, quantas vozes) e o custo aproximado e espere o sim. Se a ferramenta tem modo só-estimativa, use-o antes. Se passar do aprovado, avise na hora.
4. **Casting por amostra.** Gere 3–4 vozes lendo o mesmo trecho curto (o gancho) e deixe a pessoa escolher. Critério: idade e gênero de quem compra. Voz de locutor de audiobook ou documentário soa como anúncio; prefira as que "conversam com a câmera". Não use voz pública que é clone nomeado de uma pessoa real.
5. **Sem tags de emoção** (`[nervous]`, `[sighs]`, `[warmly]`) nem CAIXA ALTA: soaram como "gemendo" e com mudança brusca de tom. O tom vem da pontuação.
6. **Texto do TTS ≠ texto da legenda.** O texto enviado ao TTS (`roteiro-tts.txt`) leva os ajustes de pronúncia: acento no nome da marca (uma marca fictícia "Nuvra" pode precisar de "Núvra"), números por extenso ("trezentos e vinte clientes", "noventa e sete reais"). A legenda usa a grafia correta, em `roteiro.txt`, que vai no `--script` do `ss align`.
7. **Gere tudo em 1x.** Acelerar o vídeo pronto foi rejeitado. Se o ritmo estiver lento, encurte o roteiro ou escolha uma voz mais rápida.
8. **Uma voz por roteiro** na leva final, alternando masculina e feminina.
9. Links de download que a ferramenta devolve costumam ser assinados e expirar: baixe na hora e não grave o link em log nem em arquivo.

## Correção parcial em vez de gerar de novo

- **Trocar a última frase** (preço, CTA): gere só a frase nova e emende com fade curto (ajuste os tempos ao seu arquivo):
  ```bash
  ffmpeg -i antigo.mp3 -i final-novo.mp3 -filter_complex "[0]atrim=0:46.70,asetpts=PTS-STARTPTS,afade=t=out:st=46.62:d=0.08[a];[1]afade=t=in:d=0.03[b];[a][b]concat=n=2:v=0:a=1" narracao.mp3
  ```
- **Tirar palavras:** corte em pontos de baixa energia com fades de 15 ms, rode o `ss align` de novo e guarde a versão anterior com outro nome.

## Clone de voz (só quando a pessoa existe e consente)

1. Junte 1–3 min de fala limpa de uma pessoa só, sem música:
   ```bash
   ffmpeg -i a.wav -i b.wav -filter_complex "[0][1]concat=n=2:v=0:a=1,silenceremove=stop_periods=-1:stop_duration=0.6:stop_threshold=-40dB,loudnorm=I=-16:TP=-1.5" -ar 44100 -ac 1 -b:a 192k amostra.mp3
   ```
2. Suba na função de clonagem da ferramenta, com remoção de ruído ligada se houver.
3. **O consentimento na ferramenta só é marcado depois que a pessoa dona da voz confirma por escrito.** Registre quem confirmou e quando (no `BRAND.md`, sem o ID do clone).
4. Gere uma frase de teste antes da narração inteira.
5. O ID do clone e as amostras **nunca entram no repositório do plugin**. Ficam na pasta de trabalho da pessoa.

## Volume (o plugin aplica sozinho)

| Etapa | Alvo |
|---|---|
| Narração processada (`ss align`) | −16 LUFS, TP −1,5 |
| Trilha (`ss kit add-music`) | −20 LUFS no arquivo; no vídeo, volume 0,11 sob a voz, subindo para 0,3 na tela final |
| Efeitos (`ss kit add-sfx`) | pico em −3 dBFS no arquivo; no vídeo, volume 0,25–0,5 |
| Vídeo final de motion narrado (`ss render`) | −15 LUFS, TP −1,5 (duas passadas, vídeo copiado sem reencode) |

Onde conseguir trilha e efeitos: [som.md](som.md).

O agente não escuta áudio. Medição e retranscrição são aproximações. **Peça para uma pessoa ouvir** a pronúncia da marca, siglas, a trilha e os efeitos antes de entregar.
