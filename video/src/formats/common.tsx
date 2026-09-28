import React from "react";
import { AbsoluteFill, Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { Brand, Labels } from "../types";
import { useLayout } from "../layout";
import { useTheme } from "../theme";

export const useSpring = (delay: number, damping = 14, stiffness = 170) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return spring({ frame: frame - delay, fps, config: { damping, stiffness } });
};

/** Small rounded label (format, beat name, "QUESTION 2"...). */
export const Chip: React.FC<{ text: string; color?: string; size?: number }> = ({ text, color, size = 28 }) => {
  const theme = useTheme();
  const { s } = useLayout();
  return (
    <span
      style={{
        display: "inline-block",
        fontFamily: theme.body,
        fontWeight: theme.bodyWeight,
        fontSize: size * s,
        letterSpacing: 2 * s,
        textTransform: "uppercase",
        color: theme.name === "comic" ? "#111" : theme.colors.bg,
        background: color ?? theme.colors.accent,
        padding: `${6 * s}px ${18 * s}px`,
        borderRadius: theme.name === "comic" ? 8 * s : 999,
        border: theme.name === "comic" ? `${4 * s}px solid #111` : "none",
        whiteSpace: "nowrap",
      }}
    >
      {text}
    </span>
  );
};

/** Big headline text in the theme's display font. */
export const Display: React.FC<{ text: string; size: number; color?: string; align?: "left" | "center"; style?: React.CSSProperties }> = ({
  text,
  size,
  color,
  align = "left",
  style,
}) => {
  const theme = useTheme();
  const { s } = useLayout();
  return (
    <div
      style={{
        fontFamily: theme.display,
        fontWeight: theme.displayWeight,
        fontSize: size * s,
        lineHeight: theme.name === "comic" ? 1.0 : 1.08,
        letterSpacing: theme.name === "comic" ? 1 * s : -size * 0.02 * s,
        textTransform: theme.upper ? "uppercase" : "none",
        color: color ?? theme.colors.text,
        textAlign: align,
        ...style,
      }}
    >
      {text}
    </div>
  );
};

/** Story image in a themed frame, with a slow Ken Burns move; a typographic card when there is no image. */
export const StoryImage: React.FC<{
  image: string | null | undefined;
  source: string;
  box: { left: number; top: number; width: number; height: number };
  zoomFrom?: number;
  zoomTo?: number;
  durationFrames: number;
  opacity?: number;
}> = ({ image, source, box, zoomFrom = 1.05, zoomTo = 1.18, durationFrames, opacity = 1 }) => {
  const frame = useCurrentFrame();
  const theme = useTheme();
  const { s } = useLayout();
  const zoom = interpolate(frame, [0, Math.max(1, durationFrames)], [zoomFrom, zoomTo], { extrapolateRight: "clamp" });
  const frameStyle = theme.card(s);
  return (
    <div style={{ position: "absolute", ...box, ...frameStyle, overflow: "hidden", opacity, padding: 0 }}>
      {image ? (
        <Img src={staticFile(image)} style={{ width: "100%", height: "100%", objectFit: "cover", transform: `scale(${zoom})` }} />
      ) : (
        <div
          style={{
            width: "100%",
            height: "100%",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            background: `radial-gradient(circle at 50% 40%, ${theme.colors.primary}88, transparent 65%), ${theme.colors.bgAlt}`,
          }}
        >
          <Display text={source} size={72} align="center" color={theme.name === "paper" ? theme.colors.text : "#fff"} />
        </div>
      )}
      {theme.name === "paper" ? <Tape /> : null}
    </div>
  );
};

/** A strip of masking tape (paper theme). */
export const Tape: React.FC<{ left?: string; rotate?: number }> = ({ left = "42%", rotate = -4 }) => {
  const { s } = useLayout();
  return (
    <div
      style={{
        position: "absolute",
        top: -14 * s,
        left,
        width: 170 * s,
        height: 44 * s,
        background: "rgba(245, 222, 160, 0.85)",
        transform: `rotate(${rotate}deg)`,
        boxShadow: "0 2px 4px rgba(0,0,0,0.15)",
      }}
    />
  );
};

