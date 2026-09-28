"""Make one video for a niche: sources -> script -> voice -> animated video -> upload kit.

Usage:
  run.py <niche>                         # edition picked from the clock (before 14:00 = morning)
  run.py <niche> --edition evening
  run.py <niche> --reuse output/<niche>/2026-09-28-morning   # re-voice/re-render after editing script.json
  run.py <niche> --landscape             # also render a 16:9 version
"""

from __future__ import annotations

import argparse
import json
import random
import re
import shutil
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

from formats import FORMATS, choose as choose_format
from configure import _set as set_value, all_settings
from common import CONFIG, ROOT, load_history, load_niche, log, niche_output, notify, save_history, write_json
from llm import complete_json
from sounds import ensure_assets
from sources import collect, normalize_url
from voice import narrate
from write_script import write_script

VIDEO_DIR = ROOT / "video"
ASSETS = ROOT / "assets"
AUDIO_EXT = {".mp3", ".wav", ".m4a", ".ogg", ".aac"}


def timing(niche: dict) -> tuple[float, float]:
    """(target, max) video seconds: config.json defaults, overridable per niche (comedy and number-heavy niches run longer)."""
    v = {**CONFIG["video"], **niche.get("video", {})}
    return v["targetSeconds"], v["maxSeconds"]


def tighten(lines: list[dict], current_seconds: float, target_seconds: float) -> list[dict]:
    """Shorten the trimmable lines: one LLM request with per-line word budgets, then code enforces the budgets.

    Length is never a validation error (models cannot count reliably, and every retry costs a request).
    Hooks, outros, questions and each line's `tail` (e.g. a punchline) are never shortened.
    """
    idx = [i for i, ln in enumerate(lines) if ln.get("trim")]
    if not idx:
        return lines
    ratio = target_seconds / current_seconds * 0.92
    texts = [lines[i]["text"] for i in idx]
    budgets = [max(10, int(len(x.split()) * ratio)) for x in texts]
    log(f"  video is {current_seconds:.0f}s, shortening {len(idx)} lines from {sum(len(x.split()) for x in texts)} to ~{sum(budgets)} words")
    schema = {"type": "object", "properties": {"texts": {"type": "array", "items": {"type": "string"},
                                                         "minItems": len(texts), "maxItems": len(texts)}},
              "required": ["texts"]}
    listing = "\n".join(f"{i + 1}. (max {b} words) {x}" for i, (x, b) in enumerate(zip(texts, budgets)))
    prompt = (
        "Shorten each numbered text below to at most the word count given in brackets. Keep the same language, "
        "the key numbers and names, the speaker's voice and the punchy spoken tone. "
        f"Do not add facts. Return all {len(texts)} texts in order.\n\n{listing}"
    )
    try:
        short = complete_json(prompt, schema, "shortened", 0.3)["texts"]
        short = [s if len(s.split()) < len(x.split()) else x for s, x in zip(short, texts)]  # keep only real cuts
    except RuntimeError as exc:
        log(f"  LLM could not shorten ({exc})")
        short = texts
    out = [dict(ln) for ln in lines]
    for i, text, budget in zip(idx, short, budgets):
        out[i]["text"] = clean_text(trim_to_words(text, budget) if len(text.split()) > budget * 1.2 else text)
    return out


def trim_to_words(text: str, budget: int) -> str:
    """Deterministic fallback: keep whole sentences within the word budget; if even the first sentence is too long,
    cut it at a clause boundary (dash, semicolon, colon, comma). Never cuts mid-clause."""
    words = lambda s: len(s.split())  # noqa: E731
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    kept = [sentences[0]]
    for s in sentences[1:]:
        if words(" ".join(kept + [s])) > budget:
            break
        kept.append(s)
    result = " ".join(kept)
    if words(result) <= budget * 1.2:
        return result
    clauses = re.split(r"\s*(?:—|–|;|:|,)\s+", sentences[0])
    out = clauses[0]
    for c in clauses[1:]:
        if words(out + ", " + c) > budget and words(out) >= 10:
            break
        out += ", " + c
    return out.rstrip(",;:—– ") + "."


