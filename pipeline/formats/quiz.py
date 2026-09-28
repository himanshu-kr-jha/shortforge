"""News quiz: 3 questions from today's stories, 3 options each, a thinking timer, then the reveal."""

from __future__ import annotations

from .base import MOOD, common_rules, line, obj, with_meta

NAME = "quiz"
LABEL = "Quiz"
PICK_HINT = "a news quiz; pick 3 stories with a clear, surprising, checkable fact (a number, a name, an outcome)"
THINK_SECONDS = 3.0
LETTERS = "ABC"
CHECK_NOTES = ("The wrong options are deliberate: keep them wrong. Only check that the option at the answer index is the one "
               "the source supports, and that the question and reveal are accurate.")


def stories_needed(niche: dict) -> int:
    return 3


def schema(niche: dict) -> dict:
    return with_meta({
        "hook": {"type": "string", "description": "Spoken opener, 8-12 words, challenges the viewer to score 3 out of 3."},
        "questions": {
            "type": "array", "minItems": 3, "maxItems": 3,
            "items": obj({
                "candidateId": {"type": "integer"},
                "question": {"type": "string", "maxLength": 90, "description": "On-screen and spoken, 6-14 words, about the story's key fact."},
                "options": {"type": "array", "minItems": 3, "maxItems": 3,
                            "items": {"type": "string", "maxLength": 28},
                            "description": "3 short answer options (1-4 words); exactly one is correct, the others plausible but wrong."},
                "answer": {"type": "integer", "minimum": 0, "maximum": 2, "description": "Index of the correct option (0, 1 or 2). Vary it across questions."},
                "reveal": {"type": "string", "description": "Spoken after the timer, 12-20 words: says the right answer, then one extra fact from the story."},
                "mood": MOOD,
            }),
        },
        "outro": {"type": "string", "description": "Spoken closer, 10-15 words: ask viewers to comment their score, and follow for tomorrow's quiz."},
    }, ["hook", "questions", "outro"])


def prompt(niche: dict, ctx: str) -> str:
    return f"""Write a ~55 second news quiz video with 3 questions, one per story below. {ctx}
{common_rules(niche)}
- Each question has 3 options; only one is correct according to the source, and the wrong ones must be clearly wrong per the source.
- The viewer gets {THINK_SECONDS:.0f} seconds to think after each question, then the reveal."""


def story_ids(script: dict) -> list[int]:
    return [q["candidateId"] for q in script["questions"]]


def to_lines(script: dict, niche: dict) -> list[dict]:
    out = [line(script["hook"], "hook", "excited")]
    for i, q in enumerate(script["questions"]):
        options = ", ".join(f"{LETTERS[j]}, {o}" for j, o in enumerate(q["options"][:-1])) + f", or {LETTERS[2]}, {q['options'][-1]}?"
        data = dict(story=i, number=i + 1, question=q["question"], options=q["options"], answer=q["answer"])
        out.append(line(f"{q['question']} {options}", "question", "thinking", pause_after=THINK_SECONDS, **data))
        out.append(line(q["reveal"], "reveal", q["mood"], trim=True, **data))
    out.append(line(script["outro"], "outro", "happy"))
    return out
