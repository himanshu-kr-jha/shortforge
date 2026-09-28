import React from "react";
import { AbsoluteFill, Html5Audio, Sequence, interpolate, staticFile } from "remotion";
import { VideoProps } from "../types";
import { useLine } from "../timeline";
import { useLayout } from "../layout";
import { Background } from "../components/Background";
import { Header, ProgressBar } from "../components/Header";
import { Captions } from "../components/Captions";
import { OutroScene } from "../components/OutroScene";
import { Presenter, Box } from "../components/Presenter";
import { Gesture, Mood } from "../components/Mascot";
import { FormatIntro } from "./common";
import { QuizScene } from "./QuizScene";
import { TrueFalseScene } from "./TrueFalseScene";
import { ExplainerScene } from "./ExplainerScene";
import { SketchScene } from "./SketchScene";
import { SfxTrack } from "./SfxTrack";

const SCENES = { quiz: QuizScene, truefalse: TrueFalseScene, explainer: ExplainerScene, sketch: SketchScene };

/** Shell for every non-countdown format: background, intro, scene, presenter, captions, outro, audio. */
export const FormatVideo: React.FC<VideoProps> = (props) => {
  const { brand, labels, lines = [], format = "quiz" } = props;
  const { s } = useLayout();
  const { line, t, since, fps } = useLine(lines);
  const Scene = SCENES[format as keyof typeof SCENES] ?? QuizScene;
  const hook = lines[0]?.kind === "hook" ? lines[0] : null;
  const outro = lines[lines.length - 1]?.kind === "outro" ? lines[lines.length - 1] : null;
  const inIntro = !!hook && t < hook.end;
  const inOutro = !!outro && t >= outro.start;
  const sketch = format === "sketch";

  const intro = {
    quiz: { title: "News Quiz", subtitle: `Can you get ${lines.filter((l) => l.kind === "question").length} out of ${lines.filter((l) => l.kind === "question").length}?` },
    truefalse: { title: "True or False?", subtitle: "Spot the fake news" },
    explainer: { title: "Explained", subtitle: hook?.title ?? "" },
  }[format as "quiz" | "truefalse" | "explainer"];

  // where the host stands, and what it does, in each phase
  let box: Box = { x: 770 * s, y: 1010 * s, w: 250 * s };
  let gesture: Gesture = since < fps * 1.5 ? "point" : "idle";
  if (format === "explainer") box = { x: 790 * s, y: 900 * s, w: 230 * s };
  if (inIntro) {
    box = { x: 380 * s, y: 900 * s, w: 320 * s };
    gesture = "cheer";
  }
  if (inOutro) {
    box = { x: 395 * s, y: 1000 * s, w: 290 * s };
    gesture = "wave";
  }
  const mood = (line?.mood as Mood) || "neutral";
  const counter =
    line?.number && !inIntro && !inOutro
      ? `${props.formatLabel} · ${line.number}/${lines.filter((l) => l.kind === lines.find((x) => x.number)?.kind).length}`
      : props.formatLabel;

  return (
    <AbsoluteFill style={{ backgroundColor: brand.colors.bg }}>
      <Background brand={brand} energy={inIntro ? 0 : 1} />

      {inIntro && intro ? <FormatIntro brand={brand} labels={labels} title={intro.title} subtitle={intro.subtitle} dateLabel={props.dateLabel} /> : null}
      {!inIntro && !inOutro ? <Scene {...props} /> : sketch && !inOutro ? <Scene {...props} /> : null}
      {inOutro && outro ? (
        <Sequence from={Math.round(outro.start * fps)} layout="none">
          <OutroScene brand={brand} labels={labels} />
        </Sequence>
      ) : null}

      {props.mascot?.enabled && !sketch ? (
        <Presenter brand={brand} box={box} mood={inOutro ? "happy" : mood} gesture={gesture} speaking since={inIntro ? 0 : Math.round((line?.start ?? 0) * fps)} />
      ) : null}

      <Header brand={brand} ranks={[]} chip={counter} editionLabel={props.editionLabel} dateLabel={props.dateLabel} activeRank={null} />
      {!sketch ? <Captions brand={brand} words={lines.flatMap((l) => l.words)} /> : null}
      <ProgressBar brand={brand} total={Math.round(props.durationSeconds * fps)} />

      <Html5Audio src={staticFile("voice.wav")} />
      <SfxTrack lines={lines} />
      {props.music ? (
        <Html5Audio
          src={staticFile(props.music)}
          loop
          volume={(fr) =>
            props.musicVolume *
            interpolate(fr, [0, 12, Math.round(props.durationSeconds * fps) - 36, Math.round(props.durationSeconds * fps)], [0, 1, 1, 0], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            })
          }
        />
      ) : null}
    </AbsoluteFill>
  );
};
