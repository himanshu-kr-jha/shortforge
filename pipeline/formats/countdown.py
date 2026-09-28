"""Top-N countdown: #N ... #1, one story each."""

from __future__ import annotations

from .base import MOOD, common_rules, line, obj, with_meta

NAME = "countdown"
LABEL = "Top {n}"
PICK_HINT = "a countdown of the day's {n} most important or surprising stories"


def stories_needed(niche: dict) -> int:
    return niche.get("count", 5)


def schema(niche: dict) -> dict:
    n = stories_needed(niche)
    comedy = niche.get("style") == "comedy"
    story = {
        "candidateId": {"type": "integer"},
        "headline": {"type": "string", "maxLength": 60, "description": "On-screen headline, 3-7 words."},
        "category": {"type": "string", "description": f"One short word. Prefer one of: {', '.join(niche['editorial']['categories'])}."},
        "keyFact": {"type": "string", "maxLength": 34, "description": "On-screen stat or fact from the article, 1-5 words."},
        "narration": {"type": "string", "description": "Spoken fact, 14-18 words, no joke." if comedy else "Spoken text, 18-24 words, conversational, 1-2 concrete facts."},
        "mood": MOOD,
    }
    if comedy:
        story["punchline"] = {"type": "string", "description": "Spoken right after the narration: one witty 3-9 word punchline."}
    return with_meta({
        "hook": {"type": "string", "description": "Spoken opener, 8-12 words, teases #1 without revealing it."},
        "stories": {"type": "array", "minItems": n, "maxItems": n, "items": obj(story),
                    "description": f"Countdown order: first item is #{n}, last item is #1 (the biggest story)."},
        "outro": {"type": "string", "description": "Spoken closer, 10-15 words: follow call-to-action plus one question for the comments."},
    }, ["hook", "stories", "outro"])


def prompt(niche: dict, ctx: str) -> str:
    n = stories_needed(niche)
    return f"""Write a ~55 second video counting down the top {n} {niche['topic']} stories from #{n} to #1. {ctx}
{common_rules(niche)}
- The most important or surprising story is #1 (last in the list). Use exactly {n} of the stories below; if two cover the same event, use it once.
- Narrations explain what happened and why it matters; do not repeat the headline word for word."""


def story_ids(script: dict) -> list[int]:
    return [s["candidateId"] for s in script["stories"]]


def to_lines(script: dict, niche: dict) -> list[dict]:
    n = len(script["stories"])
    out = [line(script["hook"], "hook", "excited")]
    for i, s in enumerate(script["stories"]):
        out.append(line(s["narration"], "story", s["mood"], trim=True, tail=s.get("punchline", ""), rank=n - i, story=i,
                        headline=s["headline"], category=s["category"], keyFact=s["keyFact"]))
    out.append(line(script["outro"], "outro", "happy"))
    return out
