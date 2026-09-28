"""View and change a niche's configuration from the command line.

  configure.py menu    <niche>                 interactive menu
  configure.py show    <niche>                 readable summary
  configure.py get     <niche> <key>           one value (e.g. voice.pitch)
  configure.py set     <niche> <key> <value>   change one value (validated)
  configure.py keys                            every setting you can change, with allowed values
  configure.py sources <niche> [list|add <url> [name]|remove <n>|test]
  configure.py voices  [language]              available voices
  configure.py voice-test <niche> [host|cohost]   hear the voice (with its pitch) reading a sample line
  configure.py llm     [provider [model]]      show or change the LLM provider/model in .env
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

from common import CONFIG, NICHES_DIR, ROOT, load_env
from formats import FORMATS

THEMES = ["neon", "comic", "paper", "minimal"]
STYLES = ["news", "comedy"]
# Kokoro voices by language code (f = female, m = male in the second letter)
VOICES = {
    "a": ["af_heart", "af_bella", "af_nicole", "af_sarah", "af_sky", "af_nova", "af_river", "af_jessica", "af_kore", "af_aoede", "af_alloy",
          "am_michael", "am_fenrir", "am_puck", "am_adam", "am_echo", "am_eric", "am_liam", "am_onyx", "am_santa"],
    "b": ["bf_emma", "bf_isabella", "bf_alice", "bf_lily", "bm_george", "bm_fable", "bm_lewis", "bm_daniel"],
    "h": ["hf_alpha", "hf_beta", "hm_omega", "hm_psi"],
    "e": ["ef_dora", "em_alex", "em_santa"],
    "f": ["ff_siwis"],
    "i": ["if_sara", "im_nicola"],
    "p": ["pf_dora", "pm_alex", "pm_santa"],
}
LANGUAGES = {"english": "a", "english (uk)": "b", "hindi": "h", "spanish": "e", "french": "f", "italian": "i", "portuguese": "p"}
HEX = r"^#[0-9A-Fa-f]{6}$"
TIME = r"^([01]\d|2[0-3]):[0-5]\d$"


# ---------------------------------------------------------------- settings registry

class Setting:
    def __init__(self, key: str, kind: str, help: str, choices=None, lo=None, hi=None, pattern=None):
        self.key, self.kind, self.help = key, kind, help
        self.choices, self.lo, self.hi, self.pattern = choices, lo, hi, pattern

    def allowed(self, niche: dict | None = None) -> str:
        choices = self.choices(niche) if callable(self.choices) else self.choices
        if choices:
            return ("comma-separated from: " if self.kind == "list" else "one of: ") + ", ".join(choices)
        if self.kind in ("int", "float"):
            return f"{self.kind} {self.lo}-{self.hi}"
        if self.kind == "bool":
            return "yes / no"
        if self.pattern == HEX:
            return "colour like #FF3D71"
        if self.pattern == TIME:
            return "time like 07:30"
        return "text" if self.kind == "str" else "comma-separated list"

    def parse(self, raw: str, niche: dict):
        raw = raw.strip()
        choices = self.choices(niche) if callable(self.choices) else self.choices
        if self.kind == "bool":
            if raw.lower() in ("y", "yes", "true", "on", "1"):
                return True
            if raw.lower() in ("n", "no", "false", "off", "0"):
                return False
            raise ValueError("answer yes or no")
        if self.kind in ("int", "float"):
            value = int(raw) if self.kind == "int" else float(raw)
            if not (self.lo <= value <= self.hi):
                raise ValueError(f"must be between {self.lo} and {self.hi}")
            return value
        if self.kind == "list":
            items = [x.strip() for x in raw.split(",") if x.strip()]
            if not items:
                raise ValueError("give at least one item")
            if choices:
                bad = [x for x in items if x not in choices]
                if bad:
                    raise ValueError(f"unknown: {', '.join(bad)} (allowed: {', '.join(choices)})")
            return items
        if not raw:
            raise ValueError("value cannot be empty")
        if choices and raw not in choices:
            raise ValueError(f"must be one of: {', '.join(choices)}")
        if self.pattern and not re.match(self.pattern, raw):
            raise ValueError(f"expected {self.allowed()}")
        return raw


def _voices_for(path: str):
    def pick(niche: dict | None):
        if not niche:
            return sorted(v for vs in VOICES.values() for v in vs)
        code = _get(niche, path) or "a"
        return VOICES.get(code, VOICES["a"])
    return pick


SECTIONS: dict[str, list[Setting]] = {
    "Channel": [
        Setting("channel.name", "str", "Channel name (shown on every video)"),
        Setting("channel.handle", "str", "Social handle, e.g. @over5", pattern=r"^@[\w.]+$"),
        Setting("channel.tagline", "str", "Tagline under the logo"),
        Setting("channel.logo.glyph", "str", "1-2 characters in the logo tile", pattern=r"^.{1,2}$"),
        Setting("channel.logo.plain", "str", "Wordmark: first part (plain colour)"),
        Setting("channel.logo.accent", "str", "Wordmark: second part (gradient)"),
        Setting("channel.colors.primary", "str", "Main brand colour", pattern=HEX),
        Setting("channel.colors.accent", "str", "Second brand colour", pattern=HEX),
        Setting("channel.colors.hot", "str", "Highlight colour (stickers, buttons)", pattern=HEX),
        Setting("channel.colors.bg", "str", "Background colour (dark themes)", pattern=HEX),
    ],
    "Content": [
        Setting("style", "str", "news = straight, comedy = jokes and punchlines", choices=STYLES),
        Setting("formats", "list", "Formats to rotate, one per video", choices=list(FORMATS)),
        Setting("count", "int", "Stories in a countdown video", lo=3, hi=7),
        Setting("language", "str", "Language of all text and voices (also switches the voices)", choices=list(LANGUAGES)),
        Setting("labels.topic", "str", "Topic word on screen: 'TODAY IN <topic>'"),
        Setting("labels.introSubtitle", "str", "Countdown intro text under 'TOP 5'"),
        Setting("labels.outroLine", "str", "Line under the follow button"),
    ],
    "Look": [
        Setting("theme", "str", "Visual theme", choices=THEMES),
        Setting("useArticleImages", "bool", "Use article images (no = generated title cards)"),
    ],
    "Characters": [
        Setting("mascot.enabled", "bool", "Animated presenter on screen (needed for sketches)"),
        Setting("mascot.name", "str", "Host character's name"),
        Setting("mascot.personality", "str", "Host personality (used when writing sketches)"),
        Setting("cohost.name", "str", "Sketch sidekick's name"),
        Setting("cohost.personality", "str", "Sidekick personality"),
    ],
    "Voices": [
        Setting("voice.name", "str", "Host voice", choices=_voices_for("voice.langCode")),
        Setting("voice.speed", "float", "Host speaking speed", lo=0.7, hi=1.6),
        Setting("voice.pitch", "float", "Host pitch: 1.0 natural, >1 cartoon, <1 deeper", lo=0.6, hi=1.6),
        Setting("cohost.voice.name", "str", "Sidekick voice", choices=_voices_for("cohost.voice.langCode")),
        Setting("cohost.voice.speed", "float", "Sidekick speaking speed", lo=0.7, hi=1.6),
        Setting("cohost.voice.pitch", "float", "Sidekick pitch", lo=0.6, hi=1.6),
    ],
    "Schedule": [],  # built per niche from its editions (see _edition_settings)
    "Editorial": [
        Setting("topic", "str", "What the channel covers (guides story picking)"),
        Setting("editorial.audience", "str", "Who the videos are for"),
        Setting("editorial.pickRules", "str", "What makes a story worth picking"),
        Setting("editorial.avoid", "str", "What never to pick"),
        Setting("editorial.tone", "str", "How the narration sounds"),
        Setting("editorial.categories", "list", "Category chips shown on stories"),
    ],
    "Video": [
        Setting("video.targetSeconds", "int", "Target video length (seconds)", lo=20, hi=170),
        Setting("video.maxSeconds", "int", "Hard maximum length (seconds)", lo=25, hi=180),
        Setting("baseHashtags", "list", "Hashtags added to every video (without #)"),
    ],
}


def _edition_settings(niche: dict) -> list[Setting]:
    out = []
    for ed in niche.get("editions", {}):
        out.append(Setting(f"editions.{ed}.time", "str", f"{ed.title()} video time", pattern=TIME))
        out.append(Setting(f"editions.{ed}.lookbackHours", "int", f"{ed.title()}: hours of news to consider", lo=2, hi=72))
        out.append(Setting(f"editions.{ed}.label", "str", f"{ed.title()}: label on screen"))
    return out


def all_settings(niche: dict | None) -> dict[str, Setting]:
    settings = {s.key: s for section in SECTIONS.values() for s in section}
    if niche:
        settings.update({s.key: s for s in _edition_settings(niche)})
    return settings


# ---------------------------------------------------------------- read / write

def _get(niche: dict, key: str):
    if key == "language":
        return niche.get("language", {}).get("name", "English").lower()
    node = niche
    for part in key.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def _set(niche: dict, key: str, value) -> None:
    if key == "language":
        code = LANGUAGES[value]
        niche.setdefault("language", {})["name"] = value.title()
        taken: set[str] = set()
        for path in ("voice", "cohost.voice"):
            voice = _get(niche, path)
            if isinstance(voice, dict):
                female = voice.get("name", "af")[1:2] != "m"
                voice["langCode"] = code
                # same gender as before, but never the same voice for host and co-host
                options = [v for v in VOICES[code] if (v[1] == "f") == female and v not in taken] or \
                          [v for v in VOICES[code] if v not in taken] or VOICES[code]
                voice["name"] = options[0]
                taken.add(voice["name"])
        return
    parts = key.split(".")
    node = niche
    for part in parts[:-1]:
        node = node.setdefault(part, {})
    node[parts[-1]] = value


def load(slug: str) -> tuple[Path, dict]:
    path = NICHES_DIR / slug / "niche.json"
    if not path.exists():
        names = ", ".join(sorted(p.name for p in NICHES_DIR.iterdir() if (p / "niche.json").exists()))
        sys.exit(f"No niche '{slug}'. Niches: {names}")
    return path, json.loads(path.read_text())


def save(path: Path, niche: dict, before: dict) -> None:
    shutil.copy(path, path.with_suffix(".json.bak"))
    path.write_text(json.dumps(niche, indent=2, ensure_ascii=False) + "\n")
    times = lambda n: {k: v.get("time") for k, v in n.get("editions", {}).items()}  # noqa: E731
    if times(niche) != times(before) and _is_scheduled(path.parent.name):
        print("Schedule changed: updating the timers...")
        subprocess.run([str(ROOT / "forge.sh"), "schedule", path.parent.name], check=False)


def _is_scheduled(slug: str) -> bool:
    """systemd timers (Linux) or launchd agents (macOS)."""
    return any((Path.home() / ".config/systemd/user").glob(f"shortforge-{slug}-*.timer")) or \
        any((Path.home() / "Library/LaunchAgents").glob(f"com.shortforge.{slug}.*.plist"))


def fmt_value(value) -> str:
    if value is None:
        return "(not set)"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, list):
        return ", ".join(str(v) for v in value) if value and not isinstance(value[0], dict) else f"{len(value)} items"
    text = str(value)
    return text if len(text) <= 70 else text[:67] + "..."


# ---------------------------------------------------------------- commands

def cmd_show(slug: str) -> None:
    _, niche = load(slug)
    print(f"\n{niche['channel']['name']}  ({slug})" + ("   [scheduled]" if _is_scheduled(slug) else ""))
    for section, settings in SECTIONS.items():
        settings = _edition_settings(niche) if section == "Schedule" else settings
        print(f"\n  {section}")
        for s in settings:
            print(f"    {s.key:<28} {fmt_value(_get(niche, s.key))}")
    print(f"\n  Sources: {len(niche.get('sources', []))} (./forge.sh sources {slug})\n")


def cmd_set(slug: str, key: str, raw: str) -> None:
    path, niche = load(slug)
    setting = all_settings(niche).get(key)
    if not setting:
        import difflib
        keys = list(all_settings(niche))
        close = difflib.get_close_matches(key, keys, n=3, cutoff=0.6) or [k for k in keys if key.split(".")[-1].lower() in k.lower()][:3]
        sys.exit(f"Unknown setting '{key}'." + (f" Did you mean: {', '.join(close)}?" if close else " See: ./forge.sh keys"))
    try:
        value = setting.parse(raw, niche)
    except ValueError as exc:
        sys.exit(f"Invalid value for {key}: {exc}")
    before = json.loads(json.dumps(niche))
    old = _get(niche, key)
    _set(niche, key, value)
    _check(niche, notes=key in ("formats", "mascot.enabled"))
    save(path, niche, before)
    print(f"{key}: {fmt_value(old)} -> {fmt_value(_get(niche, key))}")
    if key == "language":
        print(f"voices switched to {niche['voice']['name']} (host) and {_get(niche, 'cohost.voice.name')} (co-host)")


def _check(niche: dict, notes: bool = True) -> None:
    """Cross-field sanity: warn about combinations that will not behave as expected."""
    if notes and "sketch" in niche.get("formats", []) and not niche.get("mascot", {}).get("enabled"):
        print("Note: 'sketch' needs the mascot; it is skipped while mascot.enabled is no.")
    v = niche.get("video", {})
    target = v.get("targetSeconds", CONFIG["video"]["targetSeconds"])
    maximum = v.get("maxSeconds", CONFIG["video"]["maxSeconds"])
    if target > maximum:
        sys.exit(f"video.targetSeconds ({target}) must not exceed video.maxSeconds ({maximum}); raise video.maxSeconds first.")


def cmd_keys() -> None:
    for section, settings in SECTIONS.items():
        print(f"\n{section}")
        if section == "Schedule":
            print(f"  {'editions.<name>.time':<28} time like 07:30 (one per edition: morning, evening...)")
            print(f"  {'editions.<name>.lookbackHours':<28} int 2-72")
            continue
        for s in settings:
            print(f"  {s.key:<28} {s.allowed():<40} {s.help}")
    print()


def cmd_sources(slug: str, args: list[str]) -> None:
    path, niche = load(slug)
    sources = niche.setdefault("sources", [])
    action = args[0] if args else "list"
    if action == "list":
        for i, s in enumerate(sources, 1):
            print(f"  {i:>2}. {s.get('name', s['type']):<24} {s.get('url', s['type'])}")
        print(f"\n  add: ./forge.sh sources {slug} add <rss-url> [name]   remove: ./forge.sh sources {slug} remove <number>   check: ./forge.sh sources {slug} test")
        return
    if action == "add":
        if len(args) < 2:
            sys.exit("usage: sources <niche> add <rss-url> [name]")
        url, name = args[1], " ".join(args[2:])
        if url.startswith("r/"):
            name = name or url
            url = f"https://www.reddit.com/r/{url[2:]}/top/.rss?t=day"
        from new_niche import verify_feed
        src, problem = verify_feed({"type": "rss", "name": name or url, "url": url})
        if problem:
            sys.exit(f"Not added: {problem}")
        src.pop("_sample", None)
        if not name:
            from sources import parse_feed
            src["name"] = parse_feed(url).feed.get("title", url)[:40]
        if any(s.get("url") == url for s in sources):
            sys.exit("Already in the list.")
        before = json.loads(json.dumps(niche))
        sources.append(src)
        save(path, niche, before)
        print(f"Added {src['name']} ({len(sources)} sources)")
        return
    if action == "remove":
        if len(args) < 2 or not args[1].isdigit() or not 1 <= int(args[1]) <= len(sources):
            sys.exit(f"usage: sources {slug} remove <1-{len(sources)}>")
        before = json.loads(json.dumps(niche))
        gone = sources.pop(int(args[1]) - 1)
        save(path, niche, before)
        print(f"Removed {gone.get('name', gone['type'])} ({len(sources)} sources left)")
        return
    if action == "test":
        from new_niche import verify_feed
        for i, s in enumerate(sources, 1):
            if s["type"] != "rss":
                print(f"  {i:>2}. {s.get('name', s['type']):<24} (built-in source)")
                continue
            _, problem = verify_feed(dict(s))
            print(f"  {i:>2}. {s.get('name', ''):<24} {'OK' if not problem else 'PROBLEM: ' + problem}")
        return
    sys.exit("sources actions: list, add, remove, test")


def cmd_voices(language: str | None) -> None:
    codes = {LANGUAGES[language.lower()]: language} if language else {v: k for k, v in LANGUAGES.items()}
    for code, name in codes.items():
        vs = VOICES[code]
        print(f"{name.title():<14} female: {', '.join(v for v in vs if v[1] == 'f') or '-'}")
        print(f"{'':<14} male:   {', '.join(v for v in vs if v[1] == 'm') or '-'}")


def cmd_voice_test(slug: str, who: str = "host") -> None:
    import numpy as np
    import soundfile as sf
    from voice import SAMPLE_RATE, character_voice, synthesize
    _, niche = load(slug)
    voice = niche["voice"] if who == "host" else niche.get("cohost", {}).get("voice")
    if not voice:
        sys.exit("This niche has no co-host voice.")
    name = niche.get("mascot", {}).get("name") if who == "host" else niche.get("cohost", {}).get("name")
    line = f"Hi, I'm {name or 'your host'} from {niche['channel']['name']}. Here's what happened in {niche['labels']['topic']} today."
    audio, _ = synthesize(line, voice)
    audio = character_voice(audio, voice.get("pitch", 1.0))
    out = ROOT / "output" / f"voice-test-{slug}-{who}.wav"
    out.parent.mkdir(exist_ok=True)
    sf.write(out, audio / (np.max(np.abs(audio)) or 1) * 0.9, SAMPLE_RATE)
    print(f"{who} voice: {voice['name']}, speed {voice.get('speed', 1)}, pitch {voice.get('pitch', 1)}\nSaved: {out}")
    player = shutil.which("ffplay") and ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", str(out)] or \
        shutil.which("paplay") and ["paplay", str(out)]
    if player and sys.stdout.isatty():
        subprocess.run(player, check=False)


def cmd_llm(args: list[str]) -> None:
    load_env()
    env = ROOT / ".env"
    lines = env.read_text().splitlines() if env.exists() else []
    current = {m.group(1): m.group(2) for l in lines if (m := re.match(r"^(LLM_\w+)=(.*)$", l))}
    if not args:
        provider = current.get("LLM_PROVIDER") or CONFIG["llm"]["defaultProvider"]
        model = current.get("LLM_MODEL") or CONFIG["llm"]["providers"].get(provider, {}).get("model", "?")
        key = current.get("LLM_API_KEY", "")
        print(f"provider: {provider}\nmodel:    {model}\nkey:      {'set (' + key[:6] + '...)' if key else 'NOT SET'}")
        print(f"providers: {', '.join(CONFIG['llm']['providers'])}")
        return
    provider = args[0]
    if provider not in CONFIG["llm"]["providers"]:
        sys.exit(f"Unknown provider. Choose: {', '.join(CONFIG['llm']['providers'])}")
    updates = {"LLM_PROVIDER": provider}
    if len(args) > 1:
        updates["LLM_MODEL"] = args[1]
    out, done = [], set()
    for l in lines:
        m = re.match(r"^#?\s*(LLM_PROVIDER|LLM_MODEL)=", l)
        if m and m.group(1) in updates:
            if m.group(1) not in done:
                out.append(f"{m.group(1)}={updates[m.group(1)]}")
                done.add(m.group(1))
            continue
        out.append(l)
    out += [f"{k}={v}" for k, v in updates.items() if k not in done]
    if len(args) == 1:  # new provider: drop a model override that belonged to the old one
        out = [l for l in out if not l.startswith("LLM_MODEL=")]
    env.write_text("\n".join(out) + "\n")
    print(f"LLM set to {provider}" + (f" / {args[1]}" if len(args) > 1 else f" (default model {CONFIG['llm']['providers'][provider]['model']})"))
    print("Remember: the API key in .env must belong to this provider.")


# ---------------------------------------------------------------- interactive menu

def ask(prompt: str) -> str:
    try:
        return input(prompt)
    except EOFError:
        return "q"


def cmd_menu(slug: str) -> None:
    path, niche = load(slug)
    before = json.loads(json.dumps(niche))
    names = list(SECTIONS)
    while True:
        print(f"\n== {niche['channel']['name']} ({slug}) ==")
        for i, section in enumerate(names, 1):
            print(f"  {i}. {section}")
        print(f"  {len(names) + 1}. Sources")
        print("  p. Preview host voice   c. Preview co-host voice   s. Show all")
        print("  w. Save and quit        q. Quit without saving")
        choice = ask("> ").strip().lower()
        if choice == "w":
            _check(niche)
            save(path, niche, before)
            print(f"Saved {path.relative_to(ROOT)} (previous version: niche.json.bak)")
            return
        if choice == "q":
            if niche != before and ask("Discard changes? (y/n) ").strip().lower() != "y":
                continue
            return
        if choice == "s":
            print(json.dumps({k: v for k, v in niche.items() if k != "sources"}, indent=2, ensure_ascii=False))
            continue
        if choice in ("p", "c"):
            tmp = json.loads(path.read_text())
            path.write_text(json.dumps(niche, indent=2, ensure_ascii=False))  # preview with unsaved edits
            try:
                cmd_voice_test(slug, "host" if choice == "p" else "cohost")
            finally:
                path.write_text(json.dumps(tmp, indent=2, ensure_ascii=False) + "\n")
            continue
        if choice == str(len(names) + 1):
            _sources_menu(slug, path, niche)
            continue
        if not choice.isdigit() or not 1 <= int(choice) <= len(names):
            continue
        section = names[int(choice) - 1]
        settings = _edition_settings(niche) if section == "Schedule" else SECTIONS[section]
        while True:
            print(f"\n-- {section} --")
            for i, s in enumerate(settings, 1):
                print(f"  {i:>2}. {s.help:<52} {fmt_value(_get(niche, s.key))}")
            pick = ask("Number to change (Enter = back): ").strip()
            if not pick:
                break
            if not pick.isdigit() or not 1 <= int(pick) <= len(settings):
                continue
            s = settings[int(pick) - 1]
            print(f"  {s.key} = {fmt_value(_get(niche, s.key))}   ({s.allowed(niche)})")
            raw = ask("  New value (Enter = keep): ")
            if not raw.strip():
                continue
            try:
                _set(niche, s.key, s.parse(raw, niche))
                print(f"  -> {fmt_value(_get(niche, s.key))}   (not saved yet: choose 'w' to save)")
            except ValueError as exc:
                print(f"  Not changed: {exc}")


def _sources_menu(slug: str, path: Path, niche: dict) -> None:
    print("\n(Source changes are saved immediately.)")
    while True:
        _, fresh = load(slug)
        niche["sources"] = fresh.get("sources", [])
        cmd_sources(slug, ["list"])
        action = ask("a <url> [name] = add, r <number> = remove, t = test, Enter = back: ").strip()
        if not action:
            return
        parts = action.split()
        try:
            if parts[0] == "a" and len(parts) > 1:
                cmd_sources(slug, ["add", *parts[1:]])
            elif parts[0] == "r" and len(parts) > 1:
                cmd_sources(slug, ["remove", parts[1]])
            elif parts[0] == "t":
                cmd_sources(slug, ["test"])
        except SystemExit as exc:
            print(exc)


def main() -> None:
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return
    cmd, rest = args[0], args[1:]
    need = lambda n, usage: rest[:n] if len(rest) >= n else sys.exit(f"usage: ./forge.sh {usage}")  # noqa: E731
    if cmd == "menu":
        cmd_menu(*need(1, "config <niche>"))
    elif cmd == "show":
        cmd_show(*need(1, "show <niche>"))
    elif cmd == "get":
        slug, key = need(2, "get <niche> <key>")
        _, niche = load(slug)
        print(fmt_value(_get(niche, key)) if not isinstance(_get(niche, key), (dict, list)) else json.dumps(_get(niche, key), indent=2, ensure_ascii=False))
    elif cmd == "set":
        slug, key = need(2, "set <niche> <key> <value>")
        if len(rest) < 3:
            sys.exit("usage: ./forge.sh set <niche> <key> <value>")
        cmd_set(slug, key, " ".join(rest[2:]))
    elif cmd == "keys":
        cmd_keys()
    elif cmd == "sources":
        cmd_sources(need(1, "sources <niche> [list|add|remove|test]")[0], rest[1:])
    elif cmd == "voices":
        cmd_voices(" ".join(rest) or None)
    elif cmd == "voice-test":
        slug = need(1, "voice-test <niche> [host|cohost]")[0]
        cmd_voice_test(slug, rest[1] if len(rest) > 1 else "host")
    elif cmd == "llm":
        cmd_llm(rest)
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
