// Telas para vídeo com apresentador (bruto cortado pelo `ss cut`) alternado com motion.
// Tipos de tela: apresentador em close (PresenterShot), tela dividida (SplitScreen), só motion (BrandStage + cena),
// flash de palavra (WordFlash). Transições em Shot; legenda por trecho em SegmentCaptions.
import React from 'react';
import {AbsoluteFill, OffthreadVideo, Sequence, getStaticFiles, interpolate, staticFile, useCurrentFrame} from 'remotion';
import {easeOut, pop, ramp, sec} from './lib/anim';
import {CornerShapes, DotGrid, MaskedGrid, Vignette, clayShadow, darkShadow, fontFamily, monoFamily} from './lib/ui';
import {Captions, Chunk} from './kit';
import {findPhrase, Word} from './engine/words';
import {brand} from './brand';

const C = brand.colors;
const W = 1080;
const H = 1920;

// Vídeo do apresentador e ponto do rosto no quadro (0–1). Meça o rosto num quadro do corte com grade.
export type PresenterSource = {src: string; face: {x: number; y: number}};

const hasFile = (p: string) => getStaticFiles().some((f) => f.name === p);

// Enquadramento: zoom z com o rosto levado à altura ty da área; nunca deixa borda vazia
const frameStyle = (face: {x: number; y: number}, z: number, ty: number, w: number, h: number): React.CSSProperties => {
  const vw = Math.max(w, (h * 9) / 16) * z;
  const vh = (vw * 16) / 9;
  let x = 0.5 * w - face.x * vw;
  let y = ty * h - face.y * vh;
  x = Math.min(0, Math.max(w - vw, x));
  y = Math.min(0, Math.max(h - vh, y));
  return {position: 'absolute', left: x, top: y, width: vw, height: vh};
};

// Sem o vídeo em public/, mostra um apresentador de mentira para o layout poder ser revisado
const Placeholder: React.FC<{w: number; h: number}> = ({w, h}) => (
  <div style={{position: 'absolute', inset: 0, width: w, height: h, background: 'linear-gradient(180deg, #4A4A4A, #2A2A2A)', overflow: 'hidden'}}>
    <div style={{position: 'absolute', left: w / 2 - h * 0.09, top: h * 0.2, width: h * 0.18, height: h * 0.22, borderRadius: '50%', background: '#6A6A6A'}} />
    <div style={{position: 'absolute', left: w / 2 - h * 0.24, top: h * 0.44, width: h * 0.48, height: h * 0.7, borderRadius: '45% 45% 0 0', background: '#5A5A5A'}} />
    <div style={{position: 'absolute', top: 24, left: 0, right: 0, textAlign: 'center', fontFamily: monoFamily, fontSize: 26, color: 'rgba(255,255,255,.5)'}}>apresentador (coloque o vídeo em public/)</div>
  </div>
);

// Apresentador sincronizado com a linha do tempo global (o corte já está no tempo final).
// z: zoom no início e no fim do trecho (push-in lento); punchAt: segundos com salto curto de zoom (+14%).
export const PresenterShot: React.FC<{
  source: PresenterSource;
  from: number;
  to: number;
  z?: [number, number];
  ty?: number;
  w?: number;
  h?: number;
  punchAt?: number[];
}> = ({source, from, to, z = [1.4, 1.5], ty = 0.3, w = W, h = H, punchAt = []}) => {
  const a = sec(from);
  const b = sec(to);
  return (
    // +8 quadros: acompanha a sobreposição do Shot na transição
    <Sequence from={a} durationInFrames={Math.max(1, b - a + 8)} layout="none">
      <ShotBody source={source} a={a} len={b - a} z={z} ty={ty} w={w} h={h} punchAt={punchAt.map((p) => sec(p) - a)} />
    </Sequence>
  );
};

const ShotBody: React.FC<{source: PresenterSource; a: number; len: number; z: [number, number]; ty: number; w: number; h: number; punchAt: number[]}> = ({source, a, len, z, ty, w, h, punchAt}) => {
  const frame = useCurrentFrame();
  let zz = interpolate(frame, [0, len], z, {extrapolateRight: 'clamp'});
  for (const p of punchAt) zz *= 1 + 0.14 * ramp(frame, p, 4, easeOut);
  return (
    <div style={{position: 'absolute', inset: 0, overflow: 'hidden', width: w, height: h}}>
      {hasFile(source.src) ? (
        <OffthreadVideo src={staticFile(source.src)} startFrom={a} muted style={{...frameStyle(source.face, zz, ty, w, h), objectFit: 'cover'}} />
      ) : (
        <div style={{position: 'absolute', inset: 0, transform: `scale(${zz / 1.4})`}}>
          <Placeholder w={w} h={h} />
        </div>
      )}
    </div>
  );
};

// Fundo de marca (claro ou escuro) com formas desfocadas e grade mascarada em volta do objeto
export const BrandStage: React.FC<{theme: 'light' | 'dark'; set?: number; gridAt?: {x: number; y: number}; children?: React.ReactNode}> = ({theme, set = 0, gridAt, children}) => {
  const t = theme === 'dark' ? C.dark : C.light;
  return (
    <AbsoluteFill style={{background: t.bg}}>
      <Vignette dark={theme === 'dark'} />
      <CornerShapes set={set} color={t.corner} />
      <MaskedGrid
        color={theme === 'dark' ? 'color-mix(in srgb, var(--accent) 16%, transparent)' : 'color-mix(in srgb, var(--accent-display) 22%, transparent)'}
        cx={gridAt?.x}
        cy={gridAt?.y}
      />
      {children}
    </AbsoluteFill>
  );
};

