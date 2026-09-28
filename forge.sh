#!/usr/bin/env bash
# ShortForge command line (installed as `shortforge`). Run `shortforge help` for usage.
set -euo pipefail

# Resolve the real install directory, also when called through the ~/.local/bin/shortforge symlink.
resolve_dir() {
  local p="$1" d
  while [ -L "$p" ]; do
    d="$(cd "$(dirname "$p")" && pwd)"
    p="$(readlink "$p")"
    [[ "$p" != /* ]] && p="$d/$p"
  done
  cd "$(dirname "$p")" && pwd
}
ROOT="$(resolve_dir "${BASH_SOURCE[0]}")"
PY="$ROOT/.venv/bin/python"
PROG="$(basename "$0")"; [ "$PROG" = "forge.sh" ] && PROG="./forge.sh"
OS="$(uname -s)"
VERSION="$(cat "$ROOT/VERSION" 2>/dev/null || echo dev)"
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
export HF_HUB_OFFLINE=1   # the voice model is downloaded once by setup.sh; missing voices are fetched on first use
UNIT_DIR="$HOME/.config/systemd/user"
AGENT_DIR="$HOME/Library/LaunchAgents"

usage() {
  cat <<EOF
ShortForge $VERSION: daily short videos for any niche.

Make videos
  $PROG new                          create a niche (asks a few questions)
  $PROG list                         your niches and their schedules
  $PROG run <niche> [edition]        make a video now (edition: morning, evening, ...)
        --format <name>              force a format: sketch, quiz, truefalse, explainer, countdown
        --set key=value              try a setting for this video only (repeatable)
        --landscape                  also render a 16:9 version
  $PROG reuse <niche> <run-dir>      re-voice and re-render after editing script.json
  $PROG schedule <niche>             make videos automatically every day
  $PROG unschedule <niche>           stop automatic videos

Configure
  $PROG config <niche>               interactive menu for every setting
  $PROG show <niche>                 all settings at a glance
  $PROG get <niche> <key>            one setting, e.g. voice.pitch
  $PROG set <niche> <key> <value>    change one setting, e.g. set over5 theme paper
  $PROG keys                         every setting with its allowed values
  $PROG sources <niche> [list|add <url|r/sub> [name]|remove <n>|test]
  $PROG voices [language]            available voices
  $PROG voice-test <niche> [host|cohost]   hear a voice before using it
  $PROG llm [provider [model]]       show or switch the LLM (groq, nvidia, cerebras, ...)
  $PROG brand <niche>                (re)render profile picture, logo and banner

Maintain
  $PROG doctor                       check that everything is installed and working
  $PROG update                       get the latest version
  $PROG studio                       open the animation editor (live preview in the browser)
  $PROG --version

Docs: $ROOT/README.md
EOF
}

need_niche() {
  local names="" f
  for f in "$ROOT"/niches/*/niche.json; do [ -e "$f" ] && names+="$(basename "$(dirname "$f")") "; done
  [ -n "${1:-}" ] || { echo "Missing <niche>. Your niches: ${names:-none (create one: $PROG new)}"; exit 1; }
  [ -f "$ROOT/niches/$1/niche.json" ] || { echo "No niche '$1'. Your niches: ${names:-none (create one: $PROG new)}"; exit 1; }
}

need_install() {
  [ -x "$PY" ] || { echo "ShortForge is not set up yet. Run: $ROOT/install.sh"; exit 1; }
}

wait_for_network() {
  # After the computer wakes up, Wi-Fi needs a few seconds to reconnect: wait for it (max 10 min).
  for _ in $(seq 1 60); do
    curl -s -o /dev/null -m 5 https://www.google.com && return 0
    echo "[$(date +%T)] waiting for network..."; sleep 10
  done
}

# Seconds since this edition was last due (today's time, or yesterday's if today's is still ahead).
seconds_late() {
  "$PY" - "$ROOT/niches/$1/niche.json" "$2" <<'PYEOF'
import json, sys
from datetime import datetime, timedelta
t = json.load(open(sys.argv[1]))["editions"][sys.argv[2]].get("time")
if not t:
    print(0); sys.exit()
now = datetime.now()
due = now.replace(hour=int(t[:2]), minute=int(t[3:5]), second=0, microsecond=0)
if due > now:
    due -= timedelta(days=1)
print(int((now - due).total_seconds()))
PYEOF
}

editions_of() {
  "$PY" -c "import json; print(' '.join(json.load(open('$ROOT/niches/$1/niche.json'))['editions']))"
}

edition_time() {
  "$PY" -c "import json; print(json.load(open('$ROOT/niches/$1/niche.json'))['editions']['$2'].get('time',''))"
}

# One render at a time across all niches: flock on Linux, an atomic mkdir lock elsewhere (macOS has no flock).
take_lock() {
  mkdir -p "$ROOT/logs"
  if command -v flock >/dev/null; then
    exec 9>"$ROOT/logs/.run.lock"; flock 9
  else
    until mkdir "$ROOT/logs/.run.lock.d" 2>/dev/null; do
      local pid; pid="$(cat "$ROOT/logs/.run.lock.d/pid" 2>/dev/null || true)"
      if [ -n "$pid" ] && ! kill -0 "$pid" 2>/dev/null; then rm -rf "$ROOT/logs/.run.lock.d"; continue; fi
      sleep 5
    done
    echo $$ > "$ROOT/logs/.run.lock.d/pid"
    trap 'rm -rf "$ROOT/logs/.run.lock.d"' EXIT
  fi
}

schedule_linux() {
  local niche="$1" edition t unit
  mkdir -p "$UNIT_DIR"
  for edition in $(editions_of "$niche"); do
    t=$(edition_time "$niche" "$edition"); unit="shortforge-$niche-$edition"
    cat > "$UNIT_DIR/$unit.service" <<EOF
[Unit]
Description=ShortForge $niche $edition video
# A failed run (e.g. offline right after wake-up) retries every 5 min, up to 3 times.
StartLimitIntervalSec=2h
StartLimitBurst=4

[Service]
Type=oneshot
ExecStart=$ROOT/forge.sh run $niche $edition --scheduled
TimeoutStartSec=60min
Nice=5
Restart=on-failure
RestartSec=5min
EOF
    cat > "$UNIT_DIR/$unit.timer" <<EOF
[Unit]
Description=ShortForge $niche $edition video at $t

[Timer]
OnCalendar=*-*-* $t:00
# If the computer was off or asleep at that time, run as soon as it wakes.
Persistent=true
RandomizedDelaySec=60

[Install]
WantedBy=timers.target
EOF
    echo "  $edition at $t"
  done
  systemctl --user daemon-reload
  # shellcheck disable=SC2046
  systemctl --user enable --now $(cd "$UNIT_DIR" && ls shortforge-"$niche"-*.timer) >/dev/null 2>&1
  systemctl --user list-timers "shortforge-$niche-*" --no-pager
}

schedule_mac() {
  local niche="$1" edition t label plist
  mkdir -p "$AGENT_DIR" "$ROOT/logs"
  for edition in $(editions_of "$niche"); do
    t=$(edition_time "$niche" "$edition"); label="com.shortforge.$niche.$edition"; plist="$AGENT_DIR/$label.plist"
    cat > "$plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$label</string>
  <key>ProgramArguments</key>
  <array><string>$ROOT/forge.sh</string><string>run</string><string>$niche</string><string>$edition</string><string>--scheduled</string></array>
  <!-- launchd runs a missed calendar job once when the Mac wakes from sleep -->
  <key>StartCalendarInterval</key>
  <dict><key>Hour</key><integer>$((10#${t%%:*}))</integer><key>Minute</key><integer>$((10#${t##*:}))</integer></dict>
  <key>StandardOutPath</key><string>$ROOT/logs/launchd-$niche-$edition.log</string>
  <key>StandardErrorPath</key><string>$ROOT/logs/launchd-$niche-$edition.log</string>
</dict>
</plist>
EOF
    launchctl bootout "gui/$(id -u)" "$plist" 2>/dev/null || true
    launchctl bootstrap "gui/$(id -u)" "$plist"
    echo "  $edition at $t"
  done
}

cmd="${1:-help}"; shift || true
case "$cmd" in
  new)
    need_install; exec "$PY" -W ignore "$ROOT/pipeline/new_niche.py" "$@" ;;

  run)
    need_install
    niche="${1:-}"; need_niche "$niche"; shift
    edition=""; if [ -n "${1:-}" ] && [[ "$1" != --* ]]; then edition="$1"; shift; fi
    scheduled=0; args=()
    for a in "$@"; do [ "$a" = "--scheduled" ] && scheduled=1 || args+=("$a"); done
    if [ "$scheduled" = 1 ] && [ -n "$edition" ]; then
      # A run that only catches up many hours late (computer was off) is stale: skip it, the next edition covers the news.
      late=$(seconds_late "$niche" "$edition")
      if [ "$late" -gt $(( 10 * 3600 )) ]; then
        echo "[$(date +%T)] skipping stale $niche $edition run ($(( late / 3600 )) h late)"; exit 0
      fi
    fi
    take_lock
    wait_for_network
    log="$ROOT/logs/$(date +%F)-$niche-${edition:-auto}.log"
    cd "$ROOT/pipeline"
    "$PY" -W ignore run.py "$niche" ${edition:+--edition "$edition"} ${args[@]+"${args[@]}"} 2>&1 | tee -a "$log"
    exit "${PIPESTATUS[0]}" ;;

  reuse)
    need_install; niche="${1:-}"; need_niche "$niche"
    [ -n "${2:-}" ] || { echo "usage: $PROG reuse <niche> <run-dir>"; exit 1; }
    dir="$(cd "$2" && pwd)"
    cd "$ROOT/pipeline" && exec "$PY" -W ignore run.py "$niche" --reuse "$dir" ;;

  brand)
    need_install; niche="${1:-}"; need_niche "$niche"
    out="$ROOT/niches/$niche/brand"; mkdir -p "$out" "$ROOT/video/public" "$ROOT/logs"
    props="$ROOT/logs/.brand-props-$niche.json"
    "$PY" -c "import json; print(json.dumps({'brand': json.load(open('$ROOT/niches/$niche/niche.json'))['channel']}))" > "$props"
    cd "$ROOT/video"
    for c in ProfilePicture:profile-picture.png LogoLockup:logo-lockup.png ChannelBanner:youtube-banner.png; do
      npx remotion still src/index.ts "${c%%:*}" "$out/${c#*:}" --props="$props" --image-format=png --log=error
    done
    rm -f "$props"; echo "Brand images: $out" ;;

  schedule)
    need_install; niche="${1:-}"; need_niche "$niche"
    if [ "$OS" = "Linux" ] && command -v systemctl >/dev/null; then
      schedule_linux "$niche"
    elif [ "$OS" = "Darwin" ]; then
      schedule_mac "$niche"; echo "Scheduled with launchd (runs when due; a missed run happens once the Mac wakes)."
    else
      echo "Automatic scheduling needs systemd (Linux) or launchd (macOS). Use cron instead, e.g.:"
      for edition in $(editions_of "$niche"); do
        t=$(edition_time "$niche" "$edition")
        echo "  $((10#${t##*:})) $((10#${t%%:*})) * * * $ROOT/forge.sh run $niche $edition --scheduled"
      done
    fi ;;

  unschedule)
    niche="${1:-}"; need_niche "$niche"
    if [ "$OS" = "Darwin" ]; then
      for plist in "$AGENT_DIR"/com.shortforge."$niche".*.plist; do
        [ -e "$plist" ] || continue
        launchctl bootout "gui/$(id -u)" "$plist" 2>/dev/null || true; rm -f "$plist"
      done
    else
      units=$(cd "$UNIT_DIR" 2>/dev/null && ls shortforge-"$niche"-*.timer 2>/dev/null || true)
      # shellcheck disable=SC2086
      [ -n "$units" ] && systemctl --user disable --now $units >/dev/null 2>&1 || true
      rm -f "$UNIT_DIR"/shortforge-"$niche"-*.{timer,service}
      command -v systemctl >/dev/null && systemctl --user daemon-reload || true
    fi
    echo "Automatic videos stopped for $niche." ;;

  list)
    need_install
    found=0
    for d in "$ROOT"/niches/*/; do
      n=$(basename "$d"); [ -f "$d/niche.json" ] || continue; found=1
      "$PY" -c "import json; c=json.load(open('$d/niche.json')); print(f\"{'$n':<20} {c['channel']['name']:<16} {c.get('theme','neon'):<8} \" + ', '.join(f\"{k} {v.get('time','')}\" for k,v in c['editions'].items()) + '   formats: ' + ', '.join(c.get('formats',['countdown'])))"
    done
    [ "$found" = 1 ] || echo "No niches yet. Create one: $PROG new"
    echo
    if [ "$OS" = "Darwin" ]; then
      launchctl list 2>/dev/null | grep com.shortforge || echo "Nothing scheduled ($PROG schedule <niche>)."
    else
      systemctl --user list-timers 'shortforge-*' --no-pager 2>/dev/null | grep -q shortforge \
        && systemctl --user list-timers 'shortforge-*' --no-pager || echo "Nothing scheduled ($PROG schedule <niche>)."
    fi ;;

  studio)
    cd "$ROOT/video" && exec npx remotion studio ;;

  config)
    need_install; need_niche "${1:-}"; exec "$PY" -W ignore "$ROOT/pipeline/configure.py" menu "$@" ;;
  show|get|set|sources|voice-test)
    need_install; need_niche "${1:-}"; exec "$PY" -W ignore "$ROOT/pipeline/configure.py" "$cmd" "$@" ;;
  keys|voices|llm)
    need_install; exec "$PY" -W ignore "$ROOT/pipeline/configure.py" "$cmd" "$@" ;;

  doctor)
    exec bash "$ROOT/scripts/doctor.sh" "$@" ;;

  update)
    [ -d "$ROOT/.git" ] || { echo "Not a git checkout; download the latest release instead."; exit 1; }
    git -C "$ROOT" pull --ff-only
    exec bash "$ROOT/setup.sh" ;;

  -v|--version|version) echo "ShortForge $VERSION" ;;
  help|-h|--help) usage ;;
  *) echo "Unknown command: $cmd"; echo; usage; exit 1 ;;
esac
