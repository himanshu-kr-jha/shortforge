"""Create a niche profile from a few answers: the LLM drafts it, every source is verified live.

Usage:
  new_niche.py                                  # interactive
  new_niche.py --name "PitchSide" --topic "football (soccer) news" --audience "..." --language English --voice female
"""

from __future__ import annotations

import argparse
import calendar
import json
import re
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

from common import NICHES_DIR, ROOT, log, write_json
from llm import complete_json
from sources import clean, parse_feed

# Kokoro voices per language: (lang code, female voice, male voice)
LANGUAGES = {
    "english": ("a", "af_heart", "am_michael"),
    "english (uk)": ("b", "bf_emma", "bm_george"),
    "hindi": ("h", "hf_alpha", "hm_omega"),
    "spanish": ("e", "ef_dora", "em_alex"),
    "french": ("f", "ff_siwis", "ff_siwis"),
    "italian": ("i", "if_sara", "im_nicola"),
    "portuguese": ("p", "pf_dora", "pm_alex"),
}

PROFILE_SCHEMA = {
    "type": "object",
    "properties": {
        "handle": {"type": "string", "description": "Suggested social handle starting with @, lowercase, no spaces."},
        "tagline": {"type": "string", "description": "Short catchy tagline that fits the channel's formats (only mention 'Top 5' if countdown is the only format), e.g. 'Football news, served with jokes. Daily.'"},
        "logoGlyph": {"type": "string", "description": "1 or 2 characters for the square logo tile (a digit or initials)."},
        "wordmarkPlain": {"type": "string", "description": "First part of the channel name, shown in white."},
        "wordmarkAccent": {"type": "string", "description": "Rest of the channel name, shown in the gradient. plain + accent must equal the channel name exactly."},
        "colors": {
            "type": "object",
            "description": "Dark-theme palette as #RRGGBB hex. bg/bgAlt very dark; primary+accent vivid and fitting the niche; hot a bold highlight; text near-white; muted greyish.",
            "properties": {k: {"type": "string", "pattern": "^#[0-9A-Fa-f]{6}$"} for k in ("bg", "bgAlt", "primary", "accent", "hot", "text", "muted")},
            "required": ["bg", "bgAlt", "primary", "accent", "hot", "text", "muted"],
        },
        "topicLabel": {"type": "string", "description": "1-2 word on-screen topic, e.g. 'Football' (used as 'TODAY IN FOOTBALL', 'TOP 5 FOOTBALL')."},
        "introSubtitle": {"type": "string", "description": "2-3 words under 'TOP 5', e.g. 'Football Stories'."},
        "pickRules": {"type": "string", "description": "What makes a story worth picking for this audience (one paragraph)."},
        "avoid": {"type": "string", "description": "What to never pick (one sentence)."},
        "tone": {"type": "string", "description": "Narration tone in one sentence."},
        "categories": {"type": "array", "items": {"type": "string"}, "minItems": 6, "maxItems": 14, "description": "One-word on-screen category chips."},
        "baseHashtags": {"type": "array", "items": {"type": "string"}, "minItems": 2, "maxItems": 5, "description": "Evergreen hashtags without '#'."},
        "feeds": {
            "type": "array",
            "minItems": 10,
            "maxItems": 25,
            "description": "Real, currently working RSS/Atom feed URLs of well-known publications covering this niche daily. Prefer official /feed or /rss URLs you are confident exist.",
            "items": {"type": "object", "properties": {"name": {"type": "string"}, "url": {"type": "string"}}, "required": ["name", "url"]},
        },
        "subreddits": {"type": "array", "items": {"type": "string"}, "maxItems": 5, "description": "Active subreddit names (without r/) where this niche's news is discussed."},
        "theme": {"type": "string", "enum": ["neon", "comic", "paper", "minimal"],
                  "description": "Visual theme that fits the niche's vibe: neon = futuristic/tech, comic = loud, fun, sports, entertainment, paper = friendly, educational, lifestyle, minimal = serious, finance, business."},
        "mascotName": {"type": "string", "description": "Catchy 1-word name for the host character (an original cartoon robot)."},
        "mascotPersonality": {"type": "string", "description": "One-line personality of the host, fitting the niche (e.g. 'an over-dramatic robot superfan')."},
        "cohostName": {"type": "string", "description": "Catchy 1-word name for the sidekick character."},
        "cohostPersonality": {"type": "string", "description": "One-line personality that contrasts with the host (e.g. 'a sarcastic veteran who is never impressed')."},
        "useHackerNews": {"type": "boolean", "description": "True only for tech, startup, science or developer niches."},
        "useDailyDev": {"type": "boolean", "description": "True only for software-development niches."},
    },
    "required": ["handle", "tagline", "logoGlyph", "wordmarkPlain", "wordmarkAccent", "colors", "topicLabel", "introSubtitle",
                 "pickRules", "avoid", "tone", "categories", "baseHashtags", "feeds", "subreddits", "useHackerNews", "useDailyDev",
                 "theme", "mascotName", "mascotPersonality", "cohostName", "cohostPersonality"],
}


