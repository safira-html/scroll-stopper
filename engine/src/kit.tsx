import React from 'react';
import {AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame} from 'remotion';
import {easeInOut, pop, ramp, sec} from './lib/anim';
import {fontFamily, monoFamily, darkShadow, clayShadow} from './lib/ui';
import {Theme, THEME, endStartOf} from './engine/AdShell';
import {Word, findPhrase} from './engine/words';
import {StableWord, breakLines, toRows, wordWidth} from './lib/textLayout';
import {brand, brandAsset} from './brand';

export const ACCENT = 'var(--accent)';
export const ACCENT_DEEP = 'var(--accent-display)';
export const INK = '#1A1A1A';
export const ACCENT_INK = 'var(--accent-ink)';
// Cores de erro/risco vêm da marca (brand.colors.danger / strike), via variáveis CSS
export const RED = 'var(--danger)';
export const RED_DEEP = 'var(--strike)';
export const S1 = '#242424';
export const S2 = '#313131';
export const LINE = 'rgba(255,255,255,.08)';
export {fontFamily, monoFamily, darkShadow, clayShadow};

// ---------- Tempo amarrado à fala ----------
// Cursor sequencial: cada frase é procurada depois da anterior, então repetições não confundem.
export const makeCues = (words: Word[]) => {
  let cursor = 0;
  const cache = new Map<string, [number, number]>();
  const range = (phrase: string): [number, number] => {
    const hit = cache.get(phrase);
    if (hit) return hit;
    const r = findPhrase(words, phrase.replace(/-/g, ''), cursor);
    cursor = r[0];
    cache.set(phrase, r);
    return r;
  };
  return {
    range,
    s: (phrase: string) => words[range(phrase)[0]]?.s ?? 0,
    e: (phrase: string) => words[range(phrase)[1]]?.e ?? 0,
    // início de uma palavra específica dentro da frase (offset de palavras)
    w: (phrase: string, k: number) => words[Math.min(words.length - 1, range(phrase)[0] + k)]?.s ?? 0,
    end: endStartOf(words),
  };
};

const norm = (t: string) => t.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[^a-z0-9]/g, '');

// ---------- Legenda karaokê com palavra-chave em pill ----------
export type Chunk = {p: string; key?: string; small?: boolean; top?: number; size?: number};

