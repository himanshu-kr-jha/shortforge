import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { Brand, Labels } from "../types";
import { LogoMark, Wordmark } from "./Logo";
import { display } from "../fonts";
import { useTheme } from "../theme";
import { useLayout } from "../layout";

/** Closing card: brand, follow CTA, and the posting rhythm so viewers know to come back. */
export const OutroScene: React.FC<{ brand: Brand; labels: Labels }> = ({ brand, labels }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { vertical, s } = useLayout();
  const { colors } = brand;
  const sp = (delay: number, damping = 12) => spring({ frame: frame - delay, fps, config: { damping, stiffness: 170 } });
  const pulse = 1 + Math.max(0, Math.sin((frame - 20) / 5)) * 0.05;
  const theme = useTheme(brand);
  const mono = theme.body;
  return (
    <AbsoluteFill
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: vertical ? "flex-start" : "center",
        paddingTop: vertical ? 250 : 0,
        gap: 34 * s,
      }}
    >
      {theme.panel ? (
        <div
          style={{
            position: "absolute",
            top: (vertical ? 215 : 150) * s,
            left: 60 * s,
            right: 60 * s,
            height: 800 * s,
            ...theme.panel,
            transform: `scale(${sp(0, 14)})`,
          }}
        />
      ) : null}
      <div style={{ transform: `scale(${sp(0, 9)}) rotate(${interpolate(sp(0, 9), [0, 1], [-30, 0])}deg)` }}>
        <LogoMark brand={brand} size={(vertical ? 260 : 200) * s} blink />
      </div>
      <div style={{ opacity: sp(6), transform: `translateY(${(1 - sp(6)) * 40 * s}px)` }}>
        <Wordmark brand={brand} size={(vertical ? 110 : 96) * s} />
      </div>
      <span
        style={{
          fontFamily: mono,
          fontWeight: 700,
          fontSize: 30 * s,
          color: colors.muted,
          opacity: sp(10),
          textAlign: "center",
          maxWidth: 900 * s,
        }}
      >
        {brand.tagline}
      </span>
      <div
        style={{
          marginTop: 16 * s,
          fontFamily: display,
          fontWeight: 900,
          fontSize: 58 * s,
          color: "#fff",
          background: colors.hot,
          padding: `${22 * s}px ${64 * s}px`,
          borderRadius: 999,
          boxShadow: `0 ${10 * s}px 0 #8a1238, 0 0 ${50 * s}px ${colors.hot}88`,
          transform: `scale(${sp(14) * pulse})`,
          letterSpacing: 1 * s,
        }}
      >
        FOLLOW {brand.handle.toUpperCase()}
      </div>
      <span
        style={{
          fontFamily: mono,
          fontWeight: 800,
          fontSize: 28 * s,
          color: colors.accent,
          letterSpacing: 3 * s,
          opacity: sp(20),
        }}
      >
        {labels.outroLine.toUpperCase()}
      </span>
    </AbsoluteFill>
  );
};
