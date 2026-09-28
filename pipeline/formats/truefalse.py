"""True or false: claims based on today's news, a beat to guess, then a TRUE/FALSE stamp and the real fact."""

from __future__ import annotations

from .base import MOOD, common_rules, line, obj, with_meta

NAME = "truefalse"
LABEL = "True or False"
PICK_HINT = "a 'true or false' game; pick 4 stories with surprising facts that sound unbelievable but are checkable"
GUESS_SECONDS = 2.0
CHECK_NOTES = ("FALSE claims are deliberate fakes (one detail changed): never turn them into true claims. "
               "Only check that each isTrue label matches the source, and that each verdict states the real fact correctly.")


def stories_needed(niche: dict) -> int:
    return 4


def schema(niche: dict) -> dict:
    return with_meta({
        "hook": {"type": "string", "description": "Spoken opener, 8-12 words, dares the viewer to spot the fakes."},
        "claims": {
            "type": "array", "minItems": 4, "maxItems": 4,
            "items": obj({
                "candidateId": {"type": "integer"},
                "claim": {"type": "string", "maxLength": 100, "description": "On-screen and spoken statement, 7-15 words. Either the real fact, or the real fact with one detail changed."},
                "isTrue": {"type": "boolean"},
                "verdict": {"type": "string", "description": "Spoken after the pause, 10-18 words: starts with 'True!' or 'False!', then states the real fact."},
                "mood": MOOD,
            }),
        },
        "outro": {"type": "string", "description": "Spoken closer, 10-15 words: ask how many they got right, and to follow."},
    }, ["hook", "claims", "outro"])


def prompt(niche: dict, ctx: str) -> str:
    return f"""Write a ~50 second "true or false" video with 4 claims, one per story below. {ctx}
{common_rules(niche)}
- Mix them: at least one TRUE and at least one FALSE claim. A false claim changes exactly one detail of the real fact
  (a number, a name, an outcome) and its verdict must state the real fact from the source.
- True claims must be exactly supported by the source."""


def story_ids(script: dict) -> list[int]:
    return [c["candidateId"] for c in script["claims"]]


def to_lines(script: dict, niche: dict) -> list[dict]:
    out = [line(script["hook"], "hook", "excited")]
    for i, c in enumerate(script["claims"]):
        data = dict(story=i, number=i + 1, claim=c["claim"], isTrue=c["isTrue"])
        out.append(line(f"True or false? {c['claim']}", "claim", "thinking", pause_after=GUESS_SECONDS, **data))
        out.append(line(c["verdict"], "verdict", c["mood"], trim=True, **data))
    out.append(line(script["outro"], "outro", "happy"))
    return out
