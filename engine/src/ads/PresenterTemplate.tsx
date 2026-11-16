import React from 'react';
import {AbsoluteFill, Audio, Img, Sequence, getStaticFiles, interpolate, staticFile, useCurrentFrame} from 'remotion';
import {AdProps} from '../engine/AdShell';
import {FactChip, makeCues} from '../kit';
import {pop, ramp, sec} from '../lib/anim';
import {ClayCard, Grain, fontFamily, monoFamily} from '../lib/ui';
import {Dashboard} from '../lib/illustrations';
import {brand, brandAsset} from '../brand';
import {BrandStage, CAPTION_TOP, CaptionScrim, PresenterShot, PresenterSource, SegmentCaptions, Shot, SplitScreen, WhiteHit, WordFlash} from '../presenter';
import {demoWords} from './Template';

// Modelo de vídeo com apresentador alternado com motion.
// 1. Corte o bruto com o `ss cut` (só corte, sem legenda nem logo) e coloque em public/video/presenter.mp4.
// 2. Coloque a voz em public/audio/<id>-m.mp3 e as palavras com tempos em public/audio/<id>-m.words.json.
// 3. Copie este arquivo, troque SCRIPT pelas frases faladas e ajuste as telas.
// Sem os arquivos, roda com um apresentador de mentira e tempos de demonstração.

export const PRESENTER_SCRIPT =
  'Seu anúncio pode estar perdendo gente no primeiro segundo. Olha esse painel: ele mostra quem parou de assistir. Quem segura a atenção faz três coisas. Mostra, explica e convida. E é isso que faz alguém ficar até o fim. Me conta aqui embaixo.';

export const OUTRO_SECONDS = 2.5;

// Ponto do rosto no quadro do corte (0–1). Meça com um quadro e grade: ffmpeg -vf drawgrid
const SOURCE: PresenterSource = {src: 'video/presenter.mp4', face: {x: 0.5, y: 0.22}};

const has = (p: string) => getStaticFiles().some((f) => f.name === p);
const Sfx: React.FC<{at: number; name: string; v?: number}> = ({at, name, v = 0.35}) =>
  has(`sfx/${name}.mp3`) ? (
    <Sequence from={Math.max(0, sec(at))} durationInFrames={90} layout="none">
      <Audio src={staticFile(`sfx/${name}.mp3`)} volume={v} />
    </Sequence>
  ) : null;

