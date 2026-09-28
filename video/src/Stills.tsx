import React from "react";
import { AbsoluteFill, Img, staticFile } from "remotion";
import { Brand, VideoProps } from "./types";
import { Background } from "./components/Background";
import { LogoMark, Wordmark } from "./components/Logo";
import { display, mono } from "./fonts";
import { ThemeProvider, makeTheme, useTheme } from "./theme";
import { useLayout } from "./layout";

/** Reel cover / Shorts thumbnail: the #1 story image with the teaser headline. */
export const Cover: React.FC<VideoProps> = (props) => {
  const theme = makeTheme(props.theme, props.brand);
  const brand = { ...props.brand, colors: theme.colors };
  return (
    <ThemeProvider theme={theme}>
      <CoverInner {...props} brand={brand} />
    </ThemeProvider>
  );
};

const CoverInner: React.FC<VideoProps> = ({ brand, labels, stories, coverHeadline, dateLabel, format, formatLabel, sources = [] }) => {
  const { s, vertical, width, height } = useLayout();
  const countdown = !format || format === "countdown";
  const top = countdown ? stories.find((st) => st.rank === 1) : { image: sources[0]?.image ?? null };
  const theme = useTheme(brand);
  const { colors } = brand;
  const kicker = countdown ? `TOP ${stories.length} ${labels.topic.toUpperCase()}` : `${(formatLabel ?? "").toUpperCase()} · ${labels.topic.toUpperCase()}`;
  const badge = countdown ? `+ ${stories.length - 1} MORE STORIES` : format === "quiz" ? "CAN YOU GET 3/3?" : format === "truefalse" ? "SPOT THE FAKE" : format === "sketch" ? "WATCH THEM REACT" : "EXPLAINED IN 60S";
  return (
    <AbsoluteFill>
      <Background brand={brand} />
      {top?.image ? (
        <Img
          src={staticFile(top.image)}
          style={{ position: "absolute", inset: 0, width, height, objectFit: "cover", opacity: 0.55 }}
        />
      ) : null}
      <AbsoluteFill style={{ background: `linear-gradient(180deg, ${colors.bg}ee 0%, ${colors.bg}33 40%, ${colors.bg}33 55%, ${colors.bg}f5 85%)` }} />
      <AbsoluteFill style={{ padding: vertical ? `${260 * s}px ${70 * s}px` : `${80 * s}px`, display: "flex", flexDirection: "column", gap: 24 * s }}>
        <div style={{ display: "flex", alignItems: "center", gap: 18 * s }}>
          <LogoMark brand={brand} size={90 * s} />
          <Wordmark brand={brand} size={56 * s} />
        </div>
        <span style={{ fontFamily: mono, fontWeight: 800, fontSize: 34 * s, color: colors.accent, letterSpacing: 4 * s, marginTop: 30 * s }}>
          {kicker} · {dateLabel.toUpperCase()}
        </span>
        <span
          style={{
            fontFamily: theme.display,
            fontWeight: theme.displayWeight,
            fontSize: (vertical ? 150 : 120) * s,
            lineHeight: 0.95,
            letterSpacing: -4 * s,
            color: colors.text,
            textTransform: "uppercase",
            textShadow: `0 ${8 * s}px ${40 * s}px rgba(0,0,0,0.7)`,
          }}
        >
          {coverHeadline}
        </span>
        <span
          style={{
            alignSelf: "flex-start",
            fontFamily: display,
            fontWeight: 900,
            fontSize: 54 * s,
            color: "#fff",
            background: colors.hot,
            padding: `${10 * s}px ${30 * s}px`,
            borderRadius: 18 * s,
            transform: "rotate(-3deg)",
            marginTop: 10 * s,
          }}
        >
          {badge}
        </span>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

/** Profile picture (square; platforms crop it to a circle, so the mark sits well inside). */
export const ProfilePicture: React.FC<{ brand: Brand }> = ({ brand }) => {
  const { width } = useLayout();
  return (
    <AbsoluteFill style={{ background: brand.colors.bg, alignItems: "center", justifyContent: "center" }}>
      <LogoMark brand={brand} size={width * 0.7} />
    </AbsoluteFill>
  );
};

/** Full logo lockup for watermarks and banners. */
export const LogoLockup: React.FC<{ brand: Brand }> = ({ brand }) => {
  const { height } = useLayout();
  return (
    <AbsoluteFill style={{ background: brand.colors.bg, alignItems: "center", justifyContent: "center", flexDirection: "row", gap: height * 0.08 }}>
      <LogoMark brand={brand} size={height * 0.62} />
      <Wordmark brand={brand} size={height * 0.36} />
    </AbsoluteFill>
  );
};

/** YouTube channel banner 2560x1440; the important part stays in the 1546x423 centre safe area. */
export const ChannelBanner: React.FC<{ brand: Brand }> = ({ brand }) => {
  const { colors } = brand;
  return (
    <AbsoluteFill>
      <Background brand={brand} />
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", flexDirection: "column", gap: 26 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 40 }}>
          <LogoMark brand={brand} size={210} />
          <Wordmark brand={brand} size={150} />
        </div>
        <span style={{ fontFamily: mono, fontWeight: 800, fontSize: 44, color: colors.accent, letterSpacing: 6 }}>
          {brand.tagline.toUpperCase()}
        </span>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
