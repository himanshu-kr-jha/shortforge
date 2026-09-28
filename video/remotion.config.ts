import { Config } from "@remotion/cli/config";

Config.setVideoImageFormat("jpeg");
Config.setJpegQuality(92);
Config.setConcurrency(4); // 4 Chrome workers: keeps rendering within a 16 GB laptop's memory alongside other apps
Config.setChromiumOpenGlRenderer("angle");
