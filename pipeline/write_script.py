"""Pick stories for today's video format, read the articles, write the script, and fact-check it."""

from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from PIL import Image

from common import log, write_json
from llm import complete_json
from sources import UA

# Free tiers allow roughly 8K tokens/minute, so prompts are kept compact.
MAX_CANDIDATES = 60
ARTICLE_CHARS = 1400


def pick_schema(count: int) -> dict:
    return {
        "type": "object",
        "properties": {
            "picks": {"type": "array", "items": {"type": "integer"}, "minItems": count, "maxItems": count + 4,
                      "description": "Candidate ids, best first, with a few backups."}
        },
        "required": ["picks"],
    }


def pick_prompt(niche: dict, fmt, edition: str, date: str, candidates: list[dict], avoid: list[str]) -> str:
    ed, k = niche["editorial"], fmt.stories_needed(niche)
    avoid_text = ""
    if avoid:
        avoid_text = "\nAlready covered in recent videos, do NOT pick these events again:\n- " + "\n- ".join(avoid[-30:]) + "\n"
    return f"""You are the editor of "{niche['channel']['name']}", a daily short-video channel about {niche['topic']}.
Audience: {ed['audience']}
This is the {edition} for {date}. Today's video is {fmt.PICK_HINT.format(n=k)}.
Pick the {k} best stories for it, plus a few backups.

Pick: {ed['pickRules']}
Avoid: {ed['avoid']}
A story reported by several sources, or with strong engagement signals, is a stronger pick.
Never pick two candidates about the same event. Keep topics varied.
{avoid_text}
Candidates (JSON lines):
""" + "\n".join(json.dumps(c, ensure_ascii=False) for c in candidates)


def _try_fetch_article(url: str) -> dict | Exception:
    try:
        return fetch_article(url)
    except Exception as exc:  # noqa: BLE001
        return exc


def fetch_article(url: str) -> dict:
    resp = requests.get(url, headers={"User-Agent": UA}, timeout=(6, 12), stream=True)
    resp.raise_for_status()
    body, deadline = b"", time.monotonic() + 15
    for chunk in resp.iter_content(65536):
        body += chunk
        if time.monotonic() > deadline or len(body) > 4_000_000:
            break
    soup = BeautifulSoup(body.decode(resp.encoding or "utf-8", errors="replace"), "html.parser")
    image = None
    for attr, key in (("property", "og:image"), ("name", "twitter:image"), ("property", "og:image:url")):
        tag = soup.find("meta", attrs={attr: key})
        if tag and tag.get("content"):
            image = tag["content"]
            break
    for tag in soup(["script", "style", "nav", "header", "footer", "aside", "form"]):
        tag.decompose()
    text = " ".join(p.get_text(" ", strip=True) for p in soup.find_all("p") if len(p.get_text(strip=True)) > 60)
    return {"url": resp.url, "text": text, "image": image}


def download_image(url: str, dest: Path) -> bool:
    try:
        resp = requests.get(url, headers={"User-Agent": UA}, timeout=(6, 15))
        resp.raise_for_status()
        img = Image.open(BytesIO(resp.content)).convert("RGB")
    except Exception as exc:  # noqa: BLE001
        log(f"    image failed: {exc.__class__.__name__}")
        return False
    if img.width < 500 or img.height < 280:
        return False
    img.thumbnail((1600, 1600))
    img.save(dest, "JPEG", quality=90)
    return True


def _shortlist(candidates: list[dict]) -> list[dict]:
    """Keep the prompt inside free-tier limits while giving every source a fair share: round-robin, newest first."""
    by_feed: dict[str, list[dict]] = {}
    for c in sorted(candidates, key=lambda c: c.get("published") or "", reverse=True):
        by_feed.setdefault(c.get("feed", c["source"]), []).append(c)
    queues = list(by_feed.values())
    picked: list[dict] = []
    while queues and len(picked) < MAX_CANDIDATES:
        for q in list(queues):
            picked.append(q.pop(0))
            if not q:
                queues.remove(q)
            if len(picked) == MAX_CANDIDATES:
                break
    return picked


def _read_articles(batch: list[dict]) -> list[dict]:
    log(f"Reading {len(batch)} articles...")
    with ThreadPoolExecutor(max_workers=8) as pool:
        fetched = list(pool.map(_try_fetch_article, [c["url"] for c in batch]))
    readable = []
    for cand, article in zip(batch, fetched):
        if isinstance(article, Exception) or len(article["text"]) < 200:
            # Publisher blocks readers (403) or page is JS-only: headline + feed summary is still a factual basis.
            brief = f"{cand['title']}. {cand['summary']}".strip()
            if len(brief) < 120:
                log(f"  skip #{cand['id']} (unreadable): {cand['title'][:60]}")
                continue
            article = {"url": cand["url"], "text": brief, "image": None}
        readable.append({**cand, "url": article["url"], "articleText": article["text"][:ARTICLE_CHARS],
                         "image": article["image"] or cand.get("image")})
        log(f"  ok #{cand['id']}: {cand['title'][:70]}")
    return readable


