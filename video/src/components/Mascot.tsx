import React, { useId } from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { Brand } from "../types";

export type Mood = "neutral" | "excited" | "happy" | "shocked" | "thinking" | "sad" | "laughing";
export type Gesture = "idle" | "point" | "wave" | "cheer";
export type Variant = "bot" | "buddy";

/**
 * Original mascot: a floating robot with a screen for a face. Everything is vector, coloured from the brand.
 * `talk` (0..1) drives the mouth from the voice loudness; `since` is the frame the current scene started (for the pop-in).
 */
export const Mascot: React.FC<{
  brand: Brand;
  size: number;
  mood: Mood;
  gesture: Gesture;
  talk: number;
  since: number;
  /** "bot" = the host (screen-face robot); "buddy" = the co-host (round head, twin antennae, glasses) */
  variant?: Variant;
  /** mirror horizontally, e.g. so a character on the right faces left */
  flip?: boolean;
}> = ({ brand, size, mood, gesture, talk, since, variant = "bot", flip = false }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const buddy = variant === "buddy";
  // the face is a glowing screen: always dark, even on light themes (paper) where the page background is beige
  const bg = "#0E1016";
  // the co-host swaps the palette so the two characters never look alike
  const primary = buddy ? rotateHue(brand.colors.primary, 180) : brand.colors.primary;
  const accent = buddy ? rotateHue(brand.colors.accent, 150) : brand.colors.accent;
  const hot = buddy ? "#FFE66D" : brand.colors.hot;
  const t = frame / fps;

  const pop = spring({ frame: frame - since, fps, config: { damping: 9, stiffness: 200 } });
  const float = Math.sin(t * 2.2) * 5;
  const tilt = Math.sin(t * 1.3) * 3 + (mood === "thinking" ? -6 : 0) + (mood === "laughing" ? Math.sin(t * 18) * 4 : 0);
  const squash = 1 + talk * 0.03;

  // blink every ~3.2 s for 4 frames (never while shocked)
  const blinkPhase = (frame + 17) % Math.round(fps * 3.2);
  const blink = mood !== "shocked" && blinkPhase < 4 ? 0.12 : 1;

  const armSwing = Math.sin(t * 2.2 + 1) * 6;
  const wave = Math.sin(t * 9) * 22;
  const arms: Record<Gesture, [number, number]> = {
    idle: [22 + armSwing, -22 - armSwing],
    point: [58 + Math.sin(t * 3) * 4, -24 - armSwing],
    wave: [24 + armSwing, -122 + wave],
    cheer: [125 + Math.sin(t * 8) * 10, -125 - Math.sin(t * 8) * 10],
  };
  const [leftArm, rightArm] = arms[gesture];
  // unique per instance: two characters of the same size must not share SVG gradient ids
  const id = `m-${useId().replace(/:/g, "")}`;

  return (
    <svg
      width={size}
      height={size * 1.2}
      viewBox="0 0 200 240"
      style={{
        overflow: "visible",
        transform: `scale(${interpolate(pop, [0, 1], [0.6, 1]) * (flip ? -1 : 1)}, ${interpolate(pop, [0, 1], [0.6, 1])})`,
        opacity: Math.min(1, pop * 1.5),
        filter: `drop-shadow(0 ${size * 0.04}px ${size * 0.06}px rgba(0,0,0,0.45))`,
      }}
    >
      <defs>
        <linearGradient id={`${id}-shell`} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor={primary} />
          <stop offset="1" stopColor={accent} />
        </linearGradient>
        <radialGradient id={`${id}-glow`}>
          <stop offset="0" stopColor={hot} stopOpacity="0.9" />
          <stop offset="1" stopColor={hot} stopOpacity="0" />
        </radialGradient>
      </defs>

      {/* floor shadow shrinks as the robot floats up */}
      <ellipse cx="100" cy="232" rx={48 - float} ry="7" fill="#000" opacity="0.35" />

      <g transform={`translate(0 ${float}) rotate(${tilt} 100 130)`}>
        {/* body */}
        <rect x="64" y="154" width="72" height="58" rx="24" fill={`url(#${id}-shell)`} />
        <circle cx="100" cy="182" r="9" fill={bg} opacity="0.35" />
        <circle cx="100" cy="182" r={4 + talk * 3} fill={hot} />

        {/* antenna (co-host: two short ones) */}
        {buddy ? (
          [62, 138].map((x, i) => (
            <g key={x}>
              <line x1={x} y1="46" x2={x + (i ? 8 : -8)} y2={20 - talk * 3} stroke={accent} strokeWidth="5" strokeLinecap="round" />
              <circle cx={x + (i ? 8 : -8)} cy={17 - talk * 3} r="6" fill={hot} />
            </g>
          ))
        ) : (
          <>
            <line x1="100" y1="40" x2="100" y2={16 - talk * 3} stroke={accent} strokeWidth="5" strokeLinecap="round" />
            <circle cx="100" cy={12 - talk * 3} r="16" fill={`url(#${id}-glow)`} opacity={0.5 + 0.5 * Math.abs(Math.sin(t * 4))} />
            <circle cx="100" cy={12 - talk * 3} r="7" fill={hot} />
          </>
        )}

        {/* head */}
        <g transform={`translate(100 98) scale(1 ${squash}) translate(-100 -98)`}>
          <rect x="18" y="38" width="164" height="122" rx={buddy ? 61 : 38} fill={`url(#${id}-shell)`} />
          <rect x="30" y="50" width="140" height="98" rx={buddy ? 49 : 28} fill={bg} />
          <rect x="30" y="50" width="140" height="40" rx={buddy ? 49 : 28} fill="#fff" opacity="0.05" />
          <Face mood={mood} talk={talk} blink={blink} accent={accent} hot={hot} bg={bg} t={t} />
          {buddy ? (
            <g fill="none" stroke="#fff" strokeWidth="4" opacity="0.9">
              <rect x="52" y="72" width="40" height="32" rx="12" />
              <rect x="108" y="72" width="40" height="32" rx="12" />
              <line x1="92" y1="86" x2="108" y2="86" />
            </g>
          ) : null}
        </g>

        {/* arms last, so raised hands show in front of the head (drawn hanging down; positive rotation swings left) */}
        <Arm x={66} y={170} angle={leftArm} fill={`url(#${id}-shell)`} hand={accent} />
        <Arm x={134} y={170} angle={rightArm} fill={`url(#${id}-shell)`} hand={accent} />
      </g>
    </svg>
  );
};

