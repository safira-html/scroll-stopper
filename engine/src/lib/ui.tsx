import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {sansFamily, monoFamily as brandMono, displayFamily} from '../brand/fonts';
import {ramp} from './anim';
import {StableWord, breakLines, toRows, wordWidth} from './textLayout';

// Fontes da marca ativa (brand.json → src/brand/fonts.ts)
export const fontFamily = sansFamily;
export const monoFamily = brandMono;
export {displayFamily};

// Sombra "clay": sombra macia e longa embaixo. Sem o brilho branco interno: em pills escuros
// e verdes ele virava um contorno claro que brigava com o texto.
export const clayShadow =
  'inset 0 -3px 6px rgba(26,26,26,.06), 0 40px 80px -28px rgba(26,26,26,.32), 0 14px 28px -14px rgba(26,26,26,.22)';
export const darkShadow =
  'inset 0 1px 0 rgba(255,255,255,.10), 0 40px 80px -24px rgba(0,0,0,.7), 0 0 0 1px rgba(255,255,255,.08)';

export const DotGrid: React.FC<{color: string; size?: number}> = ({color, size = 40}) => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill
      style={{
        backgroundImage: `radial-gradient(${color} 2.2px, transparent 2.4px)`,
        backgroundSize: `${size}px ${size}px`,
        backgroundPosition: `0px ${-frame * 0.4}px`,
      }}
    />
  );
};

// Luz suave no centro, para dar volume ao fundo
export const Vignette: React.FC<{dark?: boolean}> = ({dark}) => (
  <AbsoluteFill
    style={{
      background: dark
        ? 'radial-gradient(60% 45% at 50% 48%, color-mix(in srgb, var(--accent) 10%, transparent), transparent 70%), radial-gradient(120% 90% at 50% 50%, transparent 55%, rgba(0,0,0,.55))'
        : 'radial-gradient(70% 50% at 50% 50%, rgba(255,255,255,.9), transparent 70%), radial-gradient(120% 90% at 50% 50%, transparent 60%, rgba(26,26,26,.10))',
    }}
  />
);

export const Grain: React.FC<{opacity?: number}> = ({opacity = 0.07}) => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{mixBlendMode: 'multiply', opacity, pointerEvents: 'none'}}>
      <svg width="100%" height="100%">
        <filter id="grain">
          <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves={2} seed={frame % 12} />
        </filter>
        <rect width="100%" height="100%" filter="url(#grain)" />
      </svg>
    </AbsoluteFill>
  );
};

// Janela estilo macOS (base do editor, do dashboard e do navegador)
export const AppWindow: React.FC<{
  width: number;
  height: number;
  title: string;
  dark?: boolean;
  children: React.ReactNode;
  style?: React.CSSProperties;
}> = ({width, height, title, dark, children, style}) => (
  <div
    style={{
      width,
      height,
      borderRadius: 28,
      overflow: 'hidden',
      background: dark ? '#141414' : '#FFFFFF',
      boxShadow: dark ? darkShadow : clayShadow,
      border: dark ? '1px solid rgba(255,255,255,.08)' : '1px solid #E3E5E9',
      display: 'flex',
      flexDirection: 'column',
      ...style,
    }}
  >
    <div
      style={{
        height: 64,
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        padding: '0 24px',
        background: dark ? '#1F1F1F' : '#F2F3F5',
        borderBottom: dark ? '1px solid rgba(255,255,255,.06)' : '1px solid #E3E5E9',
      }}
    >
      {['#FF5F57', '#FEBC2E', '#28C840'].map((c) => (
        <div key={c} style={{width: 18, height: 18, borderRadius: 9, background: c}} />
      ))}
      <div
        style={{
          marginLeft: 18,
          fontFamily: monoFamily,
          fontSize: 24,
          color: dark ? '#9A9A9A' : '#6E6E73',
        }}
      >
        {title}
      </div>
    </div>
    <div style={{flex: 1, position: 'relative'}}>{children}</div>
  </div>
);

// Cartão "clay" genérico
export const ClayCard: React.FC<{
  children: React.ReactNode;
  style?: React.CSSProperties;
  dark?: boolean;
}> = ({children, style, dark}) => (
  <div
    style={{
      borderRadius: 32,
      background: dark ? '#242424' : '#FFFFFF',
      boxShadow: dark ? darkShadow : clayShadow,
      border: dark ? '1px solid rgba(255,255,255,.08)' : '1px solid #ECEEF1',
      ...style,
    }}
  >
    {children}
  </div>
);

