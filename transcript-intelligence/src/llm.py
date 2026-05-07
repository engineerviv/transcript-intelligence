"""
Thin wrapper around the OpenAI API.
- Uses gpt-4o-mini for cost-efficiency at scale
- All calls use JSON mode for reliable structured output
- Implements a file-based cache keyed on prompt hash to avoid re-calling the API
"""

import hashlib
import json
import os
import time

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

CACHE_PATH = os.path.join(os.path.dirname(__file__), "..", "outputs", "cache.json")
MODEL = "gpt-4o-mini"

_client: OpenAI | None = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key or api_key == "your_key_here":
            raise ValueError("Set OPENAI_API_KEY in .env")
        _client = OpenAI(api_key=api_key)
    return _client


def _load_cache() -> dict:
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH, "r") as f:
            return json.load(f)
    return {}


def _save_cache(cache: dict):
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    with open(CACHE_PATH, "w") as f:
        json.dump(cache, f, indent=2)


def _cache_key(prompt: str) -> str:
    return hashlib.sha256(prompt.encode()).hexdigest()[:16]


def call_llm(system_prompt: str, user_prompt: str, retries: int = 3) -> dict:
    """Calls gpt-4o-mini with JSON mode. Results cached to disk."""
    return _call(system_prompt, user_prompt, json_mode=True, retries=retries)  # type: ignore


def call_llm_stream(
    system_prompt: str,
    user_prompt: str,
    history: list[dict] | None = None,
):
    """Yields text chunks for streaming display. Not cached."""
    messages = [{"role": "system", "content": system_prompt}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": user_prompt})
    client = get_client()
    stream = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0,
        stream=True,
    )
    for chunk in stream:
        text = chunk.choices[0].delta.content
        if text:
            yield text


def call_llm_text(
    system_prompt: str,
    user_prompt: str,
    history: list[dict] | None = None,
    retries: int = 3,
) -> str:
    """Calls gpt-4o-mini returning plain text (for chatbot responses).

    history: list of {"role": "user"|"assistant", "content": str} prior turns.
    Chatbot responses with history are NOT cached (context is dynamic per session).
    """
    return _call(system_prompt, user_prompt, json_mode=False, history=history, retries=retries)  # type: ignore


def _call(
    system_prompt: str,
    user_prompt: str,
    json_mode: bool,
    history: list[dict] | None = None,
    retries: int = 3,
):
    has_history = bool(history)
    full_prompt = system_prompt + "||" + user_prompt + ("||json" if json_mode else "||text")
    key = _cache_key(full_prompt)

    # Skip cache for conversational turns — context is session-specific
    cache = _load_cache()
    if not has_history and key in cache:
        return cache[key]

    client = get_client()
    kwargs = {}
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    messages = [{"role": "system", "content": system_prompt}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": user_prompt})

    for attempt in range(retries):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                temperature=0,
                **kwargs,
            )
            raw = response.choices[0].message.content
            result = json.loads(raw) if json_mode else raw
            if not has_history:
                cache[key] = result
                _save_cache(cache)
            return result
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            else:
                raise RuntimeError(f"LLM call failed after {retries} attempts: {e}") from e
