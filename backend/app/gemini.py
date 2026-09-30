"""One place for Gemini JSON calls.

The free tier answers 503 whenever the model is busy, often several times in a
row. Callers that fan out over many ingredients turn that into minutes of dead
waiting, so every call retries a few times before giving up.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Optional

import httpx

from .config import GEMINI_API_KEY, GEMINI_MODEL

logger = logging.getLogger(__name__)

# Transient overload, clears on retry. 429 is a spent quota and will not.
RETRY_STATUS = {500, 502, 503, 504}

QUOTA_MESSAGE = (
    "Gemini rejected the call as over quota (HTTP 429). The free tier has a "
    "daily and per-minute request cap, so wait for it to reset or use another key."
)


def generate_json(
    prompt: str,
    *,
    label: str = "request",
    temperature: float = 0.2,
    timeout: float = 45,
    attempts: int = 3,
) -> Optional[dict]:
    payload, _ = generate_json_with_reason(
        prompt, label=label, temperature=temperature, timeout=timeout, attempts=attempts
    )
    return payload


def generate_json_with_reason(
    prompt: str,
    *,
    label: str = "request",
    temperature: float = 0.2,
    timeout: float = 45,
    attempts: int = 3,
) -> tuple[Optional[dict], str]:
    """Return the parsed JSON, plus a message explaining any failure."""
    if not GEMINI_API_KEY:
        return None, "Gemini is not configured. Add GEMINI_API_KEY to .env."

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent"
    )
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": temperature,
        },
    }

    for attempt in range(1, attempts + 1):
        last = attempt == attempts
        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.post(url, params={"key": GEMINI_API_KEY}, json=body)

            if response.status_code in RETRY_STATUS and not last:
                logger.warning(
                    "Gemini %s got HTTP %s, retry %s of %s",
                    label,
                    response.status_code,
                    attempt,
                    attempts - 1,
                )
                time.sleep(1.5 * attempt)
                continue

            if response.status_code == 429:
                logger.warning("Gemini %s is out of quota: %s", label, response.text[:400])
                return None, QUOTA_MESSAGE

            response.raise_for_status()
            payload = response.json()
            text = payload["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(text), ""
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "Gemini %s failed with HTTP %s: %s",
                label,
                exc.response.status_code,
                exc.response.text[:400],
            )
            return None, f"Gemini returned HTTP {exc.response.status_code}."
        except httpx.HTTPError as exc:
            if not last:
                logger.warning("Gemini %s failed (%s), retrying", label, type(exc).__name__)
                time.sleep(1.5 * attempt)
                continue
            logger.warning("Gemini %s failed: %s", label, type(exc).__name__)
            return None, "Gemini did not respond in time."
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            logger.warning("Gemini %s returned unusable JSON: %s", label, type(exc).__name__)
            return None, "Gemini returned output that was not usable JSON."

    logger.warning("Gemini %s gave up after %s attempts", label, attempts)
    return None, "Gemini stayed overloaded across retries. Try again shortly."