def clean_text(text: str) -> str:
    """Models sometimes shorten with '...'; spoken text should end sentences properly."""
    text = re.sub(r"(?:\.\.\.|…)\s+", ". ", text)
    return re.sub(r"\s*(?:\.\.\.|…)\s*$", ".", text).strip()


def fit_length(lines: list[dict], niche: dict, voices: dict, gap: float, run_dir: Path) -> tuple[list[dict], dict]:
    target_seconds, max_seconds = timing(niche)
    timeline = narrate(lines, voices, gap, run_dir)
    for _ in range(2):
        if timeline["duration"] <= max_seconds:
            break
        lines = tighten(lines, timeline["duration"], target_seconds)
        timeline = narrate(lines, voices, gap, run_dir)
    if timeline["duration"] > max_seconds:
        ratio = target_seconds / timeline["duration"]
        log(f"  still {timeline['duration']:.0f}s: trimming the longest lines to whole sentences")
        lines = [{**ln, "text": trim_to_words(ln["text"], max(10, int(len(ln["text"].split()) * ratio)))} if ln.get("trim") else ln
                 for ln in lines]
        timeline = narrate(lines, voices, gap, run_dir)
    return lines, timeline


def pick_music(niche: dict, run_dir: Path, history: dict) -> str:
    tracks = []
    for folder in (ROOT / "niches" / niche["slug"] / "music", ASSETS / "music"):
        if folder.is_dir():
            tracks = sorted(p for p in folder.iterdir() if p.suffix.lower() in AUDIO_EXT)
        if tracks:
            break
    if tracks:
        recent = [r.get("music") for r in history["runs"][-(len(tracks) - 1):]] if len(tracks) > 1 else []
        track = random.choice([t for t in tracks if t.name not in recent] or tracks)
    else:
        track = ASSETS / "generated" / "generated-bed.wav"
    shutil.copy(track, run_dir / "public" / f"music{track.suffix.lower()}")
    log(f"  music: {track.name}")
    return track.name


def build_props(niche: dict, script: dict, timeline: dict, edition: str, date: datetime, fmt) -> dict:
    segs = timeline["segments"]
    music = next((p.name for p in (Path(timeline["publicDir"])).glob("music.*")), None)
    stories = script["sources"]
    props = {
        "format": fmt.NAME,
        "formatLabel": fmt.LABEL.format(n=len(stories)),
        "brand": niche["channel"],
        "labels": niche["labels"],
        "theme": niche.get("theme", "neon"),
        "editionLabel": niche["editions"][edition]["label"],
        "dateLabel": date.strftime("%b %-d"),
        "durationSeconds": timeline["duration"],
        "lines": segs,
        "sources": [{k: s[k] for k in ("source", "image")} for s in stories],
        "coverHeadline": script["coverHeadline"],
        "music": music,
        "musicVolume": CONFIG["video"]["musicVolume"],
        "mascot": {"enabled": niche.get("mascot", {}).get("enabled", False), "name": niche.get("mascot", {}).get("name", "")},
        "cohost": {"name": niche.get("cohost", {}).get("name", "")},
    }
    if fmt.NAME == "countdown":
        # the countdown scenes use hook / stories / outro
        timed = lambda s: {"start": s["start"], "end": s["end"], "voiceEnd": s["voiceEnd"], "words": s["words"]}  # noqa: E731
        props["hook"], props["outro"] = timed(segs[0]), timed(segs[-1])
        props["stories"] = [
            {**timed(s), "rank": s["rank"], "headline": s["headline"], "category": s["category"], "keyFact": s["keyFact"],
             "mood": s["mood"], **props["sources"][s["story"]]}
            for s in segs if s["kind"] == "story"
        ]
    else:
        props["hook"], props["outro"] = {"start": 0, "end": 0, "voiceEnd": 0, "words": []}, {"start": timeline["duration"], "end": timeline["duration"], "voiceEnd": timeline["duration"], "words": []}
        props["stories"] = []
    return props


