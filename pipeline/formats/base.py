"""Shared building blocks for video formats.

A format turns picked stories into a script (its own JSON shape, natural for the LLM to write), and then into
`lines`: everything spoken, in order. Each line is a dict:

    {"speaker": "host" | "cohost", "text": str, "mood": str, "kind": str,
     "pauseAfter": seconds of silence after it (e.g. a quiz timer),
     "trim": whether length control may shorten it, ...format-specific on-screen data}

Voice, timing, length control and rendering only ever deal with lines, so a new format only needs this module.
"""

from __future__ import annotations

MOODS = ["neutral", "excited", "happy", "shocked", "thinking", "sad", "laughing"]

META_PROPS = {
    "coverHeadline": {"type": "string", "description": "3-5 word teaser for the cover image."},
    "youtubeTitle": {"type": "string", "description": "Max 70 characters, curiosity plus clarity, ends with ' #shorts'."},
    "youtubeDescription": {"type": "string", "description": "Two-line hook, then one line per story covered, then a subscribe line. No hashtags. Never start a line with '#'."},
    "youtubeTags": {"type": "array", "items": {"type": "string"}, "minItems": 10, "maxItems": 25},
    "hashtags": {"type": "array", "items": {"type": "string"}, "minItems": 6, "maxItems": 12, "description": "Without '#'."},
    "instagramCaption": {"type": "string", "description": "Hook line, short emoji bullet lines about the content, a question for comments, a save/share call-to-action. No hashtags."},
    "pinnedComment": {"type": "string", "description": "1-2 sentences that spark discussion."},
}
META_REQUIRED = list(META_PROPS)

MOOD = {"type": "string", "enum": MOODS, "description": "The presenter's facial reaction."}


def obj(props: dict, required: list[str] | None = None, **extra) -> dict:
    return {"type": "object", "properties": props, "required": required or list(props), **extra}


def with_meta(props: dict, required: list[str]) -> dict:
    return obj({**props, **META_PROPS}, required + META_REQUIRED)


def line(text: str, kind: str, mood: str = "neutral", speaker: str = "host", pause_after: float = 0.0,
         trim: bool = False, **data) -> dict:
    return {"speaker": speaker, "text": text.strip(), "mood": mood, "kind": kind,
            "pauseAfter": pause_after, "trim": trim, **data}


def comedy_rules(niche: dict) -> str:
    if niche.get("style") != "comedy":
        return ""
    return """
Style: comedy. Keep every fact exact, but be genuinely funny: quick wit, playful exaggeration of situations, puns.
Punch up, not down: joke about situations, companies and absurdities, never about anyone's looks, religion, caste,
gender, nationality or tragedy (for sad news, stay kind and skip the joke).
Do not impersonate or mention any real comedian or celebrity's catchphrases."""


def common_rules(niche: dict) -> str:
    ed = niche["editorial"]
    lang = niche.get("language", {}).get("name", "English")
    return f"""Channel: "{niche['channel']['name']}" ({niche['channel']['tagline']}), vertical short videos about {niche['topic']}.
Audience: {ed['audience']}
Tone: {ed['tone']}
Language: write all spoken and on-screen text in {lang}.
Rules:
- Write for the ear: short sentences, active voice, plain words. Word limits are strict: the video must stay under a minute.
- Strictly factual: every claim, number and name must come from the source texts below. Leave out anything not stated there.
- Hooks create curiosity and never start with "Hey guys" or "Welcome back".{comedy_rules(niche)}"""
