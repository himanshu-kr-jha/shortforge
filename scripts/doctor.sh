#!/usr/bin/env bash
# `shortforge doctor [--llm]`: check the installation and explain how to fix anything missing.
# --llm also sends one tiny request to the LLM provider to confirm the API key works.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="$ROOT/.venv/bin/python"
problems=0; warnings=0
if [ -t 1 ]; then G=$'\033[32m'; R=$'\033[31m'; Y=$'\033[33m'; B=$'\033[1m'; N=$'\033[0m'; else G=; R=; Y=; B=; N=; fi
ok()   { printf '  %s✓%s %s\n' "$G" "$N" "$1"; }
bad()  { printf '  %s✗%s %s\n      fix: %s\n' "$R" "$N" "$1" "$2"; problems=$((problems + 1)); }
warn() { printf '  %s!%s %s\n      %s\n' "$Y" "$N" "$1" "$2"; warnings=$((warnings + 1)); }

echo "${B}ShortForge doctor${N} ($(cat "$ROOT/VERSION" 2>/dev/null || echo dev), $(uname -s) $(uname -m))"
echo
echo "${B}System${N}"
if command -v node >/dev/null && [ "$(node -p 'process.versions.node.split(".")[0]')" -ge 18 ]; then ok "Node.js $(node --version)"
else bad "Node.js 18+ missing" "install from https://nodejs.org (or: brew install node / sudo apt install nodejs npm)"; fi
if command -v ffmpeg >/dev/null; then
  ok "ffmpeg $(ffmpeg -version | head -1 | awk '{print $3}')"
  # capture first: with pipefail, `grep -q` closing the pipe early would make ffmpeg's SIGPIPE count as a failure
  filters="$(ffmpeg -hide_banner -filters 2>/dev/null || true)"
  if grep -q rubberband <<<"$filters"; then ok "ffmpeg has rubberband (character voices)"
  else warn "ffmpeg lacks the rubberband filter" "voice.pitch other than 1.0 will fail; install a full ffmpeg build (Ubuntu: apt install ffmpeg; macOS: brew install ffmpeg)"; fi
else bad "ffmpeg missing" "sudo apt install ffmpeg  (macOS: brew install ffmpeg)"; fi
free_gb=$(df -Pk "$ROOT" | awk 'NR==2 {print int($4/1048576)}')
[ "$free_gb" -ge 3 ] && ok "disk space: ${free_gb} GB free" || warn "only ${free_gb} GB free" "each video run needs ~200 MB; keep at least 3 GB free"
if [ "$(uname -s)" = "Linux" ]; then
  mem_gb=$(awk '/MemTotal/ {print int($2/1048576)}' /proc/meminfo)
  [ "$mem_gb" -ge 7 ] && ok "memory: ${mem_gb} GB" || warn "only ${mem_gb} GB RAM" "rendering may be slow or fail; lower Config.setConcurrency in video/remotion.config.ts to 2"
fi

echo
echo "${B}ShortForge${N}"
if [ -x "$PY" ]; then ok "Python environment ($("$PY" --version))"
else bad "Python environment missing" "$ROOT/setup.sh"; fi
if [ -x "$PY" ] && "$PY" -c "import kokoro, feedparser, jsonschema" 2>/dev/null; then ok "Python packages (voice engine, feeds)"
else bad "Python packages missing" "$ROOT/setup.sh"; fi
if [ -d "$ROOT/video/node_modules/remotion" ]; then ok "Remotion (video renderer)"
else bad "Remotion not installed" "cd $ROOT/video && npm install"; fi
if [ -x "$PY" ] && HF_HUB_OFFLINE=1 "$PY" -c "
from huggingface_hub import try_to_load_from_cache as c
import sys; sys.exit(0 if isinstance(c('hexgrad/Kokoro-82M','kokoro-v1_0.pth'), str) else 1)" 2>/dev/null; then ok "voice model downloaded"
else bad "voice model not downloaded" "$ROOT/setup.sh"; fi
[ -f "$ROOT/assets/sfx/whoosh.wav" ] && ok "sound effects" || bad "sound effects missing" "$ROOT/setup.sh"
if command -v shortforge >/dev/null; then ok "'shortforge' command on PATH"
else warn "'shortforge' is not on your PATH" "add this to ~/.bashrc or ~/.zshrc:  export PATH=\"\$HOME/.local/bin:\$PATH\"   (or use $ROOT/forge.sh)"; fi

echo
echo "${B}LLM${N}"
if [ -x "$PY" ]; then
  llm_out="$(cd "$ROOT/pipeline" && "$PY" configure.py llm 2>&1)"
  provider=$(echo "$llm_out" | awk '/^provider:/ {print $2}')
  model=$(echo "$llm_out" | awk '/^model:/ {print $2}')
  if echo "$llm_out" | grep -q "NOT SET" && [ "$provider" != "ollama" ]; then
    bad "no API key for $provider" "shortforge llm  (see which provider), then put the key in $ROOT/.env as LLM_API_KEY=..."
  else
    ok "provider $provider, model $model, key set"
    if [ "${1:-}" = "--llm" ]; then
      if (cd "$ROOT/pipeline" && "$PY" -W ignore -c "
from llm import complete_json
r = complete_json('Reply with the word ok.', {'type':'object','properties':{'answer':{'type':'string'}},'required':['answer']})
print(r['answer'])" >/dev/null 2>&1); then ok "LLM answered a test request"
      else bad "LLM test request failed" "check the key and provider in $ROOT/.env (shortforge llm); the provider may also be rate-limiting you"; fi
    else
      echo "      (run 'shortforge doctor --llm' to send one test request)"
    fi
  fi
fi

echo
echo "${B}Niches${N}"
names=""; count=0
for f in "$ROOT"/niches/*/niche.json; do [ -e "$f" ] && { names+="$(basename "$(dirname "$f")") "; count=$((count + 1)); }; done
[ "$count" -gt 0 ] && ok "$count niche(s): $names" || warn "no niches yet" "create one: shortforge new"
scheduled=$( (ls "$HOME/.config/systemd/user"/shortforge-*.timer "$HOME/Library/LaunchAgents"/com.shortforge.*.plist 2>/dev/null || true) | wc -l | tr -d ' ')
[ "$scheduled" -gt 0 ] && ok "$scheduled scheduled video job(s)" || echo "      nothing scheduled yet (shortforge schedule <niche>)"

echo
if [ "$problems" -eq 0 ]; then
  echo "${G}${B}All good.${N}$([ "$warnings" -gt 0 ] && echo " ($warnings warning(s) above)")"
else
  echo "${R}${B}$problems problem(s) found.${N} Fix them with the commands above, then run 'shortforge doctor' again."
  exit 1
fi
