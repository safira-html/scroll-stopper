import React from 'react';
import {Composition, CalculateMetadataFunction} from 'remotion';
import {AdProps} from './engine/AdShell';
import {loadWords, Voice} from './engine/words';
import {ADS, AdEntry, DEFAULT_TAIL} from './ads';
import {demoWords} from './ads/Template';

const ENTRIES: AdEntry[] = ADS;
const DEMO = new Map(ENTRIES.filter((e) => e.demoScript).map((e) => [e.id, e.demoScript as string]));
const TAILS = new Map(ENTRIES.map((e) => [e.id, e.tail ?? DEFAULT_TAIL]));

// Carrega as palavras da fala e calcula a duração (fala + respiro + tela final ou saída)
const withWords: CalculateMetadataFunction<AdProps> = async ({props}) => {
  let words;
  try {
    words = await loadWords(props.id, props.voice);
  } catch {
    const demo = DEMO.get(props.id);
    if (!demo) return {durationInFrames: 30 * 40, props: {...props, words: []}};
    words = demoWords(demo);
  }
  const end = words[words.length - 1].e;
  return {durationInFrames: Math.ceil((end + (TAILS.get(props.id) ?? DEFAULT_TAIL)) * 30), props: {...props, words}};
};

export const Root: React.FC = () => (
  <>
    {ENTRIES.flatMap(({id, component, voices}) =>
      (voices ?? (['f', 'm'] as Voice[])).map((voice) => (
        <Composition
          key={`${id}-${voice}`}
          id={`${id}-${voice}`}
          component={component}
          fps={30}
          width={1080}
          height={1920}
          durationInFrames={1200}
          defaultProps={{id, voice, words: []}}
          calculateMetadata={withWords}
        />
      )),
    )}
  </>
);
