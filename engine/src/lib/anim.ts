import {Easing, interpolate, spring} from 'remotion';

export const FPS = 30;
export const sec = (s: number) => Math.round(s * FPS);
export const easeOut = Easing.bezier(0.23, 1, 0.32, 1);
export const easeInOut = Easing.bezier(0.77, 0, 0.175, 1);

export const ramp = (frame: number, start: number, dur: number, easing = easeOut) =>
  interpolate(frame, [start, start + dur], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing,
  });

// Mola com leve overshoot, para entradas "carimbadas"
export const pop = (frame: number, start: number, fps = FPS, damping = 11) =>
  spring({frame: frame - start, fps, config: {damping, mass: 0.6, stiffness: 140}});

// Entrada e saída de uma cena: escala sutil na entrada e zoom-through com blur na saída
export const sceneEnvelope = (frame: number, start: number, end: number) => {
  const inT = ramp(frame, start, 8);
  const outT = ramp(frame, end - 6, 6, easeInOut);
  return {
    opacity: inT * (1 - outT),
    scale: 0.94 + inT * 0.06 + outT * 0.35,
    blur: outT * 14,
    visible: frame >= start - 1 && frame <= end + 1,
  };
};
