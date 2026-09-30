from __future__ import annotations

import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from .ai_foods import estimate_food
from .diet_guidance import condition_guidance
from .foods import get_exact_local, get_usda_food, search_usda
from .gemini import generate_json_with_reason
from .models import FoodItem, Nutrients, RecipeIn
from .store import store

logger = logging.getLogger(__name__)

COOKING_MODES = ["Stovetop / gas", "Pressure cooker", "Air fryer", "Microwave"]


def _gemini_json(prompt: str, label: str) -> tuple[Optional[dict], str]:
    return generate_json_with_reason(prompt, label=label, temperature=0.25, timeout=60)


def suggest_dishes(ingredients: list[str]) -> tuple[Optional[list[dict]], str]:
    # Deliberately uncached: preserve the submitted list and order exactly.
    prompt = f"""
Given these available ingredients, in this exact submitted order:
{json.dumps(ingredients, ensure_ascii=False)}

Suggest up to 8 practical Indian dishes. Prefer dishes that use mostly the
available ingredients. Small pantry additions are allowed but must be listed.

Return JSON only:
{{
  "dishes": [
    {{
      "name": "dish name",
      "reason": "why it fits the available ingredients",
      "uses": ["available ingredient"],
      "extra_ingredients": ["required ingredient not provided"]
    }}
  ]
}}
Do not include recipes or nutrition yet.
"""
    payload, reason = _gemini_json(prompt, "dish suggestions")
    if not payload or not isinstance(payload.get("dishes"), list):
        return None, reason or "Gemini did not return a dish list."
    dishes = []
    for row in payload["dishes"][:8]:
        if not isinstance(row, dict) or not str(row.get("name", "")).strip():
            continue
        dishes.append(
            {
                "name": str(row["name"]).strip(),
                "reason": str(row.get("reason", "")).strip(),
                "uses": [str(x) for x in row.get("uses", [])],
                "extra_ingredients": [str(x) for x in row.get("extra_ingredients", [])],
            }
        )
    return dishes, ""


def generate_recipe(
    dish_name: str, available_ingredients: list[str]
) -> tuple[Optional[RecipeIn], str]:
    # Deliberately uncached: each request reflects the exact input and order.
    available_context = (
        "No ingredient list was supplied; provide a standard home recipe."
        if not available_ingredients
        else (
            "Use these supplied ingredients as much as possible, preserving their "
            f"meaning: {json.dumps(available_ingredients, ensure_ascii=False)}. "
            "Mark every required ingredient not in that list with is_extra=true."
        )
    )
    modes_json = json.dumps(COOKING_MODES)
    prompt = f"""
Create a practical Indian home recipe for "{dish_name}".
{available_context}

Return JSON only in exactly this structure:
{{
  "name": "recipe name",
  "description": "one sentence",
  "servings": 2,
  "ingredients": [
    {{
      "name": "generic ingredient name",
      "quantity": 1,
      "unit": "cup",
      "grams": 150,
      "is_extra": false,
      "notes": "optional preparation note"
    }}
  ],
  "preparation": ["ordered prep step"],
  "cooking_methods": [
    {{
      "mode": "Stovetop / gas",
      "applicable": true,
      "steps": ["ordered cooking step"]
    }}
  ],
  "source": "gemini"
}}

Rules:
- Ingredient order: supplied ingredients first, extras afterward.
- Every ingredient needs a realistic edible gram weight for nutrition calculation.
- Include oil, salt, sugar, garnishes, and water when used.
- Include each mode exactly once: {modes_json}.
- If a mode is unsuitable, set applicable=false and steps=[]; do not invent unsafe instructions.
- Preparation is only washing, soaking, cutting, marinating, mixing, or preheating.
- Cooking steps contain heat, timing, doneness, and safety details.
- Do not include nutrient values; the backend calculates them.
"""
    payload, reason = _gemini_json(prompt, f"recipe for {dish_name!r}")
    if not payload:
        return None, reason or "Gemini did not return a recipe."
    payload["source"] = "gemini"

    # Guarantee every required cooking mode is present, even if the model omitted one.
    methods = payload.get("cooking_methods") or []
    by_mode = {str(row.get("mode", "")).lower(): row for row in methods if isinstance(row, dict)}
    normalized_methods = []
    for mode in COOKING_MODES:
        match = next(
            (row for key, row in by_mode.items() if mode.lower() in key or key in mode.lower()),
            None,
        )
        normalized_methods.append(
            match
            or {
                "mode": mode,
                "applicable": False,
                "steps": [],
            }
        )
    payload["cooking_methods"] = normalized_methods
    try:
        return RecipeIn(**payload), ""
    except (TypeError, ValueError):
        logger.warning("Gemini recipe did not match the required schema for %r", dish_name)
        return None, "Gemini returned a recipe that did not match the expected format."


