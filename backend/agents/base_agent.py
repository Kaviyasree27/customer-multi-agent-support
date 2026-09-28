"""
LLM gateway for every Aria agent.

- Exponential backoff + jitter on transient failures (429 / 5xx / timeouts)
- Hard request timeout; every failure is normalised to LLMUnavailableError
- Native JSON mode (response_format) with defensive parsing and optional
  Pydantic schema validation (structured outputs)
- Per-call telemetry (agent, model, latency, tokens, status) -> logs and the
  MongoDB `llm_calls` collection, feeding the admin cost/latency dashboard
"""

import json
import logging
import random
import re
import time
from datetime import datetime, timezone

import groq
from groq import Groq

from config import Config

log = logging.getLogger("aria.llm")

MAX_ATTEMPTS = getattr(Config, "LLM_MAX_ATTEMPTS", 3)
TIMEOUT_S = getattr(Config, "LLM_TIMEOUT_S", 20.0)

_client = (
    Groq(api_key=Config.GROQ_API_KEY, timeout=TIMEOUT_S, max_retries=0)
    if Config.GROQ_API_KEY
    else None
)

_TRANSIENT = (
    groq.RateLimitError,
    groq.APITimeoutError,
    groq.APIConnectionError,
    groq.InternalServerError,
)


class LLMUnavailableError(Exception):
    pass


def _record(entry: dict) -> None:
    """Best-effort telemetry. It must never break a customer request."""
    log.info("llm_call %s", entry)
    try:
        from extensions import db

        db.llm_calls.insert_one(dict(entry, created_at=datetime.now(timezone.utc)))
    except Exception:
        pass


def call_llm(
    system_prompt: str,
    user_prompt: str,
    max_tokens=800,
    temperature=0.4,
    agent: str = "unknown",
    json_mode: bool = False,
) -> str:
    """Single entry point for every agent's LLM calls (Groq)."""

    if _client is None:
        raise LLMUnavailableError(
            "GROQ_API_KEY is not configured on the server. Set it in backend/.env."
        )

    kwargs = dict(
        model=Config.GROQ_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=max_tokens,
        temperature=temperature,
    )
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    last_error = None

    for attempt in range(1, MAX_ATTEMPTS + 1):
        started = time.perf_counter()
        base = {"agent": agent, "model": Config.GROQ_MODEL, "attempt": attempt}

        try:
            resp = _client.chat.completions.create(**kwargs)

        except groq.BadRequestError as e:
            if "response_format" in kwargs:
                # Model without JSON mode: fall back to prompt-only JSON.
                kwargs.pop("response_format")
                continue
            last_error = e
            _record({**base, "status": "error", "error": type(e).__name__})
            break

        except _TRANSIENT as e:
            last_error = e
            _record(
                {
                    **base,
                    "status": "retry",
                    "error": type(e).__name__,
                    "latency_ms": int((time.perf_counter() - started) * 1000),
                }
            )
            if attempt < MAX_ATTEMPTS:
                time.sleep(min(8.0, 0.5 * 2 ** (attempt - 1)) + random.random() * 0.25)
            continue

        except groq.APIError as e:
            last_error = e
            _record({**base, "status": "error", "error": type(e).__name__})
            break

        usage = getattr(resp, "usage", None)
        _record(
            {
                **base,
                "status": "ok",
                "latency_ms": int((time.perf_counter() - started) * 1000),
                "prompt_tokens": getattr(usage, "prompt_tokens", None),
                "completion_tokens": getattr(usage, "completion_tokens", None),
            }
        )
        return (resp.choices[0].message.content or "").strip()

    raise LLMUnavailableError(
        "I'm having trouble reaching the AI service right now. "
        "Please try again in a moment."
    ) from last_error


def _parse_json_object(raw: str) -> dict:
    cleaned = re.sub(r"```(?:json)?", "", raw, flags=re.IGNORECASE).replace("```", "").strip()
    start = cleaned.find("{")
    if start == -1:
        return {}
    try:
        result, _ = json.JSONDecoder().raw_decode(cleaned[start:])
    except json.JSONDecodeError:
        return {}
    return result if isinstance(result, dict) else {}


def call_llm_json(
    system_prompt: str,
    user_prompt: str,
    max_tokens=500,
    agent: str = "unknown",
    schema=None,
) -> dict:
    """
    Structured output: JSON mode + defensive parsing. If a Pydantic model is
    passed as `schema`, the result is validated/coerced against it and {} is
    returned on violation (callers already fall back to safe defaults).
    """

    raw = call_llm(
        system_prompt + "\n\nRespond with ONLY valid JSON. No prose, no markdown fences.",
        user_prompt,
        max_tokens=max_tokens,
        temperature=0.1,
        agent=agent,
        json_mode=True,
    )

    result = _parse_json_object(raw)

    if schema is not None and result:
        try:
            return schema.model_validate(result).model_dump()
        except Exception:
            log.warning("Schema validation failed for agent=%s", agent)
            return {}

    return result


class AgentResult:
    """Uniform return shape every agent produces, so the orchestrator can compose them."""

    def __init__(self, reply: str, data=None, agent="", actions=None):
        self.reply = reply
        self.data = data or {}
        self.agent = agent
        self.actions = actions or []

    def to_dict(self):
        return {
            "reply": self.reply,
            "data": self.data,
            "agent": self.agent,
            "actions": self.actions,
        }