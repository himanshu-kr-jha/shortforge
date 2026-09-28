import React from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";
import { useTalk } from "./Presenter";
import { VideoProps } from "../types";
import { useLayout } from "../layout";
import { Gesture, Mascot, Mood } from "./Mascot";

export const MascotLayer: React.FC<VideoProps> = ({ brand, hook, stories, outro }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { vertical, s, width, height } = useLayout();
  const talk = useTalk();
  const t = frame / fps;

  const story = stories.find((st) => t >= st.start && t < st.end);
  let mood: Mood = "excited";
  let gesture: Gesture = "cheer";
  let since = 0;
  // box = top-left corner + width of the mascot for this scene
  let box = vertical ? { x: 735, y: 885, w: 300 } : { x: width - 360 * s, y: height - 470 * s, w: 300 * s };

  if (story) {
    mood = (story.mood as Mood) || "neutral";
    gesture = frame - Math.round(story.start * fps) < fps * 2.2 ? "point" : "idle";
    since = Math.round(story.start * fps);
    box = vertical ? { x: 770, y: 150, w: 260 } : { x: width - 330 * s, y: 150 * s, w: 250 * s };
  } else if (t >= outro.start) {
    mood = "happy";
    gesture = "wave";
    since = Math.round(outro.start * fps);
    box = vertical ? { x: 395, y: 1000, w: 290 } : { x: width - 360 * s, y: height - 470 * s, w: 300 * s };
  } else if (t >= hook.voiceEnd) {
    gesture = "idle";
  }

  return (
    <div style={{ position: "absolute", left: box.x, top: box.y, width: box.w, pointerEvents: "none" }}>
      <Mascot brand={brand} size={box.w} mood={mood} gesture={gesture} talk={talk} since={since} />
    </div>
  );
};
