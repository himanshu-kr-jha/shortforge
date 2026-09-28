from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = json.loads((ROOT / "config.json").read_text())
NICHES_DIR = ROOT / "niches"


def log(msg: str) -> None:
    print(f"[{datetime.now():%H:%M:%S}] {msg}", file=sys.stderr, flush=True)


def notify(title: str, body: str, critical: bool = False) -> None:
    """Desktop notification on Linux (notify-send) or macOS (osascript); silently skipped elsewhere."""
    import shutil
    import subprocess
    if shutil.which("notify-send"):
        cmd = ["notify-send", "-i", "video-x-generic", title, body]
        if critical:
            cmd[1:1] = ["-u", "critical"]
        subprocess.run(cmd, check=False)
    elif shutil.which("osascript"):
        esc = lambda s: s.replace("\\", "\\\\").replace('"', '\\"')  # noqa: E731
        subprocess.run(["osascript", "-e", f'display notification "{esc(body[:200])}" with title "{esc(title)}"'], check=False)


def load_env() -> None:
    """Read KEY=value lines from .env into the environment (real env vars win)."""
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def load_niche(slug: str) -> dict:
    path = NICHES_DIR / slug / "niche.json"
    if not path.exists():
        available = ", ".join(sorted(p.name for p in NICHES_DIR.iterdir() if (p / "niche.json").exists())) or "none"
        raise SystemExit(f"Unknown niche '{slug}'. Available: {available}. Create one with: ./forge.sh new")
    niche = json.loads(path.read_text())
    niche["slug"] = slug
    return niche


def niche_output(slug: str) -> Path:
    return ROOT / "output" / slug


def load_history(slug: str) -> dict:
    path = niche_output(slug) / "history.json"
    return json.loads(path.read_text()) if path.exists() else {"runs": []}


def save_history(slug: str, history: dict) -> None:
    path = niche_output(slug) / "history.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(history, indent=2))


def write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
