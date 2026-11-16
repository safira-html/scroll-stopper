// Extrai pistas de design system de um site: variáveis CSS, cores mais usadas, fontes e links do Google Fonts.
// Ponto de partida para o onboarding de marca; confirme o resultado com a pessoa.
// Uso: node tools/extract-site-tokens.mjs <url> [--json]
const url = process.argv[2];
const asJson = process.argv.includes('--json');
if (!url) {
  console.error('Usage: node tools/extract-site-tokens.mjs <url> [--json]');
  process.exit(1);
}

const UA = {'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36'};
const get = async (u) => {
  const res = await fetch(u, {headers: UA, redirect: 'follow', signal: AbortSignal.timeout(15000)});
  if (!res.ok) throw new Error(`${res.status} ${u}`);
  return res.text();
};

let html;
try {
  html = await get(url);
} catch (e) {
  console.error(`Não consegui abrir ${url}: ${e.cause?.code ?? e.message}`);
  process.exit(1);
}
const base = new URL(url);
const sheetUrls = [...html.matchAll(/<link[^>]+rel=["']?stylesheet["']?[^>]*>/gi)]
  .map((m) => m[0].match(/href=["']([^"']+)["']/i)?.[1])
  .filter(Boolean)
  .map((h) => new URL(h.replace(/&amp;/g, '&'), base).href);
const inline = [...html.matchAll(/<style[^>]*>([\s\S]*?)<\/style>/gi)].map((m) => m[1]);

const googleFonts = sheetUrls.filter((u) => u.includes('fonts.googleapis.com'));
const css = [...inline];
const failed = [];
for (const u of sheetUrls.filter((s) => !s.includes('fonts.googleapis.com')).slice(0, 25)) {
  try {
    css.push(await get(u));
  } catch (e) {
    failed.push(String(e.message));
  }
}
const all = css.join('\n') + '\n' + html;

// variáveis CSS com valor de cor ou fonte
const vars = new Map();
for (const m of all.matchAll(/(--[\w-]+)\s*:\s*([^;}{]+)[;}]/g)) {
  const v = m[2].trim();
  // presets padrão do WordPress/Elementor não são da marca
  if (/[<>]/.test(v) || v.length > 200) continue;
  if (/^--(wp--preset|wp-admin|e-global-typography-[a-z]+-font-(size|weight|line))/.test(m[1])) continue;
  if (/#[0-9a-f]{3,8}\b|rgba?\(|hsla?\(|oklch\(|font|serif|sans/i.test(v) || /font|color|bg|text|accent|primary|brand/i.test(m[1])) {
    if (!vars.has(m[1])) vars.set(m[1], v);
  }
}

// frequência de cores
const norm = (c) => {
  let h = c.toLowerCase();
  if (/^#[0-9a-f]{3}$/.test(h)) h = '#' + [...h.slice(1)].map((x) => x + x).join('');
  return h.length === 9 ? h.slice(0, 7) : h;
};
const colors = new Map();
for (const m of all.matchAll(/#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b|rgba?\([^)]+\)/g)) {
  const c = m[0].startsWith('#') ? norm(m[0]) : m[0].replace(/\s+/g, '');
  colors.set(c, (colors.get(c) ?? 0) + 1);
}
const topColors = [...colors.entries()].sort((a, b) => b[1] - a[1]).slice(0, 24);

// famílias de fonte
const fonts = new Map();
for (const m of all.matchAll(/font-family\s*:\s*([^;}{]+)/gi)) {
  const f = m[1].trim().replace(/!important/, '').trim();
  fonts.set(f, (fonts.get(f) ?? 0) + 1);
}
const topFonts = [...fonts.entries()].sort((a, b) => b[1] - a[1]).slice(0, 10);
const gfFamilies = googleFonts.flatMap((u) => [...new URL(u).searchParams.getAll('family')].map((f) => f.split(':')[0].replace(/\+/g, ' ')));

const theme = html.match(/<meta[^>]+name=["']theme-color["'][^>]+content=["']([^"']+)/i)?.[1];
const result = {url, themeColor: theme ?? null, googleFonts: gfFamilies, fonts: topFonts, cssVariables: Object.fromEntries(vars), topColors, stylesheets: sheetUrls.length, failed};

if (asJson) {
  console.log(JSON.stringify(result, null, 2));
} else {
  console.log(`Site: ${url}`);
  if (theme) console.log(`theme-color: ${theme}`);
  console.log(`\nGoogle Fonts: ${gfFamilies.join(', ') || '(nenhum link)'}`);
  console.log('\nfont-family mais usados:');
  for (const [f, n] of topFonts) console.log(`  ${n}×  ${f}`);
  console.log('\nVariáveis CSS (cor/fonte):');
  for (const [k, v] of [...vars.entries()].slice(0, 60)) console.log(`  ${k}: ${v}`);
  console.log('\nCores mais frequentes:');
  for (const [c, n] of topColors) console.log(`  ${String(n).padStart(4)}×  ${c}`);
  if (failed.length) console.log(`\nNão consegui ler: ${failed.join('; ')}`);
  console.log('\nConfirme com a pessoa: qual é o fundo, o texto e o destaque (accent).');
}
