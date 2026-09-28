import { loadFont as loadMontserrat } from "@remotion/google-fonts/Montserrat";
import { loadFont as loadMono } from "@remotion/google-fonts/JetBrainsMono";

// System Noto fonts cover scripts Montserrat lacks (Devanagari, CJK, ...), so any niche language renders.
const FALLBACK = ', "Noto Sans", "Noto Sans Devanagari", "Noto Sans CJK SC", sans-serif';

export const display = loadMontserrat("normal", {
  weights: ["600", "700", "800", "900"],
  subsets: ["latin", "latin-ext"],
}).fontFamily + FALLBACK;

export const mono = loadMono("normal", {
  weights: ["500", "700", "800"],
  subsets: ["latin"],
}).fontFamily + FALLBACK;