export const Captions: React.FC<{
  words: Word[];
  chunks: Chunk[];
  darkFrom?: number; // segundos; antes disso, tema claro (P9)
  theme?: Theme;
  top?: number;
  size?: number;
  family?: string; // fonte opcional da legenda (padrão: sans da marca)
  weights?: [number, number]; // peso da palavra não falada → falada
  letterSpacing?: number; // em em
}> = ({words, chunks, darkFrom, theme = 'dark', top = 300, size = 66, family = fontFamily, weights = brand.captions.weights, letterSpacing = -0.035}) => {
  const frame = useCurrentFrame();
  if (!words.length) return null;
  const endAt = endStartOf(words);
  let cursor = 0;
  const ranges = chunks.map((c) => {
    const r = findPhrase(words, c.p.replace(/-/g, ''), cursor);
    cursor = r[1] + 1;
    return r;
  });
  return (
    <>
      {chunks.map((c, i) => {
        const [a, b] = ranges[i];
        const start = sec(words[a].s) - 4;
        const stop = i < chunks.length - 1 ? sec(words[ranges[i + 1][0]].s) - 4 : sec(endAt) - 2;
        if (frame < start - 1 || frame > stop + 1) return null;
        const th: Theme = darkFrom !== undefined ? (words[a].s >= darkFrom - 0.05 ? 'dark' : 'light') : theme;
        const t = THEME[th];
        const appear = ramp(frame, start, 8);
        const out = ramp(frame, stop - 4, 4, easeInOut);
        // a palavra-chave é uma frase contígua dentro do trecho
        const keyToks = (c.key ?? '').replace(/-/g, '').split(/\s+/).map(norm).filter(Boolean);
        let k0 = -1;
        let k1 = -1;
        if (keyToks.length) {
          const target = keyToks.join('');
          for (let i0 = a; i0 <= b && k0 < 0; i0++) {
            let acc = '';
            for (let j = i0; j <= b; j++) {
              acc += norm(words[j].w);
              if (acc === target) {
                k0 = i0;
                k1 = j;
                break;
              }
              if (!target.startsWith(acc)) break;
            }
          }
        }
        const segs: Array<{idx: number[]; pill: boolean}> = [];
        for (let k = a; k <= b; k++) {
          const pill = k >= k0 && k <= k1 && k0 >= 0;
          const last = segs[segs.length - 1];
          if (last && last.pill === pill) last.idx.push(k);
          else segs.push({idx: [k], pill});
        }
        const baseFs = c.size ?? (c.small ? size * 0.72 : size);
        // trecho curto (até 5 palavras) que não cabe numa linha: reduz a fonte até caber (mín. 72%)
        const nWords = b - a + 1;
        const oneLine = words.slice(a, b + 1).reduce((acc, w, j) => acc + wordWidth(w.w, {family, size: baseFs, weight: c.small ? Math.min(600, weights[1]) : weights[1], letterSpacingEm: letterSpacing}) + (j ? baseFs * 0.22 : 0), 0) + baseFs * 0.7;
        const fs = nWords <= 5 && oneLine > 940 ? baseFs * Math.max(0.72, 940 / oneLine) : baseFs;
        const fw = c.small ? Math.min(600, weights[1]) : weights[1];
        const wordEl = (k: number, inPill: boolean, last: boolean) => {
          const tt = ramp(frame, sec(words[k].s) - 2, 6);
          const color = inPill && tt >= 0.5 ? (th === 'dark' ? ACCENT_INK : ACCENT) : tt < 0.5 ? (th === 'dark' ? '#6A6A6A' : '#A3A3A3') : t.text;
          return (
            <StableWord
              key={k}
              text={words[k].w}
              finalWeight={fw}
              boxStyle={{marginRight: last ? 0 : '0.22em'}}
              style={{opacity: inPill ? 1 : 0.4 + tt * 0.6, fontWeight: Math.round(weights[0] + tt * (fw - weights[0])), color}}
            />
          );
        };
        // unidades inseparáveis: cada palavra solta ou o pill inteiro; quebra decidida com o peso final
        const spec = {family, size: fs, weight: fw, letterSpacingEm: letterSpacing};
        const gap = fs * 0.22;
        const units = segs.flatMap((sg) => (sg.pill ? [{pill: true, idx: sg.idx}] : sg.idx.map((k) => ({pill: false, idx: [k]}))));
        const unitW = units.map((u) => {
          const text = u.idx.reduce((acc, k, j) => acc + wordWidth(words[k].w, spec) + (j < u.idx.length - 1 ? gap : 0), 0);
          return u.pill ? text + fs * 0.48 + fs * 0.18 : text;
        });
        const rows = toRows(units, breakLines(unitW, gap, 940, units.map((u) => words[u.idx[u.idx.length - 1]].w)));
        return (
          <div
            key={i}
            style={{
              position: 'absolute',
              top: c.top ?? top,
              left: 0,
              width: '100%',
              padding: '0 70px',
              boxSizing: 'border-box',
              display: 'flex',
              justifyContent: 'center',
              opacity: appear * (1 - out),
              filter: `blur(${(1 - appear) * 8 + out * 6}px)`,
              transform: `translateY(${(1 - appear) * 34 - out * 24}px)`,
              zIndex: 50,
            }}
          >
            {/* sem textShadow: a sombra clara/escura atrás do texto derrubava o contraste dentro do pill */}
            <div style={{fontFamily: family, fontSize: fs, letterSpacing: `${letterSpacing}em`, lineHeight: 1.12, textAlign: 'center', whiteSpace: 'nowrap'}}>
              {rows.map((row, ri) => (
                <div key={ri}>
                  {row.map((u, ui) => {
                    const lastInRow = ui === row.length - 1;
                    if (!u.pill) return wordEl(u.idx[0], false, lastInRow);
                    const p = pop(frame, sec(words[u.idx[0]].s) - 2, 30, 10);
                    const on = frame >= sec(words[u.idx[0]].s) - 2;
                    return (
                      <span
                        key={`p${u.idx[0]}`}
                        style={{
                          display: 'inline-block',
                          background: on ? (th === 'dark' ? ACCENT : INK) : 'transparent',
                          outline: on ? 'none' : `2px dashed ${th === 'dark' ? 'color-mix(in srgb, var(--accent) 35%, transparent)' : 'rgba(26,26,26,.25)'}`,
                          borderRadius: fs * 0.28,
                          padding: `${fs * 0.04}px ${fs * 0.24}px ${fs * 0.08}px`,
                          margin: `0 ${lastInRow ? 0 : fs * 0.18}px ${fs * 0.06}px 0`,
                          transform: on ? `scale(${0.8 + Math.min(1.1, p) * 0.2}) rotate(${(1 - Math.min(1, p)) * -4}deg)` : 'none',
                          boxShadow: !on ? 'none' : th === 'dark' ? 'none' : '0 18px 36px -18px rgba(26,26,26,.45)',
                        }}
                      >
                        {u.idx.map((k, j) => wordEl(k, true, j === u.idx.length - 1))}
                      </span>
                    );
                  })}
                </div>
              ))}
            </div>
          </div>
        );
      })}
    </>
  );
};

