"""Procedurally generated sound effects and a fallback music bed.

Everything here is synthesised from scratch, so it is copyright-free by construction.
Real tracks dropped into assets/music/ always take precedence over the generated bed.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import soundfile as sf

SR = 44100
rng = np.random.default_rng(7)


def _lowpass(x: np.ndarray, cutoff: np.ndarray | float) -> np.ndarray:
    """One-pole low-pass with an optionally time-varying cutoff (Hz)."""
    cutoff = np.broadcast_to(cutoff, x.shape)
    alpha = 1 - np.exp(-2 * np.pi * cutoff / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i, (v, a) in enumerate(zip(x, alpha)):
        acc += a * (v - acc)
        y[i] = acc
    return y


def whoosh(duration: float = 0.5) -> np.ndarray:
    n = int(SR * duration)
    t = np.linspace(0, 1, n)
    noise = rng.standard_normal(n)
    cutoff = 300 + 5200 * np.sin(np.pi * t) ** 2
    bright = _lowpass(noise, cutoff) - _lowpass(noise, cutoff * 0.25)
    env = np.sin(np.pi * t**0.7) ** 2
    out = bright * env
    return out / np.max(np.abs(out)) * 0.8


def pop(duration: float = 0.14) -> np.ndarray:
    n = int(SR * duration)
    t = np.arange(n) / SR
    freq = 1100 * np.exp(-t * 18) + 380
    phase = 2 * np.pi * np.cumsum(freq) / SR
    out = np.sin(phase) * np.exp(-t * 32)
    return out / np.max(np.abs(out)) * 0.8


def tick(duration: float = 0.06) -> np.ndarray:
    n = int(SR * duration)
    t = np.arange(n) / SR
    out = np.sin(2 * np.pi * 1800 * t) * np.exp(-t * 90) + 0.3 * rng.standard_normal(n) * np.exp(-t * 200)
    return out / np.max(np.abs(out)) * 0.7


def ding(duration: float = 0.9) -> np.ndarray:
    """Bright two-note chime for correct answers and verdicts."""
    t = np.arange(int(SR * duration)) / SR
    out = np.zeros_like(t)
    for start, f in ((0.0, 1318.5), (0.09, 1975.5)):
        tt = np.clip(t - start, 0, None)
        out += (t >= start) * (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(4 * np.pi * f * tt)) * np.exp(-tt * 5)
    return out / np.max(np.abs(out)) * 0.7


def _note(midi: int) -> float:
    return 440.0 * 2 ** ((midi - 69) / 12)


def music_bed(bars: int = 24, bpm: int = 104) -> np.ndarray:
    """Chill electronic loop: warm pad chords, plucked arp, soft kick and hats."""
    beat = 60 / bpm
    bar = 4 * beat
    total = int(SR * bars * bar)
    out = np.zeros(total)
    progression = [[57, 60, 64, 67], [53, 57, 60, 64], [48, 52, 55, 59], [55, 59, 62, 66]]  # Am7 Fmaj7 Cmaj7 G(maj7)

    for b in range(bars):
        chord = progression[b % 4]
        start = int(b * bar * SR)
        n = int(bar * SR)
        t = np.arange(n) / SR
        pad = np.zeros(n)
        for m in chord:
            f = _note(m)
            for detune in (-0.12, 0.0, 0.12):
                ff = f * 2 ** (detune / 12)
                pad += np.sin(2 * np.pi * ff * t) + 0.3 * np.sin(4 * np.pi * ff * t)
        env = np.minimum(1, t / 0.4) * np.minimum(1, (bar - t) / 0.3)
        out[start:start + n] += pad * env * 0.035

        # bass on the root
        f = _note(chord[0] - 12)
        bass = np.sin(2 * np.pi * f * t) * np.exp(-((t % (2 * beat)) * 2.2))
        out[start:start + n] += bass * 0.16

        # 16th-note pluck arpeggio
        step = beat / 2
        for k in range(8):
            m = chord[(k * 3) % 4] + 12
            s0 = start + int(k * step * SR)
            ln = int(step * SR)
            tt = np.arange(ln) / SR
            pl = np.sign(np.sin(2 * np.pi * _note(m) * tt)) * 0.5 + np.sin(2 * np.pi * _note(m) * tt)
            out[s0:s0 + ln] += pl * np.exp(-tt * 14) * 0.03

        # drums
        for k in range(4):
            s0 = start + int(k * beat * SR)
            ln = int(0.25 * SR)
            tt = np.arange(ln) / SR
            kick = np.sin(2 * np.pi * (45 + 90 * np.exp(-tt * 30)) * tt) * np.exp(-tt * 12)
            out[s0:s0 + ln] += kick * 0.35
            for h in (0.5,):
                hs = start + int((k + h) * beat * SR)
                hl = int(0.05 * SR)
                hat = rng.standard_normal(hl) * np.exp(-np.arange(hl) / SR * 90)
                out[hs:hs + hl] += np.diff(np.concatenate([[0], hat])) * 0.05

    out = _lowpass(out, 7000.0)
    return out / np.max(np.abs(out)) * 0.8


def ensure_assets(assets_dir: Path) -> None:
    sfx = assets_dir / "sfx"
    sfx.mkdir(parents=True, exist_ok=True)
    if not (sfx / "whoosh.wav").exists():
        sf.write(sfx / "whoosh.wav", whoosh(), SR)
    if not (sfx / "pop.wav").exists():
        sf.write(sfx / "pop.wav", pop(), SR)
    if not (sfx / "tick.wav").exists():
        sf.write(sfx / "tick.wav", tick(), SR)
    if not (sfx / "ding.wav").exists():
        sf.write(sfx / "ding.wav", ding(), SR)
    bed = assets_dir / "generated" / "generated-bed.wav"
    if not bed.exists():
        bed.parent.mkdir(parents=True, exist_ok=True)
        sf.write(bed, music_bed(), SR)
