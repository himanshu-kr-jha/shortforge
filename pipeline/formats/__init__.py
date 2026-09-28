"""Video format registry and rotation."""

from __future__ import annotations

from . import countdown, explainer, quiz, sketch, truefalse

FORMATS = {m.NAME: m for m in (countdown, sketch, quiz, truefalse, explainer)}


def choose(niche: dict, history: dict, override: str | None = None):
    """Next format for this niche: rotate through its list, never repeating the previous video's format."""
    if override:
        if override not in FORMATS:
            raise SystemExit(f"Unknown format '{override}'. Formats: {', '.join(FORMATS)}")
        return FORMATS[override]
    allowed = [f for f in niche.get("formats", ["countdown"]) if f in FORMATS]
    if not niche.get("mascot", {}).get("enabled") and "sketch" in allowed:
        allowed.remove("sketch")  # a sketch needs the characters
    allowed = allowed or ["countdown"]
    last = next((r.get("format", "countdown") for r in reversed(history["runs"])), None)
    if last in allowed and len(allowed) > 1:
        return FORMATS[allowed[(allowed.index(last) + 1) % len(allowed)]]
    return FORMATS[allowed[0]]
