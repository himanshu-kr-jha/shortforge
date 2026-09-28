import React from "react";
import { AbsoluteFill, interpolate, spring } from "remotion";
import { VideoProps } from "../types";
import { useLayout } from "../layout";
import { useTheme } from "../theme";
import { useLine } from "../timeline";
import { Mood } from "../components/Mascot";
import { Presenter } from "../components/Presenter";
import { Display, FactSticker, StoryImage } from "./common";

/** Two characters banter about one story: news card on top, speech bubble in the middle, characters below. */
export const SketchScene: React.FC<VideoProps> = (props) => {
  const { lines = [], sources = [], brand, mascot, cohost, durationSeconds } = props;
  const theme = useTheme();
  const { s, width } = useLayout();
  const { line, index, since, t, fps, frame } = useLine(lines);
  if (!line) return null;

  const left = 60 * s;
  const w = width - 120 * s;
  const intro = spring({ frame, fps, config: { damping: 13, stiffness: 150 } });
  const bubbleIn = spring({ frame: since, fps, config: { damping: 14, stiffness: 240 } });
  const hostTalks = line.speaker === "host";
  const last = index === lines.length - 1;
  const lastMood = (who: string): Mood =>
    ([...lines.slice(0, index + 1)].reverse().find((l) => l.speaker === who)?.mood as Mood) || "neutral";
  const src = sources[0];
  const card = theme.card(s);

  // speech bubble words, the current one highlighted
  const words = line.words;
  const active = words.findIndex((wd, i) => t >= wd.start - 0.03 && t < (words[i + 1]?.start ?? line.voiceEnd + 0.3));
  const name = hostTalks ? mascot?.name : cohost?.name;

  return (
    <AbsoluteFill>
      {/* news card */}
      <div style={{ opacity: intro, transform: `translateY(${(1 - intro) * -80 * s}px)` }}>
        <StoryImage image={src?.image} source={src?.source ?? ""} box={{ left, top: 175 * s, width: w, height: 360 * s }} durationFrames={Math.round(durationSeconds * fps)} />
        <FactSticker text={line.keyFact ?? ""} progress={spring({ frame: frame - 18, fps, config: { damping: 9, stiffness: 200 } })} left={left - 10 * s} top={480 * s} />
        <div style={{ position: "absolute", left, top: 580 * s, width: w }}>
          <Display text={line.title ?? ""} size={(line.title ?? "").length > 30 ? 58 : 70} color={theme.name === "comic" ? "#fff" : theme.colors.text} style={theme.name === "comic" ? { textShadow: `${6 * s}px ${6 * s}px 0 #111` } : undefined} />
        </div>
      </div>

      {/* speech bubble */}
      <div
        style={{
          position: "absolute",
          left,
          top: 790 * s,
          width: w,
          minHeight: 250 * s,
          ...card,
          padding: `${26 * s}px ${34 * s}px`,
          boxSizing: "border-box",
          transform: `scale(${interpolate(bubbleIn, [0, 1], [0.9, 1])})`,
          transformOrigin: hostTalks ? "20% 100%" : "80% 100%",
          opacity: bubbleIn,
        }}
      >
        <div style={{ fontFamily: theme.body, fontWeight: theme.bodyWeight, fontSize: 30 * s, color: hostTalks ? theme.colors.primary : theme.colors.hot, textTransform: "uppercase", letterSpacing: 2 * s, marginBottom: 10 * s }}>
          {name}
        </div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: `${4 * s}px ${14 * s}px` }}>
          {words.map((wd, i) => (
            <span
              key={i}
              style={{
                fontFamily: theme.display,
                fontWeight: theme.displayWeight,
                fontSize: (words.length > 13 ? 50 : 58) * s,
                lineHeight: 1.15,
                textTransform: theme.upper ? "uppercase" : "none",
                color: i === active ? theme.colors.hot : (card.color as string),
                opacity: t >= wd.start - 0.05 ? 1 : 0.35,
              }}
            >
              {wd.text}
            </span>
          ))}
        </div>
        {/* tail pointing at the speaker */}
        <div
          style={{
            position: "absolute",
            bottom: -34 * s,
            left: hostTalks ? 150 * s : undefined,
            right: hostTalks ? undefined : 150 * s,
            width: 0,
            height: 0,
            borderLeft: `${26 * s}px solid transparent`,
            borderRight: `${26 * s}px solid transparent`,
            borderTop: `${36 * s}px solid ${card.background as string}`,
          }}
        />
      </div>

      {/* characters */}
      <Presenter
        brand={brand}
        box={{ x: 70 * s, y: 1110 * s, w: 320 * s }}
        mood={hostTalks ? (line.mood as Mood) : lastMood("host")}
        gesture={last ? "wave" : hostTalks ? (since < fps * 1.2 ? "point" : "idle") : "idle"}
        speaking={hostTalks}
        since={0}
      />
      <Presenter
        brand={brand}
        box={{ x: 670 * s, y: 1110 * s, w: 320 * s }}
        mood={!hostTalks ? (line.mood as Mood) : lastMood("cohost")}
        gesture={!hostTalks && since < fps * 1.2 ? "point" : "idle"}
        speaking={!hostTalks}
        since={6}
        variant="buddy"
        flip
      />
    </AbsoluteFill>
  );
};
