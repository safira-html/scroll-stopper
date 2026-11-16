import React from 'react';
import {Img, interpolate, staticFile, useCurrentFrame} from 'remotion';
import {AppWindow, ClayCard, fontFamily, monoFamily} from './ui';
import {pop, ramp} from './anim';

const ACCENT = 'var(--accent)';
const INK = '#1A1A1A';

// ---------- Editor de código com digitação e erro ----------
const CODE = [
  [{t: 'const ', c: 'var(--accent)'}, {t: 'items ', c: '#FAFAFA'}, {t: '= ', c: '#9A9A9A'}, {t: 'await ', c: 'var(--accent)'}, {t: 'load', c: '#8AB4FF'}, {t: '(', c: '#9A9A9A'}, {t: '"lista"', c: '#F4C62E'}, {t: ');', c: '#9A9A9A'}],
  [{t: 'const ', c: 'var(--accent)'}, {t: 'total ', c: '#FAFAFA'}, {t: '= items.', c: '#9A9A9A'}, {t: 'length', c: '#8AB4FF'}, {t: ';', c: '#9A9A9A'}],
  [{t: 'console.', c: '#9A9A9A'}, {t: 'log', c: '#8AB4FF'}, {t: '(', c: '#9A9A9A'}, {t: '"total:"', c: '#F4C62E'}, {t: ', total', c: '#FAFAFA'}],
];

export const CodeEditor: React.FC<{start: number; errorAt: number}> = ({start, errorAt}) => {
  const frame = useCurrentFrame();
  const totalChars = CODE.flat().reduce((n, tok) => n + tok.t.length, 0);
  const typed = Math.floor(interpolate(frame, [start, start + 30], [0, totalChars], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}));
  let budget = typed;
  const err = pop(frame, errorAt);
  const shake = frame >= errorAt && frame < errorAt + 10 ? Math.sin((frame - errorAt) * 2.6) * (10 - (frame - errorAt)) * 1.6 : 0;
  return (
    <div style={{position: 'relative', transform: `translateX(${shake}px)`}}>
      <AppWindow width={860} height={520} title="index.ts" dark>
        <div style={{display: 'flex', height: '100%'}}>
          <div style={{width: 70, padding: '30px 0', fontFamily: monoFamily, fontSize: 28, color: '#4A4A4A', textAlign: 'right', lineHeight: '56px'}}>
            {[1, 2, 3, 4, 5].map((n) => (
              <div key={n} style={{paddingRight: 16}}>{n}</div>
            ))}
          </div>
          <div style={{padding: '30px 24px', fontFamily: monoFamily, fontSize: 30, lineHeight: '56px'}}>
            {CODE.map((line, li) => (
              <div key={li} style={{whiteSpace: 'pre'}}>
                {line.map((tok, ti) => {
                  const shown = tok.t.slice(0, Math.max(0, budget));
                  budget -= tok.t.length;
                  return (
                    <span key={ti} style={{color: tok.c}}>
                      {shown}
                    </span>
                  );
                })}
                {/* cursor piscando na linha ativa */}
                {li === 2 && (
                  <span style={{display: 'inline-block', width: 16, height: 36, background: ACCENT, verticalAlign: 'middle', opacity: Math.floor(frame / 8) % 2 ? 1 : 0.2}} />
                )}
              </div>
            ))}
          </div>
        </div>
      </AppWindow>
      {/* Toast de erro */}
      <div
        style={{
          position: 'absolute',
          left: 70,
          right: 70,
          bottom: -70,
          borderRadius: 22,
          background: '#2A1416',
          border: '2px solid #F5737A',
          boxShadow: '0 30px 60px -20px rgba(0,0,0,.6), 0 0 40px rgba(245,115,122,.35)',
          padding: '22px 28px',
          fontFamily: monoFamily,
          fontSize: 26,
          color: '#F5737A',
          opacity: Math.min(1, err),
          transform: `translateY(${(1 - err) * 60}px) scale(${0.9 + err * 0.1})`,
        }}
      >
        <div style={{fontWeight: 700}}>SyntaxError</div>
        <div style={{color: '#FFB3B7'}}>missing ) after argument list</div>
      </div>
    </div>
  );
};

