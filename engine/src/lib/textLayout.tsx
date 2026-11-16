import React from 'react';
import {brand} from '../brand';

// Quebra de linha decidida antes da animação, com a largura final (peso cheio) de cada palavra.
// Assim nenhuma palavra muda de linha quando o peso cresce no karaokê, e evitamos viúvas
// (palavra sozinha numa linha) e preposição/artigo pendurado no fim da linha.

let ctx: CanvasRenderingContext2D | null = null;
const cache = new Map<string, number>();
const measure = (text: string, font: string, letterSpacingPx: number) => {
  if (typeof document === 'undefined') return text.length * 30;
  const key = `${font}|${letterSpacingPx}|${text}`;
  const hit = cache.get(key);
  if (hit !== undefined) return hit;
  if (!ctx) ctx = document.createElement('canvas').getContext('2d');
  if (!ctx) return text.length * 30;
  ctx.font = font;
  const w = ctx.measureText(text).width + letterSpacingPx * text.length;
  cache.set(key, w);
  return w;
};

export type MeasureSpec = {family: string; size: number; weight: number; letterSpacingEm: number};

export const wordWidth = (text: string, m: MeasureSpec) =>
  measure(text, `${m.weight} ${m.size}px "${m.family.replace(/"/g, '')}"`, m.letterSpacingEm * m.size);

// Palavras que não devem ficar no fim de uma linha (pt-BR)
const WEAK = new Set(['a', 'o', 'as', 'os', 'e', 'de', 'do', 'da', 'dos', 'das', 'em', 'no', 'na', 'nos', 'nas', 'um', 'uma', 'pra', 'para', 'por', 'com', 'que', 'se', 'ou', 'ao', 'à']);
const bare = (w: string) => w.toLowerCase().replace(/[^a-zà-ú]/g, '');

// Nomes que não se quebram no meio (produto, marca, ferramentas, CTA)
const NAMES = brand.captions.keepTogether.map((n) => n.split(/\s+/).map(bare));
const splitsName = (labels: string[], s: number) =>
  NAMES.some((name) => {
    for (let k = 1; k < name.length; k++) {
      const a = s - k;
      if (a < 0 || a + name.length > labels.length) continue;
      if (name.every((p, j) => bare(labels[a + j]) === p)) return true;
    }
    return false;
  });

// units: larguras de cada unidade inseparável; gap: espaço entre unidades.
// Devolve os índices onde cada linha começa.
export const breakLines = (units: number[], gap: number, maxWidth: number, labels?: string[]): number[] => {
  const n = units.length;
  const lineW = (a: number, b: number) => {
    let w = 0;
    for (let i = a; i <= b; i++) w += units[i] + (i < b ? gap : 0);
    return w;
  };
  if (n <= 1 || lineW(0, n - 1) <= maxWidth) return [0];
  let best: {starts: number[]; cost: number} | null = null;
  let fallback: number[] | null = null;
  // tenta 2, 3 e 4 linhas; aceita a menor contagem que tenha solução sem viúva
  for (let lines = 2; lines <= Math.min(4, n); lines++) {
    const search = (start: number, left: number, acc: number[]): void => {
      if (left === 1) {
        const starts = [...acc, start];
        const widths = starts.map((s, i) => lineW(s, (starts[i + 1] ?? n) - 1));
        if (widths.some((w) => w > maxWidth)) return;
        const counts = starts.map((s, i) => (starts[i + 1] ?? n) - s);
        const widow = counts.some((c) => c < 2) ? 1 : 0;
        const weak = labels ? starts.slice(1).filter((s) => WEAK.has(bare(labels[s - 1])) || splitsName(labels, s)).length : 0;
        const max = Math.max(...widths);
        const min = Math.min(...widths);
        // linha de baixo um pouco mais curta que a de cima lê melhor (pirâmide invertida suave)
        const shape = widths[widths.length - 1] > widths[0] * 1.15 ? 0.15 : 0;
        const cost = widow * 1000 + weak * 50 + (max - min) / maxWidth + shape;
        if (!best || cost < best.cost) best = {starts, cost};
        return;
      }
      for (let next = start + 1; next <= n - left + 1; next++) {
        if (lineW(start, next - 1) > maxWidth) break;
        search(next, left - 1, [...acc, start]);
      }
    };
    best = null;
    search(0, lines, []);
    if (best && (best as {cost: number}).cost < 1000) return (best as {starts: number[]}).starts;
    // sem solução sem viúva: guarda a de menos linhas (não espalha uma palavra por linha)
    if (best && !fallback) fallback = (best as {starts: number[]}).starts;
  }
  if (fallback) return fallback;
  // nada coube: uma unidade por linha
  return units.map((_, i) => i);
};

// Palavra do karaokê. A linha já está fixada por breakLines (calculada no peso final),
// então o espaçamento pode ser natural: a linha só alarga um pouco enquanto o peso cresce,
// sem nunca mudar a quebra. Travar a largura de cada palavra deixava buracos entre as finas.
export const StableWord: React.FC<{
  text: string;
  finalWeight: number;
  style?: React.CSSProperties;
  boxStyle?: React.CSSProperties;
}> = ({text, style, boxStyle}) => <span style={{display: 'inline-block', ...boxStyle, ...style}}>{text}</span>;

// Agrupa itens em linhas a partir dos inícios devolvidos por breakLines
export const toRows = <T,>(items: T[], starts: number[]): T[][] => starts.map((s, i) => items.slice(s, starts[i + 1] ?? items.length));
