import { useVideoConfig } from "remotion";

/**
 * Vertical (9:16) is the primary format. Shorts/Reels overlay their own UI on the
 * bottom ~20% and the right edge, so vertical content stays inside `safe`.
 */
export const useLayout = () => {
  const { width, height } = useVideoConfig();
  const vertical = height > width;
  return {
    width,
    height,
    vertical,
    // scale factor relative to the 1080px short side
    s: Math.min(width, height) / 1080,
    safe: vertical
      ? { top: 70, bottom: height - 400, left: 60, right: width - 60 }
      : { top: 50, bottom: height - 60, left: 80, right: width - 80 },
  };
};
