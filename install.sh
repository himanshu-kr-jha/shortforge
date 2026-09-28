#!/usr/bin/env bash
# ShortForge installer.
#
#   curl -fsSL https://raw.githubusercontent.com/himanshu-kr-jha/shortforge/main/install.sh | bash
#   # or, from a clone:  ./install.sh
#
# Options (also usable through `curl ... | bash -s -- <options>`):
#   --dir <path>        where to install (default: ~/shortforge, or the current checkout)
#   --yes               no questions: install missing requirements, skip optional steps
#   --provider <name>   LLM provider to configure (groq, nvidia, cerebras, openrouter, gemini, ollama)
#   --key <api-key>     its API key (or set LLM_API_KEY in the environment)
#
# Environment: SHORTFORGE_REPO (git URL to clone), SHORTFORGE_DIR (same as --dir).
set -euo pipefail

REPO_URL="${SHORTFORGE_REPO:-https://github.com/himanshu-kr-jha/shortforge.git}"
INSTALL_DIR="${SHORTFORGE_DIR:-}"
ASSUME_YES=0
PROVIDER="${LLM_PROVIDER:-}"
API_KEY="${LLM_API_KEY:-}"
while [ $# -gt 0 ]; do
  case "$1" in
    --dir) INSTALL_DIR="$2"; shift 2 ;;
    --yes|-y) ASSUME_YES=1; shift ;;
    --provider) PROVIDER="$2"; shift 2 ;;
    --key) API_KEY="$2"; shift 2 ;;
    -h|--help) sed -n '2,16p' "$0" 2>/dev/null || true; exit 0 ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

# ---------------------------------------------------------------- terminal helpers
if [ -t 1 ]; then
  B=$'\033[1m'; D=$'\033[2m'; G=$'\033[32m'; R=$'\033[31m'; Y=$'\033[33m'; C=$'\033[36m'; N=$'\033[0m'
else B=; D=; G=; R=; Y=; C=; N=; fi
step() { printf '\n%s==> %s%s\n' "$B$C" "$1" "$N"; }
ok()   { printf '  %s✓%s %s\n' "$G" "$N" "$1"; }
warn() { printf '  %s!%s %s\n' "$Y" "$N" "$1"; }
die()  { printf '\n%s✗ %s%s\n' "$R" "$1" "$N" >&2; exit 1; }

# With `curl | bash`, stdin is the script itself: questions must read from the terminal.
# (CI and containers can have a /dev/tty that cannot be opened: then fall back to defaults, as with --yes)
if [ "$ASSUME_YES" = 0 ] && (: < /dev/tty) 2>/dev/null; then TTY=/dev/tty; else TTY=""; ASSUME_YES=1; fi
ask() {  # ask "question" default -> echoes the answer
  local answer=""
  if [ -n "$TTY" ]; then printf '%s%s%s %s[%s]%s ' "$B" "$1" "$N" "$D" "$2" "$N" > "$TTY"; read -r answer < "$TTY" || true; fi
  echo "${answer:-$2}"
}
confirm() { case "$(ask "$1 (y/n)" "$2")" in [Yy]*) return 0 ;; *) return 1 ;; esac; }
ask_secret() {
  local answer=""
  if [ -n "$TTY" ]; then printf '%s%s%s ' "$B" "$1" "$N" > "$TTY"; stty -echo < "$TTY"; read -r answer < "$TTY" || true; stty echo < "$TTY"; echo > "$TTY"; fi
  echo "$answer"
}

cat <<EOF

${B}  ____  _                _   _____
 / ___|| |__   ___  _ __| |_|  ___|__  _ __ __ _  ___
 \___ \| '_ \ / _ \| '__| __| |_ / _ \| '__/ _\` |/ _ \\
  ___) | | | | (_) | |  | |_|  _| (_) | | | (_| |  __/
 |____/|_| |_|\___/|_|   \__|_|  \___/|_|  \__, |\___|
                                           |___/${N}
  Daily short videos for any niche: sketches, quizzes, explainers.
  Free and open source; everything runs on your computer.
EOF

# ---------------------------------------------------------------- platform
OS="$(uname -s)"
case "$OS" in
  Linux) if grep -qi microsoft /proc/version 2>/dev/null; then PLATFORM="WSL"; else PLATFORM="Linux"; fi ;;
  Darwin) PLATFORM="macOS" ;;
  *) die "Unsupported system: $OS. ShortForge runs on Linux and macOS (on Windows, use WSL2: https://learn.microsoft.com/windows/wsl/install)." ;;