def fact_check(niche: dict, fmt, script: dict, sources: dict[int, dict]) -> dict:
    """Second pass in reasoning mode: compare every line with its source and fix anything unsupported."""
    schema = fmt.schema(niche)
    schema = {**schema, "properties": {**schema["properties"], "changes": {
        "type": "array", "items": {"type": "string"}, "description": "One line per correction; empty if none."}},
        "required": [*schema["required"], "changes"]}
    used = {i: sources[i]["articleText"] for i in fmt.story_ids(script) if i in sources}
    prompt = f"""You are a strict fact-checker for a {niche['topic']} short video ({fmt.NAME} format).
Compare every text in the script with the SOURCE texts (keyed by candidateId) and fix anything the sources do not directly support:
- wrong tense (an event that already happened described as upcoming, or the reverse),
- names, competitions, numbers, dates or claims that are not in the sources,
- quiz answers / true-false labels that do not match the source.
Change only the words that are wrong; leave correct text exactly as it is (do not restyle it).
Keep every candidateId, speaker, answer index and array length unchanged unless it is factually wrong.
Hooks must stay curiosity-building spoken lines, never lists.
Jokes, puns and clearly humorous opinions are allowed; only fix them if they state something false as fact.
{getattr(fmt, "CHECK_NOTES", "")}
Return the complete corrected script in the same JSON structure, plus the list of changes.

SOURCES:
{json.dumps(used, ensure_ascii=False)}

SCRIPT:
{json.dumps(script, ensure_ascii=False)}"""
    log("Fact-checking script against sources...")
    checked = complete_json(prompt, schema, "fact_check", 0.1, deep=True)
    changes = checked.pop("changes")
    if fmt.story_ids(checked) != fmt.story_ids(script):
        log("  fact-check changed which stories are used; keeping the original script")
        return script
    for change in changes:
        log(f"  fixed: {change[:150]}")
    checked["factCheckChanges"] = changes
    return checked


def write_script(niche: dict, fmt, candidates: list[dict], edition: str, date_label: str,
                 avoid_titles: list[str], run_dir: Path) -> dict:
    k = fmt.stories_needed(niche)
    want = getattr(fmt, "READ_CANDIDATES", k + (2 if k >= 3 else 1))  # backups, in case two picks are the same event
    by_id = {c["id"]: c for c in candidates}
    slim = [
        {"id": c["id"], "source": c["source"], "title": c["title"][:140],
         **({"signal": c["signal"]} if c.get("signal") else {}),
         **({"about": c["summary"][:140]} if c.get("summary") else {})}
        for c in _shortlist(candidates)
    ]

    log(f"Picking stories for a {fmt.NAME} video from {len(slim)} candidates...")
    picks = complete_json(pick_prompt(niche, fmt, edition, date_label, slim, avoid_titles), pick_schema(k), "picks", 0.3)["picks"]

    chosen, tried = [], set()
    for round_ in range(3):
        batch = [by_id[i] for i in dict.fromkeys(picks) if i in by_id and i not in tried]
        tried.update(c["id"] for c in batch)
        chosen = (chosen + _read_articles(batch))[:want]
        # backups only matter for multi-story formats (two picks can turn out to be the same event)
        if len(chosen) >= (want if k >= 3 or hasattr(fmt, "READ_CANDIDATES") else k) or round_ == 2:
            break
        remaining = [c for c in slim if c["id"] not in tried]
        if not remaining:
            break
        log(f"Only {len(chosen)} readable stories, asking for replacements...")
        picks = complete_json(
            pick_prompt(niche, fmt, edition, date_label, remaining, avoid_titles + [c["title"] for c in chosen])
            + f"\n\nPick {want - len(chosen)} or more replacement stories (not about the same events as the ones listed as already covered).",
            pick_schema(1), "picks", 0.3)["picks"]
    if len(chosen) < k:
        raise RuntimeError(f"only {len(chosen)} readable stories, need {k}")

    if getattr(fmt, "RICHEST_FIRST", False):
        chosen.sort(key=lambda c: len(c["articleText"]), reverse=True)
        log(f"  explaining the richest story ({len(chosen[0]['articleText'])} chars): {chosen[0]['title'][:60]}")
    log(f"Writing the {fmt.NAME} script...")
    ctx = f"This is the {edition} for {date_label}."
    stories = [{"candidateId": c["id"], "source": c["source"], "title": c["title"], "text": c["articleText"]} for c in chosen]
    script = complete_json(fmt.prompt(niche, ctx) + "\n\nStories (JSON lines):\n" + "\n".join(json.dumps(s, ensure_ascii=False) for s in stories),
                           fmt.schema(niche), fmt.NAME, 0.7)

    chosen_by_id = {c["id"]: c for c in chosen}
    write_json(run_dir / "sources.json", [{k_: c[k_] for k_ in ("id", "source", "title", "url", "articleText")} for c in chosen])
    script = fact_check(niche, fmt, script, chosen_by_id)

    images_dir = run_dir / "public" / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    used = []
    for i, cid in enumerate(fmt.story_ids(script)):
        cand = chosen_by_id.get(cid) or by_id.get(cid) or chosen[min(i, len(chosen) - 1)]
        entry = {"candidateId": cid, "source": cand["source"], "url": cand["url"], "originalTitle": cand["title"], "image": None}
        if niche.get("useArticleImages", True) and cand.get("image"):
            dest = images_dir / f"story{i}.jpg"
            if download_image(cand["image"], dest):
                entry["image"] = f"images/{dest.name}"
        used.append(entry)
    return {"format": fmt.NAME, **script, "sources": used}
