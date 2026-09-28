"""Structured JSON generation through any OpenAI-compatible chat API.

Works with free hosted open-source models (Groq, Cerebras, OpenRouter, Gemini's
OpenAI endpoint, ...) and local ones (Ollama). Provider presets live in config.json;
the key and optional overrides come from .env.
"""

from __future__ import annotations

import json
import os
import re
import time

import jsonschema
import requests

from common import CONFIG, load_env, log

load_env()


def _settings() -> dict:
    provider = os.environ.get("LLM_PROVIDER", CONFIG["llm"]["defaultProvider"])
    preset = CONFIG["llm"]["providers"].get(provider)
    if preset is None and not os.environ.get("LLM_BASE_URL"):
        raise SystemExit(f"Unknown LLM_PROVIDER '{provider}'. Known: {', '.join(CONFIG['llm']['providers'])}, or set LLM_BASE_URL.")
    preset = preset or {}
    key = os.environ.get("LLM_API_KEY", "")
    if preset.get("needsKey", True) and not key:
        raise SystemExit(f"LLM_API_KEY is not set. Get a free key at {preset.get('keyUrl', 'your provider')} and put it in .env")
    return {
        "provider": provider,
        "baseUrl": os.environ.get("LLM_BASE_URL", preset.get("baseUrl", "")).rstrip("/"),
        "model": os.environ.get("LLM_MODEL", preset.get("model", "")),
        "key": key,
        "jsonSchema": preset.get("jsonSchema", False),
        "extra": preset.get("extraBody", {}),
        "deep": preset.get("deepBody", {}),
    }


def _extract_json(text: str) -> dict:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, flags=re.S)
    if fenced:
        text = fenced.group(1)
    start = text.find("{")
    if start == -1:
        raise ValueError("no JSON object in the reply")
    # raw_decode parses the first complete object and ignores anything the model wrote after it.
    obj, _ = json.JSONDecoder().raw_decode(text[start:])
    return obj


def complete_json(prompt: str, schema: dict, name: str = "result", temperature: float = 0.6, deep: bool = False) -> dict:
    """Ask the model for JSON matching `schema`; validates and self-corrects.

    deep=True switches on the provider's reasoning mode (config "deepBody") for calls where care beats speed.
    """
    s = _settings()
    system = (
        "You are a careful assistant that replies with a single JSON object only, no prose. "
        "The JSON must match this JSON Schema exactly (all required fields, correct types, array lengths):\n"
        + json.dumps(schema)
    )
    messages = [{"role": "system", "content": system}, {"role": "user", "content": prompt}]
    # JSON enforcement modes, strongest first; a provider that rejects one falls back to the next.
    modes = ["schema", "object", "none"] if s["jsonSchema"] else ["object", "none"]
    last_error = ""

    for attempt in range(1, 7):
        body = {"model": s["model"], "messages": messages, "temperature": temperature, **s["extra"], **(s["deep"] if deep else {})}
        if modes[0] == "schema":
            body["response_format"] = {"type": "json_schema", "json_schema": {"name": name, "schema": schema}}
        elif modes[0] == "object":
            body["response_format"] = {"type": "json_object"}

        resp = _post(s, body)
        if resp.status_code in (400, 422) and len(modes) > 1:
            log(f"  provider rejected '{modes[0]}' JSON mode, falling back to '{modes[1]}'")
            modes.pop(0)
            continue
        if resp.status_code >= 400:
            last_error = f"HTTP {resp.status_code}: {resp.text[:300]}"
            log(f"  LLM error (attempt {attempt}): {last_error}")
            time.sleep(5 * attempt)
            continue

        data = resp.json()
        usage = data.get("usage", {})
        log(f"  llm {s['provider']}/{s['model']}: {usage.get('prompt_tokens', '?')} in, {usage.get('completion_tokens', '?')} out")
        content = data["choices"][0]["message"].get("content") or ""
        try:
            result = _extract_json(content)
            jsonschema.validate(result, schema)
            return result
        except (ValueError, json.JSONDecodeError, jsonschema.ValidationError) as exc:
            last_error = str(exc).split("\n")[0][:300]
            log(f"  invalid JSON from model (attempt {attempt}): {last_error}")
            messages = messages[:2] + [
                {"role": "assistant", "content": content[:6000]},
                {"role": "user", "content": f"That JSON is invalid: {last_error}. Reply again with the corrected, complete JSON object only."},
            ]
    raise RuntimeError(f"LLM did not return valid JSON: {last_error}")


def _post(s: dict, body: dict) -> requests.Response:
    """POST with patience for free-tier rate limits (429 + retry-after)."""
    headers = {"Content-Type": "application/json"}
    if s["key"]:
        headers["Authorization"] = f"Bearer {s['key']}"
    for wait_round in range(8):
        try:
            resp = requests.post(f"{s['baseUrl']}/chat/completions", json=body, headers=headers, timeout=300)
        except requests.RequestException as exc:
            log(f"  LLM connection problem: {exc.__class__.__name__}, retrying")
            time.sleep(10)
            continue
        if resp.status_code not in (429, 503):
            return resp
        wait = float(resp.headers.get("retry-after") or 0) or 15 * (wait_round + 1)
        wait = min(max(wait, 3), 90)
        log(f"  rate limited by {s['provider']}, waiting {wait:.0f}s")
        time.sleep(wait)
    return resp
