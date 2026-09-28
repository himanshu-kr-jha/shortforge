import React from "react";
import { AbsoluteFill, Html5Audio, Sequence, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { VideoProps } from "./types";
import { Background } from "./components/Background";
import { Header, ProgressBar } from "./components/Header";
import { HookScene } from "./components/HookScene";
import { StoryScene } from "./components/StoryScene";
import { OutroScene } from "./components/OutroScene";
import { Captions } from "./components/Captions";
import { MascotLayer } from "./components/MascotLayer";
import { FormatVideo } from "./formats/FormatVideo";
import { ThemeProvider, makeTheme } from "./theme";

const CountdownVideo: React.FC<VideoProps> = (props) => {
  const { brand, labels, hook, stories, outro } = props;
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const f = (sec: number) => Math.round(sec * fps);

  const t = frame / fps;
  const current = stories.find((st) => t >= st.start && t < st.end);
  const allWords = [...hook.words, ...stories.flatMap((st) => st.words), ...outro.words];

  const musicVolume = (fr: number) =>
    props.musicVolume *
    interpolate(fr, [0, f(0.4), durationInFrames - f(1.2), durationInFrames], [0, 1, 1, 0], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });

  return (
    <AbsoluteFill style={{ backgroundColor: brand.colors.bg }}>
      <Background brand={brand} energy={current ? 1 : 0} />

      <Sequence from={0} durationInFrames={f(hook.end)} name="Hook">
        <HookScene brand={brand} labels={labels} stories={stories} dateLabel={props.dateLabel} makeRoom={!!props.mascot?.enabled} />
      </Sequence>

      {stories.map((story) => (
        <Sequence key={story.rank} from={f(story.start)} durationInFrames={f(story.end) - f(story.start)} name={`#${story.rank}`}>
          <StoryScene brand={brand} story={story} />
          <Html5Audio src={staticFile("sfx/whoosh.wav")} volume={0.55} />
          <Sequence from={16}>
            <Html5Audio src={staticFile("sfx/pop.wav")} volume={0.45} />
          </Sequence>
        </Sequence>
      ))}

      <Sequence from={f(outro.start)} name="Outro">
        <OutroScene brand={brand} labels={labels} />
        <Html5Audio src={staticFile("sfx/whoosh.wav")} volume={0.5} />
      </Sequence>

      {props.mascot?.enabled ? <MascotLayer {...props} /> : null}
      <Header brand={brand} ranks={stories.map((st) => st.rank)} editionLabel={props.editionLabel} dateLabel={props.dateLabel} activeRank={current ? current.rank : t >= outro.start ? 0 : null} />
      <Captions brand={brand} words={allWords} />
      <ProgressBar brand={brand} total={durationInFrames} />

      <Html5Audio src={staticFile("voice.wav")} />
      {props.music ? <Html5Audio src={staticFile(props.music)} volume={musicVolume} loop /> : null}
    </AbsoluteFill>
  );
};

/** Every video: apply the niche's theme (fonts, colours), then render its format. */
export const ShortVideo: React.FC<VideoProps> = (props) => {
  const theme = makeTheme(props.theme, props.brand);
  const themed = { ...props, brand: { ...props.brand, colors: theme.colors } };
  return (
    <ThemeProvider theme={theme}>
      {!props.format || props.format === "countdown" ? <CountdownVideo {...themed} /> : <FormatVideo {...themed} />}
    </ThemeProvider>
  );
};