export const PresenterTemplate: React.FC<AdProps> = (props) => {
  const frame = useCurrentFrame();
  const words = props.words.length ? props.words : demoWords(PRESENTER_SCRIPT);
  const c = makeCues(words);
  // Cada tela começa numa frase falada; as cues são buscadas na ordem da fala (cursor sequencial),
  // por isso os punch-ins entram aqui, entre as telas, e não depois.
  const T = {
    hook: 0,
    hookPunch: c.s('primeiro segundo'),
    painel: c.s('Olha esse painel'),
    tres: c.s('Quem segura a atenção'),
    flash: c.s('três coisas'),
    organiza: c.s('Mostra, explica e convida'),
    vale: c.s('E é isso que faz'),
    valePunch: c.s('até o fim'),
    conta: c.s('Me conta aqui embaixo'),
    end: words[words.length - 1].e + 0.35,
  };
  const total = T.end + OUTRO_SECONDS;
  const bed = (f: number) => interpolate(f, [0, 12, sec(T.end), sec(total) - 6], [0, 0.09, 0.09, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const voice = `audio/${props.id}-${props.voice}.mp3`;

  return (
    <AbsoluteFill style={{background: brand.colors.dark.bg}}>
      {/* 1. Gancho: apresentador em close, punch-in na palavra forte */}
      <Shot from={T.hook} to={T.painel}>
        <PresenterShot source={SOURCE} from={T.hook} to={T.painel} z={[1.75, 1.95]} punchAt={[T.hookPunch]} />
        <CaptionScrim y={1210} />
        <SegmentCaptions words={words} theme="dark" top={CAPTION_TOP.presenter} chunks={[{p: 'Seu anúncio pode estar'}, {p: 'perdendo gente', key: 'perdendo'}, {p: 'no primeiro segundo.'}]} />
      </Shot>

      {/* 2. Só motion: o objeto do que ele está falando */}
      <Shot from={T.painel} to={T.tres} enter="whipL">
        <BrandStage theme="dark" set={0} gridAt={{x: 540, y: 650}}>
          <div style={{position: 'absolute', top: 330, left: 0, right: 0, display: 'flex', justifyContent: 'center'}}>
            <ClayCard dark style={{width: 900, padding: 20, transform: `scale(${Math.min(1, 0.9 + 0.1 * pop(frame, sec(T.painel)))})`}}>
              <Dashboard start={sec(T.painel) - 12} dark width={860} />
            </ClayCard>
          </div>
        </BrandStage>
        <SegmentCaptions words={words} theme="dark" top={CAPTION_TOP.motion} chunks={[{p: 'Olha esse painel:', key: 'painel'}, {p: 'ele mostra'}, {p: 'quem parou de assistir.'}]} />
      </Shot>

      {/* 3. Apresentador médio */}
      <Shot from={T.tres} to={T.flash} enter="zoom">
        <PresenterShot source={SOURCE} from={T.tres} to={T.flash} z={[1.35, 1.5]} />
        <CaptionScrim y={1210} />
        <SegmentCaptions words={words} theme="dark" top={CAPTION_TOP.presenter} chunks={[{p: 'Quem segura a atenção'}, {p: 'faz'}]} />
      </Shot>

      {/* 4. Flash de palavra */}
      <Shot from={T.flash} to={T.organiza}>
        <WordFlash from={T.flash} word="3" sub="COISAS" />
      </Shot>

      {/* 5. Tela dividida: motion em cima, apresentador embaixo, legenda na emenda */}
      <Shot from={T.organiza} to={T.vale} enter="up">
        <SplitScreen
          source={SOURCE}
          from={T.organiza}
          to={T.vale}
          top={
            <div style={{position: 'absolute', top: 260, left: 0, right: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 24}}>
              <FactChip at={sec(c.w('Mostra, explica e convida', 0))} text="mostra" />
              <FactChip at={sec(c.w('Mostra, explica e convida', 1))} text="explica" />
              <FactChip at={sec(c.w('Mostra, explica e convida', 3))} text="convida" />
            </div>
          }
        />
        <SegmentCaptions words={words} theme="dark" top={CAPTION_TOP.split} size={80} chunks={[{p: 'Mostra, explica e convida.', key: 'convida'}]} />
      </Shot>

      {/* 6. Close com corte seco e flash branco */}
      <Shot from={T.vale} to={T.conta}>
        <PresenterShot source={SOURCE} from={T.vale} to={T.conta} z={[2.0, 2.1]} punchAt={[T.valePunch]} />
        <CaptionScrim y={1210} />
        <SegmentCaptions words={words} theme="dark" top={CAPTION_TOP.presenter} chunks={[{p: 'E é isso que faz alguém'}, {p: 'ficar até o fim.', key: 'até o fim'}]} />
      </Shot>
      <WhiteHit at={T.vale} />

      {/* 7. CTA */}
      <Shot from={T.conta} to={T.end}>
        <PresenterShot source={SOURCE} from={T.conta} to={T.end} z={[1.4, 1.5]} ty={0.24} />
        <CaptionScrim y={1010} h={320} />
        <SegmentCaptions words={words} theme="dark" top={950} chunks={[{p: 'Me conta aqui embaixo.', key: 'aqui embaixo'}]} />
      </Shot>

      {/* 8. Saída curta com o logo (conteúdo orgânico não leva a tela de oferta de 11 s) */}
      <Shot from={T.end} to={total} enter="zoom">
        <BrandStage theme="dark" set={4}>
          <AbsoluteFill style={{alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: 30}}>
            <Img src={staticFile(brandAsset(brand.logos.header))} style={{width: 420, opacity: ramp(frame, sec(T.end), 8)}} />
            <div style={{fontFamily: monoFamily, fontSize: 30, letterSpacing: '0.16em', color: brand.colors.accent, opacity: ramp(frame, sec(T.end) + 8, 8)}}>{brand.endCard.kicker ?? ''}</div>
            <div style={{fontFamily, fontWeight: 700, fontSize: 40, color: brand.colors.accentInk, background: brand.colors.accent, padding: '14px 36px', borderRadius: 999, opacity: ramp(frame, sec(T.end) + 14, 8)}}>{brand.endCard.cta}</div>
          </AbsoluteFill>
        </BrandStage>
      </Shot>

      <Grain opacity={0.05} />

      {has(voice) && <Audio src={staticFile(voice)} />}
      {has('music/bed-dark.mp3') && <Audio src={staticFile('music/bed-dark.mp3')} volume={bed} loop />}
      {/* um efeito em cada troca de tela */}
      <Sfx at={T.painel - 0.12} name="whoosh-short" />
      <Sfx at={T.tres - 0.1} name="zoom-swish" />
      <Sfx at={T.flash} name="impact-low" v={0.45} />
      <Sfx at={T.organiza - 0.1} name="card-slide" />
      <Sfx at={T.vale} name="impact-low" v={0.4} />
      <Sfx at={T.end - 0.25} name="whoosh-riser" />
    </AbsoluteFill>
  );
};
