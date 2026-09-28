import React from "react";
import { Html5Audio, Sequence, staticFile, useVideoConfig } from "remotion";
import { Line } from "../types";

const REVEALS = ["reveal", "verdict"];
const SCENE_CHANGES = ["question", "claim", "beat"];

/** All sound effects for a format video, placed at absolute frames (always mounted, so Remotion mixes them correctly). */
export const SfxTrack: React.FC<{ lines: Line[] }> = ({ lines }) => {
  const { fps } = useVideoConfig();
  const events: { at: number; src: string; volume: number; key: string }[] = [];
  lines.forEach((l, i) => {
    if (SCENE_CHANGES.includes(l.kind)) events.push({ at: l.start, src: "sfx/whoosh.wav", volume: 0.45, key: `w${i}` });
    if (REVEALS.includes(l.kind)) events.push({ at: l.start, src: "sfx/ding.wav", volume: 0.55, key: `d${i}` });
    if (l.pauseAfter > 0) {
      for (let k = 0; k < Math.floor(l.pauseAfter); k++) {
        events.push({ at: l.voiceEnd + k, src: "sfx/tick.wav", volume: 0.6, key: `t${i}-${k}` });
      }
    }
  });
  return (
    <>
      {events.map((e) => (
        <Sequence key={e.key} from={Math.round(e.at * fps)} durationInFrames={Math.round(fps * 1.5)}>
          <Html5Audio src={staticFile(e.src)} volume={e.volume} />
        </Sequence>
      ))}
    </>
  );
};