def render(composition: str, out: Path, run_dir: Path, still: bool = False) -> None:
    cmd = ["npx", "remotion", "still" if still else "render", "src/index.ts", composition, str(out),
           f"--props={run_dir / 'props.json'}", f"--public-dir={run_dir / 'public'}", "--log=error"]
    if not still:
        cmd += ["--codec=h264", "--crf=18", "--audio-codec=aac", "--audio-bitrate=192k"]
    log(f"  rendering {composition} -> {out.name}")
    subprocess.run(cmd, cwd=VIDEO_DIR, check=True)
    if not still:
        normalize_loudness(out)


def normalize_loudness(video: Path) -> None:
    """Shorts/Reels play back around -14 LUFS; match it so the voice is never quieter than neighbouring videos."""
    tmp = video.with_suffix(".norm.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(video), "-c:v", "copy",
                    "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "48000", "-c:a", "aac", "-b:a", "192k",
                    "-movflags", "+faststart", str(tmp)], check=True)
    tmp.replace(video)


def write_metadata(niche: dict, script: dict, lines: list[dict], run_dir: Path) -> None:
    tags = list(dict.fromkeys(h.lstrip("#") for h in ["shorts", *niche.get("baseHashtags", []), *script["hashtags"]]))
    yt_hashtags = " ".join(f"#{h}" for h in tags[:12])
    ig_hashtags = " ".join(f"#{h}" for h in tags[:25] if h != "shorts")
    sources = "\n".join(f"- {s['source']}: {s['url']}" for s in script["sources"])
    yt_tags = ", ".join(script["youtubeTags"])
    while len(yt_tags) > 480:
        yt_tags = yt_tags.rsplit(", ", 1)[0]
    meta = {
        "youtube": {"title": script["youtubeTitle"][:100],
                    "description": f"{script['youtubeDescription']}\n\nSources:\n{sources}\n\n{yt_hashtags}",
                    "tags": yt_tags},
        "instagram": {"caption": f"{script['instagramCaption']}\n\n{ig_hashtags}"},
        "pinnedComment": script["pinnedComment"],
    }
    write_json(run_dir / "metadata.json", meta)
    fence = "```"
    md = f"""# Upload kit: {niche['channel']['name']} ({script['format']})

Video: `short.mp4` (9:16) · Cover: `cover.jpg`

## YouTube Shorts

**Title**
{fence}
{meta['youtube']['title']}
{fence}

**Description**
{fence}
{meta['youtube']['description']}
{fence}

**Tags** (YouTube Studio → Show more → Tags)
{fence}
{meta['youtube']['tags']}
{fence}

**Pinned comment**
{fence}
{meta['pinnedComment']}
{fence}

## Instagram Reels

Cover: "Edit cover → Add from camera roll" → `cover.jpg`

**Caption**
{fence}
{meta['instagram']['caption']}
{fence}

## Fact-check before posting

"""
    names = {"host": niche.get("mascot", {}).get("name") or "Host", "cohost": niche.get("cohost", {}).get("name") or "Co-host"}
    for ln in lines:
        who = f"{names[ln['speaker']]}: " if script["format"] == "sketch" else ""
        tail = f" *{ln['tail']}*" if ln.get("tail") else ""
        md += f"- {who}{ln['text']}{tail}\n"
    md += "\nSources:\n" + sources + "\n"
    (run_dir / "UPLOAD.md").write_text(md)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("niche")
    ap.add_argument("--edition")
    ap.add_argument("--format", help=f"force a format ({', '.join(FORMATS)}); default: rotate through the niche's formats")
    ap.add_argument("--reuse", type=Path, help="existing run directory to re-voice and re-render")
    ap.add_argument("--landscape", action="store_true", help="also render a 16:9 version")
    ap.add_argument("--no-render", action="store_true")
    ap.add_argument("--set", action="append", default=[], metavar="KEY=VALUE",
                    help="override a niche setting for this video only, e.g. --set theme=paper (repeatable)")
    args = ap.parse_args()

    niche = load_niche(args.niche)
    for override in args.set:
        key, _, raw = override.partition("=")
        setting = all_settings(niche).get(key)
        if not setting or not raw:
            raise SystemExit(f"--set {override}: unknown setting or missing value (see ./forge.sh keys)")
        try:
            set_value(niche, key, setting.parse(raw, niche))
        except ValueError as exc:
            raise SystemExit(f"--set {override}: {exc}")
        log(f"override for this video: {key} = {raw}")
    history = load_history(niche["slug"])
    ensure_assets(ASSETS)
    now = datetime.now()

    if args.reuse:
        run_dir = (args.reuse if args.reuse.is_absolute() else ROOT / args.reuse).resolve()
        state = json.loads((run_dir / "run.json").read_text())
        edition, date = state["edition"], datetime.fromisoformat(state["date"])
        script = json.loads((run_dir / "script.json").read_text())
        fmt = FORMATS[script["format"]]
        lines = json.loads((run_dir / "lines.json").read_text()) if (run_dir / "lines.json").exists() else fmt.to_lines(script, niche)
    else:
        edition = args.edition or ("morning" if now.hour < 14 else "evening")
        if edition not in niche["editions"]:
            edition = next(iter(niche["editions"]))
        fmt = choose_format(niche, history, args.format)
        date = now
        run_dir = niche_output(niche["slug"]) / f"{now:%Y-%m-%d}-{edition}"
        if run_dir.exists():
            shutil.rmtree(run_dir)
        (run_dir / "public").mkdir(parents=True)
        write_json(run_dir / "run.json", {"edition": edition, "date": now.isoformat()})

        recent = [r for r in history["runs"] if datetime.fromisoformat(r["date"]) > now - timedelta(days=4)]
        used_urls = {u for r in history["runs"] for u in r["urls"]}
        log(f"== {niche['channel']['name']} · {niche['editions'][edition]['label']} · {fmt.NAME} · {now:%Y-%m-%d} ==")
        log("Fetching sources...")
        lookback = niche["editions"][edition]["lookbackHours"]
        candidates = collect(niche["sources"], lookback, used_urls)
        if len(candidates) < 15:
            log(f"Only {len(candidates)} fresh stories; widening lookback to {lookback * 2}h")
            candidates = collect(niche["sources"], lookback * 2, used_urls)
        write_json(run_dir / "candidates.json", candidates)
        script = write_script(niche, fmt, candidates, niche["editions"][edition]["label"], now.strftime("%A, %B %-d, %Y"),
                              [t for r in recent for t in r["titles"]], run_dir)
        write_json(run_dir / "script.json", script)
        lines = fmt.to_lines(script, niche)

    log("Voicing...")
    voices = {"host": niche["voice"], "cohost": niche.get("cohost", {}).get("voice", niche["voice"])}
    lines, timeline = fit_length(lines, niche, voices, niche["voice"].get("gapSeconds", 0.35), run_dir)
    write_json(run_dir / "lines.json", lines)
    write_json(run_dir / "timeline.json", timeline)

    shutil.copytree(ASSETS / "sfx", run_dir / "public" / "sfx", dirs_exist_ok=True)
    music_name = pick_music(niche, run_dir, history)
    timeline["publicDir"] = str(run_dir / "public")
    write_json(run_dir / "props.json", build_props(niche, script, timeline, edition, date, fmt))
    write_metadata(niche, script, lines, run_dir)

    if not args.no_render:
        log("Rendering...")
        render("Short", run_dir / "short.mp4", run_dir)
        render("Cover", run_dir / "cover.jpg", run_dir, still=True)
        if args.landscape:
            render("Landscape", run_dir / "landscape.mp4", run_dir)
            render("CoverLandscape", run_dir / "thumbnail-landscape.jpg", run_dir, still=True)

    if not args.reuse:
        history["runs"].append({
            "date": date.isoformat(), "edition": edition, "dir": run_dir.name, "music": music_name, "format": fmt.NAME,
            "urls": [normalize_url(s["url"]) for s in script["sources"]],
            "titles": [s["originalTitle"] for s in script["sources"]],
        })
        save_history(niche["slug"], history)

    log(f"Done: {run_dir}  ({fmt.NAME}, {timeline['duration']:.0f}s)")
    notify(f"{niche['channel']['name']}: {edition} {fmt.NAME} video ready", f"{script['youtubeTitle']}\n{run_dir}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        log(f"FAILED: {exc}")
        notify("ShortForge run failed", str(exc)[:200], critical=True)
        raise