esac
PM=""
for p in brew apt-get dnf pacman zypper; do command -v "$p" >/dev/null && { PM="$p"; break; }; done
SUDO=""; [ "$(id -u)" -ne 0 ] && command -v sudo >/dev/null && SUDO="sudo"
step "System: $PLATFORM ($(uname -m))${PM:+, package manager: $PM}"

pm_install() {  # pm_install <package...>
  case "$PM" in
    brew) brew install "$@" ;;
    apt-get) $SUDO apt-get update -qq && $SUDO apt-get install -y "$@" ;;
    dnf) $SUDO dnf install -y "$@" ;;
    pacman) $SUDO pacman -S --needed --noconfirm "$@" ;;
    zypper) $SUDO zypper install -y "$@" ;;
    *) return 1 ;;
  esac
}

# ---------------------------------------------------------------- requirements
step "Checking requirements"
find_python() {
  for p in python3.12 python3.11 python3.10 python3; do
    if command -v "$p" >/dev/null && "$p" -c 'import sys; sys.exit(0 if (3,10) <= sys.version_info[:2] < (3,13) else 1)' 2>/dev/null \
       && "$p" -c 'import venv, ensurepip' 2>/dev/null; then command -v "$p"; return 0; fi
  done
  return 1
}
node_ok() { command -v node >/dev/null && [ "$(node -p 'process.versions.node.split(".")[0]')" -ge 18 ]; }

missing=()
command -v git >/dev/null && ok "git" || missing+=(git)
command -v curl >/dev/null && ok "curl" || missing+=(curl)
command -v ffmpeg >/dev/null && ok "ffmpeg" || missing+=(ffmpeg)
node_ok && ok "Node.js $(node --version)" || missing+=(node)
PYTHON="$(find_python || true)"
[ -n "$PYTHON" ] && ok "Python $("$PYTHON" --version | cut -d' ' -f2) ($PYTHON)" || missing+=(python)

if [ ${#missing[@]} -gt 0 ]; then
  warn "missing: ${missing[*]}"
  [ -n "$PM" ] || die "No supported package manager found. Please install: ${missing[*]} (Python 3.10-3.12, Node.js 18+), then run this installer again."
  [ "$PLATFORM" = "macOS" ] && ! command -v brew >/dev/null && die "Install Homebrew first (https://brew.sh), then run this installer again."
  if confirm "Install them now with $PM${SUDO:+ (asks for your password)}?" "y"; then
    for m in "${missing[@]}"; do
      case "$m" in
        git|curl|ffmpeg) pm_install "$m" ;;
        node)
          if [ "$PM" = "apt-get" ]; then
            # distro Node.js is often too old for the video renderer: use the official NodeSource build
            curl -fsSL https://deb.nodesource.com/setup_20.x | $SUDO -E bash - && $SUDO apt-get install -y nodejs
          elif [ "$PM" = "brew" ]; then pm_install node
          elif [ "$PM" = "pacman" ]; then pm_install nodejs npm
          else pm_install nodejs npm; fi ;;
        python)
          case "$PM" in
            apt-get) pm_install python3 python3-venv python3-pip || true ;;
            brew) pm_install python@3.12 || true ;;
            dnf) pm_install python3.12 || true ;;
          esac ;;
      esac
    done
  else
    die "Please install: ${missing[*]}, then run this installer again."
  fi
  node_ok || die "Node.js 18+ is still missing. Install it from https://nodejs.org and run the installer again."
  command -v ffmpeg >/dev/null || die "ffmpeg is still missing."
  PYTHON="$(find_python || true)"
fi

