// Ativa uma marca: copia brand.json para o engine, gera o carregamento de fontes e copia os assets.
// Uso: node scripts/use-brand.mjs <pasta-da-marca>
// A pasta pode ser absoluta ou relativa ao diretório atual; precisa ter brand.json (e, opcionalmente, assets/).
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const app = path.resolve(here, '..');
const arg = process.argv[2];

const fail = (message) => {
  console.error(`[!!] ${message}`);
  process.exit(1);
};

if (!arg) fail('Uso: node scripts/use-brand.mjs <pasta-da-marca> (caminho absoluto ou relativo ao diretório atual)');

const brandDir = path.resolve(process.cwd(), arg);
const brandFile = path.join(brandDir, 'brand.json');
if (!fs.existsSync(brandFile)) {
  fail(`brand.json não encontrado em ${brandFile}. Confira o caminho da pasta da marca (ela precisa ter um brand.json).`);
}
let brand;
try {
  brand = JSON.parse(fs.readFileSync(brandFile, 'utf8'));
} catch (err) {
  fail(`brand.json inválido em ${brandFile}: ${err.message}`);
}

// Fontes: nome do Google Fonts ("Instrument Serif") vira o módulo do @remotion/google-fonts ("InstrumentSerif")
const fontsDir = path.join(app, 'node_modules/@remotion/google-fonts/dist/esm');
const moduleOf = (name) => name.replace(/[^A-Za-z0-9]/g, '');
const roles = ['sans', 'mono', 'display'];
for (const role of roles) {
  const name = brand.fonts?.[role];
  if (!name) fail(`brand.fonts.${role} não está definido em ${brandFile}`);
  // sem node_modules (engine ainda não instalado) a checagem é pulada
  if (fs.existsSync(fontsDir) && !fs.existsSync(path.join(fontsDir, `${moduleOf(name)}.mjs`))) {
    fail(`A fonte "${name}" não está no Google Fonts (módulo ${moduleOf(name)} não encontrado). Escolha outra no brand.json.`);
  }
}
const fontsTs = [
  '// Gerado por scripts/use-brand.mjs. Não edite à mão.',
  ...roles.map((r, i) => `import {loadFont as load${i}} from '@remotion/google-fonts/${moduleOf(brand.fonts[r])}';`),
  '',
  ...roles.map((r, i) => `export const ${r}Family = load${i}().fontFamily;`),
  '',
].join('\n');

const brandSrc = path.join(app, 'src/brand');
fs.mkdirSync(brandSrc, {recursive: true});
fs.writeFileSync(path.join(brandSrc, 'active.json'), JSON.stringify(brand, null, 2) + '\n');
fs.writeFileSync(path.join(brandSrc, 'fonts.ts'), fontsTs);

// Assets da marca (logos, ícones) ficam em public/brand/
const assetsSrc = path.join(brandDir, 'assets');
const assetsDst = path.join(app, 'public/brand');
fs.rmSync(assetsDst, {recursive: true, force: true});
fs.mkdirSync(assetsDst, {recursive: true});
if (fs.existsSync(assetsSrc)) fs.cpSync(assetsSrc, assetsDst, {recursive: true});

console.log(`Marca ativa: ${brand.name} (${brandDir})`);
