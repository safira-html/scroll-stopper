import {staticFile} from 'remotion';

export type Word = {w: string; s: number; e: number};
export type Voice = 'f' | 'm';

const norm = (t: string) =>
  t
    .toLowerCase()
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/[^a-z0-9]/g, '');

// Acha uma frase do roteiro na lista de palavras e devolve [primeiro, último] índice.
// Tolera diferenças pequenas de tokenização (hífens, pontuação) e, se não achar a frase
// inteira, ancora na primeira palavra que bater.
export const findPhrase = (words: Word[], phrase: string, from = 0): [number, number] => {
  const toks = phrase.split(/[\s-]+/).map(norm).filter(Boolean);
  const flat = words.map((w) => norm(w.w));
  for (let i = from; i <= flat.length - 1; i++) {
    let k = 0;
    let j = i;
    let acc = '';
    while (k < toks.length && j < flat.length) {
      acc += flat[j];
      const target = toks.slice(0, k + 1).join('');
      if (acc === target) {
        k++;
        j++;
        continue;
      }
      if (target.startsWith(acc)) {
        j++;
        continue;
      }
      break;
    }
    if (k === toks.length) return [i, j - 1];
  }
  const first = flat.indexOf(toks[0], from);
  if (first >= 0) return [first, Math.min(words.length - 1, first + toks.length - 1)];
  // último recurso: não quebra o render
  return [Math.min(from, words.length - 1), Math.min(from + toks.length - 1, words.length - 1)];
};

export const loadWords = async (id: string, voice: Voice): Promise<Word[]> => {
  const res = await fetch(staticFile(`audio/${id}-${voice}.words.json`));
  if (!res.ok) throw new Error(`missing words for ${id}-${voice}`);
  return (await res.json()) as Word[];
};

export const startOf = (words: Word[], i: number) => words[Math.max(0, Math.min(i, words.length - 1))]?.s ?? 0;
export const endOf = (words: Word[], i: number) => words[Math.max(0, Math.min(i, words.length - 1))]?.e ?? 0;
