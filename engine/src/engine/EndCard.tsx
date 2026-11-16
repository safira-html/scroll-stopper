import React from 'react';
import {AbsoluteFill, Img, staticFile, useCurrentFrame} from 'remotion';
import {pop, ramp} from '../lib/anim';
import {DotGrid, Vignette, darkShadow, fontFamily, monoFamily} from '../lib/ui';
import {Dashboard} from '../lib/illustrations';
import {alpha, brand, brandAsset} from '../brand';

const C = brand.colors;
const E = brand.endCard;

const Tile: React.FC<{logo: string; name: string; sub?: string; at: number; fromLeft: boolean}> = ({logo, name, sub, at, fromLeft}) => {
  const frame = useCurrentFrame();
  const p = pop(frame, at, 30, 12);
  return (
    <div
      style={{
        width: 380,
        height: 100,
        borderRadius: 26,
        background: C.dark.surface,
        boxShadow: darkShadow,
        display: 'flex',
        alignItems: 'center',
        gap: 18,
        padding: '0 22px',
        boxSizing: 'border-box',
        opacity: Math.min(1, p * 1.4),
        transform: `translateX(${(1 - p) * (fromLeft ? -300 : 300)}px)`,
      }}
    >
      <div style={{width: 62, height: 62, borderRadius: 16, background: C.dark.surfaceAlt, display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: 'inset 0 1px 0 rgba(255,255,255,.12)'}}>
        <Img src={staticFile(brandAsset(logo))} style={{width: 40, height: 40, objectFit: 'contain'}} />
      </div>
      <div>
        <div style={{fontFamily, fontSize: 34, fontWeight: 700, color: C.dark.text, letterSpacing: '-0.03em', lineHeight: 1}}>{name}</div>
        {sub && <div style={{fontFamily: monoFamily, fontSize: 20, color: C.accent, marginTop: 6}}>{sub}</div>}
      </div>
    </div>
  );
};

// Tela final escura, sem fala, montada a partir de brand.endCard. `start` em frames.
// Tudo entre y≈280 e y≈1180 (margem segura de Reels: 14% em cima, 35% embaixo).
export const EndCard: React.FC<{start: number}> = ({start: s}) => {
  const frame = useCurrentFrame();
  if (frame < s - 1) return null;
  const wipe = ramp(frame, s, 16);
  const title = ramp(frame, s + 8, 12);
  const chips = ramp(frame, s + 46, 14);
  const price = ramp(frame, s + 64, 12);
  const cta = pop(frame, s + 74);
  const pulse = 0.5 + Math.sin(frame / 6) * 0.5;
  const tiles = E.tiles ?? [];
  return (
    <AbsoluteFill style={{clipPath: `circle(${wipe * 2300}px at 540px 960px)`, background: C.dark.bg}}>
      <DotGrid color={alpha(C.accent, 0.1)} />
      {E.backdrop === 'dashboard' && (
        <div style={{position: 'absolute', left: 80, top: 1180, opacity: 0.22, filter: 'blur(6px)', transform: 'scale(1.1) rotate(-6deg)'}}>
          <Dashboard start={s} dark width={920} />
        </div>
      )}
      <Vignette dark />
      <div style={{position: 'absolute', top: 285, width: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 16}}>
        <Img src={staticFile(brandAsset(brand.logos.header))} style={{width: 210, opacity: title}} />
        {E.kicker && <div style={{fontFamily: monoFamily, fontSize: 24, letterSpacing: '0.16em', color: C.accent, opacity: title}}>{E.kicker}</div>}
        <div style={{fontFamily, fontSize: 80, fontWeight: 700, letterSpacing: '-0.04em', lineHeight: 1, color: C.dark.text, textAlign: 'center', opacity: title, transform: `translateY(${(1 - title) * 40}px)`}}>
          {E.title.map((l, i) => (
            <div key={i}>{l}</div>
          ))}
        </div>
        {tiles.length > 0 && (
          <div style={{display: 'grid', gridTemplateColumns: `repeat(${Math.min(2, tiles.length)}, 380px)`, gap: 14, marginTop: 8}}>
            {tiles.map((t, i) => (
              <Tile key={t.name} logo={t.logo} name={t.name} sub={t.sub} at={s + 18 + i * 5} fromLeft={i % 2 === 0} />
            ))}
          </div>
        )}
        {(E.chips ?? []).length > 0 && (
          <div style={{display: 'flex', flexWrap: 'wrap', justifyContent: 'center', gap: 10, width: 800, opacity: chips, transform: `translateY(${(1 - chips) * 20}px)`}}>
            {(E.chips ?? []).map((b) => (
              <div key={b} style={{fontFamily, fontSize: 22, fontWeight: 600, color: C.dark.text, padding: '7px 16px', borderRadius: 999, border: `1px solid ${alpha(C.accent, 0.35)}`, background: alpha(C.accent, 0.08)}}>
                + {b}
              </div>
            ))}
          </div>
        )}
        {E.price && (
          <div style={{fontFamily: monoFamily, fontSize: 34, color: C.dark.text, textAlign: 'center', opacity: price, lineHeight: 1.35}}>
            {E.price}
            {E.priceSub && <div style={{fontSize: 24, color: C.dark.muted}}>{E.priceSub}</div>}
          </div>
        )}
        <div style={{fontFamily, fontSize: 42, fontWeight: 700, color: C.accentInk, background: C.accent, padding: '16px 46px 20px', borderRadius: 999, transform: `scale(${cta})`, boxShadow: `0 0 ${30 + pulse * 40}px ${alpha(C.accent, 0.35 + pulse * 0.3)}`}}>
          {E.cta}
        </div>
      </div>
    </AbsoluteFill>
  );
};
