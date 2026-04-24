"""
extractor.py — LLM-based extraction of structured memory from git diffs.

To add a new provider, subclass LLMProvider in a new file and register it
in get_extractor(). No other file needs to change.

Returned dict shape (matches store.py schema):
    {
        "commit_hash":    str,   # empty — caller must fill in
        "commit_message": str,
        "reason":         str,
        "decision_type":  str,   # see VALID_DECISION_TYPES
        "tradeoffs":      dict,  # {chosen, rejected, known_downsides}
        "tags":           list[str],
    }
"""

import json
import logging
import os
import time
from abc import ABC, abstractmethod
from pathlib import Path

logger = logging.getLogger(__name__)

VALID_DECISION_TYPES = {
    "design_choice",
    "design_change",
    "performance",
    "security_incident_response",
    "incident",
}

_PROMPTS_DIR = Path(__file__).parent / "prompts"
_SYSTEM_PROMPT: str = (_PROMPTS_DIR / "extract_system.txt").read_text(encoding="utf-8")
_USER_TEMPLATE: str = (_PROMPTS_DIR / "extract_user.txt").read_text(encoding="utf-8")


def _fallback(commit_message: str) -> dict:
    """Return a best-effort memory when extraction fails after all retries."""
    return {
        "commit_hash": "",
        "commit_message": commit_message,
        "reason": commit_message,
        "decision_type": "design_choice",
        "tradeoffs": {
            "chosen": "Not determined — extraction failed.",
            "rejected": "Not determined — extraction failed.",
            "known_downsides": "Not determined — extraction failed.",
        },
        "tags": [],
    }


def _parse_and_validate(raw: str, commit_message: str) -> dict:
    """
    Parse the LLM response and ensure all required keys are present.
    Raises ValueError on any structural problem so the caller can retry.
    """
    # Strip accidental markdown fences
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.rsplit("```", 1)[0].strip()

    data = json.loads(text)

    required = {"reason", "decision_type", "tradeoffs", "tags"}
    missing = required - data.keys()
    if missing:
        raise ValueError(f"Missing keys in LLM response: {missing}")

    if data["decision_type"] not in VALID_DECISION_TYPES:
        raise ValueError(
            f"Invalid decision_type {data['decision_type']!r}. "
            f"Must be one of {VALID_DECISION_TYPES}"
        )

    tradeoffs = data["tradeoffs"]
    for field in ("chosen", "rejected", "known_downsides"):
        if field not in tradeoffs:
            raise ValueError(f"tradeoffs missing key: {field!r}")

    if not isinstance(data["tags"], list):
        raise ValueError("tags must be a list")

    return {
        "commit_hash": "",
        "commit_message": commit_message,
        "reason": str(data["reason"]),
        "decision_type": data["decision_type"],
        "tradeoffs": {
            "chosen": str(tradeoffs["chosen"]),
            "rejected": str(tradeoffs["rejected"]),
            "known_downsides": str(tradeoffs["known_downsides"]),
        },
        "tags": [str(t) for t in data["tags"]],
    }


