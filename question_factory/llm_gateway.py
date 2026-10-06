"""The team's LLM gateway: one function, generate(system, user) -> text.

Talks to the Claude API (Messages API) with Python's standard library only (no extra installs).
Settings come from environment variables:
    ANTHROPIC_API_KEY   your key from the Claude Console (required)
    ANTHROPIC_MODEL     which model (default below; a cheaper one also works)
Docs: https://platform.claude.com/docs/en/api  ·  POST https://api.anthropic.com/v1/messages
"""
import json
import os
import urllib.error
import urllib.request

API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"
DEFAULT_MODEL = "claude-sonnet-5-5"
MAX_TOKENS = 8000
TIMEOUT_SECONDS = 120


class LLMError(RuntimeError):
    pass


def build_request(system: str, user: str, api_key: str, model: str) -> urllib.request.Request:
    body = {"model": model, "max_tokens": MAX_TOKENS, "system": system,
            "messages": [{"role": "user", "content": user}]}
    return urllib.request.Request(API_URL, data=json.dumps(body).encode("utf-8"), method="POST",
                                  headers={"x-api-key": api_key, "anthropic-version": API_VERSION,
                                           "content-type": "application/json"})


def generate(system: str, user: str, opener=urllib.request.urlopen) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        raise LLMError("ANTHROPIC_API_KEY is not set (see HOW_TO_TRY_AR.md: how to add the key)")
    model = os.environ.get("ANTHROPIC_MODEL", DEFAULT_MODEL)
    try:
        with opener(build_request(system, user, api_key, model), timeout=TIMEOUT_SECONDS) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise LLMError(f"Claude API error {e.code}: {e.read().decode('utf-8', 'ignore')[:300]}") from e
    except urllib.error.URLError as e:
        raise LLMError(f"cannot reach the Claude API: {e.reason}") from e
    text = "".join(block.get("text", "") for block in data.get("content", []) if block.get("type") == "text")
    if not text:
        raise LLMError("the Claude API answered without text")
    return text
