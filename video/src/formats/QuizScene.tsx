import React from "react";
import { AbsoluteFill, Img, interpolate, spring, staticFile } from "remotion";
import { VideoProps } from "../types";
import { useLayout } from "../layout";
import { useTheme } from "../theme";
import { useLine } from "../timeline";
import { Display, TimerRing } from "./common";

const LETTERS = "ABC";

/** Question card + three options; a timer ring during the thinking pause; the reveal lights up the right answer. */
export const QuizScene: React.FC<VideoProps> = ({ lines = [], sources = [] }) => {
  const theme = useTheme();
  const { s, width } = useLayout();
  const { line, since, t, fps, frame } = useLine(lines);
  if (!line || (line.kind !== "question" && line.kind !== "reveal")) return null;

  const question = lines.find((l) => l.kind === "question" && l.number === line.number)!;
  const revealing = line.kind === "reveal";
  const qSince = frame - Math.round(question.start * fps);
  const enter = spring({ frame: qSince, fps, config: { damping: 15, stiffness: 170 } });
  const reveal = revealing ? spring({ frame: since, fps, config: { damping: 10, stiffness: 200 } }) : 0;
  const img = sources[line.story ?? 0]?.image;
  const card = theme.card(s);
  const left = 60 * s;
  const w = width - 120 * s;
  const thinking = t >= question.voiceEnd && t < question.voiceEnd + question.pauseAfter;

  return (
    <AbsoluteFill>
      {/* question card */}
      <div
        style={{
          position: "absolute",
          left,
          top: 200 * s,
          width: w,
          minHeight: 330 * s,
          ...card,
          overflow: "hidden",
          opacity: enter,
          transform: `translateY(${(1 - enter) * -60 * s}px)`,
        }}
      >
        {img ? (
          <Img src={staticFile(img)} style={{ position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "cover", opacity: theme.name === "paper" ? 0.12 : 0.22 }} />
        ) : null}
        <div style={{ position: "relative", padding: `${32 * s}px ${40 * s}px`, display: "flex", flexDirection: "column", gap: 18 * s }}>
          <span style={{ fontFamily: theme.body, fontWeight: theme.bodyWeight, fontSize: 30 * s, letterSpacing: 3 * s, color: theme.colors.hot, textTransform: "uppercase" }}>
            Question {line.number} of {lines.filter((l) => l.kind === "question").length}
          </span>
          <Display text={line.question ?? ""} size={(line.question ?? "").length > 60 ? 54 : 64} color={card.color as string} />
        </div>
      </div>

      {/* options */}
      {(line.options ?? []).map((opt, i) => {
        const appear = spring({ frame: qSince - 8 - i * 5, fps, config: { damping: 14, stiffness: 190 } });
        const correct = i === line.answer;
        const state = revealing ? (correct ? "right" : "wrong") : "open";
        const bg = state === "right" ? theme.good : state === "wrong" ? theme.bad : (card.background as string);
        const pulse = thinking ? 1 + Math.sin((frame + i * 6) / 4) * 0.015 : 1;
        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left,
              top: (590 + i * 138) * s,
              width: w,
              height: 116 * s,
              ...card,
              background: bg,
              display: "flex",
              alignItems: "center",
              gap: 26 * s,
              padding: `0 ${28 * s}px`,
              boxSizing: "border-box",
              opacity: appear * (state === "wrong" ? interpolate(reveal, [0, 1], [1, 0.4]) : 1),
              transform: `translateX(${(1 - appear) * (i % 2 ? 120 : -120) * s}px) scale(${pulse * (state === "right" ? 1 + reveal * 0.05 : 1)})`,
            }}
          >
            <span
              style={{
                width: 72 * s,
                height: 72 * s,
                flexShrink: 0,
                borderRadius: 999,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                background: state === "open" ? theme.colors.primary : "rgba(255,255,255,0.3)",
                color: "#fff",
                fontFamily: theme.display,
                fontWeight: theme.displayWeight,
                fontSize: 42 * s,
              }}
            >
              {state === "right" ? "✓" : state === "wrong" ? "✗" : LETTERS[i]}
            </span>
            <Display text={opt} size={opt.length > 18 ? 42 : 52} color={state === "open" ? (card.color as string) : "#fff"} />
          </div>
        );
      })}

      {/* thinking timer */}
      {thinking ? <TimerRing secondsLeft={Math.max(0, question.voiceEnd + question.pauseAfter - t)} total={question.pauseAfter} size={190 * s} x={120 * s} y={1030 * s} /> : null}
    </AbsoluteFill>
  );
};
