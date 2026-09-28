"""Collect candidate stories from the sources listed in a niche profile.

Source types:
  {"type": "rss", "name": "The Verge", "url": "https://..."}      any RSS/Atom feed (also works for Reddit: /r/<sub>/top/.rss?t=day)
  {"type": "hackernews", "minPoints": 80, "query": "optional"}      Hacker News stories via Algolia
  {"type": "dailydev"}                                              daily.dev most-upvoted posts
Every source is best-effort: a failing one is logged and skipped.
"""

from __future__ import annotations

import calendar
import html
import re
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

import feedparser
import requests

from common import log

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128 Safari/537.36"
TIMEOUT = (6, 20)


def clean(text: str | None, limit: int = 400) -> str:
    text = html.unescape(re.sub(r"<[^>]+>", " ", text or ""))
    return re.sub(r"\s+", " ", text).strip()[:limit]


def site_name(url: str) -> str:
    return urlparse(url).netloc.lower().removeprefix("www.") or "web"


def _rss_image(entry) -> str | None:
    for key in ("media_content", "media_thumbnail"):
        for media in entry.get(key) or []:
            if media.get("url"):
                return media["url"]
    for link in entry.get("links") or []:
        if link.get("type", "").startswith("image/"):
            return link.get("href")
    match = re.search(r'<img[^>]+src="([^"]+)"', entry.get("summary", "") or "")
    return match.group(1) if match else None


def parse_feed(url: str):
    resp = requests.get(url, headers={"User-Agent": UA}, timeout=TIMEOUT)
    resp.raise_for_status()
    return feedparser.parse(resp.content)


def fetch_rss(src: dict, since: datetime) -> list[dict]:
    feed = parse_feed(src["url"])
    name = src.get("name") or feed.feed.get("title") or site_name(src["url"])
    items = []
    for entry in feed.entries:
        stamp = entry.get("published_parsed") or entry.get("updated_parsed")
        if not stamp:
            continue
        published = datetime.fromtimestamp(calendar.timegm(stamp), tz=timezone.utc)
        if published < since:
            continue
        item = {
            "source": name,
            "title": clean(entry.get("title"), 200),
            "url": entry.get("link"),
            "summary": clean(entry.get("summary"), 900),
            "published": published.isoformat(),
            "image": _rss_image(entry),
            "signal": None,
        }
        if "techmeme.com" in src["url"]:
            _unwrap_techmeme(item, entry.get("summary", ""))
        if "reddit.com" in src["url"]:
            _unwrap_reddit(item, entry.get("summary", ""))
        items.append(item)
    return items


def _unwrap_techmeme(item: dict, summary_html: str) -> None:
    article = re.search(r'<a href="(https?://(?!www\.techmeme\.com)[^"]+)">', summary_html)
    if article:
        item["url"] = article.group(1)
    publisher = re.search(r"\(([^()]*?)\)\s*$", item["title"])
    if publisher:
        item["source"] = publisher.group(1).split("/")[-1].strip()
        item["title"] = item["title"][: publisher.start()].strip()
    item["image"] = None
    item["signal"] = "featured on Techmeme (curated top story)"


def _unwrap_reddit(item: dict, summary_html: str) -> None:
    """Link posts point at the external article; self posts stay on Reddit."""
    link = re.search(r'<a href="(https?://(?![^"]*reddit\.com)[^"]+)">\[link\]', summary_html)
    # Image/video posts link to Reddit's own media hosts (i.redd.it, v.redd.it): keep the discussion as the source.
    if link and "redd.it" not in link.group(1):
        item["url"] = link.group(1)
        item["source"] = site_name(link.group(1))
    item["signal"] = "popular on Reddit"


def fetch_hn(src: dict, since: datetime) -> list[dict]:
    params = {
        "tags": "story",
        "numericFilters": f"created_at_i>{int(since.timestamp())},points>{src.get('minPoints', 80)}",
        "hitsPerPage": 60,
    }
    if src.get("query"):
        params["query"] = src["query"]
    resp = requests.get("https://hn.algolia.com/api/v1/search", params=params, timeout=TIMEOUT)
    resp.raise_for_status()
    return [
        {
            "source": site_name(hit["url"]),
            "title": clean(hit["title"], 200),
            "url": hit["url"],
            "summary": "",
            "published": hit["created_at"],
            "image": None,
            "signal": f"{hit.get('points', 0)} points on Hacker News",
        }
        for hit in resp.json()["hits"]
        if hit.get("url")
    ]


def fetch_dailydev(src: dict, since: datetime) -> list[dict]:
    query = """{ mostUpvotedFeed(first: 30, period: 1) { edges { node {
        title permalink numUpvotes image createdAt summary source { name } } } } }"""
    resp = requests.post("https://api.daily.dev/graphql", json={"query": query},
                         headers={"User-Agent": UA, "content-type": "application/json"}, timeout=TIMEOUT)
    resp.raise_for_status()
    return [
        {
            "source": e["node"]["source"]["name"],
            "title": clean(e["node"]["title"], 200),
            "url": e["node"]["permalink"],
            "summary": clean(e["node"].get("summary"), 900),
            "published": e["node"].get("createdAt"),
            "image": e["node"].get("image"),
            "signal": f"{e['node'].get('numUpvotes', 0)} upvotes on daily.dev",
        }
        for e in resp.json()["data"]["mostUpvotedFeed"]["edges"]
    ]


FETCHERS = {"rss": fetch_rss, "hackernews": fetch_hn, "dailydev": fetch_dailydev}


def collect(sources: list[dict], lookback_hours: int, exclude_urls: set[str]) -> list[dict]:
    since = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
    results: list[dict] = []
    reddit = [s for s in sources if "reddit.com" in s.get("url", "")]
    others = [s for s in sources if s not in reddit]
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [(src, pool.submit(FETCHERS[src["type"]], src, since)) for src in others]
        # Reddit answers 429 to bursts: its feeds go one after another in a single worker, with backoff.
        futures += [(src, pool.submit(_polite, fetch_rss, src, since, i)) for i, src in enumerate(reddit)]
        for src, future in futures:
            label = src.get("name") or src["type"]
            try:
                got = future.result()
                for item in got:
                    item["feed"] = label
                log(f"  {label}: {len(got)} stories")
                results.extend(got)
            except Exception as exc:  # noqa: BLE001 - one bad source must not stop the run
                log(f"  {label}: FAILED ({exc.__class__.__name__})")
    if not results:
        raise RuntimeError("no source returned stories (offline, or all feeds broken?)")

    seen: set[str] = set()
    unique = []
    for item in results:
        key = normalize_url(item["url"] or "")
        if not item["title"] or not key or key in seen or key in exclude_urls:
            continue
        seen.add(key)
        unique.append(item)
    for i, item in enumerate(unique):
        item["id"] = i
    return unique


def _polite(fetch, src: dict, since: datetime, index: int) -> list[dict]:
    """Reddit allows anonymous feed readers about one request per ~30-60 s: wait as long as it asks, then retry."""
    time.sleep(index * 2)
    for attempt in range(4):
        try:
            return fetch(src, since)
        except requests.HTTPError as exc:
            resp = exc.response
            if resp is None or resp.status_code != 429 or attempt == 3:
                raise
            wait = float(resp.headers.get("x-ratelimit-reset") or resp.headers.get("retry-after") or 30)
            time.sleep(min(wait, 65) + 1)
    return []


def normalize_url(url: str) -> str:
    return url.split("?")[0].rstrip("/")
