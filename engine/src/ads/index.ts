// Anúncios do projeto ativo.
// - demoScript: texto usado com tempos de demonstração enquanto a narração não existe em public/audio/.
// - voices: quais vozes viram composição (<id>-f, <id>-m). Vídeo com apresentador tem uma voz só.
// - tail: segundos depois da última palavra (tela final de 11 s no motion narrado; saída curta no apresentador).
import React from 'react';
import {AdProps, END_SECONDS, TAIL} from '../engine/AdShell';
import {Voice} from '../engine/words';
import {SCRIPT, Template} from './Template';
import {OUTRO_SECONDS, PRESENTER_SCRIPT, PresenterTemplate} from './PresenterTemplate';
import {CLIP_TAIL, SimpleClip} from './SimpleClip';

export type AdEntry = {id: string; component: React.FC<AdProps>; demoScript?: string; voices?: Voice[]; tail?: number};

export const ADS: AdEntry[] = [
  // Modo 1: só motion + narração (voz enviada, ElevenLabs ou outra plataforma)
  {id: 'Template', component: Template, demoScript: SCRIPT},
  // Modo 2: apresentador (corte feito pelo `ss cut`) alternado com motion
  {id: 'PresenterTemplate', component: PresenterTemplate, demoScript: PRESENTER_SCRIPT, voices: ['m'], tail: 0.35 + OUTRO_SECONDS},
  // Modo 3: clipe simples de vídeo longo (`ss clips render`): corte + legenda automática + logo opcional
  {id: 'SimpleClip', component: SimpleClip, voices: ['m'], tail: CLIP_TAIL},
];

export const DEFAULT_TAIL = TAIL + END_SECONDS;
