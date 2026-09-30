from __future__ import annotations

import logging
import re
import time
from typing import Optional

import httpx

from .catalog import FOODS, foods_by_id
from .config import IFCT_IMPORT_FILE, USDA_API_KEY
from .models import FoodItem, Nutrients, NUTRIENT_KEYS
from .store import store

logger = logging.getLogger(__name__)

USDA_NUTRIENT_MAP = {
    1008: "energy_kcal",
    208: "energy_kcal",
    1003: "protein_g",
    203: "protein_g",
    1004: "fat_g",
    204: "fat_g",
    1005: "carb_g",
    205: "carb_g",
    1079: "fiber_g",
    291: "fiber_g",
    1093: "sodium_mg",
    307: "sodium_mg",
    1092: "potassium_mg",
    306: "potassium_mg",
    1087: "calcium_mg",
    301: "calcium_mg",
    1089: "iron_mg",
    303: "iron_mg",
    1090: "magnesium_mg",
    304: "magnesium_mg",
    1095: "zinc_mg",
    309: "zinc_mg",
    1106: "vitamin_a_ug",
    320: "vitamin_a_ug",
    1162: "vitamin_c_mg",
    401: "vitamin_c_mg",
    1177: "folate_ug",
    435: "folate_ug",
    1178: "vitamin_b12_ug",
    418: "vitamin_b12_ug",
    1114: "vitamin_d_ug",
    328: "vitamin_d_ug",
}

_ifct_extra: list[FoodItem] = []


def load_ifct_import() -> None:
    global _ifct_extra
    _ifct_extra = []
    if not IFCT_IMPORT_FILE.exists():
        return
    import json

    raw = json.loads(IFCT_IMPORT_FILE.read_text(encoding="utf-8"))
    for row in raw:
        nuts = row.get("nutrients_per_100g") or row.get("nutrients") or {}
        _ifct_extra.append(
            FoodItem(
                id=str(row["id"]),
                name=row["name"],
                names=row.get("names", []),
                form=row.get("form", "raw"),
                source="ifct",
                default_grams=float(row.get("default_grams", 100)),
                piece_grams=row.get("piece_grams"),
                health_notes=row.get("health_notes", "Imported from IFCT 2017 file you provided."),
                nutrients_per_100g=Nutrients(**{k: float(nuts.get(k, 0) or 0) for k in NUTRIENT_KEYS}),
            )
        )


load_ifct_import()


def all_local_foods() -> list[FoodItem]:
    cached_ai = []
    for row in store.ai_food_values():
        try:
            cached_ai.append(FoodItem(**row["food"]))
        except (KeyError, TypeError, ValueError):
            continue
    return list(FOODS) + _ifct_extra + cached_ai