// ---------- Ladrilhos de fórmulas que explodem e caem ----------
const SYMBOLS = ['Σ', '√x', 'σ²', '∫dx', 'π', 'x̄', '%', 'Δ'];
export const MathTiles: React.FC<{start: number; fallAt: number}> = ({start, fallAt}) => {
  const frame = useCurrentFrame();
  return (
    <div style={{position: 'relative', width: 900, height: 820}}>
      {SYMBOLS.map((sym, i) => {
        const angle = (i / SYMBOLS.length) * Math.PI * 2 + frame * 0.006;
        const radius = 300 + (i % 2) * 60;
        const p = pop(frame, start + i * 2, 30, 10);
        const fall = ramp(frame, fallAt + (i % 4) * 2, 18);
        const x = 450 + Math.cos(angle) * radius * p - 85;
        const y = 410 + Math.sin(angle) * radius * 0.78 * p - 85 + fall * 900;
        const rot = Math.sin(frame / 20 + i) * 8 + fall * (i % 2 ? 90 : -90);
        return (
          <ClayCard
            key={sym}
            style={{
              position: 'absolute',
              left: x,
              top: y,
              width: 170,
              height: 170,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transform: `rotate(${rot}deg) scale(${p})`,
              fontFamily: monoFamily,
              fontSize: 64,
              fontWeight: 700,
              color: i % 3 === 0 ? 'var(--accent-display)' : INK,
              opacity: 1 - fall * 0.6,
            }}
          >
            {sym}
          </ClayCard>
        );
      })}
      {/* Calculadora central */}
      <ClayCard
        style={{
          position: 'absolute',
          left: 330,
          top: 260,
          width: 240,
          height: 300,
          padding: 22,
          boxSizing: 'border-box',
          transform: `scale(${pop(frame, start)}) translateY(${ramp(frame, fallAt, 18) * 900}px) rotate(${ramp(frame, fallAt, 18) * 30}deg)`,
        }}
      >
        <div style={{height: 74, borderRadius: 14, background: INK, color: ACCENT, fontFamily: monoFamily, fontSize: 40, display: 'flex', alignItems: 'center', justifyContent: 'flex-end', padding: '0 16px'}}>
          {frame % 20 < 10 ? '?' : 'ERR'}
        </div>
        <div style={{display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10, marginTop: 14}}>
          {Array.from({length: 9}).map((_, k) => (
            <div key={k} style={{height: 50, borderRadius: 12, background: k === 8 ? ACCENT : '#F2F3F5', boxShadow: 'inset 0 -3px 0 rgba(26,26,26,.08)'}} />
          ))}
        </div>
      </ClayCard>
    </div>
  );
};

// ---------- Calendário com anos passando + relógio ----------
export const AgeCalendar: React.FC<{start: number; end: number}> = ({start, end}) => {
  const frame = useCurrentFrame();
  const year = Math.round(interpolate(frame, [start, end - 8], [2004, 2026], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: (t) => 1 - Math.pow(1 - t, 3)}));
  const flip = (frame % 4) / 4;
  const p = pop(frame, start);
  const handA = frame * 24;
  const handB = frame * 2;
  return (
    <div style={{position: 'relative', width: 900, height: 760}}>
      <ClayCard
        style={{
          position: 'absolute',
          left: 110,
          top: 80,
          width: 460,
          height: 540,
          overflow: 'hidden',
          transform: `scale(${p}) rotate(-4deg)`,
        }}
      >
        <div style={{height: 120, background: INK, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 120}}>
          {[0, 1].map((k) => (
            <div key={k} style={{width: 28, height: 70, borderRadius: 14, background: '#3D3D3D', marginTop: -70, boxShadow: 'inset 0 -6px 0 #2a2a2a'}} />
          ))}
        </div>
        <div style={{fontFamily: monoFamily, fontSize: 30, letterSpacing: '0.2em', color: '#6E6E73', textAlign: 'center', marginTop: 34}}>ANO</div>
        <div
          style={{
            fontFamily,
            fontSize: 150,
            fontWeight: 700,
            letterSpacing: '-0.05em',
            textAlign: 'center',
            color: INK,
            transform: `perspective(600px) rotateX(${year < 2026 ? flip * 40 : 0}deg)`,
          }}
        >
          {year}
        </div>
        <div style={{display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: 8, padding: '0 40px'}}>
          {Array.from({length: 14}).map((_, k) => (
            <div key={k} style={{height: 26, borderRadius: 6, background: k === 10 ? ACCENT : '#F2F3F5'}} />
          ))}
        </div>
      </ClayCard>
      {/* Relógio */}
      <ClayCard
        style={{
          position: 'absolute',
          left: 500,
          top: 330,
          width: 330,
          height: 330,
          borderRadius: 165,
          transform: `scale(${pop(frame, start + 6)}) rotate(6deg)`,
        }}
      >
        <svg width={330} height={330} viewBox="0 0 330 330">
          {Array.from({length: 12}).map((_, k) => {
            const a = (k / 12) * Math.PI * 2;
            return <rect key={k} x={165 + Math.sin(a) * 120 - 4} y={165 - Math.cos(a) * 120 - 12} width={8} height={24} rx={4} fill={k % 3 === 0 ? INK : '#C9CCD1'} transform={`rotate(${(k / 12) * 360} ${165 + Math.sin(a) * 120} ${165 - Math.cos(a) * 120})`} />;
          })}
          <line x1={165} y1={165} x2={165} y2={70} stroke={INK} strokeWidth={10} strokeLinecap="round" transform={`rotate(${handB} 165 165)`} />
          <line x1={165} y1={165} x2={165} y2={50} stroke="var(--strike)" strokeWidth={5} strokeLinecap="round" transform={`rotate(${handA} 165 165)`} />
          <circle cx={165} cy={165} r={14} fill={ACCENT} stroke={INK} strokeWidth={4} />
        </svg>
      </ClayCard>
    </div>
  );
};

