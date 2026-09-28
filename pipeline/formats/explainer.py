"""One story explained in 4 beats: what happened, why it matters, the twist, what's next."""

from __future__ import annotations

from .base import MOOD, common_rules, line, obj, with_meta

NAME = "explainer"
LABEL = "Explained"
# read a few candidates and explain the one with the most source text: a thin story makes beats repeat themselves
READ_CANDIDATES = 3
RICHEST_FIRST = True
PICK_HINT = "a one-story explainer; pick the single most important story that has enough depth (context, stakes, consequences)"


def stories_needed(niche: dict) -> int:
    return 1


def schema(niche: dict) -> dict:
    return with_meta({
        "candidateId": {"type": "integer"},
        "title": {"type": "string", "maxLength": 60, "description": "On-screen title, 3-7 words."},
        "hook": {"type": "string", "description": "Spoken opener, 8-12 words, makes the viewer need to know more."},
        "beats": {
            "type": "array", "minItems": 4, "maxItems": 4,
            "description": "In order: what happened, why it matters, the surprising detail, what happens next.",
            "items": obj({
                "label": {"type": "string", "maxLength": 20, "description": "Beat label, 1-3 words, e.g. 'What happened'."},
                "keyText": {"type": "string", "maxLength": 40, "description": "Big on-screen text for this beat, 2-6 words (a number, name or phrase)."},
                "narration": {"type": "string", "description": "Spoken, 18-26 words."},
                "mood": MOOD,
            }),
        },
        "outro": {"type": "string", "description": "Spoken closer, 10-15 words: one question for the comments, and follow."},
    }, ["candidateId", "title", "hook", "beats", "outro"])


def prompt(niche: dict, ctx: str) -> str:
    return f"""Write a ~55 second video that explains ONE story (the first one below; the others are only context) in 4 beats. {ctx}
{common_rules(niche)}
- Beats: what happened, why it matters, the surprising detail, what happens next. If the source says nothing about
  what happens next, make the last beat what to watch for, based only on the source."""


def story_ids(script: dict) -> list[int]:
    return [script["candidateId"]]


def to_lines(script: dict, niche: dict) -> list[dict]:
    out = [line(script["hook"], "hook", "excited", title=script["title"], story=0)]
    for i, b in enumerate(script["beats"]):
        out.append(line(b["narration"], "beat", b["mood"], trim=True, story=0, number=i + 1,
                        label=b["label"], keyText=b["keyText"], title=script["title"]))
    out.append(line(script["outro"], "outro", "happy", title=script["title"], story=0))
    return out
