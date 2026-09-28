import React from "react";
import { staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { useAudioData } from "@remotion/media-utils";
import { Brand } from "../types";
import { Gesture, Mascot, Mood, Variant } from "./Mascot";

/**
 * How far the mouth opens (0..1): loudness (RMS) of the voice around this frame, read straight from the waveform.
 * Calibrated on Kokoro narration: silence stays below ~0.01 RMS, normal speech sits around 0.02-0.13.
 */
export const useTalk = (): number => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const audio = useAudioData(staticFile("voice.wav"));
  if (!audio) return 0;
  const samples = audio.channelWaveforms[0];
  const perFrame = audio.sampleRate / fps;
  const from = Math.max(0, Math.floor((frame - 0.5) * perFrame));
  const to = Math.min(samples.length, Math.floor((frame + 1.5) * perFrame));
  if (to <= from) return 0;
  let sum = 0;
  for (let i = from; i < to; i++) sum += samples[i] * samples[i];
  const rms = Math.sqrt(sum / (to - from));
  return Math.min(1, Math.max(0, (rms - 0.012) / 0.07));
};

export type Box = { x: number; y: number; w: number };

/** A character at a position; its mouth only moves while it is the one speaking. */
export const Presenter: React.FC<{
  brand: Brand;
  box: Box;
  mood: Mood;
  gesture: Gesture;
  speaking: boolean;
  since: number;
  variant?: Variant;
  flip?: boolean;
}> = ({ brand, box, mood, gesture, speaking, since, variant, flip }) => {
  const talk = useTalk();
  return (
    <div style={{ position: "absolute", left: box.x, top: box.y, width: box.w, pointerEvents: "none" }}>
      <Mascot brand={brand} size={box.w} mood={mood} gesture={gesture} talk={speaking ? talk : 0} since={since} variant={variant} flip={flip} />
    </div>
  );
};
