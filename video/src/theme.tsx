import React, { createContext, useContext } from "react";
import { loadFont as loadBangers } from "@remotion/google-fonts/Bangers";
import { loadFont as loadBaloo } from "@remotion/google-fonts/Baloo2";
import { loadFont as loadMarker } from "@remotion/google-fonts/PermanentMarker";
import { loadFont as loadHand } from "@remotion/google-fonts/PatrickHand";
import { loadFont as loadInter } from "@remotion/google-fonts/Inter";
import { Brand } from "./types";
import { display as montserrat, mono as jetbrains } from "./fonts";

export type ThemeName = "neon" | "comic" | "paper" | "minimal";

const FALLBACK = ', "Noto Sans", "Noto Sans Devanagari", sans-serif';
const bangers = loadBangers("normal", { weights: ["400"], subsets: ["latin"] }).fontFamily + FALLBACK;
const baloo = loadBaloo("normal", { weights: ["600", "800"], subsets: ["latin", "devanagari"] }).fontFamily + FALLBACK;
const marker = loadMarker("normal", { weights: ["400"], subsets: ["latin"] }).fontFamily + FALLBACK;
const hand = loadHand("normal", { weights: ["400"], subsets: ["latin"] }).fontFamily + FALLBACK;
const inter = loadInter("normal", { weights: ["500", "700", "800", "900"], subsets: ["latin"] }).fontFamily + FALLBACK;

export type Theme = {
  name: ThemeName;
  /** headline font and its natural weight */
  display: string;
  displayWeight: number;
  /** small labels, sources, dates */
  body: string;
  bodyWeight: number;
  /** comic and marker fonts look best in capitals */
  upper: boolean;
  colors: Brand["colors"];
  /** styling for cards/panels (question cards, news cards, bubbles) */
  card: (s: number) => React.CSSProperties;
  /** colour for "correct/true" and "wrong/false" */
  good: string;
  bad: string;
  /** caption highlight pill (must stand out from the background) */
  pill: string;
  pillText: string;
  /** backdrop behind brand/outro texts when the background is busy (comic sunburst); null = none */
  panel: React.CSSProperties | null;
};

export const makeTheme = (name: string | undefined, brand: Brand): Theme => {
  const c = brand.colors;
  switch (name) {
    case "comic":
      return {
        name: "comic",
        display: bangers,
        displayWeight: 400,
        body: baloo,
        bodyWeight: 800,
        upper: true,
        colors: c,
        card: (s) => ({
          background: "#fff",
          color: "#111",
          border: `${6 * s}px solid #111`,
          borderRadius: 18 * s,
          boxShadow: `${10 * s}px ${10 * s}px 0 #111`,
        }),
        good: "#2BD46B",
        bad: "#FF3B3B",
        pill: "#111",
        pillText: "#FFE14D",
        panel: { background: "#111", border: "6px solid #111", borderRadius: 22, boxShadow: "10px 10px 0 rgba(0,0,0,0.35)" },
      };
    case "paper":
      return {
        name: "paper",
        display: marker,
        displayWeight: 400,
        body: hand,
        bodyWeight: 400,
        upper: false,
        // light theme: paper background, ink text; brand primary/accent/hot stay as highlights
        colors: { ...c, bg: "#F3EBDD", bgAlt: "#E9DDC7", text: "#1E1B18", muted: "#6B6258" },
        card: (s) => ({
          background: "#FFFDF7",
          color: "#1E1B18",
          borderRadius: 6 * s,
          boxShadow: `0 ${6 * s}px ${18 * s}px rgba(60,40,20,0.22)`,
        }),
        good: "#1F9D55",
        bad: "#D64545",
        pill: c.hot,
        pillText: "#fff",
        panel: null,
      };
    case "minimal":
      return {
        name: "minimal",
        display: inter,
        displayWeight: 900,
        body: inter,
        bodyWeight: 600,
        upper: false,
        colors: c,
        card: (s) => ({
          background: "rgba(255,255,255,0.06)",
          color: c.text,
          border: `${2 * s}px solid rgba(255,255,255,0.12)`,
          borderRadius: 28 * s,
          boxShadow: `0 ${20 * s}px ${50 * s}px rgba(0,0,0,0.35)`,
        }),
        good: "#34D399",
        bad: "#F87171",
        pill: c.primary,
        pillText: "#fff",
        panel: null,
      };
    default:
      return {
        name: "neon",
        display: montserrat,
        displayWeight: 900,
        body: jetbrains,
        bodyWeight: 700,
        upper: false,
        colors: c,
        card: (s) => ({
          background: c.bgAlt,
          color: c.text,
          border: `${4 * s}px solid ${c.primary}`,
          borderRadius: 36 * s,
          boxShadow: `0 ${24 * s}px ${60 * s}px rgba(0,0,0,0.5), 0 0 ${50 * s}px ${c.primary}44`,
        }),
        good: "#2EE59D",
        bad: "#FF4D6D",
        pill: c.primary,
        pillText: "#fff",
        panel: null,
      };
  }
};

const ThemeContext = createContext<Theme | null>(null);

export const ThemeProvider: React.FC<{ theme: Theme; children: React.ReactNode }> = ({ theme, children }) => (
  <ThemeContext.Provider value={theme}>{children}</ThemeContext.Provider>
);

/** Theme of the current video; falls back to neon for components rendered outside a provider (brand stills). */
export const useTheme = (brand?: Brand): Theme => {
  const t = useContext(ThemeContext);
  if (t) return t;
  return makeTheme("neon", brand ?? ({ colors: { bg: "#07080F", bgAlt: "#12142A", primary: "#7C5CFF", accent: "#22D3EE", hot: "#FF3D71", text: "#F5F7FF", muted: "#9AA3C7" } } as Brand));
};
