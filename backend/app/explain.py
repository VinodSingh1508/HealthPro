from __future__ import annotations

import json

import httpx

from .config import GEMINI_API_KEY, GEMINI_MODEL


def explain_analysis(payload: dict) -> str | None:
    if not GEMINI_API_KEY:
        return None
    prompt = (
        "You are a cautious nutrition explainer for a personal tracker. "
        "Use ONLY the JSON numbers. Do not invent calorie or micronutrient values. "
        "Do not diagnose or prescribe treatment. "
        "Write 3-6 short sentences in plain English for an Indian home cook. "
        "If the log looks incomplete, say so.\n\nJSON:\n"
        + json.dumps(payload, ensure_ascii=False)[:8000]
    )
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent"
    )
    try:
        with httpx.Client(timeout=40) as client:
            r = client.post(
                url,
                params={"key": GEMINI_API_KEY},
                json={"contents": [{"parts": [{"text": prompt}]}]},
            )
            r.raise_for_status()
            data = r.json()
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception:
        return None