if [ -z "$PYTHON" ]; then
  # e.g. Arch or Fedora with only Python 3.13: fetch a private Python 3.12 with uv (no sudo, does not touch the system Python)
  warn "no Python 3.10-3.12 found (the voice engine does not support newer versions yet)"
  if confirm "Download a private Python 3.12 with uv (about 30 MB, no sudo)?" "y"; then
    command -v uv >/dev/null || { curl -LsSf https://astral.sh/uv/install.sh | sh; export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"; }
    uv python install 3.12
    PYTHON="$(uv python find 3.12)"
  fi
  [ -n "$PYTHON" ] || die "Python 3.10-3.12 is required."
  ok "Python $("$PYTHON" --version | cut -d' ' -f2) ($PYTHON)"
fi
filters="$(ffmpeg -hide_banner -filters 2>/dev/null || true)"
grep -q rubberband <<<"$filters" \
  || warn "your ffmpeg has no 'rubberband' filter: everything works, except character voices (voice.pitch other than 1.0)"

# ---------------------------------------------------------------- get the code
step "Getting ShortForge"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd || true)"
if [ -z "$INSTALL_DIR" ] && [ -n "$HERE" ] && [ -f "$HERE/forge.sh" ] && [ -f "$HERE/setup.sh" ]; then
  INSTALL_DIR="$HERE"; ok "using this checkout: $INSTALL_DIR"
else
  INSTALL_DIR="${INSTALL_DIR:-$HOME/shortforge}"
  if [ -d "$INSTALL_DIR/.git" ]; then
    git -C "$INSTALL_DIR" pull --ff-only --quiet && ok "updated $INSTALL_DIR"
  elif [ -e "$INSTALL_DIR" ] && [ -n "$(ls -A "$INSTALL_DIR" 2>/dev/null)" ]; then
    die "$INSTALL_DIR exists and is not a ShortForge checkout. Choose another folder: --dir <path>"
  else
    git clone --depth 1 --quiet "$REPO_URL" "$INSTALL_DIR" && ok "downloaded to $INSTALL_DIR"
  fi
fi
cd "$INSTALL_DIR"

# ---------------------------------------------------------------- dependencies
step "Installing the voice engine and video renderer (first time: 3-10 minutes, ~2.5 GB)"
PYTHON="$PYTHON" SHORTFORGE_INSTALLER=1 bash ./setup.sh

# ---------------------------------------------------------------- LLM
step "Connecting a free AI model (writes the scripts)"
touch .env
current_key="$(sed -n 's/^LLM_API_KEY=\(.*\)$/\1/p' .env | tail -1)"
current_provider="$(sed -n 's/^LLM_PROVIDER=\(.*\)$/\1/p' .env | tail -1)"
if [ -n "$current_key" ] && [ -z "$API_KEY" ]; then
  ok "already configured (provider: ${current_provider:-groq}); change it any time with: shortforge llm"
else
  if [ -z "$PROVIDER" ]; then
    cat > "${TTY:-/dev/stdout}" <<EOF

  Pick a provider. All have a free tier; you only need an account to get an API key:
    1) groq      (recommended) free, fast; key: https://console.groq.com/keys
    2) nvidia    free credits, Nemotron models; key: https://build.nvidia.com  (Get API Key)
    3) cerebras  free, fast; key: https://cloud.cerebras.ai
    4) gemini    free tier; key: https://aistudio.google.com/apikey
    5) openrouter  free models; key: https://openrouter.ai/keys
    6) ollama    no key, runs on your computer (needs a strong machine and https://ollama.com)
    7) skip for now