def _water_food() -> FoodItem:
    return FoodItem(
        id="ingredient-water",
        name="Water",
        names=["drinking water"],
        form="liquid",
        source="built_in",
        nutrients_per_100g=Nutrients(),
    )


def _salt_food() -> FoodItem:
    return FoodItem(
        id="ingredient-salt",
        name="Salt, table",
        names=["salt", "table salt"],
        form="raw",
        source="built_in",
        nutrients_per_100g=Nutrients(sodium_mg=38758),
    )


WATER_NAMES = {"water", "drinking water", "warm water", "hot water", "cold water"}
SALT_NAMES = {"salt", "table salt", "iodized salt", "rock salt", "sea salt"}

# Words that describe handling rather than the food itself. Food tables index
# "cumin", not "roasted cumin powder", so these are dropped when a full-phrase
# lookup misses.
QUALIFIERS = {
    "beaten", "boneless", "chilled", "chopped", "cold", "cooked", "cooking",
    "crushed", "cubed", "diced", "dried", "fine", "finely", "fresh", "freshly",
    "grated", "ground", "hot", "large", "medium", "minced", "optional",
    "organic", "peeled", "plain", "powder", "powdered", "raw", "ripe",
    "roasted", "shredded", "sliced", "small", "soaked", "thinly", "to",
    "taste", "unsalted", "warm", "washed", "whole",
}


def _query_variants(name: str) -> list[str]:
    """Progressively simpler lookup phrases, most specific first."""
    without_gloss = re.sub(r"\([^)]*\)", " ", name)
    without_gloss = re.sub(r"\s+", " ", without_gloss).strip()
    words = re.findall(r"[A-Za-z]+", without_gloss)
    core = [w for w in words if w.lower() not in QUALIFIERS]

    candidates = [name.strip(), without_gloss]
    if len(core) == 1:
        # Only a single-word food can be searched by that word alone. Splitting
        # "curry leaves" into "curry" just finds curry sauce.
        candidates.append(core[0])
    elif core:
        candidates.append(" ".join(core))
        candidates.append(" ".join(core[:2]))
        candidates.append(" ".join(core[-2:]))

    variants: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = candidate.lower().strip()
        if key and key not in seen:
            seen.add(key)
            variants.append(candidate.strip())
    return variants


def _same_word(a: str, b: str) -> bool:
    """Loose equality so 'onion' matches USDA's 'onions'."""
    if a == b:
        return True
    longer, shorter = (a, b) if len(a) > len(b) else (b, a)
    return len(shorter) >= 4 and len(longer) - len(shorter) <= 2 and longer.startswith(shorter)


def _match_score(query: str, description: str) -> int:
    """Rank a USDA hit. Its search is fuzzy enough to answer 'black pepper' with
    'Black Russian', so a weak best hit is worse than no hit at all."""
    q = query.lower().strip()
    d = description.lower().strip()
    q_tokens = re.findall(r"[a-z]+", q)
    d_tokens = re.findall(r"[a-z]+", d)
    if not q_tokens or not d_tokens:
        return 0

    matched = [t for t in q_tokens if any(_same_word(t, o) for o in d_tokens)]
    if len(matched) < len(q_tokens):
        # A hit that drops one of the words is a different food: "green chillies"
        # against "Green bean casserole". No match beats a wrong match.
        return 0

    unmatched_desc = [o for o in d_tokens if not any(_same_word(t, o) for t in q_tokens)]
    score = 100 - 8 * len(unmatched_desc)
    if d.startswith(q):
        score += 25
    return score