// ---------- Celular com as objeções como mensagens ----------
export const PhoneChat: React.FC<{
  bubbles: Array<{text: string; at: number}>;
  pushAway: number;
}> = ({bubbles, pushAway}) => {
  const frame = useCurrentFrame();
  const away = ramp(frame, pushAway, 14);
  return (
    <div
      style={{
        width: 560,
        height: 1080,
        borderRadius: 86,
        background: '#0E0E0E',
        padding: 22,
        boxSizing: 'border-box',
        boxShadow: '0 60px 120px -30px rgba(26,26,26,.45), inset 0 0 0 3px #2B2B2B',
        transform: `perspective(1600px) rotateY(${-away * 28}deg) translateX(${-away * 260}px) scale(${1 - away * 0.12})`,
        filter: `blur(${away * 5}px)`,
        opacity: 1 - away * 0.45,
      }}
    >
      <div style={{width: '100%', height: '100%', borderRadius: 66, background: '#F2F3F5', overflow: 'hidden', position: 'relative'}}>
        <div style={{position: 'absolute', top: 18, left: '50%', width: 160, height: 44, marginLeft: -80, borderRadius: 22, background: '#0E0E0E'}} />
        <div style={{display: 'flex', justifyContent: 'space-between', padding: '24px 44px 0', fontFamily, fontSize: 24, fontWeight: 700, color: INK}}>
          <span>22:47</span>
          <span>●●● ▮</span>
        </div>
        <div style={{display: 'flex', alignItems: 'center', gap: 16, padding: '36px 30px 24px', borderBottom: '1px solid #E3E5E9', background: '#FFFFFF'}}>
          <div style={{width: 62, height: 62, borderRadius: 31, background: INK, color: ACCENT, fontFamily, fontWeight: 700, fontSize: 28, display: 'flex', alignItems: 'center', justifyContent: 'center'}}>?</div>
          <div style={{fontFamily}}>
            <div style={{fontSize: 28, fontWeight: 700, color: INK}}>Eu</div>
            <div style={{fontSize: 20, color: '#6E6E73'}}>pensando em mudar de área…</div>
          </div>
        </div>
        <div style={{padding: '40px 28px', display: 'flex', flexDirection: 'column', gap: 22, alignItems: 'flex-end'}}>
          {bubbles.map((b, i) => {
            const p = pop(frame, b.at, 30, 12);
            return (
              <div
                key={i}
                style={{
                  maxWidth: 400,
                  background: INK,
                  color: '#FAFAFA',
                  fontFamily,
                  fontSize: 32,
                  fontWeight: 600,
                  padding: '20px 26px',
                  borderRadius: '30px 30px 8px 30px',
                  transform: `scale(${p}) translateY(${(1 - p) * 30}px)`,
                  transformOrigin: 'bottom right',
                  boxShadow: '0 12px 24px -12px rgba(26,26,26,.4)',
                }}
              >
                {b.text}
              </div>
            );
          })}
          <div style={{fontFamily, fontSize: 20, color: '#6E6E73', opacity: ramp(frame, bubbles[bubbles.length - 1].at + 6, 6)}}>Lida 22:47</div>
        </div>
      </div>
    </div>
  );
};

