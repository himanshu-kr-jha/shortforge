import React from "react";
import { AbsoluteFill, interpolate, spring } from "remotion";
import { VideoProps } from "../types";
import { useLayout } from "../layout";
import { useTheme } from "../theme";
import { useLine } from "../timeline";
import { Chip, Display, StoryImage } from "./common";

/** One story in 4 beats: persistent title and image; each beat brings a label, progress dots and a big key text. */
export const ExplainerScene: React.FC<VideoProps> = ({ lines = [], sources = [], durationSeconds }) => {
  const theme = useTheme();
  const { s, width } = useLayout();
  const { line, since, fps, frame } = useLine(lines);
  if (!line || line.kind !== "beat") return null;

  const beats = lines.filter((l) => l.kind === "beat");
  const first = beats[0];
  const enter = spring({ frame: frame - Math.round(first.start * fps), fps, config: { damping: 15, stiffness: 160 } });
  const beatIn = spring({ frame: since, fps, config: { damping: 13, stiffness: 190 } });
  const src = sources[0];
  const zoom = [1.05, 1.16, 1.1, 1.22][((line.number ?? 1) - 1) % 4];
  const left = 60 * s;
  const w = width - 120 * s;

  return (
    <AbsoluteFill>
      <div style={{ position: "absolute", left, top: 185 * s, width: w, opacity: enter }}>
        <Display text={line.title ?? ""} size={(line.title ?? "").length > 32 ? 60 : 72} />
      </div>

      <div style={{ opacity: enter, transform: `translateY(${(1 - enter) * 80 * s}px)` }}>
        <StoryImage
          image={src?.image}
          source={src?.source ?? ""}
          box={{ left, top: 380 * s, width: w, height: 450 * s }}
          zoomFrom={zoom - 0.04}
          zoomTo={zoom + 0.04}
          durationFrames={Math.round(durationSeconds * fps)}
        />
      </div>

      <div style={{ position: "absolute", left, top: 870 * s, display: "flex", alignItems: "center", gap: 18 * s }}>
        <div style={{ transform: `scale(${beatIn})`, transformOrigin: "left center" }}>
          <Chip text={line.label ?? ""} color={theme.colors.hot} />
        </div>
        {beats.map((b, i) => (
          <div
            key={i}
            style={{
              width: 18 * s,
              height: 18 * s,
              borderRadius: 999,
              background: (b.number ?? 0) <= (line.number ?? 0) ? theme.colors.accent : "rgba(128,128,128,0.35)",
            }}
          />
        ))}
      </div>

      <div
        style={{
          position: "absolute",
          left,
          top: 950 * s,
          width: 660 * s,
          opacity: beatIn,
          transform: `translateY(${interpolate(beatIn, [0, 1], [40, 0]) * s}px)`,
        }}
      >
        <Display text={line.keyText ?? ""} size={(line.keyText ?? "").length > 22 ? 70 : 88} color={theme.name === "comic" ? "#fff" : theme.colors.text} style={theme.name === "comic" ? { textShadow: `${6 * s}px ${6 * s}px 0 #111` } : undefined} />
      </div>
    </AbsoluteFill>
  );
};