class LLMProvider(ABC):
    """
    Interface for extracting structured memory from a git diff + commit message.

    To implement a new provider:
    1. Create a new file (e.g. core/providers/my_provider.py).
    2. Subclass LLMProvider and implement _call_llm.
    3. Register the provider in get_extractor() below.
    4. No other file needs to change.

    extract() contract
    ------------------
    Input:
        diff    — full text of `git diff` for the commit
        message — the commit message string

    Output (dict):
        commit_hash    str   empty string — the caller fills this in
        commit_message str   echoed from `message`
        reason         str   detailed explanation of WHY the change was made
        decision_type  str   one of VALID_DECISION_TYPES
        tradeoffs      dict  keys: chosen, rejected, known_downsides (all str)
        tags           list  list of relevant string tags

    Reliability:
        (Already baked in) 3 attempts with exponential backoff.
        On permanent failure, returns _fallback(message) rather than raising.
    """

    _MAX_RETRIES = 3
    _BASE_DELAY = 1.0  # seconds

    def extract(self, diff: str, message: str) -> dict:
        """
        Dispatch to _call_llm with retry + exponential backoff.
        Falls back gracefully if all attempts fail.
        """
        last_exc: Exception | None = None

        for attempt in range(self._MAX_RETRIES):
            try:
                raw = self._call_llm(diff, message)
                return _parse_and_validate(raw, message)
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                delay = self._BASE_DELAY * (2 ** attempt)
                logger.warning(
                    "Extraction attempt %d/%d failed (%s). Retrying in %.1fs.",
                    attempt + 1,
                    self._MAX_RETRIES,
                    exc,
                    delay,
                )
                if attempt < self._MAX_RETRIES - 1:
                    time.sleep(delay)

        logger.error(
            "All %d extraction attempts failed. Using fallback. Last error: %s",
            self._MAX_RETRIES,
            last_exc,
        )
        return _fallback(message)

    @abstractmethod
    def _call_llm(self, diff: str, message: str) -> str:
        """
        Make a single LLM call and return the raw response text.
        Raise any exception on failure; extract() handles retry logic.
        """


class AnthropicProvider(LLMProvider):
    """
    Extracts memory using the Anthropic SDK.

    Reads ANTHROPIC_API_KEY from the environment.
    Model: claude-sonnet-4-20250514 (as specified by the user).
    """

    MODEL = os.environ.get("ANTHROPIC_MODEL")

    def __init__(self) -> None:
        import anthropic  # local import keeps the dep optional

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise EnvironmentError("ANTHROPIC_API_KEY is not set.")
        self._client = anthropic.Anthropic(api_key=api_key)

    def _call_llm(self, diff: str, message: str) -> str:
        response = self._client.messages.create(
            model=self.MODEL,
            max_tokens=1024,
            system=_SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": _USER_TEMPLATE.format(diff=diff, message=message),
                }
            ],
        )
        return response.content[0].text


class OpenAICompatibleProvider(LLMProvider):
    """
    Extracts memory using the OpenAI SDK (or any OpenAI-compatible endpoint).

    Environment variables:
        OPENAI_API_KEY   — required
        OPENAI_BASE_URL  — optional (defaults to OpenAI's endpoint)
        OPENAI_MODEL     — optional (defaults to gpt-4o)

    This single adapter covers OpenAI, Grok, Groq, DeepSeek, Qwen,
    Gemini (via OpenAI-compat), vLLM, and any other OpenAI-compatible API.
    """

    DEFAULT_MODEL = os.environ.get("OPENAI_MODEL")

    def __init__(self) -> None:
        from openai import OpenAI  # local import keeps the dep optional

        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise EnvironmentError("OPENAI_API_KEY is not set.")

        base_url = os.environ.get("OPENAI_BASE_URL")  # None → uses OpenAI default
        self._model = os.environ.get("OPENAI_MODEL", self.DEFAULT_MODEL)
        self._client = OpenAI(api_key=api_key, base_url=base_url)

    def _call_llm(self, diff: str, message: str) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            max_tokens=1024,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": _USER_TEMPLATE.format(diff=diff, message=message),
                },
            ],
        )
        return response.choices[0].message.content


def get_extractor() -> LLMProvider:
    """
    Factory that reads LLM_PROVIDER from the environment and returns the
    appropriate provider instance.

    Supported values (case-insensitive):
        anthropic  — AnthropicProvider  (default)
        openai     — OpenAICompatibleProvider
    """
    provider = os.environ.get("LLM_PROVIDER", "anthropic").lower().strip()

    if provider == "anthropic":
        return AnthropicProvider()
    if provider == "openai":
        return OpenAICompatibleProvider()

    raise ValueError(
        f"Unknown LLM_PROVIDER {provider!r}. "
        "Valid options: 'anthropic', 'openai'."
    )
