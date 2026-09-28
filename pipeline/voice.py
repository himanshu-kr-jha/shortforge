"""Narrate a script with Kokoro (local, free) and build a word-timed timeline for the video."""

from __future__ import annotations

import subprocess
import warnings
from pathlib import Path

import numpy as np
import soundfile as sf

from common import log

SAMPLE_RATE = 24000
LEAD_IN = 0.35   # silence before the hook so the first frame is not mid-word
TAIL = 1.6       # hold the outro card after the last word

_pipelines: dict[str, object] = {}


REPO = "hexgrad/Kokoro-82M"


def ensure_voice(name: str) -> None:
    """Runs are offline for the voice model (HF_HUB_OFFLINE=1); fetch a voice the first time a niche uses it."""
    from huggingface_hub import constants, hf_hub_download, try_to_load_from_cache

    for filename in ("config.json", "kokoro-v1_0.pth", f"voices/{name}.pt"):
        if isinstance(try_to_load_from_cache(REPO, filename), str):
            continue
        log(f"  downloading voice file {filename} (first use)")
        offline = constants.HF_HUB_OFFLINE
        constants.HF_HUB_OFFLINE = False
        try:
            hf_hub_download(REPO, filename)
        finally:
            constants.HF_HUB_OFFLINE = offline


def _short_espeak_path() -> None:
    """espeak-ng (used by Kokoro for words it does not know) cannot use a data path longer than 160 characters: it
    falls back to its build machine's path and exits the whole process. Installs in deep folders hit this. A symlink
    does not help (phonemizer resolves it), so keep a real copy (~19 MB) at a short path. Must run before
    kokoro/misaki are imported."""
    import os
    import shutil
    import tempfile
    import espeakng_loader
    source = espeakng_loader.get_data_path()
    if len(source) < 150:
        return
    home_cache = Path.home() / ".cache" / "shortforge" / "espeak-ng-data"
    target = home_cache if len(str(home_cache)) < 150 else Path(tempfile.gettempdir()) / f"sf-espeak-{os.getuid()}"
    marker = target / ".source"
    if not (marker.exists() and marker.read_text() == source):
        shutil.rmtree(target, ignore_errors=True)
        shutil.copytree(source, target, symlinks=True)
        marker.write_text(source)
    espeakng_loader.get_data_path = lambda: str(target)


def _kokoro(lang_code: str):
    if lang_code not in _pipelines:
        warnings.filterwarnings("ignore")
        _short_espeak_path()
        from kokoro import KPipeline
        _pipelines[lang_code] = KPipeline(lang_code=lang_code, repo_id=REPO)
    return _pipelines[lang_code]


def _restore_symbols(word: str, source: str) -> str:
    """Kokoro reads "$5.7 billion" as "5.7 billion dollars" and drops the "$" from the token; captions should match the script."""
    for prefix, suffix in (("$", ""), ("€", ""), ("£", ""), ("₹", ""), ("", "%")):
        if f"{prefix}{word}{suffix}" in source:
            return f"{prefix}{word}{suffix}"
    return word


def _estimate_timings(text: str, duration: float) -> list[dict]:
    """For languages where Kokoro gives no token timestamps: spread words by length over the audio."""
    words = text.split()
    weights = [len(w) + 2 for w in words]
    total, t, out = sum(weights), 0.0, []
    usable = duration * 0.96
    for word, w in zip(words, weights):
        span = usable * w / total
        out.append({"text": word, "start": t, "end": t + span})
        t += span
    return out


def synthesize(text: str, voice: dict) -> tuple[np.ndarray, list[dict]]:
    ensure_voice(voice["name"])
    audio_parts, words, offset = [], [], 0.0
    for result in _kokoro(voice["langCode"])(text, voice=voice["name"], speed=voice["speed"]):
        audio = result.audio.numpy()
        for token in result.tokens or []:
            if token.start_ts is None or token.end_ts is None:
                continue
            if not any(ch.isalnum() for ch in token.text):
                if words:
                    words[-1]["text"] += token.text
                continue
            words.append({"text": _restore_symbols(token.text, text), "start": offset + token.start_ts, "end": offset + token.end_ts})
        audio_parts.append(audio)
        offset += len(audio) / SAMPLE_RATE
    audio = np.concatenate(audio_parts)
    if not words:
        words = _estimate_timings(text, len(audio) / SAMPLE_RATE)
    return audio, words


def character_voice(audio: np.ndarray, pitch: float) -> np.ndarray:
    """Give a character its own voice: shift the pitch without changing timing, so captions stay in sync."""
    if abs(pitch - 1.0) < 0.01:
        return audio
    proc = subprocess.run(
        ["ffmpeg", "-v", "error", "-f", "f32le", "-ar", str(SAMPLE_RATE), "-ac", "1", "-i", "pipe:0",
         "-af", f"rubberband=pitch={pitch}:formant=shifted:pitchq=quality", "-f", "f32le", "pipe:1"],
        input=audio.astype(np.float32).tobytes(), capture_output=True, check=True)
    shifted = np.frombuffer(proc.stdout, dtype=np.float32)
    return shifted[: len(audio)] if len(shifted) >= len(audio) else np.pad(shifted, (0, len(audio) - len(shifted)))


def narrate(lines: list[dict], voices: dict[str, dict], gap: float, run_dir: Path) -> dict:
    """Voice every line with its speaker's voice; returns the timeline (one segment per line, with word timings)."""
    track = [np.zeros(int(LEAD_IN * SAMPLE_RATE), dtype=np.float32)]
    cursor = LEAD_IN
    segments = []
    for i, ln in enumerate(lines):
        voice = voices.get(ln.get("speaker", "host")) or voices["host"]
        spoken = f"{ln['text']} {ln.get('tail', '')}".strip()  # tail (e.g. a punchline) is spoken but never shortened
        audio, words = synthesize(spoken, voice)
        audio = character_voice(audio, voice.get("pitch", 1.0))
        duration = len(audio) / SAMPLE_RATE
        pause = ln.get("pauseAfter", 0.0)
        segments.append({
            **{k: v for k, v in ln.items() if k != "text"},
            "text": ln["text"],
            "start": cursor,
            "voiceEnd": cursor + duration,
            "words": [{**w, "start": w["start"] + cursor, "end": w["end"] + cursor} for w in words],
        })
        track += [audio.astype(np.float32), np.zeros(int((gap + pause) * SAMPLE_RATE), dtype=np.float32)]
        cursor += duration + gap + pause
    speakers = {ln.get("speaker", "host") for ln in lines}
    log(f"  voiced {len(lines)} lines ({', '.join(sorted(speakers))})")

    total = cursor - gap + TAIL
    track.append(np.zeros(int(TAIL * SAMPLE_RATE), dtype=np.float32))
    for current, nxt in zip(segments, segments[1:]):
        current["end"] = nxt["start"]
    segments[-1]["end"] = total

    audio = np.concatenate(track)
    peak = float(np.max(np.abs(audio))) or 1.0
    sf.write(run_dir / "public" / "voice.wav", audio / peak * 0.89, SAMPLE_RATE)
    log(f"  narration length: {total:.1f}s")
    return {"duration": total, "segments": segments}