/** Sticker for a key fact (overlaps the bottom-left of an image). */
export const FactSticker: React.FC<{ text: string; progress: number; left: number; top: number }> = ({ text, progress, left, top }) => {
  const theme = useTheme();
  const { s } = useLayout();
  const size = Math.min(50, (50 * 24) / Math.max(24, text.length));
  return (
    <div
      style={{
        position: "absolute",
        left,
        top,
        fontFamily: theme.display,
        fontWeight: theme.displayWeight,
        fontSize: size * s,
        color: "#fff",
        background: theme.colors.hot,
        padding: `${10 * s}px ${26 * s}px`,
        borderRadius: theme.name === "comic" ? 10 * s : 20 * s,
        border: theme.name === "comic" ? `${5 * s}px solid #111` : "none",
        textTransform: "uppercase",
        boxShadow: theme.name === "comic" ? `${6 * s}px ${6 * s}px 0 #111` : `0 ${10 * s}px ${30 * s}px rgba(0,0,0,0.4)`,
        transform: `scale(${progress}) rotate(-4deg)`,
        transformOrigin: "left bottom",
        whiteSpace: "nowrap",
      }}
    >
      {text}
    </div>
  );
};

/** Big rubber stamp (TRUE / FALSE / CORRECT). */
export const Stamp: React.FC<{ text: string; color: string; progress: number; x: number; y: number }> = ({ text, color, progress, x, y }) => {
  const theme = useTheme();
  const { s } = useLayout();
  return (
    <div
      style={{
        position: "absolute",
        left: x,
        top: y,
        transform: `translate(-50%, -50%) scale(${interpolate(progress, [0, 1], [2.6, 1])}) rotate(-12deg)`,
        opacity: Math.min(1, progress * 2),
        fontFamily: theme.display,
        fontWeight: theme.displayWeight,
        fontSize: 150 * s,
        color,
        border: `${12 * s}px solid ${color}`,
        borderRadius: 24 * s,
        padding: `${4 * s}px ${36 * s}px`,
        background: theme.name === "neon" || theme.name === "minimal" ? "rgba(0,0,0,0.6)" : "rgba(255,255,255,0.92)",
        textTransform: "uppercase",
        whiteSpace: "nowrap",
        letterSpacing: 4 * s,
      }}
    >
      {text}
    </div>
  );
};

/** Circular countdown for "think" pauses. */
export const TimerRing: React.FC<{ secondsLeft: number; total: number; size: number; x: number; y: number }> = ({ secondsLeft, total, size, x, y }) => {
  const theme = useTheme();
  const r = 42;
  const c = 2 * Math.PI * r;
  const shown = Math.max(1, Math.ceil(secondsLeft));
  return (
    <div style={{ position: "absolute", left: x, top: y, width: size, height: size }}>
      <svg width={size} height={size} viewBox="0 0 100 100">
        <circle cx="50" cy="50" r={r} fill={theme.name === "paper" ? "#fff" : "rgba(0,0,0,0.45)"} stroke={theme.colors.bgAlt} strokeWidth="10" />
        <circle
          cx="50"
          cy="50"
          r={r}
          fill="none"
          stroke={theme.colors.hot}
          strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={c * (1 - secondsLeft / total)}
          transform="rotate(-90 50 50)"
        />
        <text x="50" y="66" textAnchor="middle" fontFamily={theme.display} fontWeight={theme.displayWeight} fontSize="46" fill={theme.colors.text}>
          {shown}
        </text>
      </svg>
    </div>
  );
};

/** Opening screen for non-countdown formats: format title slam over the date. */
export const FormatIntro: React.FC<{ brand: Brand; labels: Labels; title: string; subtitle: string; dateLabel: string }> = ({
  labels,
  title,
  subtitle,
  dateLabel,
}) => {
  const theme = useTheme();
  const { s, width } = useLayout();
  const a = useSpring(0);
  const b = useSpring(5, 9, 160);
  const c = useSpring(12);
  return (
    <AbsoluteFill>
      <div style={{ position: "absolute", top: 230 * s, left: 60 * s, width: width - 120 * s, display: "flex", flexDirection: "column", alignItems: "center", gap: 18 * s }}>
        <div style={{ opacity: a, transform: `translateY(${(1 - a) * -20 * s}px)` }}>
          <Chip text={`Today in ${labels.topic} · ${dateLabel}`} />
        </div>
        <div style={{ transform: `scale(${interpolate(b, [0, 1], [2.4, 1])}) rotate(${interpolate(b, [0, 1], [-8, -2])}deg)`, opacity: Math.min(1, b * 2) }}>
          <Display
            text={title}
            size={title.length > 12 ? 130 : 170}
            align="center"
            color={theme.name === "paper" ? theme.colors.text : "#fff"}
            style={{ textShadow: theme.name === "comic" ? `${8 * s}px ${8 * s}px 0 #111` : theme.name === "paper" ? "none" : `0 0 ${40 * s}px ${theme.colors.hot}99` }}
          />
        </div>
        <div style={{ opacity: c, transform: `translateY(${(1 - c) * 30 * s}px)` }}>
          <Display text={subtitle} size={56} align="center" color={theme.name === "comic" ? "#fff" : theme.colors.text} />
        </div>
      </div>
    </AbsoluteFill>
  );
};