def normalize_food_name(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", value.lower())).strip()


def get_exact_local(query: str, exclude_sources: tuple[str, ...] = ()) -> Optional[FoodItem]:
    normalized = normalize_food_name(query)
    for food in all_local_foods():
        if food.source in exclude_sources:
            continue
        names = [food.name, *food.names]
        if any(normalize_food_name(name) == normalized for name in names):
            return food
    return None


def _score(food: FoodItem, query: str) -> int:
    q = query.lower().strip()
    hay = " ".join([food.name, *food.names]).lower()
    if hay == q or food.name.lower() == q:
        return 100
    if hay.startswith(q) or any(n.lower().startswith(q) for n in [food.name, *food.names]):
        return 80
    if q in hay:
        return 60
    tokens = [t for t in q.replace(",", " ").split() if t]
    hits = sum(1 for t in tokens if t in hay)
    return 20 * hits if hits else 0


def search_local(query: str, limit: int = 12) -> list[FoodItem]:
    ranked = sorted(((_score(f, query), f) for f in all_local_foods()), key=lambda x: -x[0])
    return [f for s, f in ranked if s > 0][:limit]


def get_local(food_id: str) -> Optional[FoodItem]:
    return {food.id: food for food in all_local_foods()}.get(food_id)


def grams_for(food: FoodItem, quantity: float, unit: str) -> float:
    u = unit.lower().strip()
    if u in {"g", "gram", "grams"}:
        return quantity
    if u in {"kg"}:
        return quantity * 1000
    if u in {"ml"}:
        return quantity
    if u in {"piece", "pieces", "pc", "roti", "idli", "egg", "banana", "cup_item"}:
        base = food.piece_grams or food.default_grams
        return quantity * base
    if u in {"katori", "bowl"}:
        return quantity * 150
    if u in {"cup"}:
        return quantity * 200
    if u in {"tbsp", "tablespoon"}:
        return quantity * 15
    if u in {"tsp", "teaspoon"}:
        return quantity * 5
    return quantity


def scale_food(food: FoodItem, quantity: float, unit: str) -> dict:
    grams = grams_for(food, quantity, unit)
    nuts = food.nutrients_per_100g.scaled(grams / 100.0)
    return {
        "id": food.id,
        "name": food.name,
        "source": food.source,
        "form": food.form,
        "health_notes": food.health_notes,
        "quantity": quantity,
        "unit": unit,
        "grams": round(grams, 2),
        "nutrients": nuts.model_dump(),
        "per_100g": food.nutrients_per_100g.model_dump(),
    }


# Nutrient ids that only appear on some records, keyed by USDA's internal id.
USDA_FALLBACK_MAP = {
    1085: "fat_g",  # Total fat (NLEA), the only fat figure on some Foundation foods
    2047: "energy_kcal",  # Energy, Atwater general factors
    2048: "energy_kcal",  # Energy, Atwater specific factors
}


def _usda_to_nutrients(food_json: dict) -> Nutrients:
    values = {k: 0.0 for k in NUTRIENT_KEYS}
    energy_kj = 0.0
    for item in food_json.get("foodNutrients") or []:
        nutrient = item.get("nutrient") or {}
        number = nutrient.get("number") or nutrient.get("id")
        try:
            number = int(float(str(number)))
        except (TypeError, ValueError):
            number = item.get("nutrientId")
        unit = (nutrient.get("unitName") or item.get("unitName") or "").lower()
        name = (nutrient.get("name") or item.get("nutrientName") or "").lower()
        amount = float(item.get("amount", item.get("value", 0)) or 0)

        key = USDA_NUTRIENT_MAP.get(number) or USDA_FALLBACK_MAP.get(nutrient.get("id"))
        if not key:
            if "energy" not in name:
                continue
            key = "energy_kcal"
        if key == "energy_kcal" and unit == "kj":
            energy_kj = energy_kj or amount
            continue
        # Several ids map to one key; the first reported figure is the primary one.
        if amount and not values[key]:
            values[key] = amount

    if not values["energy_kcal"] and energy_kj:
        values["energy_kcal"] = round(energy_kj / 4.184, 1)
    if not values["energy_kcal"]:
        label = (food_json.get("labelNutrients") or {}).get("calories") or {}
        values["energy_kcal"] = float(label.get("value") or 0)
    if not values["energy_kcal"]:
        # Foundation records often omit energy entirely; Atwater factors are the
        # same arithmetic USDA uses to derive it.
        values["energy_kcal"] = round(
            4 * values["protein_g"] + 4 * values["carb_g"] + 9 * values["fat_g"], 1
        )
    return Nutrients(**values)


def search_usda(query: str, limit: int = 5) -> list[dict]:
    if not USDA_API_KEY:
        return []
    cache_key = f"search:{query.lower()}:{limit}"
    cached = store.usda_get(cache_key)
    if cached is not None:
        return cached
    url = "https://api.nal.usda.gov/fdc/v1/foods/search"
    # dataType in the query string makes USDA's edge reject roughly a third of
    # requests with a bare nginx 400, because of the space and parentheses in
    # "Survey (FNDDS)". The POST body carries the same filter and always lands.
    body = {
        "query": query,
        "pageSize": limit,
        "dataType": ["Foundation", "SR Legacy", "Survey (FNDDS)"],
    }
    data = None
    for attempt in range(1, 4):
        try:
            with httpx.Client(timeout=20) as client:
                r = client.post(url, params={"api_key": USDA_API_KEY}, json=body)
                r.raise_for_status()
                data = r.json()
            break
        except Exception as exc:
            logger.warning("USDA search for %r failed (attempt %s): %s", query, attempt, exc)
            if attempt < 3:
                time.sleep(0.4 * attempt)
    if data is None:
        # A transient outage is not the same as "this food does not exist",
        # so leave the cache alone and let the caller retry later.
        return []
    foods = []
    for row in data.get("foods") or []:
        fdc_id = row.get("fdcId")
        foods.append(
            {
                "id": f"usda-{fdc_id}",
                "fdcId": fdc_id,
                "name": row.get("description"),
                "source": "usda",
                "dataType": row.get("dataType"),
            }
        )
    store.usda_set(cache_key, foods)
    return foods


def get_usda_food(fdc_id: int) -> Optional[FoodItem]:
    cache_key = f"food:{fdc_id}"
    cached = store.usda_get(cache_key)
    if cached:
        return FoodItem(**cached)
    if not USDA_API_KEY:
        return None
    url = f"https://api.nal.usda.gov/fdc/v1/food/{fdc_id}"
    data = None
    for attempt in range(1, 4):
        try:
            with httpx.Client(timeout=20) as client:
                r = client.get(url, params={"api_key": USDA_API_KEY})
                r.raise_for_status()
                data = r.json()
            break
        except Exception as exc:
            logger.warning("USDA fetch of %s failed (attempt %s): %s", fdc_id, attempt, exc)
            if attempt < 3:
                time.sleep(0.4 * attempt)
    if data is None:
        return None
    food = FoodItem(
        id=f"usda-{fdc_id}",
        name=data.get("description") or f"USDA {fdc_id}",
        names=[],
        form="unknown",
        source="usda",
        default_grams=100,
        health_notes="USDA FoodData Central record. Values are typically per 100 g. Not India-specific.",
        nutrients_per_100g=_usda_to_nutrients(data),
    )
    store.usda_set(cache_key, food.model_dump())
    return food


def resolve_food(food_id: Optional[str], query: Optional[str]) -> Optional[FoodItem]:
    if food_id:
        if food_id.startswith("usda-"):
            try:
                return get_usda_food(int(food_id.split("-", 1)[1]))
            except ValueError:
                return None
        return get_local(food_id)
    if query:
        local = search_local(query, limit=1)
        if local:
            return local[0]
        usda = search_usda(query, limit=1)
        if usda:
            return get_usda_food(int(usda[0]["fdcId"]))
    return None
