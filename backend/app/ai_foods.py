"""Gemini fallback that returns nutrient values for a dish we have no record for.

Values are model estimates, not measured data, so every food produced here is
tagged source="ai_estimate" and cached to disk. A dish is sent to Gemini at most
once; after that the cached food is searched like any other catalog entry.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Optional

from .foods import normalize_food_name
from .gemini import generate_json
from .models import NUTRIENT_KEYS, FoodItem, Nutrients
from .store import store

logger = logging.getLogger(__name__)

# Per 100 g upper bounds. Anything above these is a model error, not a food.
NUTRIENT_LIMITS = {
    "energy_kcal": 900,
    "protein_g": 100,
    "carb_g": 100,
    "fat_g": 100,
    "fiber_g": 100,
    "sodium_mg": 40000,
    "potassium_mg": 20000,
    "calcium_mg": 20000,
    "iron_mg": 500,
    "magnesium_mg": 5000,
    "zinc_mg": 500,
    "vitamin_a_ug": 50000,
    "vitamin_c_mg": 5000,
    "folate_ug": 5000,
    "vitamin_b12_ug": 500,
    "vitamin_d_ug": 500,
}

PROMPT = """
Give typical nutrition values for ONE serving of the Indian food "{query}" as commonly prepared at home.

Return JSON only, with exactly these keys:
{{
  "name": "canonical dish name",
  "serving_description": "1 medium roti",
  "serving_grams": 60,
  "per_serving": {{
    "energy_kcal": 0, "protein_g": 0, "carb_g": 0, "fat_g": 0, "fiber_g": 0,
    "sodium_mg": 0, "potassium_mg": 0, "calcium_mg": 0, "iron_mg": 0,
    "magnesium_mg": 0, "zinc_mg": 0, "vitamin_a_ug": 0, "vitamin_c_mg": 0,
    "folate_ug": 0, "vitamin_b12_ug": 0, "vitamin_d_ug": 0
  }},
  "assumptions": ["short note about preparation assumed"],
  "confidence": "low|medium|high"
}}

Rules:
- Describe one natural serving: one piece for rotis/idlis, one katori for dals and curries.
- per_serving values are for that single serving, in the units named by each key.
- serving_grams is the cooked, edible weight of that same single serving.
- Do not scale to 100 g and do not report values for more than one serving.
- Use 0 only when the nutrient is genuinely absent.
- Prefer values consistent with Indian food composition tables.
- No text outside the JSON, no medical advice, no extra keys.
"""


def _clean_per_serving(raw: dict, serving_grams: float) -> Optional[Nutrients]:
    """Validate a per-serving response and convert it to the per-100 g storage basis."""
    values = {}
    factor = 100.0 / serving_grams
    for key in NUTRIENT_KEYS:
        try:
            value = float(raw.get(key, 0) or 0)
        except (TypeError, ValueError):
            return None
        per_100g = value * factor
        if value < 0 or per_100g > NUTRIENT_LIMITS[key]:
            return None
        values[key] = round(per_100g, 3)
    if values["energy_kcal"] <= 0:
        return None
    return Nutrients(**values)


def _macro_warning(nutrients: Nutrients) -> str:
    implied = 4 * nutrients.protein_g + 4 * nutrients.carb_g + 9 * nutrients.fat_g
    if not implied:
        return ""
    drift = abs(implied - nutrients.energy_kcal) / nutrients.energy_kcal
    if drift > 0.3:
        return (
            f" Calories and macros disagree by {round(drift * 100)}% "
            f"({round(implied)} kcal implied by macros), so treat this as rough."
        )
    return ""


def estimate_food(query: str) -> tuple[Optional[dict], bool]:
    """Return a scaled-food dict for the dish plus whether it came from cache."""
    cache_key = normalize_food_name(query)
    cached = store.ai_food_get(cache_key)
    if cached:
        return cached, True

    payload = generate_json(
        PROMPT.format(query=query.strip()),
        label=f"nutrients for {query.strip()!r}",
        temperature=0.1,
    )
    if not payload:
        return None, False

    try:
        serving_grams = round(float(payload.get("serving_grams") or 0), 2)
    except (TypeError, ValueError):
        serving_grams = 0.0
    if serving_grams <= 0 or serving_grams > 2000:
        logger.warning("Gemini returned an unusable serving weight for %r", query)
        return None, False

    nutrients = _clean_per_serving(payload.get("per_serving") or {}, serving_grams)
    if not nutrients:
        logger.warning("Gemini returned unusable nutrient values for %r", query)
        return None, False

    name = str(payload.get("name") or query).strip() or query.strip()
    serving_description = str(payload.get("serving_description") or "").strip()
    assumptions = [str(item) for item in payload.get("assumptions", [])][:4]
    confidence = str(payload.get("confidence", "medium")).lower()
    if confidence not in {"low", "medium", "high"}:
        confidence = "medium"

    digest = hashlib.sha1(cache_key.encode("utf-8")).hexdigest()[:12]
    serving_note = (
        f"One serving = {serving_description} ({serving_grams} g). "
        if serving_description
        else f"One serving = {serving_grams} g. "
    )
    notes = (
        f"AI estimate ({confidence} confidence), not measured lab data. "
        + serving_note
        + (" ".join(assumptions) if assumptions else "Typical home preparation assumed.")
        + _macro_warning(nutrients)
    )
    food = FoodItem(
        id=f"ai-{digest}",
        name=name,
        names=[query.strip()],
        form="ai estimate",
        source="ai_estimate",
        default_grams=serving_grams,
        piece_grams=serving_grams,
        health_notes=notes,
        nutrients_per_100g=nutrients,
    )
    record = {
        "food": food.model_dump(),
        "query": query.strip(),
        "confidence": confidence,
        "assumptions": assumptions,
        "serving_description": serving_description,
        "serving_grams": serving_grams,
    }
    store.ai_food_set(cache_key, record)
    return record, False