/** Rotate a #RRGGBB colour around the hue wheel (keeps saturation and lightness). */
const rotateHue = (hex: string, degrees: number): string => {
  const n = parseInt(hex.slice(1), 16);
  const [r, g, b] = [(n >> 16) / 255, ((n >> 8) & 255) / 255, (n & 255) / 255];
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  const l = (max + min) / 2;
  const d = max - min;
  const sat = d === 0 ? 0 : d / (1 - Math.abs(2 * l - 1));
  let h = 0;
  if (d !== 0) h = max === r ? ((g - b) / d) % 6 : max === g ? (b - r) / d + 2 : (r - g) / d + 4;
  h = (h * 60 + degrees + 360) % 360;
  const c = (1 - Math.abs(2 * l - 1)) * sat;
  const x = c * (1 - Math.abs(((h / 60) % 2) - 1));
  const m = l - c / 2;
  const [r1, g1, b1] = h < 60 ? [c, x, 0] : h < 120 ? [x, c, 0] : h < 180 ? [0, c, x] : h < 240 ? [0, x, c] : h < 300 ? [x, 0, c] : [c, 0, x];
  return "#" + [r1, g1, b1].map((v) => Math.round((v + m) * 255).toString(16).padStart(2, "0")).join("");
};

const Arm: React.FC<{ x: number; y: number; angle: number; fill: string; hand: string }> = ({ x, y, angle, fill, hand }) => (
  <g transform={`rotate(${angle} ${x} ${y})`}>
    <rect x={x - 7} y={y} width="14" height="44" rx="7" fill={fill} />
    <circle cx={x} cy={y + 48} r="10" fill={hand} />
  </g>
);

