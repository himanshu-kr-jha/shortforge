import React, { useMemo } from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { Brand, Word } from "../types";
import { useTheme } from "../theme";
import { useLayout } from "../layout";

type Chunk = { words: Word[]; start: number; end: number };

const MAX_WORDS = 3;
const MAX_CHARS = 18;

/** Group words into short phrases, breaking on punctuation so phrases read naturally. */
export const chunkWords = (words: Word[]): Chunk[] => {
  const chunks: Chunk[] = [];
  let current: Word[] = [];
  const flush = () => {
    if (current.length) {
      chunks.push({ words: current, start: current[0].start, end: current[current.length - 1].end });
    }
    current = [];
  };
  for (const word of words) {
    const chars = current.reduce((n, w) => n + w.text.length + 1, 0) + word.text.length;
    if (current.length >= MAX_WORDS || (current.length > 0 && chars > MAX_CHARS)) flush();
    current.push(word);
    if (/[.,!?;:]$/.test(word.text)) flush();
  }
  flush();
  // Keep each phrase on screen until the next one starts (no flicker in short pauses).
  for (let i = 0; i < chunks.length - 1; i++) {
    const gap = chunks[i + 1].start - chunks[i].end;
    if (gap < 0.6) chunks[i].end = chunks[i + 1].start;
  }
  return chunks;
};

export const Captions: React.FC<{ brand: Brand; words: Word[] }> = ({ brand, words }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { vertical, s, height } = useLayout();
  const chunks = useMemo(() => chunkWords(words), [words]);
  const t = frame / fps;
  const theme = useTheme(brand);
  const chunk = chunks.find((c) => t >= c.start - 0.05 && t < c.end + 0.05);
  if (!chunk) return null;

  const enter = spring({ frame: frame - Math.round(chunk.start * fps), fps, config: { damping: 14, stiffness: 220 } });
  const fontSize = (vertical ? 76 : 64) * s;
  const top = vertical ? 1365 : height - 190 * s;

  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <div
        style={{
          position: "absolute",
          top,
          left: 0,
          right: 0,
          display: "flex",
          justifyContent: "center",
          flexWrap: "wrap",
          gap: `0 ${fontSize * 0.4}px`,
          padding: `0 ${80 * s}px`,
          transform: `translateY(${interpolate(enter, [0, 1], [24 * s, 0])}px) scale(${interpolate(enter, [0, 1], [0.86, 1])})`,
          opacity: enter,
        }}
      >
        {chunk.words.map((w, i) => {
          const active = t >= w.start - 0.03 && t < (chunk.words[i + 1]?.start ?? chunk.end);
          const pop = active
            ? spring({ frame: frame - Math.round(w.start * fps), fps, config: { damping: 12, stiffness: 300 } })
            : 0;
          return (
            <span
              key={`${w.start}-${i}`}
              style={{
                fontFamily: theme.display,
                fontWeight: theme.displayWeight,
                fontSize,
                lineHeight: 1.25,
                textTransform: "uppercase",
                letterSpacing: -fontSize * 0.01,
                color: active ? theme.pillText : theme.name === "paper" ? "#fff" : brand.colors.text,
                // The pill grows into the gap (negative margin) so word spacing is identical with or without it.
                padding: active ? `0 ${fontSize * 0.1}px` : 0,
                margin: active ? `0 ${-fontSize * 0.1}px` : 0,
                borderRadius: fontSize * 0.18,
                background: active ? theme.pill : "transparent",
                boxShadow: active ? `0 ${6 * s}px 0 ${theme.pill === "#111" ? "#000" : shade(theme.pill)}` : "none",
                transform: `scale(${1 + pop * 0.08}) rotate(${active ? -2 : 0}deg)`,
                textShadow: active
                  ? "none"
                  : `0 ${4 * s}px 0 #000, 0 0 ${3 * s}px #000, ${3 * s}px ${3 * s}px 0 #000, -${3 * s}px -${3 * s}px 0 #000, ${3 * s}px -${3 * s}px 0 #000, -${3 * s}px ${3 * s}px 0 #000`,
              }}
            >
              {w.text.replace(/[.,;:\-–—]+$/, "")}
            </span>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

/** Darker variant of a hex colour for the 3D under-edge of the highlight pill. */
const shade = (hex: string) => {
  const n = parseInt(hex.slice(1), 16);
  const f = (v: number) => Math.round(v * 0.55);
  return `rgb(${f(n >> 16)}, ${f((n >> 8) & 255)}, ${f(n & 255)})`;
};
