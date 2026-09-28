export type Word = { text: string; start: number; end: number };

export type Brand = {
  name: string;
  handle: string;
  tagline: string;
  /** Logo tile glyph (1-2 characters) and the wordmark split: plain part + gradient part. */
  logo: { glyph: string; plain: string; accent: string };
  colors: {
    bg: string;
    bgAlt: string;
    primary: string;
    accent: string;
    hot: string;
    text: string;
    muted: string;
  };
};

export type Segment = { start: number; end: number; voiceEnd: number; words: Word[] };

export type Story = Segment & {
  rank: number;
  headline: string;
  category: string;
  keyFact: string;
  source: string;
  image: string | null;
  /** Mascot expression for this story: neutral, excited, happy, shocked, thinking, sad, laughing. */
  mood?: string;
};

/** Niche-specific on-screen text. */
export type Labels = {
  topic: string; // e.g. "TECH" -> "TODAY IN TECH", "TOP 5 TECH"
  introSubtitle: string; // e.g. "TECH STORIES" under "TOP 5"
  outroLine: string; // e.g. "NEW EPISODES EVERY MORNING & EVENING"
};

/** One spoken line with its timing (from the pipeline's timeline) and format-specific on-screen data. */
export type Line = Segment & {
  speaker: "host" | "cohost";
  text: string;
  tail?: string;
  mood: string;
  kind: string;
  pauseAfter: number;
  story?: number;
  number?: number;
  // sketch / explainer
  title?: string;
  keyFact?: string;
  label?: string;
  keyText?: string;
  // quiz
  question?: string;
  options?: string[];
  answer?: number;
  // true or false
  claim?: string;
  isTrue?: boolean;
};

export type VideoProps = {
  format?: "countdown" | "sketch" | "quiz" | "truefalse" | "explainer";
  formatLabel?: string;
  theme?: string;
  lines?: Line[];
  /** the stories used, in order: source name and optional image path */
  sources?: { source: string; image: string | null }[];
  cohost?: { name: string };
  brand: Brand;
  labels: Labels;
  editionLabel: string;
  dateLabel: string;
  durationSeconds: number;
  hook: Segment;
  stories: Story[];
  outro: Segment;
  coverHeadline: string;
  music: string | null;
  musicVolume: number;
  mascot?: { enabled: boolean; name?: string };
};