// Janela de tempo de uma tela, com a entrada: whip lateral com blur, zoom chegando grande, subida ou corte seco
export type Enter = 'whipL' | 'whipR' | 'zoom' | 'up' | 'cut';
export const Shot: React.FC<{from: number; to: number; enter?: Enter; children: React.ReactNode}> = ({from, to, enter = 'cut', children}) => {
  const frame = useCurrentFrame();
  const a = sec(from);
  const b = sec(to);
  // fica 8 quadros a mais: a tela seguinte (desenhada depois, por cima) entra sobre esta, sem quadro vazio
  if (frame < a - 1 || frame > b + 8) return null;
  const t = ramp(frame, a, 7, easeOut);
  let style: React.CSSProperties = {};
  if (enter === 'whipL' || enter === 'whipR') {
    const dir = enter === 'whipL' ? 1 : -1;
    style = {transform: `translateX(${(1 - t) * 100 * dir}%)`, filter: `blur(${(1 - t) * 24}px)`};
  } else if (enter === 'zoom') {
    style = {transform: `scale(${1.25 - 0.25 * t})`, filter: `blur(${(1 - t) * 16}px)`, opacity: Math.min(1, t * 1.6)};
  } else if (enter === 'up') {
    style = {transform: `translateY(${(1 - t) * 100}%)`, filter: `blur(${(1 - t) * 18}px)`};
  }
  return <AbsoluteFill style={{overflow: 'hidden', ...style}}>{children}</AbsoluteFill>;
};

// Tela dividida: motion em cima (0–1060) e o apresentador num card embaixo. Legenda na emenda (top ≈ 830).
export const SplitScreen: React.FC<{source: PresenterSource; from: number; to: number; theme?: 'light' | 'dark'; set?: number; top: React.ReactNode; z?: [number, number]}> = ({
  source,
  from,
  to,
  theme = 'dark',
  set = 1,
  top,
  z = [1.9, 2.05],
}) => {
  const frame = useCurrentFrame();
  const card = ramp(frame, sec(from), 10, easeOut);
  return (
    <BrandStage theme={theme} set={set} gridAt={{x: 540, y: 560}}>
      <div style={{position: 'absolute', left: 0, top: 0, width: W, height: 1060}}>{top}</div>
      <div
        style={{
          position: 'absolute',
          left: 60,
          top: 1080,
          width: 960,
          height: 800,
          borderRadius: 44,
          overflow: 'hidden',
          boxShadow: theme === 'dark' ? darkShadow : clayShadow,
          border: theme === 'dark' ? '2px solid rgba(255,255,255,.1)' : '2px solid #FFFFFF',
          transform: `translateY(${(1 - card) * 160}px)`,
        }}
      >
        <PresenterShot source={source} from={from} to={to} z={z} ty={0.42} w={960} h={800} />
      </div>
    </BrandStage>
  );
};

// Flash de palavra: fundo sólido na cor de destaque e uma palavra ou número gigante (dura 0,6–1,2 s)
export const WordFlash: React.FC<{from: number; word: string; sub?: string}> = ({from, word, sub}) => {
  const frame = useCurrentFrame();
  const a = sec(from);
  const p = pop(frame, a, 30, 9);
  return (
    <AbsoluteFill style={{background: C.accent, alignItems: 'center', justifyContent: 'center', flexDirection: 'column'}}>
      <DotGrid color="rgba(0,0,0,.08)" />
      <div style={{fontFamily, fontWeight: 700, fontSize: 260, letterSpacing: '-0.06em', lineHeight: 0.9, color: C.accentInk, transform: `scale(${0.6 + 0.4 * Math.min(1.08, p)})`, textAlign: 'center'}}>{word}</div>
      {sub && <div style={{fontFamily: monoFamily, fontSize: 40, color: C.accentInk, marginTop: 30, opacity: ramp(frame, a + 6, 8), letterSpacing: '0.08em'}}>{sub}</div>}
    </AbsoluteFill>
  );
};

// Flash branco de 2 quadros num corte seco (fala de alerta)
export const WhiteHit: React.FC<{at: number}> = ({at}) => {
  const frame = useCurrentFrame();
  const f = sec(at);
  const o = interpolate(frame, [f - 1, f, f + 3], [0, 0.85, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return o > 0 ? <AbsoluteFill style={{background: '#FFFFFF', opacity: o}} /> : null;
};

// Degradê atrás da legenda quando ela fica sobre o vídeo (a legenda não usa sombra)
export const CaptionScrim: React.FC<{y: number; h?: number}> = ({y, h = 420}) => (
  <div
    style={{
      position: 'absolute',
      left: 0,
      right: 0,
      top: y - h / 2,
      height: h,
      background: 'linear-gradient(180deg, rgba(0,0,0,0) 0%, rgba(0,0,0,.55) 45%, rgba(0,0,0,.55) 60%, rgba(0,0,0,0) 100%)',
    }}
  />
);

// Legenda de um trecho: só as palavras até o fim do trecho, para o último bloco sair junto com a tela
export const SegmentCaptions: React.FC<{words: Word[]; chunks: Chunk[]; theme: 'light' | 'dark'; top: number; size?: number}> = ({words, chunks, theme, top, size = 92}) => {
  const last = findPhrase(words, chunks[chunks.length - 1].p.replace(/-/g, ''))[1];
  return <Captions words={words.slice(0, last + 1)} chunks={chunks} theme={theme} top={top} size={size} />;
};

// Posições de legenda testadas (1080×1920): sobre o apresentador, só motion e na emenda da tela dividida
export const CAPTION_TOP = {presenter: 1140, motion: 1110, split: 830};