EOF
    case "$(ask "Provider [1-7]" "1")" in
      1|groq) PROVIDER=groq ;; 2|nvidia) PROVIDER=nvidia ;; 3|cerebras) PROVIDER=cerebras ;;
      4|gemini) PROVIDER=gemini ;; 5|openrouter) PROVIDER=openrouter ;; 6|ollama) PROVIDER=ollama ;; *) PROVIDER="" ;;
    esac
  fi
  if [ -n "$PROVIDER" ]; then
    if [ "$PROVIDER" != "ollama" ] && [ -z "$API_KEY" ]; then
      API_KEY="$(ask_secret "Paste your $PROVIDER API key (hidden, Enter to skip):")"
    fi
    grep -v -E '^(LLM_PROVIDER|LLM_API_KEY)=' .env > .env.tmp || true
    { echo "LLM_PROVIDER=$PROVIDER"; [ -n "$API_KEY" ] && echo "LLM_API_KEY=$API_KEY"; cat .env.tmp; } > .env
    rm -f .env.tmp; chmod 600 .env
    if [ -n "$API_KEY" ] || [ "$PROVIDER" = "ollama" ]; then
      printf '  testing the connection... '
      if (cd pipeline && ../.venv/bin/python -W ignore -c "
from llm import complete_json
complete_json('Reply with the word ok.', {'type':'object','properties':{'answer':{'type':'string'}},'required':['answer']})" >/dev/null 2>&1); then
        echo "${G}works${N}"
      else
        echo "${Y}failed${N}"; warn "check the key later with: shortforge doctor --llm"
      fi
    else
      warn "no key yet: add it to $INSTALL_DIR/.env as LLM_API_KEY=... (then: shortforge doctor --llm)"
    fi
  else
    warn "skipped: set it up later with: shortforge llm <provider>, and LLM_API_KEY in $INSTALL_DIR/.env"
  fi
fi

# ---------------------------------------------------------------- command on PATH
step "Adding the 'shortforge' command"
mkdir -p "$HOME/.local/bin"
ln -sf "$INSTALL_DIR/forge.sh" "$HOME/.local/bin/shortforge"
chmod +x forge.sh setup.sh install.sh scripts/*.sh
ok "$HOME/.local/bin/shortforge -> $INSTALL_DIR/forge.sh"
case ":$PATH:" in
  *":$HOME/.local/bin:"*) ok "it is on your PATH" ;;
  *)
    rc="$HOME/.bashrc"; [ "${SHELL##*/}" = "zsh" ] && rc="$HOME/.zshrc"
    if confirm "Add ~/.local/bin to your PATH in $rc?" "y"; then
      printf '\n# ShortForge\nexport PATH="$HOME/.local/bin:$PATH"\n' >> "$rc"
      ok "added to $rc (open a new terminal, or run: source $rc)"
    else
      warn "use the full path instead: $INSTALL_DIR/forge.sh"
    fi ;;
esac
export PATH="$HOME/.local/bin:$PATH"

# ---------------------------------------------------------------- health check
step "Checking the installation"
bash scripts/doctor.sh || warn "fix the items marked ✗ above, then run: shortforge doctor"

# ---------------------------------------------------------------- welcome
cat <<EOF

${G}${B}ShortForge is installed.${N}  (${INSTALL_DIR})

${B}1. Create your channel${N} (2 minutes, asks a few questions)
     ${C}shortforge new${N}
   Describe your niche: the AI designs the brand, logo, characters, sources and style.
   Or try the examples right away: ${C}tech-daily${N} (tech news) and ${C}over5${N} (cricket comedy).

${B}2. Make a video${N} (about 4-8 minutes)
     ${C}shortforge run <niche>${N}
     ${C}shortforge run over5 --format quiz${N}           force a format: sketch, quiz, truefalse, explainer, countdown
   You get ${B}short.mp4${N}, ${B}cover.jpg${N} and ${B}UPLOAD.md${N} (title, description, tags, captions) in
     output/<niche>/<date>-<edition>/

${B}3. Put it on autopilot${N}
     ${C}shortforge schedule <niche>${N}                   videos at the niche's times, every day

${B}Customise anything${N}
     ${C}shortforge config <niche>${N}                     interactive settings menu
     ${C}shortforge set <niche> theme comic${N}            one change (see: shortforge keys)
     ${C}shortforge voice-test <niche>${N}                 hear the presenter's voice

${B}If something is off${N}
     ${C}shortforge doctor${N}      ${C}shortforge help${N}      README: ${INSTALL_DIR}/README.md

EOF

if [ -n "$TTY" ] && confirm "Create your first niche now?" "n"; then
  exec "$INSTALL_DIR/forge.sh" new
fi