def ask(prompt: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    answer = input(f"{prompt}{suffix}: ").strip()
    return answer or default


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def verify_feed(src: dict) -> tuple[dict, str | None]:
    """A feed is usable if it parses and has at least 3 entries, the newest within 7 days."""
    feed = None
    for attempt in range(3):
        try:
            feed = parse_feed(src["url"])
            break
        except Exception as exc:  # noqa: BLE001
            if "reddit.com" not in src["url"] or attempt == 2:
                return src, f"unreachable ({exc.__class__.__name__})"
            time.sleep(4)  # Reddit rate-limits bursts; back off and retry
    src["_sample"] = [clean(e.get("title"), 100) for e in feed.entries[:6]]
    stamps = [e.get("published_parsed") or e.get("updated_parsed") for e in feed.entries]
    stamps = [s for s in stamps if s]
    if len(feed.entries) < 3 or not stamps:
        return src, "not a working feed"
    newest = datetime.fromtimestamp(max(calendar.timegm(s) for s in stamps), tz=timezone.utc)
    if newest < datetime.now(timezone.utc) - timedelta(days=7):
        return src, f"stale (last post {newest:%Y-%m-%d})"
    return src, None


def drop_off_topic(sources: list[dict], topic: str) -> list[dict]:
    """A live feed can still be the wrong feed (e.g. a publisher's general news): judge relevance from recent headlines."""
    if not sources:
        return sources
    listing = "\n".join(f"{i}. {s['name']}: " + " | ".join(s["_sample"]) for i, s in enumerate(sources))
    verdict = complete_json(
        f"Niche: {topic}\nFor each numbered feed below (name and recent headlines), decide if it is mainly about this niche. "
        f"Return the numbers of the feeds that are.\n\n{listing}",
        {"type": "object", "properties": {"relevant": {"type": "array", "items": {"type": "integer"}}}, "required": ["relevant"]},
        "relevance", 0.1)
    keep = set(verdict["relevant"])
    for i, s in enumerate(sources):
        if i not in keep:
            log(f"  DROP {s['name']}: off-topic headlines, e.g. \"{s['_sample'][0] if s['_sample'] else ''}\"")
    return [{k: v for k, v in s.items() if k != "_sample"} for i, s in enumerate(sources) if i in keep]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--name")
    ap.add_argument("--topic")
    ap.add_argument("--audience")
    ap.add_argument("--language")
    ap.add_argument("--voice", choices=["female", "male"])
    ap.add_argument("--count", type=int)
    ap.add_argument("--style", choices=["news", "comedy"])
    ap.add_argument("--mascot", choices=["yes", "no"])
    ap.add_argument("--formats", help="comma separated: sketch,quiz,truefalse,explainer,countdown (rotated per video)")
    ap.add_argument("--theme", choices=["neon", "comic", "paper", "minimal"])
    ap.add_argument("--times", help="posting times, e.g. 07:00,17:30 (one edition per time)")
    ap.add_argument("--slug")
    args = ap.parse_args()

    print("\n== New ShortForge niche ==\n", flush=True)
    name = args.name or ask("Channel name (e.g. PitchSide)")
    topic = args.topic or ask("What is the niche about? (e.g. 'football (soccer) news: transfers, matches, clubs')")
    audience = args.audience or ask("Who is the audience?", "Fans who want the day's key news fast")
    language = (args.language or ask(f"Language ({', '.join(LANGUAGES)})", "english")).lower()
    if language not in LANGUAGES:
        raise SystemExit(f"Unsupported language '{language}'. Choose from: {', '.join(LANGUAGES)}")
    voice_kind = args.voice or ask("Voice (female/male)", "female")
    count = args.count or int(ask("Stories per video (3-7)", "5"))
    style = args.style or ask("Style: news (straight) or comedy (stand-up jokes)", "news")
    mascot = (args.mascot or ask("Animated mascot presenter? (yes/no)", "yes")).lower().startswith("y")
    comedy = style.lower().startswith("c")
    default_formats = "sketch,quiz,truefalse,explainer" if comedy else "explainer,quiz,truefalse,countdown"
    formats = [f.strip() for f in (args.formats or ask("Video formats to rotate (sketch, quiz, truefalse, explainer, countdown)", default_formats)).split(",") if f.strip()]
    if not mascot and "sketch" in formats:
        formats.remove("sketch")
    taken = sorted({json.loads(p.read_text()).get("theme", "neon") for p in NICHES_DIR.glob("*/niche.json")})
    times = (args.times or ask("Daily posting times (24h, comma separated)", "07:00,17:30")).split(",")
    slug = args.slug or slugify(name)
    if (NICHES_DIR / slug / "niche.json").exists():
        raise SystemExit(f"Niche '{slug}' already exists: niches/{slug}/niche.json")

    log("Drafting the niche profile with the LLM...")
    draft = complete_json(
        f"""Design a daily short-video news channel.
Channel name: {name}
Niche: {topic}
Audience: {audience}
Language of the videos: {language}
Style: {"comedy (funny, stand-up energy)" if comedy else "news (clear and credible)"}. Video formats: {", ".join(formats)}.
Existing channels already use these visual themes: {", ".join(taken) or "none"}. Prefer a different theme if one fits the niche.
Fill in the profile. For feeds, list many real RSS feeds of reputable publications that cover this niche every day.""",
        PROFILE_SCHEMA, "niche_profile", 0.5)

    log(f"Verifying {len(draft['feeds'])} suggested feeds and {len(draft['subreddits'])} subreddits...")
    candidates = [{"type": "rss", "name": f["name"], "url": f["url"]} for f in draft["feeds"]]
    candidates += [{"type": "rss", "name": f"r/{s}", "url": f"https://www.reddit.com/r/{s.strip().removeprefix('r/')}/top/.rss?t=day"}
                   for s in draft["subreddits"]]
    feeds = [c for c in candidates if "reddit.com" not in c["url"]]
    reddits = [c for c in candidates if "reddit.com" in c["url"]]
    with ThreadPoolExecutor(max_workers=10) as pool:
        checked = list(pool.map(verify_feed, feeds))
    for r in reddits:  # one at a time: Reddit blocks parallel requests
        checked.append(verify_feed(r))
        time.sleep(2)
    working = []
    for src, problem in checked:
        log(f"  {'OK  ' if not problem else 'DROP'} {src['name']}: {src['url']}{'' if not problem else '  -> ' + problem}")
        if not problem:
            working.append(src)
    sources = drop_off_topic(working, topic)
    if draft["useHackerNews"]:
        sources.append({"type": "hackernews", "name": "Hacker News", "minPoints": 80})
    if draft["useDailyDev"]:
        sources.append({"type": "dailydev", "name": "daily.dev"})

    code, female, male = LANGUAGES[language]
    host_voice = female if voice_kind == "female" else male
    cohost_voice = male if voice_kind == "female" else female  # opposite voice, so the two characters are easy to tell apart
    plain, accent = draft["wordmarkPlain"], draft["wordmarkAccent"]
    if plain + accent != name:
        half = max(1, len(name) // 2)
        plain, accent = name[:half], name[half:]
    editions = {}
    labels = ["Morning Edition", "Evening Edition", "Night Edition"] if len(times) > 1 else ["Daily Edition"]
    for i, t in enumerate(times[:3]):
        key = labels[i].split()[0].lower()
        editions[key] = {"label": labels[i], "lookbackHours": 24 if i == 0 else 14, "time": t.strip()}

    niche = {
        "channel": {
            "name": name,
            "handle": draft["handle"] if draft["handle"].startswith("@") else "@" + draft["handle"],
            "tagline": draft["tagline"],
            "logo": {"glyph": draft["logoGlyph"][:2], "plain": plain, "accent": accent},
            "colors": draft["colors"],
        },
        "topic": topic,
        "style": "comedy" if comedy else "news",
        "formats": formats,
        "theme": args.theme or draft["theme"],
        "mascot": {"enabled": mascot, "name": draft["mascotName"], "personality": draft["mascotPersonality"]},
        "cohost": {"name": draft["cohostName"], "personality": draft["cohostPersonality"],
                   "voice": {"name": cohost_voice, "langCode": code, "speed": 1.15, "pitch": 0.95}},
        "labels": {
            "topic": draft["topicLabel"],
            "introSubtitle": draft["introSubtitle"],
            "outroLine": "New episodes every day" if len(editions) == 1 else f"New episodes every {' & '.join(e.split()[0].lower() for e in labels[:len(editions)])}",
        },
        "language": {"name": language.title()},
        "voice": {"name": host_voice, "langCode": code, "speed": 1.15, "gapSeconds": 0.35,
                  "pitch": 1.1 if mascot and comedy else 1.0},
        "count": max(3, min(7, count)),
        "editorial": {"audience": audience, "pickRules": draft["pickRules"], "avoid": draft["avoid"], "tone": draft["tone"],
                      "categories": draft["categories"]},
        "baseHashtags": [h.lstrip("#") for h in draft["baseHashtags"]],
        "useArticleImages": True,
        "editions": editions,
        "sources": sources,
    }
    (NICHES_DIR / slug).mkdir(parents=True)
    write_json(NICHES_DIR / slug / "niche.json", niche)
    log(f"Saved niches/{slug}/niche.json with {len(sources)} working sources")
    if len([s for s in sources if s["type"] == "rss"]) < 4:
        log("WARNING: fewer than 4 working feeds. Add more RSS feeds to the 'sources' list in niche.json for better picks.")

    subprocess.run([str(ROOT / "forge.sh"), "brand", slug], check=False)
    print(f"""
Next steps:
  1. Review niches/{slug}/niche.json (sources, editorial rules, colours).
  2. Brand images for your profiles are in niches/{slug}/brand/.
  3. Make a video now:     ./forge.sh run {slug}
  4. Automate daily:       ./forge.sh schedule {slug}
""")


if __name__ == "__main__":
    main()
