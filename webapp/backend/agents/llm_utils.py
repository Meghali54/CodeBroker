"""Shared helper for running a one-shot Google ADK LlmAgent prompt.

Centralizes the ADK boilerplate used by the Improvement and Executive Report
agents (the only two stages in the pipeline that call an LLM at all — the
Repository, Security, Architecture, and Quality agents are pure static
analysis and never touch Gemini). Adds three things on top of a bare call:

  1. Response caching, keyed on (name, instruction, prompt) — re-analyzing
     the same repository in the same process won't re-spend quota.
  2. A reused LlmAgent/InMemoryRunner per agent `name`, instead of building
     a new one on every call.
  3. A simple self-imposed rate limiter (minimum spacing between calls) plus
     retry-with-backoff on 429s, to stay under the free tier's
     requests-per-minute cap even though the pipeline only makes two LLM
     calls per run.
"""
from __future__ import annotations

import asyncio
import hashlib
import os
import time

_response_cache: dict[str, tuple[str, int]] = {}
_agent_cache: dict[str, tuple] = {}  # name -> (LlmAgent, InMemoryRunner)

_rate_limit_lock = asyncio.Lock()
_last_call_at: float = 0.0
MIN_SECONDS_BETWEEN_CALLS = float(os.getenv("GEMINI_MIN_SECONDS_BETWEEN_CALLS", "4"))


def _cache_key(name: str, instruction: str, prompt: str) -> str:
    raw = f"{name}::{instruction}::{prompt}".encode("utf-8", errors="ignore")
    return hashlib.sha256(raw).hexdigest()


def _get_or_build_agent(name: str, instruction: str):
    """Reuses one LlmAgent/InMemoryRunner per agent name across calls."""
    if name not in _agent_cache:
        from google.adk.agents import LlmAgent
        from google.adk.runners import InMemoryRunner

        agent = LlmAgent(
            name=name,
            model="gemini-2.5-flash",
            description=f"{name} for the Code Broker executive pipeline.",
            instruction=instruction,
        )
        runner = InMemoryRunner(agent=agent)
        _agent_cache[name] = (agent, runner)
    return _agent_cache[name]


async def _throttle() -> None:
    """Ensures at least MIN_SECONDS_BETWEEN_CALLS between Gemini calls
    regardless of how many pipeline stages end up calling this concurrently."""
    global _last_call_at
    async with _rate_limit_lock:
        elapsed = time.monotonic() - _last_call_at
        wait = MIN_SECONDS_BETWEEN_CALLS - elapsed
        if wait > 0:
            await asyncio.sleep(wait)
        _last_call_at = time.monotonic()


async def run_llm_prompt(
    name: str, instruction: str, prompt: str, max_retries: int = 4
) -> tuple[str, int]:
    """Runs a single-turn Gemini prompt via Google ADK.

    Cached, throttled, retried-with-backoff on 429s, and degrades to a
    clearly-labeled fallback string (rather than raising) if the API key is
    missing or the call ultimately fails, so the rest of the pipeline still
    completes end-to-end.

    Args:
        name: A short agent name — also used as the reused-agent cache key.
        instruction: The system instruction for the agent.
        prompt: The user-turn content to send.
        max_retries: How many times to retry on a 429 before giving up.

    Returns:
        A tuple of (response_text, approximate_tokens_used).
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return (
            "[LLM unavailable: GOOGLE_API_KEY not set. Showing computed metrics only "
            "for this section; set GOOGLE_API_KEY to enable AI-generated analysis.]",
            0,
        )

    key = _cache_key(name, instruction, prompt)
    if key in _response_cache:
        return _response_cache[key]

    last_error: Exception | None = None
    for attempt in range(max_retries):
        try:
            await _throttle()
            _, runner = _get_or_build_agent(name, instruction)
            response = await runner.run_debug(prompt)
            text = response if isinstance(response, str) else str(response)

            tokens_used = 0
            usage = getattr(response, "usage_metadata", None)
            if usage is not None:
                tokens_used = getattr(usage, "total_token_count", 0) or 0
            if not tokens_used:
                # Rough fallback estimate (~4 chars/token) when usage metadata isn't exposed.
                tokens_used = max(1, (len(prompt) + len(text)) // 4)

            result = (text, tokens_used)
            _response_cache[key] = result
            return result

        except Exception as exc:  # noqa: BLE001 - surface any ADK/model error as a fallback, not a crash
            last_error = exc
            is_rate_limit = "429" in str(exc) or "RESOURCE_EXHAUSTED" in str(exc)
            if is_rate_limit and attempt < max_retries - 1:
                # Exponential backoff: 4s, 8s, 16s...
                await asyncio.sleep(2 ** (attempt + 2))
                continue
            break

    return f"[LLM call failed: {last_error}. Showing computed metrics only for this section.]", 0