// ---------- Posicionamento ----------
export const Center: React.FC<{top?: number; children: React.ReactNode; style?: React.CSSProperties}> = ({top = 600, children, style}) => (
  <div style={{position: 'absolute', top, left: 0, width: '100%', display: 'flex', justifyContent: 'center', ...style}}>{children}</div>
);

// Inclinação 3D que assenta ao entrar e respira devagar
export const Tilt: React.FC<{start: number; rx?: number; ry?: number; drift?: number; children: React.ReactNode; persp?: number}> = ({start, rx = 18, ry = -16, drift = 3, children, persp = 1800}) => {
  const frame = useCurrentFrame();
  const k = 1 - ramp(frame, start, 26);
  const d = Math.sin((frame - start) / 40) * drift;
  return <div style={{transform: `perspective(${persp}px) rotateX(${rx * k + d * 0.4}deg) rotateY(${ry * k + d}deg)`, transformStyle: 'preserve-3d'}}>{children}</div>;
};

// ---------- Janela escura ou clara ----------
export const Win: React.FC<{width: number; height: number; title: string; dark?: boolean; children: React.ReactNode; style?: React.CSSProperties; icon?: React.ReactNode}> = ({width, height, title, dark = true, children, style, icon}) => (
  <div
    style={{
      width,
      height,
      borderRadius: 30,
      overflow: 'hidden',
      background: dark ? '#141414' : '#FFFFFF',
      boxShadow: dark ? `${darkShadow}, 0 0 80px -20px color-mix(in srgb, var(--accent) 18%, transparent)` : clayShadow,
      border: dark ? `1px solid ${LINE}` : '1px solid #E3E5E9',
      display: 'flex',
      flexDirection: 'column',
      position: 'relative',
      ...style,
    }}
  >
    <div style={{height: 66, flexShrink: 0, display: 'flex', alignItems: 'center', gap: 12, padding: '0 26px', background: dark ? '#1F1F1F' : '#F2F3F5', borderBottom: dark ? '1px solid rgba(255,255,255,.06)' : '1px solid #E3E5E9'}}>
      {['#FF5F57', '#FEBC2E', '#28C840'].map((c) => (
        <div key={c} style={{width: 18, height: 18, borderRadius: 9, background: c}} />
      ))}
      {icon}
      <div style={{marginLeft: icon ? 6 : 18, fontFamily: monoFamily, fontSize: 24, color: dark ? '#9A9A9A' : '#6E6E73', whiteSpace: 'nowrap'}}>{title}</div>
    </div>
    <div style={{flex: 1, position: 'relative', overflow: 'hidden'}}>{children}</div>
  </div>
);

