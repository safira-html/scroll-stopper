// Tokens da marca ativa (src/brand/active.json), no formato que os anúncios de exemplo usam
import {alpha, brand} from './brand';

const c = brand.colors;

export const light = {
  bg: c.light.bg,
  surface: c.light.surface,
  surface3: c.light.surfaceAlt,
  text: c.light.text,
  muted: c.light.muted,
  subtle: c.light.subtle,
  line: c.light.line,
  accentDisplay: c.accentDisplay,
  dot: alpha(c.accentDisplay, 0.16),
  strike: c.strike,
};

export const dark = {
  bg: c.dark.bg,
  surface1: c.dark.surface,
  surface2: c.dark.surfaceAlt,
  text: c.dark.text,
  muted: c.dark.muted,
  line: c.dark.line,
  line2: 'rgba(255,255,255,.14)',
  dot: alpha(c.accent, 0.1),
  glow: alpha(c.accent, 0.35),
};

export const accent = c.accent;
export const accentInk = c.accentInk;
