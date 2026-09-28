import React from "react";
import { useCurrentFrame } from "remotion";
import { Brand } from "../types";
import { display } from "../fonts";

/** Brand mark: a gradient tile with a heavy glyph (from the niche profile) and a blinking terminal-style cursor. */
export const LogoMark: React.FC<{ brand: Brand; size: number; blink?: boolean }> = ({ brand, size, blink = false }) => {
  const frame = useCurrentFrame();
  const { primary, accent, bg } = brand.colors;
  const cursorOn = !blink || Math.floor(frame / 15) % 2 === 0;
  const id = `lg-${size}`;
  const glyph = brand.logo.glyph.slice(0, 2);
  const wide = glyph.length > 1;
  return (
    <svg width={size} height={size} viewBox="0 0 100 100" style={{ display: "block" }}>
      <defs>
        <linearGradient id={`${id}-tile`} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor={primary} />
          <stop offset="1" stopColor={accent} />
        </linearGradient>
        <linearGradient id={`${id}-shine`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#fff" stopOpacity="0.28" />
          <stop offset="0.5" stopColor="#fff" stopOpacity="0" />
        </linearGradient>
      </defs>
      <rect x="2" y="2" width="96" height="96" rx="24" fill={`url(#${id}-tile)`} />
      <rect x="2" y="2" width="96" height="96" rx="24" fill={`url(#${id}-shine)`} />
      <text
        x={wide ? 42 : 44}
        y={wide ? 70 : 77}
        textAnchor="middle"
        fontFamily={display}
        fontWeight={900}
        fontSize={wide ? 48 : 74}
        fill={bg}
        letterSpacing="-2"
      >
        {glyph}
      </text>
      <rect x="68" y="62" width="14" height="15" rx="2.5" fill={bg} opacity={cursorOn ? 1 : 0} />
    </svg>
  );
};

export const Wordmark: React.FC<{ brand: Brand; size: number }> = ({ brand, size }) => {
  const head = brand.logo.plain;
  const tail = brand.logo.accent;
  return (
    <span style={{ fontFamily: display, fontWeight: 900, fontSize: size, letterSpacing: -size * 0.02, lineHeight: 1 }}>
      <span style={{ color: brand.colors.text }}>{head}</span>
      <span
        style={{
          backgroundImage: `linear-gradient(90deg, ${brand.colors.primary}, ${brand.colors.accent})`,
          WebkitBackgroundClip: "text",
          backgroundClip: "text",
          color: "transparent",
        }}
      >
        {tail}
      </span>
    </span>
  );
};