// ---------- Planilha genérica ----------
export type SheetCol = {label: string; w: number; align?: 'left' | 'right' | 'center'};
export const Sheet: React.FC<{
  cols: SheetCol[];
  rows: string[][];
  rowH?: number;
  fs?: number;
  dark?: boolean;
  firstRow?: number;
  cell?: (r: number, c: number) => React.CSSProperties | undefined;
  rowStyle?: (r: number) => React.CSSProperties | undefined;
  header?: boolean;
}> = ({cols, rows, rowH = 58, fs = 24, dark = true, firstRow = 1, cell, rowStyle, header = true}) => {
  const line = dark ? 'rgba(255,255,255,.07)' : '#E6E8EC';
  const headBg = dark ? '#1C1C1C' : '#F4F5F7';
  const text = dark ? '#E6E6E6' : INK;
  const muted = dark ? '#6F6F6F' : '#8A8A8F';
  return (
    <div style={{fontFamily: monoFamily, fontSize: fs, color: text}}>
      {header && (
        <div style={{display: 'flex', height: rowH * 0.78, background: headBg, borderBottom: `1px solid ${line}`}}>
          <div style={{width: 64, borderRight: `1px solid ${line}`}} />
          {cols.map((c, i) => (
            <div key={i} style={{width: c.w, borderRight: `1px solid ${line}`, display: 'flex', alignItems: 'center', justifyContent: 'center', color: muted, fontSize: fs * 0.8}}>
              {String.fromCharCode(65 + i)}
            </div>
          ))}
        </div>
      )}
      {rows.map((row, r) => (
        <div key={r} style={{display: 'flex', height: rowH, borderBottom: `1px solid ${line}`, ...rowStyle?.(r)}}>
          <div style={{width: 64, borderRight: `1px solid ${line}`, display: 'flex', alignItems: 'center', justifyContent: 'center', color: muted, fontSize: fs * 0.78, background: headBg}}>{r + firstRow}</div>
          {cols.map((c, ci) => (
            <div
              key={ci}
              style={{
                width: c.w,
                borderRight: `1px solid ${line}`,
                display: 'flex',
                alignItems: 'center',
                justifyContent: c.align === 'right' ? 'flex-end' : c.align === 'center' ? 'center' : 'flex-start',
                padding: '0 14px',
                boxSizing: 'border-box',
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                position: 'relative',
                ...cell?.(r, ci),
              }}
            >
              {row[ci]}
            </div>
          ))}
        </div>
      ))}
    </div>
  );
};

// ---------- Logo de ferramenta num ladrilho ----------
export const LogoTile: React.FC<{logo: string; size?: number; dark?: boolean}> = ({logo, size = 84, dark = true}) => (
  <div style={{width: size, height: size, borderRadius: size * 0.26, background: dark ? S2 : '#FFFFFF', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: dark ? 'inset 0 1px 0 rgba(255,255,255,.12), 0 12px 24px -10px rgba(0,0,0,.6)' : clayShadow, flexShrink: 0}}>
    <Img src={staticFile(brandAsset(/\.\w+$/.test(logo) ? logo : `${logo}.svg`))} style={{width: size * 0.62, height: size * 0.62, objectFit: 'contain'}} />
  </div>
);

