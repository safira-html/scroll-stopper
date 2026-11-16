import React from 'react';
import {useCurrentFrame} from 'remotion';
import {AdProps, AdShell, Scene} from '../engine/AdShell';
import {Captions, Center, CtaTap, FactChip, ProductCard, makeCues} from '../kit';
import {pop, sec} from '../lib/anim';
import {ClayCard} from '../lib/ui';
import {Dashboard} from '../lib/illustrations';
import {Word} from '../engine/words';

// Anúncio-modelo: Gancho → Conteúdo → Produto → CTA, com cenas amarradas a frases da narração.
// Copie este arquivo para src/ads/<Id>.tsx, troque SCRIPT pelo roteiro e registre em src/ads/index.ts.
// Sem narração gerada, usa tempos de demonstração (0,34 s por palavra) para você ver o ritmo.

export const SCRIPT =
  'Seu cliente decide em três segundos. Mostre o problema, a solução e o resultado. É isso que faz alguém parar de rolar. Toque em Saiba Mais.';

export const demoWords = (text: string, perWord = 0.34, startAt = 0.4): Word[] =>
  text.split(/\s+/).map((w, i) => ({w, s: +(startAt + i * perWord).toFixed(2), e: +(startAt + (i + 1) * perWord - 0.04).toFixed(2)}));

export const Template: React.FC<AdProps> = (props) => {
  const frame = useCurrentFrame();
  const words = props.words.length ? props.words : demoWords(SCRIPT);
  const p = {...props, words};
  const c = makeCues(words);

  // Cada cena começa e termina numa frase falada, nunca em segundos fixos
  const s1 = c.s('Seu cliente decide');
  const s2 = c.s('Mostre o problema');
  // As cues são buscadas na ordem da fala (cursor sequencial): marque aqui, antes da cena seguinte,
  // as palavras usadas dentro da cena.
  const chips = [c.w('Mostre o problema', 2), c.w('a solução', 1), c.w('e o resultado', 2)];
  const s3 = c.s('É isso que faz');
  // A frase do CTA é a mesma de brand.endCard.cta; "Saiba Mais" fica em brand.captions.keepTogether
  // para a legenda não quebrar o botão em duas linhas. Se trocar o CTA da marca, troque aqui e no SCRIPT.
  const s4 = c.s('Toque em Saiba Mais');

  return (
    <AdShell props={p} theme="light" sfx={[{at: s2, name: 'whoosh-short', volume: 0.35}, {at: s3, name: 'pop-soft', volume: 0.35}]}>
      {/* Gancho: objeto concreto no primeiro quadro, nada de texto sozinho */}
      <Scene from={s1} to={s2} theme="light" set={0}>
        <Center top={760}>
          <div style={{transform: `scale(${Math.min(1, pop(frame, 0))})`}}>
            <ClayCard style={{width: 860, padding: 20}}>
              <Dashboard start={0} width={820} />
            </ClayCard>
          </div>
        </Center>
      </Scene>
      {/* Conteúdo: microeventos a cada 0,3–0,6 s */}
      <Scene from={s2} to={s3} theme="light" set={1}>
        <Center top={760}>
          <div style={{display: 'flex', flexDirection: 'column', gap: 22, alignItems: 'center'}}>
            <FactChip at={sec(chips[0])} text="problema" />
            <FactChip at={sec(chips[1])} text="solução" />
            <FactChip at={sec(chips[2])} text="resultado" />
          </div>
        </Center>
      </Scene>
      {/* Produto: vira para o tema escuro quando a oferta entra */}
      <Scene from={s3} to={s4} theme="dark" set={2}>
        <Center top={640}>
          <ProductCard start={sec(s3)} />
        </Center>
      </Scene>
      <Scene from={s4} to={c.end} theme="dark" set={3}>
        <Center top={760}>
          <CtaTap start={sec(s4)} tapAt={sec(s4) + 12} />
        </Center>
      </Scene>
      <Captions
        words={words}
        darkFrom={s3}
        chunks={[
          {p: 'Seu cliente decide', key: 'decide'},
          {p: 'em três segundos.', key: 'três segundos'},
          {p: 'Mostre o problema,', key: 'problema'},
          {p: 'a solução', key: 'solução'},
          {p: 'e o resultado.', key: 'resultado'},
          {p: 'É isso que faz alguém'},
          {p: 'parar de rolar.', key: 'parar de rolar'},
          {p: 'Toque em Saiba Mais.', key: 'Saiba Mais'},
        ]}
      />
    </AdShell>
  );
};
