import { useCurrentFrame, useVideoConfig } from "remotion";
import { Line } from "./types";

/** The line being spoken (or whose pause is running) at the current frame, with frame offsets. */
export const useLine = (lines: Line[]) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  let index = lines.findIndex((l) => t >= l.start && t < l.end);
  if (index === -1) index = t < (lines[0]?.start ?? 0) ? 0 : lines.length - 1;
  const line = lines[index];
  return {
    line,
    index,
    t,
    /** frames since this line started */
    since: frame - Math.round(line.start * fps),
    startFrame: Math.round(line.start * fps),
    /** true while the voice is silent after the line (quiz timer, true/false guess) */
    inPause: t >= line.voiceEnd && t < line.end && line.pauseAfter > 0,
    fps,
    frame,
  };
};

/** Seconds since the start of the most recent line of one of these kinds (for reveal animations). */
export const lastOfKind = (lines: Line[], t: number, kinds: string[]) =>
  [...lines].reverse().find((l) => kinds.includes(l.kind) && t >= l.start);