// ---------- Carimbo de check ----------
export const Stamp: React.FC<{at: number; label?: string; size?: number; rot?: number}> = ({at, label = 'conferido', size = 1, rot = -8}) => {
  const frame = useCurrentFrame();
  const p = pop(frame, at, 30, 9);
  if (frame < at) return null;
  const ring = ramp(frame, at, 14);
  return (
    <div style={{position: 'relative', transform: `scale(${(1.8 - Math.min(1, p) * 0.8) * size}) rotate(${rot}deg)`, opacity: Math.min(1, p * 2)}}>
      <div style={{position: 'absolute', inset: -16, borderRadius: 999, border: `4px solid ${ACCENT}`, opacity: (1 - ring) * 0.8, transform: `scale(${1 + ring * 0.5})`}} />
      <div style={{display: 'flex', alignItems: 'center', gap: 12, padding: '10px 24px 12px 14px', borderRadius: 999, background: 'color-mix(in srgb, var(--accent) 22%, #1A1A1A)', border: `3px solid ${ACCENT}`, boxShadow: '0 0 30px color-mix(in srgb, var(--accent) 45%, transparent), 0 16px 30px -12px rgba(0,0,0,.6)'}}>
        <div style={{width: 42, height: 42, borderRadius: 21, background: ACCENT, display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
          <svg width={26} height={26} viewBox="0 0 24 24">
            <path d="M4 12.5l5 5L20 6.5" fill="none" stroke={ACCENT_INK} strokeWidth={3.6} strokeLinecap="round" strokeLinejoin="round" strokeDasharray={30} strokeDashoffset={30 * (1 - ramp(frame, at + 3, 8))} />
          </svg>
        </div>
        <div style={{fontFamily, fontWeight: 700, fontSize: 32, color: ACCENT, letterSpacing: '-0.02em', whiteSpace: 'nowrap'}}>{label}</div>
      </div>
    </div>
  );
};

// ---------- Asterisco de pixels (motivo da marca) ----------
export const PixelStar: React.FC<{size?: number; color?: string; spin?: number}> = ({size = 120, color = ACCENT, spin = 0.4}) => {
  const frame = useCurrentFrame();
  const cells: Array<[number, number]> = [];
  for (let k = -3; k <= 3; k++) {
    cells.push([k, 0], [0, k], [k, k], [k, -k]);
  }
  return (
    <svg width={size} height={size} viewBox="-4 -4 8 8" style={{transform: `rotate(${frame * spin}deg)`}}>
      {cells.map(([x, y], i) => (
        <rect key={i} x={x - 0.42} y={y - 0.42} width={0.84} height={0.84} rx={0.12} fill={color} />
      ))}
    </svg>
  );
};

// ---------- Contador com brilho ----------
export const countUp = (frame: number, start: number, dur: number, from: number, to: number) =>
  interpolate(frame, [start, start + dur], [from, to], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: (t) => 1 - Math.pow(1 - t, 3)});

export const fmt = (n: number) => Math.round(n).toLocaleString('pt-BR');

// ---------- Cena do produto (comum às três peças) ----------
// Itens da marca (brand.endCard.tiles), mostrados em sequência no cartão do produto
const TRAIL = (brand.endCard.tiles ?? []).map((t) => ({logo: t.logo, name: t.name}));
export const ProductCard: React.FC<{start: number; kicker?: string; line?: string}> = ({start, kicker = brand.endCard.kicker ?? '', line}) => {
  const frame = useCurrentFrame();
  const p = pop(frame, start, 30, 13);
  const logo = ramp(frame, start + 4, 10);
  const draw = ramp(frame, start + 14, 30);
  return (
    <div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 40}}>
      <div
        style={{
          width: 900,
          borderRadius: 44,
          background: 'linear-gradient(160deg, #262626 0%, #1B1B1B 100%)',
          boxShadow: `${darkShadow}, 0 0 120px -30px color-mix(in srgb, var(--accent) 35%, transparent)`,
          border: `1px solid ${LINE}`,
          padding: '54px 56px 60px',
          boxSizing: 'border-box',
          transform: `scale(${0.85 + Math.min(1, p) * 0.15}) translateY(${(1 - Math.min(1, p)) * 80}px)`,
          opacity: Math.min(1, p * 1.5),
          position: 'relative',
          overflow: 'hidden',
        }}
      >
        <div style={{position: 'absolute', right: -60, top: -60, opacity: 0.16}}>
          <PixelStar size={320} />
        </div>
        <Img src={staticFile(brandAsset(brand.logos.header))} style={{width: 230, opacity: logo}} />
        <div style={{fontFamily: monoFamily, fontSize: 26, letterSpacing: '0.18em', color: ACCENT, marginTop: 34, opacity: logo}}>{kicker}</div>
        <div style={{fontFamily, fontSize: 84, fontWeight: 700, letterSpacing: '-0.045em', lineHeight: 0.98, color: '#FAFAFA', marginTop: 12}}>
          {brand.endCard.title.map((l, i) => (
            <div key={i}>{l}</div>
          ))}
        </div>
        {line && <div style={{fontFamily, fontSize: 32, color: '#B3B3B3', marginTop: 18}}>{line}</div>}
        {/* trilha */}
        <div style={{position: 'relative', display: 'flex', justifyContent: 'space-between', marginTop: 48}}>
          <div style={{position: 'absolute', left: 50, right: 50, top: 49, height: 4, background: '#333', borderRadius: 2}} />
          <div style={{position: 'absolute', left: 50, top: 49, height: 4, width: `calc((100% - 100px) * ${draw})`, background: ACCENT, borderRadius: 2, boxShadow: '0 0 18px color-mix(in srgb, var(--accent) 70%, transparent)'}} />
          {TRAIL.map((t, i) => {
            const lit = draw >= i / 3 - 0.02;
            const q = pop(frame, start + 10 + i * 6, 30, 11);
            return (
              <div key={t.name} style={{display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 14, transform: `scale(${Math.min(1.1, q)})`, zIndex: 1}}>
                <div style={{borderRadius: 30, padding: 4, background: lit ? ACCENT : 'transparent', boxShadow: lit ? '0 0 30px color-mix(in srgb, var(--accent) 55%, transparent)' : 'none'}}>
                  <LogoTile logo={t.logo} size={92} />
                </div>
                <div style={{fontFamily, fontSize: 26, fontWeight: 700, color: lit ? '#FAFAFA' : '#7A7A7A'}}>{t.name}</div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

// ---------- CTA: dedo tocando o botão do anúncio ----------
// button: texto do botão (padrão: brand.endCard.cta sem o "Toque em"); sponsored: rótulo sob o nome da marca
export const CtaTap: React.FC<{start: number; tapAt: number; button?: string; sponsored?: string}> = ({start, tapAt, button = brand.endCard.cta.replace(/^Toque em\s+/i, ''), sponsored = 'Patrocinado'}) => {
  const frame = useCurrentFrame();
  const p = pop(frame, start, 30, 12);
  const press = frame >= tapAt && frame < tapAt + 8 ? Math.sin(((frame - tapAt) / 8) * Math.PI) : 0;
  const hand = ramp(frame, start + 2, Math.max(4, tapAt - start - 2));
  const ripple = ramp(frame, tapAt, 20);
  const pulse = 0.5 + Math.sin(frame / 5) * 0.5;
  return (
    <div style={{position: 'relative', width: 900, height: 700}}>
      {/* cartão do anúncio (estilo feed) */}
      <div style={{position: 'absolute', left: 90, top: 40, width: 720, height: 560, borderRadius: 40, background: S1, border: `1px solid ${LINE}`, boxShadow: darkShadow, transform: `scale(${0.9 + Math.min(1, p) * 0.1})`, opacity: Math.min(1, p * 1.5), overflow: 'hidden'}}>
        <div style={{display: 'flex', alignItems: 'center', gap: 18, padding: '30px 34px'}}>
          <div style={{width: 70, height: 70, borderRadius: 35, background: INK, border: `2px solid ${ACCENT}`, display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
            <PixelStar size={44} spin={0.8} />
          </div>
          <div>
            <div style={{fontFamily, fontSize: 30, fontWeight: 700, color: '#FAFAFA'}}>{brand.name}</div>
            <div style={{fontFamily, fontSize: 22, color: '#8A8A8A'}}>{sponsored}</div>
          </div>
        </div>
        <div style={{margin: '0 34px', height: 250, borderRadius: 24, background: 'linear-gradient(135deg, color-mix(in srgb, var(--accent) 16%, #1A1A1A), #1A1A1A)', border: `1px solid color-mix(in srgb, var(--accent) 20%, transparent)`, display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: 8}}>
          <div style={{fontFamily: monoFamily, fontSize: 22, letterSpacing: '0.16em', color: ACCENT}}>{brand.endCard.kicker ?? ''}</div>
          <div style={{fontFamily, fontSize: 52, fontWeight: 700, color: '#FAFAFA', letterSpacing: '-0.04em', textAlign: 'center'}}>{brand.endCard.title.join(' ')}</div>
        </div>
        <div style={{position: 'absolute', left: 34, right: 34, bottom: 34, height: 110, borderRadius: 24, background: ACCENT, display: 'flex', alignItems: 'center', justifyContent: 'center', transform: `scale(${1 - press * 0.06})`, boxShadow: `0 0 ${30 + pulse * 40}px color-mix(in srgb, var(--accent) ${Math.round((0.3 + pulse * 0.3) * 100)}%, transparent)`}}>
          <div style={{fontFamily, fontSize: 50, fontWeight: 700, color: ACCENT_INK, letterSpacing: '-0.02em'}}>{button}</div>
          <svg width={40} height={40} viewBox="0 0 24 24" style={{marginLeft: 16}}>
            <path d="M5 12h13M13 6l6 6-6 6" fill="none" stroke={ACCENT_INK} strokeWidth={3} strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>
      {/* ondas do toque */}
      {frame >= tapAt && (
        <div style={{position: 'absolute', left: 560, top: 525}}>
          {[0, 1].map((k) => {
            const r = ramp(frame, tapAt + k * 5, 20);
            return <div key={k} style={{position: 'absolute', width: 320 * r, height: 320 * r, left: -160 * r, top: -160 * r, borderRadius: '50%', border: `5px solid ${ACCENT}`, opacity: (1 - r) * 0.9}} />;
          })}
        </div>
      )}
      {/* dedo */}
      <div style={{position: 'absolute', left: interpolate(hand, [0, 1], [820, 520]), top: interpolate(hand, [0, 1], [900, 510]) + press * 14, opacity: 1 - ripple * 0}}>
        <Finger />
      </div>
    </div>
  );
};

// Mão estilizada (SVG, clay claro)
export const Finger: React.FC = () => (
  <svg width={190} height={240} viewBox="0 0 190 240" style={{filter: 'drop-shadow(0 30px 30px rgba(0,0,0,.55))'}}>
    <defs>
      <linearGradient id="skin" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0" stopColor="#F4F4F4" />
        <stop offset="1" stopColor="#BFC3C8" />
      </linearGradient>
    </defs>
    <path d="M52 20c0-11 8-18 18-18s18 7 18 18v86l8-2c4-14 30-14 32 2l8-1c6-12 30-10 30 6l6 0c8-8 26-4 26 12v52c0 38-28 62-66 62H98c-24 0-40-10-52-28L10 150c-8-12 4-28 18-22l24 16V20z" fill="url(#skin)" stroke="#9EA3A9" strokeWidth={3} />
    <path d="M60 12c4-4 16-4 20 2" stroke="#FFFFFF" strokeWidth={4} fill="none" strokeLinecap="round" opacity={0.9} />
  </svg>
);

// ---------- Etiqueta de bônus ----------
export const BonusTag: React.FC<{at: number; label: string; tag?: string}> = ({at, label, tag = 'BÔNUS'}) => {
  const frame = useCurrentFrame();
  const p = pop(frame, at, 30, 10);
  if (frame < at) return null;
  return (
    <div style={{display: 'inline-flex', alignItems: 'center', gap: 16, padding: '14px 28px 16px 16px', borderRadius: 999, background: ACCENT, boxShadow: '0 0 50px color-mix(in srgb, var(--accent) 50%, transparent), 0 20px 40px -16px rgba(0,0,0,.6)', transform: `scale(${Math.min(1.2, p)}) rotate(${(1 - Math.min(1, p)) * 10 - 3}deg)`}}>
      <div style={{fontFamily: monoFamily, fontSize: 22, fontWeight: 700, color: ACCENT, background: ACCENT_INK, padding: '6px 14px', borderRadius: 999, letterSpacing: '0.12em'}}>{tag}</div>
      <div style={{fontFamily, fontSize: 36, fontWeight: 700, color: ACCENT_INK, letterSpacing: '-0.02em', whiteSpace: 'nowrap'}}>{label}</div>
    </div>
  );
};

export const Full: React.FC<{children: React.ReactNode; style?: React.CSSProperties}> = ({children, style}) => <AbsoluteFill style={style}>{children}</AbsoluteFill>;

// Chip de fato (número com fonte no roteiro)
export const FactChip: React.FC<{at: number; text: string}> = ({at, text}) => {
  const frame = useCurrentFrame();
  const p = pop(frame, at, 30, 11);
  return (
    <div style={{fontFamily: monoFamily, fontSize: 34, fontWeight: 700, color: '#FAFAFA', background: S1, border: '1px solid color-mix(in srgb, var(--accent) 35%, transparent)', boxShadow: `${darkShadow}, 0 0 40px -10px color-mix(in srgb, var(--accent) 40%, transparent)`, padding: '14px 28px', borderRadius: 999, transform: `scale(${Math.min(1.1, p)}) translateY(${(1 - Math.min(1, p)) * 30}px)`, opacity: frame < at ? 0 : 1}}>
      {text}
    </div>
  );
};
