// Blocos de legenda montados direto das palavras (para clipes sem legenda escrita à mão).
// Cada bloco tem 2–4 palavras e fecha numa pontuação; nunca sobra uma palavra sozinha no fim.
// Só imports de tipo: o arquivo roda também fora do Remotion (teste com node --experimental-strip-types).
import type {Word} from '../engine/words';
import type {Chunk} from '../kit';

const BREAK_AFTER = /[.,;:!?…]["'”’)]*$/;

export const autoChunks = (words: Word[], min = 2, max = 4): Chunk[] => {
  const groups: string[][] = [];
  let cur: string[] = [];
  for (const word of words) {
    const text = word.w.trim();
    if (!text) continue;
    cur.push(text);
    if (cur.length >= max || (cur.length >= min && BREAK_AFTER.test(text))) {
      groups.push(cur);
      cur = [];
    }
  }
  if (cur.length) groups.push(cur);
  // palavra solta no fim: junta ao bloco anterior ou pega uma palavra emprestada dele
  const last = groups[groups.length - 1];
  const prev = groups[groups.length - 2];
  if (last && prev && last.length < min) {
    if (prev.length + last.length <= max) {
      prev.push(...last);
      groups.pop();
    } else {
      last.unshift(...prev.splice(prev.length - (min - last.length)));
    }
  }
  return groups.map((g) => ({p: g.join(' ')}));
};
