import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { Brand } from "../types";
import { LogoMark, Wordmark } from "./Logo";
import { display } from "../fonts";
import { useTheme } from "../theme";
import { Chip } from "../formats/common";
import { useLayout } from "../layout";

/** Persistent top bar: brand, edition, and the countdown tracker. */
export const Header: React.FC<{
  brand: Brand;
  ranks: number[];
  chip?: string;
  editionLabel: string;
  dateLabel: string;
  activeRank: number | null;
}> = ({
  brand,
  ranks,
  chip,
  editionLabel,
  dateLabel,
  activeRank,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { s, safe, width } = useLayout();
  const enter = spring({ frame, fps, config: { damping: 16 } });
  const theme = useTheme(brand);
  return (
    <div
      style={{
        position: "absolute",
        top: safe.top,
        left: safe.left,
        width: width - safe.left * 2,
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        opacity: enter,
        transform: `translateY(${interpolate(enter, [0, 1], [-40 * s, 0])}px)`,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 18 * s, ...(theme.panel ? { ...theme.panel, padding: `${8 * s}px ${20 * s}px ${8 * s}px ${8 * s}px` } : {}) }}>
        <LogoMark brand={brand} size={76 * s} blink />
        <div style={{ display: "flex", flexDirection: "column", gap: 6 * s }}>
          <Wordmark brand={brand} size={40 * s} />
          <span style={{ fontFamily: theme.body, fontWeight: theme.bodyWeight, fontSize: 21 * s, color: theme.name === "comic" ? "#fff" : brand.colors.muted, letterSpacing: 1 * s }}>
            {editionLabel.toUpperCase()} · {dateLabel.toUpperCase()}
          </span>
        </div>
      </div>
      {chip ? <Chip text={chip} size={24} color={brand.colors.hot} /> : null}
      <div style={{ display: "flex", gap: 10 * s }}>
        {ranks.map((rank) => {
          const done = activeRank !== null && rank > activeRank;
          const active = rank === activeRank;
          return (
            <div
              key={rank}
              style={{
                width: 48 * s,
                height: 48 * s,
                borderRadius: 14 * s,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontFamily: display,
                fontWeight: 900,
                fontSize: 24 * s,
                color: active ? "#fff" : done ? brand.colors.text : brand.colors.muted,
                background: active ? brand.colors.hot : done ? `${brand.colors.primary}66` : "rgba(255,255,255,0.06)",
                border: `${2 * s}px solid ${active ? brand.colors.hot : "rgba(255,255,255,0.12)"}`,
                transform: `scale(${active ? 1.12 : 1})`,
                boxShadow: active ? `0 0 ${24 * s}px ${brand.colors.hot}99` : "none",
              }}
            >
              {rank}
            </div>
          );
        })}
      </div>
    </div>
  );
};

/** Thin bar along the very top that fills over the whole video (keeps viewers watching to the end). */
export const ProgressBar: React.FC<{ brand: Brand; total: number }> = ({ brand, total }) => {
  const frame = useCurrentFrame();
  const { s } = useLayout();
  const p = Math.min(1, frame / Math.max(1, total - 1));
  return (
    <div style={{ position: "absolute", top: 0, left: 0, right: 0, height: 10 * s, background: "rgba(255,255,255,0.08)" }}>
      <div
        style={{
          width: `${p * 100}%`,
          height: "100%",
          background: `linear-gradient(90deg, ${brand.colors.primary}, ${brand.colors.accent})`,
          boxShadow: `0 0 ${16 * s}px ${brand.colors.accent}`,
        }}
      />
    </div>
  );
};
