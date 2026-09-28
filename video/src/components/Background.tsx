import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { Brand } from "../types";
import { useLayout } from "../layout";
import { useTheme } from "../theme";

/** Themed stage. Gradients and patterns only (no CSS blur), so CPU rendering stays fast. */
export const Background: React.FC<{ brand: Brand; energy?: number }> = ({ brand, energy = 0 }) => {
  const theme = useTheme(brand);
  switch (theme.name) {
    case "comic":
      return <ComicBackground brand={brand} />;
    case "paper":
      return <PaperBackground />;
    case "minimal":
      return <MinimalBackground brand={brand} />;
    default:
      return <NeonBackground brand={brand} energy={energy} />;
  }
};

const NeonBackground: React.FC<{ brand: Brand; energy: number }> = ({ brand, energy }) => {
  const frame = useCurrentFrame();
  const { width, height } = useLayout();
  const { bg, bgAlt, primary, accent } = brand.colors;
  const t = frame / 30;
  const ax = 30 + Math.sin(t * 0.35) * 18;
  const ay = 22 + Math.cos(t * 0.27) * 10;
  const bx = 72 + Math.cos(t * 0.31) * 16;
  const by = 78 + Math.sin(t * 0.22) * 10;
  const grid = 90 * (Math.min(width, height) / 1080);
  const pulse = 0.55 + energy * 0.35;
  return (
    <AbsoluteFill style={{ backgroundColor: bg, overflow: "hidden" }}>
      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse 70% 45% at ${ax}% ${ay}%, ${primary}${alpha(0.42 * pulse)} 0%, transparent 70%),
                       radial-gradient(ellipse 65% 40% at ${bx}% ${by}%, ${accent}${alpha(0.28 * pulse)} 0%, transparent 70%),
                       linear-gradient(180deg, ${bg} 0%, ${bgAlt} 100%)`,
        }}
      />
      <AbsoluteFill
        style={{
          backgroundImage: `linear-gradient(${accent}14 1px, transparent 1px), linear-gradient(90deg, ${accent}14 1px, transparent 1px)`,
          backgroundSize: `${grid}px ${grid}px`,
          backgroundPosition: `0 ${(frame * 0.6) % grid}px`,
          maskImage: "radial-gradient(ellipse 80% 70% at 50% 45%, black 20%, transparent 80%)",
          WebkitMaskImage: "radial-gradient(ellipse 80% 70% at 50% 45%, black 20%, transparent 80%)",
        }}
      />
      <AbsoluteFill style={{ background: "radial-gradient(ellipse at 50% 50%, transparent 55%, rgba(0,0,0,0.55) 100%)" }} />
    </AbsoluteFill>
  );
};

/** Pop-art: sunburst rays in the brand colours under a halftone dot screen. */
const ComicBackground: React.FC<{ brand: Brand }> = ({ brand }) => {
  const frame = useCurrentFrame();
  const { s } = useLayout();
  const { primary, accent, bg } = brand.colors;
  const rot = frame * 0.08;
  return (
    <AbsoluteFill style={{ backgroundColor: primary, overflow: "hidden" }}>
      <AbsoluteFill
        style={{
          width: "220%",
          height: "220%",
          left: "-60%",
          top: "-60%",
          background: `repeating-conic-gradient(from ${rot}deg at 50% 50%, ${primary} 0deg 10deg, ${accent} 10deg 20deg)`,
          opacity: 0.55,
        }}
      />
      <AbsoluteFill
        style={{
          backgroundImage: `radial-gradient(${bg}55 ${3.2 * s}px, transparent ${3.6 * s}px)`,
          backgroundSize: `${22 * s}px ${22 * s}px`,
        }}
      />
      <AbsoluteFill style={{ background: `radial-gradient(ellipse at 50% 50%, transparent 40%, ${bg}AA 100%)` }} />
    </AbsoluteFill>
  );
};

/** Notebook paper with ruled lines and a margin. */
const PaperBackground: React.FC = () => {
  const { s } = useLayout();
  const theme = useTheme();
  const { bg, bgAlt, hot } = theme.colors;
  return (
    <AbsoluteFill style={{ backgroundColor: bg, overflow: "hidden" }}>
      <AbsoluteFill
        style={{
          backgroundImage: `linear-gradient(transparent ${62 * s}px, #7FA6C955 ${62 * s}px, #7FA6C955 ${64 * s}px)`,
          backgroundSize: `100% ${64 * s}px`,
        }}
      />
      <div style={{ position: "absolute", top: 0, bottom: 0, left: 40 * s, width: 3 * s, background: `${hot}66` }} />
      <AbsoluteFill style={{ background: `radial-gradient(ellipse at 50% 40%, transparent 50%, ${bgAlt} 100%)` }} />
    </AbsoluteFill>
  );
};

const MinimalBackground: React.FC<{ brand: Brand }> = ({ brand }) => {
  const { bg, bgAlt, primary } = brand.colors;
  return (
    <AbsoluteFill
      style={{ background: `radial-gradient(ellipse 90% 50% at 50% 0%, ${primary}22, transparent 70%), linear-gradient(180deg, ${bg}, ${bgAlt})` }}
    />
  );
};

const alpha = (a: number) =>
  Math.round(Math.max(0, Math.min(1, a)) * 255)
    .toString(16)
    .padStart(2, "0");