STRONG_MATCH = 60
WEAK_MATCH = 10


def _best_usda_food(variant: str) -> tuple[int, Optional[FoodItem]]:
    best_score = 0
    best_id = None
    for hit in search_usda(variant, limit=5):
        score = _match_score(variant, hit.get("name") or "")
        if best_id is None or score > best_score:
            best_score, best_id = score, hit.get("fdcId")
    if best_id is None or best_score < WEAK_MATCH:
        return best_score, None
    return best_score, get_usda_food(int(best_id))


def _resolve_ingredient(name: str) -> Optional[FoodItem]:
    variants = _query_variants(name)
    lowered = {v.lower() for v in variants}
    if lowered & WATER_NAMES:
        return _water_food()
    if lowered & SALT_NAMES:
        return _salt_food()

    # A previous AI estimate is the weakest source, so it must not shadow USDA.
    for variant in variants:
        exact = get_exact_local(variant, exclude_sources=("ai_estimate",))
        if exact:
            return exact

    fallback = None
    fallback_score = 0
    for index, variant in enumerate(variants):
        score, food = _best_usda_food(variant)
        if not food:
            continue
        if score >= STRONG_MATCH:
            return food
        # Later variants are vaguer, so a tie goes to the more specific phrase.
        ranked = score - 3 * index
        if fallback is None or ranked > fallback_score:
            fallback, fallback_score = food, ranked

    if fallback:
        return fallback

    record, _ = estimate_food(name)
    if record:
        return FoodItem(**record["food"])
    return None


def _resolve_all(names: list[str]) -> dict[str, Optional[FoodItem]]:
    """Resolve ingredients concurrently; each one is network-bound and slow."""
    unique = list(dict.fromkeys(names))
    if not unique:
        return {}
    with ThreadPoolExecutor(max_workers=min(4, len(unique))) as pool:
        return dict(zip(unique, pool.map(_resolve_ingredient, unique)))


def calculate_recipe_nutrition(recipe: RecipeIn) -> dict:
    resolved = _resolve_all([item.name for item in recipe.ingredients])
    total = Nutrients()
    matches = []
    unmatched = []
    for ingredient in recipe.ingredients:
        food = resolved.get(ingredient.name)
        if not food:
            unmatched.append(ingredient.name)
            continue
        total = total.add(food.nutrients_per_100g.scaled(ingredient.grams / 100.0))
        matches.append(
            {
                "ingredient": ingredient.name,
                "grams": ingredient.grams,
                "matched_food": food.name,
                "source": food.source,
            }
        )

    note = "Calculated from ingredient weights; recipe yield and cooking losses are estimates."
    if unmatched:
        note += (
            " No nutrition data was found for "
            + ", ".join(unmatched)
            + ", so those are missing from the totals."
        )
    return {
        "total_recipe": total.model_dump(),
        "per_serving": total.scaled(1 / recipe.servings).model_dump(),
        "servings": recipe.servings,
        "ingredient_matches": matches,
        "unmatched_ingredients": unmatched,
        "note": note,
    }


def prepare_recipe(recipe: RecipeIn, recipe_id: Optional[str] = None) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    existing = store.get_recipe(recipe_id) if recipe_id else None
    payload = {
        "id": recipe_id or str(uuid4()),
        **recipe.model_dump(),
        "nutrition": calculate_recipe_nutrition(recipe),
        "created_at": existing.get("created_at", now) if existing else now,
        "updated_at": now,
    }
    # General condition limits travel with the recipe. A named person's verdict does not.
    payload["condition_guidance"] = condition_guidance(payload)
    return payload