const Face: React.FC<{ mood: Mood; talk: number; blink: number; accent: string; hot: string; bg: string; t: number }> = ({
  mood,
  talk,
  blink,
  accent,
  hot,
  bg,
  t,
}) => {
  const lookX = mood === "thinking" ? 6 : Math.sin(t * 0.7) * 3;
  const lookY = mood === "thinking" ? -6 : 0;
  const glow = { filter: `drop-shadow(0 0 4px ${accent})` };

  const eye = (cx: number, side: -1 | 1) => {
    const x = cx + lookX;
    const y = 88 + lookY;
    switch (mood) {
      case "happy":
      case "laughing":
        // ^ ^ (laughing: > <)
        return mood === "laughing" ? (
          <path d={`M ${x - 10 * side} ${y - 9} L ${x + 8 * side} ${y} L ${x - 10 * side} ${y + 9}`} stroke={accent} strokeWidth="6" fill="none" strokeLinecap="round" strokeLinejoin="round" />
        ) : (
          <path d={`M ${x - 12} ${y + 5} Q ${x} ${y - 12} ${x + 12} ${y + 5}`} stroke={accent} strokeWidth="6" fill="none" strokeLinecap="round" />
        );
      case "shocked":
        return (
          <g>
            <circle cx={x} cy={y} r="15" fill="none" stroke={accent} strokeWidth="5" />
            <circle cx={x} cy={y} r="5" fill={accent} />
          </g>
        );
      case "excited":
        return (
          <g>
            <rect x={x - 11} y={y - 16 * blink} width="22" height={32 * blink} rx="11" fill={accent} />
            <circle cx={x + 4} cy={y - 7} r="4" fill={bg} opacity={blink} />
          </g>
        );
      default: {
        const h = (mood === "thinking" && side === 1 ? 14 : 26) * blink;
        return <rect x={x - 9} y={y - h / 2} width="18" height={Math.max(3, h)} rx="9" fill={accent} />;
      }
    }
  };

  const brow = (cx: number, side: -1 | 1) => {
    const angles: Partial<Record<Mood, number>> = { sad: -18, shocked: 0, thinking: side === 1 ? -14 : 6, excited: 8 };
    const lift: Partial<Record<Mood, number>> = { shocked: -8, excited: -4 };
    if (!(mood in angles)) return null;
    const x = cx + lookX;
    const y = 66 + (lift[mood] ?? 0) + lookY;
    return (
      <line
        x1={x - 11}
        y1={y}
        x2={x + 11}
        y2={y}
        stroke={accent}
        strokeWidth="5"
        strokeLinecap="round"
        transform={`rotate(${(angles[mood] ?? 0) * side} ${x} ${y})`}
      />
    );
  };

  // Mouth: open with the voice; its resting shape follows the mood.
  const mx = 100 + lookX * 0.5;
  const my = 124;
  let mouth: React.ReactNode;
  if (talk > 0.05) {
    const wide = mood === "happy" || mood === "laughing" || mood === "excited";
    mouth = (
      <g>
        <rect x={mx - (wide ? 17 : 13)} y={my - 3 - talk * 9} width={wide ? 34 : 26} height={6 + talk * 18} rx={Math.min(13, 3 + talk * 12)} fill={accent} />
        <rect x={mx - 8} y={my + talk * 4} width="16" height={Math.max(0, talk * 6)} rx="4" fill={hot} opacity="0.9" />
      </g>
    );
  } else if (mood === "shocked") {
    mouth = <ellipse cx={mx} cy={my + 2} rx="9" ry="12" fill="none" stroke={accent} strokeWidth="5" />;
  } else if (mood === "sad") {
    mouth = <path d={`M ${mx - 16} ${my + 8} Q ${mx} ${my - 6} ${mx + 16} ${my + 8}`} stroke={accent} strokeWidth="5" fill="none" strokeLinecap="round" />;
  } else if (mood === "thinking") {
    mouth = <line x1={mx - 4} y1={my + 3} x2={mx + 14} y2={my - 2} stroke={accent} strokeWidth="5" strokeLinecap="round" />;
  } else if (mood === "neutral") {
    mouth = <line x1={mx - 12} y1={my} x2={mx + 12} y2={my} stroke={accent} strokeWidth="5" strokeLinecap="round" />;
  } else {
    mouth = <path d={`M ${mx - 18} ${my - 4} Q ${mx} ${my + 16} ${mx + 18} ${my - 4}`} stroke={accent} strokeWidth="5" fill="none" strokeLinecap="round" />;
  }

  const blush = mood === "happy" || mood === "laughing" || mood === "excited";
  return (
    <g style={glow}>
      {blush ? (
        <>
          <ellipse cx="54" cy="112" rx="10" ry="6" fill={hot} opacity="0.55" />
          <ellipse cx="146" cy="112" rx="10" ry="6" fill={hot} opacity="0.55" />
        </>
      ) : null}
      {brow(72, -1)}
      {brow(128, 1)}
      {eye(72, -1)}
      {eye(128, 1)}
      {mouth}
      {mood === "thinking" ? (
        <g opacity={0.6 + 0.4 * Math.sin(t * 5)}>
          <circle cx="160" cy="44" r="4" fill={accent} />
          <circle cx="172" cy="32" r="6" fill={accent} />
        </g>
      ) : null}
    </g>
  );
};
