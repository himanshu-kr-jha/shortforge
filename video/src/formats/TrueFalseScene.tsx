import React from "react";
import { AbsoluteFill, Img, interpolate, spring, staticFile } from "remotion";
import { VideoProps } from "../types";
import { useLayout } from "../layout";
import { useTheme } from "../theme";
import { useLine } from "../timeline";
import { Display, Stamp } from "./common";

/** Claim card with TRUE / FALSE buttons; the verdict slams a stamp onto the claim. */
export const TrueFalseScene: React.FC<VideoProps> = ({ lines = [], sources = [] }) => {
  const theme = useTheme();
  const { s, width } = useLayout();
  const { line, since, t, fps, frame } = useLine(lines);
  if (!line || (line.kind !== "claim" && line.kind !== "verdict")) return null;

  const claim = lines.find((l) => l.kind === "claim" && l.number === line.number)!;
  const verdict = line.kind === "verdict";
  const cSince = frame - Math.round(claim.start * fps);
  const enter = spring({ frame: cSince, fps, config: { damping: 15, stiffness: 170 } });
  const stamp = verdict ? spring({ frame: since, fps, config: { damping: 11, stiffness: 220 } }) : 0;
  const guessing = t >= claim.voiceEnd && t < claim.voiceEnd + claim.pauseAfter;
  const img = sources[line.story ?? 0]?.image;
  const card = theme.card(s);
  const left = 60 * s;
  const w = width - 120 * s;
  const total = lines.filter((l) => l.kind === "claim").length;

  const button = (label: string, isTrueButton: boolean, x: number) => {
    const color = isTrueButton ? theme.good : theme.bad;
    const isAnswer = claim.isTrue === isTrueButton;
    const appear = spring({ frame: cSince - 10 - (isTrueButton ? 0 : 4), fps, config: { damping: 13, stiffness: 190 } });
    const pulse = guessing ? 1 + Math.max(0, Math.sin((frame + (isTrueButton ? 0 : 8)) / 4)) * 0.05 : 1;
    const dim = verdict && !isAnswer ? interpolate(stamp, [0, 1], [1, 0.3]) : 1;
    return (
      <div
        style={{
          position: "absolute",
          left: x,
          top: 790 * s,
          width: (w - 30 * s) / 2,
          height: 150 * s,
          ...card,
          background: color,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          opacity: appear * dim,
          transform: `scale(${appear * pulse * (verdict && isAnswer ? 1 + stamp * 0.06 : 1)})`,
        }}
      >
        <Display text={label} size={76} align="center" color="#fff" />
      </div>
    );
  };

  return (
    <AbsoluteFill>
      <div
        style={{
          position: "absolute",
          left,
          top: 200 * s,
          width: w,
          height: 540 * s,
          ...card,
          overflow: "hidden",
          opacity: enter,
          transform: `translateY(${(1 - enter) * -60 * s}px) rotate(${theme.name === "paper" ? -1 : 0}deg)`,
        }}
      >
        {img ? (
          <Img src={staticFile(img)} style={{ position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "cover", opacity: theme.name === "paper" ? 0.14 : 0.25 }} />
        ) : null}
        <div style={{ position: "relative", padding: `${36 * s}px ${44 * s}px`, display: "flex", flexDirection: "column", gap: 24 * s, height: "100%", boxSizing: "border-box" }}>
          <span style={{ fontFamily: theme.body, fontWeight: theme.bodyWeight, fontSize: 32 * s, letterSpacing: 3 * s, color: theme.colors.hot, textTransform: "uppercase" }}>
            True or false? · {line.number}/{total}
          </span>
          <Display text={claim.claim ?? ""} size={(claim.claim ?? "").length > 70 ? 58 : 70} color={card.color as string} />
        </div>
      </div>

      {button("TRUE", true, left)}
      {button("FALSE", false, left + (w + 30 * s) / 2)}

      {guessing ? (
        <div style={{ position: "absolute", left, top: 965 * s, width: w, height: 16 * s, borderRadius: 999, background: "rgba(0,0,0,0.25)", overflow: "hidden" }}>
          <div style={{ width: `${Math.max(0, (claim.voiceEnd + claim.pauseAfter - t) / claim.pauseAfter) * 100}%`, height: "100%", background: theme.colors.hot }} />
        </div>
      ) : null}

      {verdict ? (
        <Stamp text={claim.isTrue ? "True!" : "False!"} color={claim.isTrue ? theme.good : theme.bad} progress={stamp} x={width / 2} y={560 * s} />
      ) : null}
    </AbsoluteFill>
  );
};
