// Clipe simples de um vídeo longo (caminho C): o corte em plano médio, legenda karaokê automática e logo opcional.
// O `ss clips render` coloca o corte em public/video/clip.mp4 e as palavras (já no tempo do corte) em
// public/audio/SimpleClip-m.words.json. O áudio é o do próprio corte; a loudness final é ajustada na finalização.
import React from 'react';
import {AbsoluteFill, Audio, Img, getStaticFiles, staticFile} from 'remotion';
import {AdProps} from '../engine/AdShell';
import {autoChunks} from '../lib/autoChunks';
import {brand, brandAsset} from '../brand';
import {CAPTION_TOP, CaptionScrim, PresenterShot, PresenterSource, SegmentCaptions} from '../presenter';

export const CLIP_TAIL = 0.6; // segundos depois da última palavra (igual a CLIP_TAIL_S em ss_lib/clip_render.py)
const CLIP_VIDEO = 'video/clip.mp4';
// Plano médio fixo: rosto um pouco acima do centro, push-in quase imperceptível
const SOURCE: PresenterSource = {src: CLIP_VIDEO, face: {x: 0.5, y: 0.32}};
const MEDIUM: [number, number] = [1.0, 1.06];

const has = (p: string) => getStaticFiles().some((f) => f.name === p);

export type SimpleClipProps = AdProps & {logo?: boolean};

export const SimpleClip: React.FC<SimpleClipProps> = ({words, logo = false}) => {
  const end = words.length ? words[words.length - 1].e + CLIP_TAIL : 40;
  const chunks = autoChunks(words);
  return (
    <AbsoluteFill style={{background: brand.colors.dark.bg}}>
      <PresenterShot source={SOURCE} from={0} to={end} z={MEDIUM} ty={0.3} />
      {chunks.length > 0 && (
        <>
          <CaptionScrim y={1210} />
          <SegmentCaptions words={words} chunks={chunks} theme="dark" top={CAPTION_TOP.presenter} />
        </>
      )}
      {logo && (
        <div style={{position: 'absolute', top: 150, left: 0, right: 0, display: 'flex', justifyContent: 'center'}}>
          <Img src={staticFile(brandAsset(brand.logos.header))} style={{width: 280}} />
        </div>
      )}
      {has(CLIP_VIDEO) && <Audio src={staticFile(CLIP_VIDEO)} />}
    </AbsoluteFill>
  );
};