// ---------- Dashboard detalhado (dados ilustrativos) ----------
const BARS = [38, 44, 41, 52, 49, 58, 63, 60, 71, 76, 82, 90];
export const Dashboard: React.FC<{start: number; dark?: boolean; width?: number}> = ({start, dark, width = 900}) => {
  const frame = useCurrentFrame();
  const text = dark ? '#FAFAFA' : INK;
  const muted = dark ? '#9A9A9A' : '#6E6E73';
  const card = dark ? '#1F1F1F' : '#F7F8FA';
  const line = ramp(frame, start + 18, 30);
  const donut = ramp(frame, start + 14, 26);
  const kpis = [
    {k: 'Visitas', v: '12,4 mil', d: '+18%'},
    {k: 'Conversão', v: '3,1%', d: '+9%'},
    {k: 'Leads', v: '842', d: '+6%'},
  ];
  const pts = BARS.map((b, i) => `${30 + i * 50},${230 - b * 2}`).join(' ');
  return (
    <AppWindow width={width} height={width * 0.68} title="painel" dark={dark}>
      <div style={{padding: 30, display: 'flex', flexDirection: 'column', gap: 24}}>
        <div style={{display: 'flex', gap: 18}}>
          {kpis.map((k, i) => {
            const p = pop(frame, start + 4 + i * 3);
            return (
              <div key={k.k} style={{flex: 1, borderRadius: 20, background: card, padding: '18px 20px', transform: `scale(${p})`, border: dark ? '1px solid rgba(255,255,255,.06)' : '1px solid #ECEEF1'}}>
                <div style={{fontFamily, fontSize: 20, color: muted}}>{k.k}</div>
                <div style={{fontFamily, fontSize: 36, fontWeight: 700, color: text, letterSpacing: '-0.03em'}}>{k.v}</div>
                <div style={{fontFamily: monoFamily, fontSize: 18, color: 'var(--accent-display)', fontWeight: 700}}>▲ {k.d}</div>
              </div>
            );
          })}
        </div>
        <div style={{display: 'flex', gap: 18}}>
          <div style={{flex: 2.2, borderRadius: 20, background: card, padding: 18, border: dark ? '1px solid rgba(255,255,255,.06)' : '1px solid #ECEEF1'}}>
            <div style={{fontFamily, fontSize: 20, fontWeight: 700, color: text, marginBottom: 8}}>Visitas por mês</div>
            <svg width="100%" height={250} viewBox="0 0 620 250">
              {BARS.map((b, i) => {
                const g = ramp(frame, start + 8 + i * 1.5, 14);
                const h = b * 2 * g;
                return <rect key={i} x={12 + i * 50} y={235 - h} width={34} height={h} rx={8} fill={i === BARS.length - 1 ? 'var(--accent)' : dark ? '#3D3D3D' : '#D9DDE3'} />;
              })}
              <polyline points={pts} fill="none" stroke="var(--accent-display)" strokeWidth={5} strokeLinejoin="round" strokeLinecap="round" strokeDasharray={900} strokeDashoffset={900 * (1 - line)} />
            </svg>
          </div>
          <div style={{flex: 1, borderRadius: 20, background: card, padding: 18, display: 'flex', flexDirection: 'column', alignItems: 'center', border: dark ? '1px solid rgba(255,255,255,.06)' : '1px solid #ECEEF1'}}>
            <div style={{fontFamily, fontSize: 20, fontWeight: 700, color: text, alignSelf: 'flex-start'}}>Por canal</div>
            <svg width={200} height={200} viewBox="0 0 200 200" style={{marginTop: 14}}>
              <circle cx={100} cy={100} r={70} fill="none" stroke={dark ? '#313131' : '#ECEEF1'} strokeWidth={30} />
              {[
                {v: 0.42, c: 'var(--accent)'},
                {v: 0.28, c: 'var(--accent-display)'},
                {v: 0.18, c: dark ? '#9A9A9A' : '#1A1A1A'},
              ].reduce<{acc: number; els: React.ReactNode[]}>(
                (state, seg, i) => {
                  const len = 2 * Math.PI * 70;
                  state.els.push(
                    <circle key={i} cx={100} cy={100} r={70} fill="none" stroke={seg.c} strokeWidth={30} strokeDasharray={`${len * seg.v * donut} ${len}`} strokeDashoffset={-len * state.acc * donut} transform="rotate(-90 100 100)" />,
                  );
                  state.acc += seg.v;
                  return state;
                },
                {acc: 0, els: []},
              ).els}
            </svg>
          </div>
        </div>
      </div>
    </AppWindow>
  );
};

// ---------- Cartão de ferramenta para a lista da tela final ----------
export const ToolCard: React.FC<{logo: string; name: string; verb: string; at: number}> = ({logo, name, verb, at}) => {
  const frame = useCurrentFrame();
  const p = pop(frame, at, 30, 12);
  return (
    <ClayCard
      dark
      style={{
        width: 700,
        height: 128,
        display: 'flex',
        alignItems: 'center',
        gap: 30,
        padding: '0 34px',
        boxSizing: 'border-box',
        transform: `translateX(${(1 - p) * 500}px) rotate(${(1 - p) * 4}deg)`,
        opacity: Math.min(1, p * 1.4),
      }}
    >
      <div style={{width: 78, height: 78, borderRadius: 20, background: '#313131', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: 'inset 0 1px 0 rgba(255,255,255,.12)'}}>
        <Img src={staticFile(`brand/${logo}.svg`)} style={{width: 50, height: 50, objectFit: 'contain'}} />
      </div>
      <div style={{fontFamily, fontSize: 44, fontWeight: 700, color: '#FAFAFA', letterSpacing: '-0.03em', flex: 1}}>{name}</div>
      <div style={{fontFamily: monoFamily, fontSize: 24, color: 'var(--accent)'}}>{verb}</div>
    </ClayCard>
  );
};