// Linha de texto palavra a palavra, sincronizada com o áudio
export type Word = {w: string; s: number; e: number};

export const SyncedLine: React.FC<{
  words: Word[];
  from: number;
  to: number;
  size: number;
  weight: number;
  color: string;
  accentFrom?: number;
  accentColor?: string;
  style?: React.CSSProperties;
}> = ({words, from, to, size, weight, color, accentFrom, accentColor, style}) => {
  const frame = useCurrentFrame();
  const slice = words.slice(from, to + 1);
  // quebra decidida com o peso final: nada muda de linha enquanto o peso cresce
  const maxWidth = typeof style?.maxWidth === 'number' ? style.maxWidth : 940;
  const spec = {family: fontFamily, size, weight, letterSpacingEm: -0.035};
  const starts = breakLines(slice.map((w) => wordWidth(w.w, spec)), size * 0.22, maxWidth, slice.map((w) => w.w));
  const appear = ramp(frame, Math.round(words[from].s * 30) - 6, 8);
  return (
    <div
      style={{
        fontFamily,
        fontSize: size,
        fontWeight: weight,
        letterSpacing: '-0.035em',
        lineHeight: 1.05,
        textAlign: 'center',
        color,
        ...style,
        whiteSpace: 'nowrap',
      }}
    >
      {toRows(slice.map((w, i) => ({w, i})), starts).map((row, r) => (
        <div key={r}>
          {row.map(({w: word, i}, j) => {
            const t = ramp(frame, Math.round(word.s * 30) - 2, 6);
            const accent = accentFrom !== undefined && from + i >= accentFrom;
            return (
              <StableWord
                key={i}
                text={word.w}
                finalWeight={weight}
                boxStyle={{marginRight: j < row.length - 1 ? '0.22em' : 0}}
                style={{
                  opacity: appear * (0.35 + t * 0.65),
                  fontWeight: Math.round(300 + t * (weight - 300)),
                  filter: `blur(${(1 - appear) * 8}px)`,
                  transform: `translateY(${(1 - appear) * 30}px) scale(${0.97 + t * 0.03})`,
                  color: t < 0.5 ? '#9A9A9A' : accent ? accentColor : undefined,
                }}
              />
            );
          })}
        </div>
      ))}
    </div>
  );
};

const CORNER_SETS = [
  [{x: -180, y: 1350, s: 620}, {x: 760, y: -120, s: 460}],
  [{x: 700, y: 1450, s: 640}, {x: -220, y: 80, s: 420}],
  [{x: -260, y: 300, s: 560}, {x: 720, y: 1500, s: 520}],
  [{x: 640, y: 120, s: 600}, {x: -200, y: 1500, s: 480}],
  [{x: -140, y: 1500, s: 700}, {x: 780, y: 260, s: 380}],
];
export const CornerShapes: React.FC<{set: number; color?: string}> = ({set, color = '#D5D8DD'}) => {
  const frame = useCurrentFrame();
  return (
    <>
      {CORNER_SETS[set % CORNER_SETS.length].map((c, i) => (
        <svg key={i} width={c.s} height={c.s} viewBox="-50 -50 100 100" style={{position: 'absolute', left: c.x, top: c.y + Math.sin(frame / 30 + i) * 14, filter: 'blur(16px)', opacity: 0.85, transform: `rotate(${frame * (i ? 0.15 : -0.12)}deg)`}}>
          {[0, 1, 2, 3, 4, 5].map((k) => (
            <rect key={k} x={-6} y={-46} width={12} height={92} rx={6} fill={color} transform={`rotate(${k * 30})`} />
          ))}
        </svg>
      ))}
    </>
  );
};

// Grade só em volta do objeto (máscara radial), como nas referências
export const MaskedGrid: React.FC<{color: string; cx?: number; cy?: number}> = ({color, cx = 540, cy = 1000}) => (
  <AbsoluteFill style={{maskImage: `radial-gradient(520px 520px at ${cx}px ${cy}px, #000 30%, transparent 75%)`, WebkitMaskImage: `radial-gradient(520px 520px at ${cx}px ${cy}px, #000 30%, transparent 75%)`}}>
    <DotGrid color={color} />
  </AbsoluteFill>
);
