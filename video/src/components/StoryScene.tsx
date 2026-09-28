import React from "react";
import { AbsoluteFill, Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { Brand, Story } from "../types";
import { display, mono } from "../fonts";
import { useLayout } from "../layout";

export const StoryScene: React.FC<{ brand: Brand; story: Story }> = ({ brand, story }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const { vertical, s, width, safe } = useLayout();
  const { colors } = brand;

  const sp = (delay: number, config = { damping: 15, stiffness: 160 }) => spring({ frame: frame - delay, fps, config });
  const slam = sp(0, { damping: 11, stiffness: 180 });
  const exit = interpolate(frame, [durationInFrames - 8, durationInFrames], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const flash = interpolate(frame, [0, 6], [0.35, 0], { extrapolateRight: "clamp" });

  const headlineWords = story.headline.split(" ");
  const hl = story.headline.length;
  const headlineSize = (vertical ? (hl <= 22 ? 100 : hl <= 34 ? 86 : 74) : hl <= 30 ? 84 : 70) * s;

  const imageBox = vertical
    ? { left: safe.left, top: 780, width: width - safe.left * 2, height: 450 }
    : { left: 1000 * s, top: 190 * s, width: 840 * s, height: 560 * s };
  const textLeft = safe.left;
  const textWidth = vertical ? width - safe.left * 2 : 860 * s;

  return (
    <AbsoluteFill
      style={{
        opacity: 1 - exit,
        transform: `translateX(${-exit * 90 * s}px)`,
      }}
    >
      {/* rank + meta */}
      <div
        style={{
          position: "absolute",
          top: vertical ? 200 : 170 * s,
          left: textLeft,
          display: "flex",
          alignItems: "center",
          gap: 30 * s,
        }}
      >
        <div
          style={{
            fontFamily: display,
            fontWeight: 900,
            fontSize: (vertical ? 210 : 170) * s,
            lineHeight: 0.9,
            letterSpacing: -8 * s,
            backgroundImage: `linear-gradient(160deg, ${colors.hot}, ${colors.primary})`,
            WebkitBackgroundClip: "text",
            backgroundClip: "text",
            color: "transparent",
            transform: `scale(${interpolate(slam, [0, 1], [2.6, 1])}) rotate(${interpolate(slam, [0, 1], [-12, 0])}deg)`,
            opacity: Math.min(1, slam * 1.6),
            transformOrigin: "left center",
            filter: `drop-shadow(0 ${8 * s}px ${22 * s}px ${colors.hot}55)`,
          }}
        >
          #{story.rank}
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 14 * s, opacity: sp(5), transform: `translateX(${(1 - sp(5)) * 40 * s}px)` }}>
          <span
            style={{
              alignSelf: "flex-start",
              fontFamily: mono,
              fontWeight: 800,
              fontSize: 30 * s,
              color: colors.bg,
              background: colors.accent,
              padding: `${8 * s}px ${20 * s}px`,
              borderRadius: 999,
              letterSpacing: 2 * s,
            }}
          >
            {story.category.toUpperCase()}
          </span>
          <span
            style={{
              fontFamily: mono,
              fontWeight: 700,
              fontSize: 26 * s,
              color: colors.muted,
              maxWidth: 330 * s,
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
          >
            via {story.source}
          </span>
        </div>
      </div>

      {/* headline */}
      <div
        style={{
          position: "absolute",
          top: vertical ? 470 : 390 * s,
          left: textLeft,
          width: textWidth,
          display: "flex",
          flexWrap: "wrap",
          gap: `0 ${headlineSize * 0.26}px`,
        }}
      >
        {headlineWords.map((word, i) => {
          const p = sp(6 + i * 3, { damping: 14, stiffness: 200 });
          return (
            <span
              key={i}
              style={{
                fontFamily: display,
                fontWeight: 900,
                fontSize: headlineSize,
                lineHeight: 1.08,
                letterSpacing: -headlineSize * 0.02,
                color: colors.text,
                opacity: p,
                transform: `translateY(${(1 - p) * 50 * s}px)`,
                textShadow: `0 ${6 * s}px ${24 * s}px rgba(0,0,0,0.5)`,
              }}
            >
              {word}
            </span>
          );
        })}
      </div>

      {/* visual */}
      <div
        style={{
          position: "absolute",
          ...imageBox,
          borderRadius: 40 * s,
          padding: 5 * s,
          background: `linear-gradient(135deg, ${colors.primary}, ${colors.accent})`,
          boxShadow: `0 ${30 * s}px ${80 * s}px rgba(0,0,0,0.55), 0 0 ${60 * s}px ${colors.primary}44`,
          opacity: sp(4),
          transform: `translateY(${(1 - sp(4)) * 160 * s}px) rotate(${(1 - sp(4)) * 4}deg)`,
        }}
      >
        <div style={{ width: "100%", height: "100%", borderRadius: 36 * s, overflow: "hidden", position: "relative", background: colors.bgAlt }}>
          {story.image ? (
            <Img
              src={staticFile(story.image)}
              style={{
                width: "100%",
                height: "100%",
                objectFit: "cover",
                transform: `scale(${interpolate(frame, [0, durationInFrames], [1.06, 1.2])}) translateX(${interpolate(frame, [0, durationInFrames], [-1.5, 1.5])}%)`,
              }}
            />
          ) : (
            <FallbackVisual brand={brand} story={story} />
          )}
          <div style={{ position: "absolute", inset: 0, background: "linear-gradient(180deg, transparent 55%, rgba(0,0,0,0.55) 100%)" }} />
        </div>
        <KeyFact brand={brand} text={story.keyFact} progress={sp(16, { damping: 9, stiffness: 220 })} />
      </div>

      <AbsoluteFill style={{ background: "#fff", opacity: flash, pointerEvents: "none" }} />
    </AbsoluteFill>
  );
};

const KeyFact: React.FC<{ brand: Brand; text: string; progress: number }> = ({ brand, text, progress }) => {
  const { s } = useLayout();
  return (
    <div
      style={{
        position: "absolute",
        left: -12 * s,
        bottom: -38 * s,
        fontFamily: display,
        fontWeight: 900,
        // long facts shrink so the sticker never runs past the image card
        fontSize: Math.min(50, (50 * 24) / Math.max(24, text.length)) * s,
        color: "#fff",
        background: brand.colors.hot,
        padding: `${12 * s}px ${30 * s}px`,
        borderRadius: 20 * s,
        textTransform: "uppercase",
        letterSpacing: -0.5 * s,
        boxShadow: `0 ${10 * s}px 0 #8a1238, 0 ${16 * s}px ${40 * s}px rgba(0,0,0,0.5)`,
        transform: `scale(${progress}) rotate(-4deg)`,
        transformOrigin: "left bottom",
        whiteSpace: "nowrap",
      }}
    >
      {text}
    </div>
  );
};

/** Used when a story has no usable image: a bold typographic card. */
const FallbackVisual: React.FC<{ brand: Brand; story: Story }> = ({ brand, story }) => {
  const frame = useCurrentFrame();
  const { s } = useLayout();
  const { colors } = brand;
  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: 10 * s,
        background: `radial-gradient(circle at ${50 + Math.sin(frame / 25) * 20}% 40%, ${colors.primary}88, transparent 60%), repeating-linear-gradient(45deg, ${colors.bgAlt} 0 ${22 * s}px, ${colors.bg} ${22 * s}px ${44 * s}px)`,
      }}
    >
      <span style={{ fontFamily: mono, fontWeight: 800, fontSize: 44 * s, color: colors.accent, letterSpacing: 6 * s }}>
        {"// "}
        {story.category.toUpperCase()}
      </span>
      <span style={{ fontFamily: display, fontWeight: 900, fontSize: 96 * s, color: colors.text, textAlign: "center", padding: `0 ${40 * s}px`, lineHeight: 1 }}>
        {story.source}
      </span>
    </div>
  );
};
