"""Mascot sketch: the host and a co-host banter about one story (two voices, speech bubbles)."""

from __future__ import annotations

from .base import MOOD, common_rules, line, obj, with_meta

NAME = "sketch"
LABEL = "Sketch"
PICK_HINT = "a short comedy sketch; pick the single story with the most comedic, surprising or relatable potential"


def stories_needed(niche: dict) -> int:
    return 1


def schema(niche: dict) -> dict:
    return with_meta({
        "candidateId": {"type": "integer"},
        "title": {"type": "string", "maxLength": 60, "description": "On-screen title for the story, 3-7 words, punchy."},
        "keyFact": {"type": "string", "maxLength": 34, "description": "The story's key stat or fact, 1-5 words, on screen."},
        "lines": {
            "type": "array", "minItems": 8, "maxItems": 12,
            "description": "The dialogue, alternating speakers. First line: host hooks the viewer. Last line: host asks viewers to follow.",
            "items": obj({
                "speaker": {"type": "string", "enum": ["host", "cohost"]},
                "text": {"type": "string", "description": "What they say, 5-15 words."},
                "mood": MOOD,
            }),
        },
    }, ["candidateId", "title", "keyFact", "lines"])


def prompt(niche: dict, ctx: str) -> str:
    host, cohost = niche["mascot"], niche["cohost"]
    return f"""Write a ~50 second comedy sketch where two animated characters react to today's news story. {ctx}
Characters:
- host "{host['name']}": {host.get('personality', 'an excitable robot who loves the news')}
- cohost "{cohost['name']}": {cohost.get('personality', 'a sarcastic sidekick who is hard to impress')}
{common_rules(niche)}
- The dialogue must tell the viewer the real facts of the story (what happened, key numbers, why it matters) through the banter.
- 8-12 short lines, alternating speakers, each 5-15 words. Build to a funny final exchange before the host's follow call-to-action.
- Pick expressive moods (laughing, shocked, thinking...) that fit each line."""


def story_ids(script: dict) -> list[int]:
    return [script["candidateId"]]


def to_lines(script: dict, niche: dict) -> list[dict]:
    lines = script["lines"]
    return [
        line(l["text"], "dialogue", l["mood"], speaker=l["speaker"], trim=0 < i < len(lines) - 1,
             title=script["title"], keyFact=script["keyFact"], story=0)
        for i, l in enumerate(lines)
    ]
