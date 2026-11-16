import React from 'react';
import {AbsoluteFill, Audio, Sequence, getStaticFiles, interpolate, staticFile, useCurrentFrame} from 'remotion';
import {ramp, sceneEnvelope, sec} from '../lib/anim';
import {CornerShapes, DotGrid, Grain, MaskedGrid, SyncedLine, Vignette} from '../lib/ui';
import {alpha, brand} from '../brand';
import {Word, Voice} from './words';
import {EndCard} from './EndCard';

export const END_SECONDS = brand.endCard.seconds ?? 11;
export const TAIL = 0.6; // respiro depois da última palavra antes da tela final

export type AdProps = {id: string; voice: Voice; words: Word[]};
export type Theme = 'light' | 'dark';

const C = brand.colors;
export const THEME = {
  light: {bg: C.light.bg, text: C.light.text, muted: C.light.muted, grid: alpha(C.accentDisplay, C.light.gridAlpha), corner: C.light.corner, accentText: C.accentDisplay},
  dark: {bg: C.dark.bg, text: C.dark.text, muted: C.dark.muted, grid: alpha(C.accent, C.dark.gridAlpha), corner: C.dark.corner, accentText: C.accent},
};

// Só toca o áudio que existe em public/ (o repositório não traz narrações, trilhas nem efeitos)
const hasFile = (p: string) => getStaticFiles().some((f) => f.name === p);
const MaybeAudio: React.FC<{src: string; volume?: number | ((f: number) => number); loop?: boolean}> = ({src, ...rest}) =>
  hasFile(src) ? <Audio src={staticFile(src)} {...rest} /> : null;

export const endStartOf = (words: Word[]) => (words.length ? words[words.length - 1].e + TAIL : 30);

export type SfxCue = {at: number; name: string; volume?: number};

// Moldura comum: fundo, narração, trilha com volume baixo sob a voz, efeitos e tela final
export const AdShell: React.FC<{
  props: AdProps;
  theme: Theme;
  music?: 'light' | 'dark';
  sfx?: SfxCue[];
  children: React.ReactNode;
}> = ({props, theme, music, sfx = [], children}) => {
  const frame = useCurrentFrame();
  const endStart = sec(endStartOf(props.words));
  const t = THEME[theme];
  const bedVolume = (f: number) => {
    const fadeIn = interpolate(f, [0, 15], [0, 1], {extrapolateRight: 'clamp'});
    const lift = interpolate(f, [endStart - 6, endStart + 10], [0.11, 0.3], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
    const fadeOut = interpolate(f, [endStart + sec(END_SECONDS) - 25, endStart + sec(END_SECONDS)], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
    return fadeIn * lift * fadeOut;
  };
  return (
    <AbsoluteFill style={{background: t.bg}}>
      <Vignette dark={theme === 'dark'} />
      {children}
      <EndCard start={endStart} />
      <Grain opacity={theme === 'dark' ? 0.05 : 0.07} />
      <MaybeAudio src={`audio/${props.id}-${props.voice}.mp3`} />
      {music && <MaybeAudio src={`music/bed-${music}.mp3`} volume={bedVolume} loop />}
      {sfx.map((c, i) => (
        <Sequence key={i} from={Math.max(0, sec(c.at))} durationInFrames={90}>
          <MaybeAudio src={`sfx/${c.name}.mp3`} volume={c.volume ?? 0.5} />
        </Sequence>
      ))}
      {/* whoosh para a tela final, padrão em todas */}
      <Sequence from={Math.max(0, endStart - 8)} durationInFrames={90}>
        <MaybeAudio src="sfx/whoosh-riser.mp3" volume={0.45} />
      </Sequence>
      {frame < 0 ? null : null}
    </AbsoluteFill>
  );
};

// Cena: janela de tempo em segundos, com entrada, saída (zoom-through + blur), push-in de câmera,
// formas desfocadas nos cantos e grade mascarada em volta do objeto.
export const Scene: React.FC<{
  from: number;
  to: number;
  theme: Theme;
  set?: number;
  push?: number;
  gridAt?: {x: number; y: number};
  children: React.ReactNode;
}> = ({from, to, theme, set = 0, push = 0.06, gridAt, children}) => {
  const frame = useCurrentFrame();
  const a = sec(from);
  const b = sec(to);
  const env = sceneEnvelope(frame, a, b);
  if (!env.visible) return null;
  const cam = 1 + interpolate(frame, [a, b], [0, push], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const t = THEME[theme];
  return (
    <AbsoluteFill style={{opacity: env.opacity, transform: `scale(${env.scale * cam})`, filter: `blur(${env.blur}px)`, background: t.bg}}>
      <CornerShapes set={set} color={t.corner} />
      <MaskedGrid color={t.grid} cx={gridAt?.x} cy={gridAt?.y} />
      {children}
    </AbsoluteFill>
  );
};

// Legenda karaokê no topo (zona segura: acima de 14% e abaixo de 65% da altura)
export const Caption: React.FC<{
  words: Word[];
  range: [number, number];
  theme: Theme;
  size?: number;
  weight?: number;
  top?: number;
  accentFrom?: number;
  strike?: boolean;
  wrap?: boolean;
}> = ({words, range, theme, size = 64, weight = 700, top = 290, accentFrom, strike, wrap}) => {
  const frame = useCurrentFrame();
  const t = THEME[theme];
  const s = strike ? ramp(frame, sec((words[range[1]]?.e ?? 0) + 0.05), 7) : 0;
  return (
    <div style={{position: 'absolute', top, width: '100%', padding: '0 70px', boxSizing: 'border-box', display: 'flex', justifyContent: 'center'}}>
      <div style={{position: 'relative'}}>
        <SyncedLine
          words={words}
          from={range[0]}
          to={range[1]}
          size={size}
          weight={weight}
          color={strike && s > 0.6 ? '#8A8A8F' : t.text}
          accentFrom={accentFrom}
          accentColor={t.accentText}
          style={wrap ? {whiteSpace: 'normal', maxWidth: 940} : undefined}
        />
        {strike && (
          <div style={{position: 'absolute', left: -10, top: '50%', height: 10, borderRadius: 5, width: `calc((100% + 20px) * ${s})`, opacity: s > 0 ? 1 : 0, background: 'var(--strike)', transform: 'rotate(-2deg)'}} />
        )}
      </div>
    </div>
  );
};

export {DotGrid};
