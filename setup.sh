#!/usr/bin/env bash
# Installs ShortForge's dependencies into this folder (Python env, video renderer, voice model).
# Called by install.sh and by `shortforge update`; safe to re-run. Linux or macOS.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
export HF_HUB_OFFLINE=0   # forge.sh runs offline; setup is where the voice model is downloaded
if [ -t 1 ]; then G=$'\033[32m'; R=$'\033[31m'; N=$'\033[0m'; else G=; R=; N=; fi
ok() { printf '  %s✓%s %s\n' "$G" "$N" "$1"; }
fail() { printf '  %s✗%s %s\n' "$R" "$N" "$1"; exit 1; }
supported() { "$1" -c 'import sys; sys.exit(0 if (3,10) <= sys.version_info[:2] < (3,13) else 1)' 2>/dev/null; }

PYTHON="${PYTHON:-}"
if [ -z "$PYTHON" ]; then
  for p in python3.12 python3.11 python3.10 python3; do
    command -v "$p" >/dev/null && supported "$p" && { PYTHON="$p"; break; }
  done
fi
[ -n "$PYTHON" ] || fail "Python 3.10-3.12 is required (the voice engine does not support 3.13 yet). Run ./install.sh to get one."
command -v node >/dev/null && [ "$(node -p 'process.versions.node.split(".")[0]')" -ge 18 ] || fail "Node.js 18+ is required: https://nodejs.org"
command -v ffmpeg >/dev/null || fail "ffmpeg is required (Ubuntu: sudo apt install ffmpeg · macOS: brew install ffmpeg)"

echo "  Python packages (voice engine, news feeds)..."
if [ -x .venv/bin/python ] && ! supported .venv/bin/python; then rm -rf .venv; fi  # built with an unsupported Python
[ -d .venv ] || "$PYTHON" -m venv .venv
.venv/bin/python -m pip install -q --upgrade pip
if [ "$(uname)" = "Linux" ]; then
  # CPU-only PyTorch: ~200 MB instead of ~2 GB of GPU libraries nobody needs here
  .venv/bin/python -m pip install -q torch --index-url https://download.pytorch.org/whl/cpu
fi
.venv/bin/python -m pip install -q -r requirements.txt
# English text analysis model; the voice engine would otherwise pip-install it on first use (and fail offline)
.venv/bin/python -c "import spacy.util, sys; sys.exit(0 if spacy.util.is_package('en_core_web_sm') else 1)" 2>/dev/null \
  || .venv/bin/python -m spacy download en_core_web_sm >/dev/null 2>&1 \
  || fail "could not download the English language model (check your internet connection and run ./setup.sh again)"
ok "Python packages"

echo "  Video renderer (Remotion + headless Chrome)..."
(cd video && { [ -f package-lock.json ] && npm ci --silent --no-audit --no-fund || npm install --silent --no-audit --no-fund; } && npx remotion browser ensure >/dev/null)
mkdir -p video/public output logs
ok "video renderer"

echo "  Voice model and sound effects (first time: ~350 MB download)..."
(cd pipeline && ../.venv/bin/python -W ignore -c "
from pathlib import Path
from sounds import ensure_assets
ensure_assets(Path('../assets'))
from voice import synthesize
synthesize('Setup complete.', {'langCode': 'a', 'name': 'af_heart', 'speed': 1.0})
" > "$ROOT/logs/setup-voice.log" 2>&1) || {
  grep -v -i warn "$ROOT/logs/setup-voice.log" | tail -5 | sed 's/^/      /'
  fail "the voice engine could not start (full log: $ROOT/logs/setup-voice.log). Check your internet connection and run ./setup.sh again."
}
ok "voice model and sound effects"

[ -f .env ] || cp .env.example .env
chmod 600 .env

if [ -z "${SHORTFORGE_INSTALLER:-}" ]; then
  echo
  echo "Setup finished. Check everything with: ./forge.sh doctor"
fi
