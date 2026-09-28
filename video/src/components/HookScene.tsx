import React from "react";
import { AbsoluteFill, Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { Brand, Labels, Story } from "../types";
import { display, mono } from "../fonts";
import { useLayout } from "../layout";

/** Opening: "TOP <n> <SUBTITLE>" slam plus a fanned deck of today's visuals, with #1 kept hidden. */
export const HookScene: React.FC<{ brand: Brand; labels: Labels; stories: Story[]; dateLabel: string; makeRoom?: boolean }> = ({
  brand,
  labels,
  stories,
  dateLabel,
  makeRoom = false,
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const { vertical, s, width, safe } = useLayout();
  const { colors } = brand;
  const sp = (delay: number, damping = 13, stiffness = 170) => spring({ frame: frame - delay, fps, config: { damping, stiffness } });
  const exit = interpolate(frame, [durationInFrames - 8, durationInFrames], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  const five = sp(4, 9, 160);
  const titleLeft = vertical ? 0 : safe.left;
  const titleWidth = vertical ? width : 900 * s;
  const align = vertical ? "center" : "flex-start";

  const deckCenterX = vertical ? (makeRoom ? 390 : width / 2) : 1400 * s;
  const spread = makeRoom ? 95 : 120;
  const deckTop = vertical ? 860 : 250 * s;
  const cardW = (vertical ? 290 : 300) * s;
  const cardH = (vertical ? 380 : 400) * s;

  return (
    <AbsoluteFill style={{ opacity: 1 - exit, transform: `scale(${1 + exit * 0.08})` }}>
      <div
        style={{
          position: "absolute",
          top: vertical ? 215 : 190 * s,
          left: titleLeft,
          width: titleWidth,
          display: "flex",
          flexDirection: "column",
          alignItems: align,
        }}
      >
        <span
          style={{
            fontFamily: mono,
            fontWeight: 800,
            fontSize: 30 * s,
            letterSpacing: 6 * s,
            color: colors.accent,
            opacity: sp(0),
            transform: `translateY(${(1 - sp(0)) * -20 * s}px)`,
          }}
        >
          {"> "}TODAY IN {labels.topic.toUpperCase()} · {dateLabel.toUpperCase()}
        </span>
        <div style={{ display: "flex", alignItems: "center", gap: 20 * s, marginTop: 10 * s }}>
          <span
            style={{
              fontFamily: display,
              fontWeight: 900,
              fontSize: 170 * s,
              color: colors.text,
              letterSpacing: -6 * s,
              opacity: sp(2),
              transform: `translateX(${(1 - sp(2)) * -80 * s}px)`,
            }}
          >
            TOP
          </span>
          <span
            style={{
              fontFamily: display,
              fontWeight: 900,
              fontSize: 330 * s,
              lineHeight: 0.8,
              backgroundImage: `linear-gradient(160deg, ${colors.hot}, ${colors.primary} 60%, ${colors.accent})`,
              WebkitBackgroundClip: "text",
              backgroundClip: "text",
              color: "transparent",
              transform: `scale(${interpolate(five, [0, 1], [3, 1])}) rotate(${interpolate(five, [0, 1], [25, -4])}deg)`,
              opacity: Math.min(1, five * 2),
              filter: `drop-shadow(0 0 ${30 * s}px ${colors.hot}88)`,
            }}
          >
            {stories.length}
          </span>
        </div>
        <span
          style={{
            fontFamily: display,
            fontWeight: 900,
            fontSize: 92 * s,
            color: colors.text,
            letterSpacing: -2 * s,
            marginTop: 6 * s,
            opacity: sp(10),
            transform: `translateY(${(1 - sp(10)) * 40 * s}px)`,
          }}
        >
          {labels.introSubtitle.toUpperCase()}
        </span>
      </div>

      {stories.map((story, i) => {
        // i = 0 is the lowest rank ... the last one is #1 (on top, centred, hidden)
        const offset = i - (stories.length - 1) / 2;
        const p = sp(8 + i * 3, 14, 150);
        const isTop = story.rank === 1;
        const fanAngle = isTop ? 0 : offset * 9;
        const x = deckCenterX - cardW / 2 + (isTop ? 0 : offset * spread * s);
        return (
          <div
            key={story.rank}
            style={{
              position: "absolute",
              left: x,
              top: deckTop + (isTop ? -10 * s : Math.abs(offset) * 26 * s),
              width: cardW,
              height: cardH,
              borderRadius: 28 * s,
              overflow: "hidden",
              border: `${4 * s}px solid ${isTop ? colors.hot : "rgba(255,255,255,0.25)"}`,
              background: colors.bgAlt,
              boxShadow: `0 ${24 * s}px ${50 * s}px rgba(0,0,0,0.6)`,
              zIndex: isTop ? 10 : 5 - Math.abs(offset),
              opacity: p,
              transform: `translateY(${(1 - p) * 400 * s}px) rotate(${fanAngle + Math.sin((frame + i * 20) / 18) * 1.5}deg)`,
            }}
          >
            {story.image ? (
              <Img
                src={staticFile(story.image)}
                style={{ width: "100%", height: "100%", objectFit: "cover", filter: isTop ? `blur(${18 * s}px) brightness(0.7)` : "none", transform: isTop ? "scale(1.2)" : undefined }}
              />
            ) : (
              <div
                style={{
                  width: "100%",
                  height: "100%",
                  display: "flex",
                  alignItems: "flex-start",
                  // text sits in the corner the neighbouring cards do not cover
                  justifyContent: offset > 0 ? "flex-end" : "flex-start",
                  padding: 18 * s,
                  boxSizing: "border-box",
                  background: `radial-gradient(circle at 50% 35%, ${colors.primary}99, transparent 70%), ${colors.bgAlt}`,
                  fontFamily: mono,
                  fontWeight: 800,
                  fontSize: 24 * s,
                  color: colors.accent,
                  letterSpacing: 2 * s,
                }}
              >
                {isTop ? null : story.category.toUpperCase()}
              </div>
            )}
            <div
              style={{
                position: "absolute",
                inset: 0,
                display: "flex",
                alignItems: isTop ? "center" : "flex-end",
                justifyContent: isTop ? "center" : offset > 0 ? "flex-end" : "flex-start",
                padding: 16 * s,
                background: isTop ? `${colors.bg}55` : "linear-gradient(180deg, transparent 50%, rgba(0,0,0,0.7))",
              }}
            >
              <span
                style={{
                  fontFamily: display,
                  fontWeight: 900,
                  fontSize: (isTop ? 170 : 56) * s,
                  color: isTop ? colors.text : "#fff",
                  textShadow: `0 0 ${20 * s}px ${isTop ? colors.hot : "#000"}`,
                  transform: isTop ? `scale(${1 + Math.sin(frame / 6) * 0.05})` : undefined,
                }}
              >
                {isTop ? "?" : `#${story.rank}`}
              </span>
            </div>
          </div>
        );
      })}
    </AbsoluteFill>
  );
};
