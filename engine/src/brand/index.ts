// Marca ativa. Troque com `npm run brand -- <pasta-da-marca>` (copia <pasta-da-marca>/brand.json para active.json).
import active from './active.json';

export type ThemeColors = {
  bg: string;
  surface: string;
  surfaceAlt: string;
  text: string;
  muted: string;
  subtle: string;
  line: string;
  corner: string;
  gridAlpha: number;
};

export type Brand = {
  slug: string;
  name: string;
  language: string;
  colors: {
    accent: string;
    accentInk: string;
    accentDisplay: string;
    strike: string;
    danger: string;
    light: ThemeColors;
    dark: ThemeColors;
  };
  fonts: {sans: string; mono: string; display: string};
  logos: {header: string; mark?: string};
  captions: {keepTogether: string[]; weights: [number, number]};
  endCard: {
    kicker?: string;
    title: string[];
    tiles?: Array<{logo: string; name: string; sub?: string}>;
    chips?: string[];
    price?: string;
    priceSub?: string;
    cta: string;
    seconds: number;
    backdrop?: 'dashboard' | 'none';
  };
};

export const brand = active as unknown as Brand;

// "#FF6A3D" + .35 → "rgba(255,106,61,0.35)"
export const alpha = (hex: string, a: number) => {
  const h = hex.replace('#', '');
  const full = h.length === 3 ? h.split('').map((c) => c + c).join('') : h;
  const n = parseInt(full, 16);
  return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`;
};

export const brandAsset = (file: string) => `brand/${file}`;

// Variáveis CSS da marca: os componentes do motor usam var(--accent) etc. em vez de cor fixa.
// Definidas uma vez no documento, ao carregar o bundle (src/index.ts).
export const applyBrandCss = () => {
  if (typeof document === 'undefined') return;
  const c = brand.colors;
  const vars: Record<string, string> = {
    '--accent': c.accent,
    '--accent-ink': c.accentInk,
    '--accent-display': c.accentDisplay,
    '--strike': c.strike,
    '--danger': c.danger,
  };
  for (const [k, v] of Object.entries(vars)) document.documentElement.style.setProperty(k, v);
};
