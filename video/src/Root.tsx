import React from "react";
import { CalculateMetadataFunction, Composition, Still } from "remotion";
import { ShortVideo } from "./ShortVideo";
import { ChannelBanner, Cover, LogoLockup, ProfilePicture } from "./Stills";
import { VideoProps } from "./types";
import config from "../../config.json";
import sampleProps from "./sample-props.json";

// Real renders always pass --props; the sample only feeds `npx remotion studio`.
const FPS = config.video.fps;
const sample = sampleProps as unknown as VideoProps;
const brandOnly = { brand: sample.brand };

const fromTimeline: CalculateMetadataFunction<VideoProps> = ({ props }) => ({
  durationInFrames: Math.ceil(props.durationSeconds * FPS),
});

export const RemotionRoot: React.FC = () => (
  <>
    <Composition id="Short" component={ShortVideo} width={1080} height={1920} fps={FPS} durationInFrames={1} defaultProps={sample} calculateMetadata={fromTimeline} />
    <Composition id="Landscape" component={ShortVideo} width={1920} height={1080} fps={FPS} durationInFrames={1} defaultProps={sample} calculateMetadata={fromTimeline} />
    <Still id="Cover" component={Cover} width={1080} height={1920} defaultProps={sample} />
    <Still id="CoverLandscape" component={Cover} width={1280} height={720} defaultProps={sample} />
    <Still id="ProfilePicture" component={ProfilePicture} width={800} height={800} defaultProps={brandOnly} />
    <Still id="LogoLockup" component={LogoLockup} width={1600} height={400} defaultProps={brandOnly} />
    <Still id="ChannelBanner" component={ChannelBanner} width={2560} height={1440} defaultProps={brandOnly} />
  </>
);
