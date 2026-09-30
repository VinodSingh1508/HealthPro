from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .explain import explain_analysis
from .foods import (
    get_exact_local,
    normalize_food_name,
    resolve_food,
    scale_food,
    search_local,
    search_usda,
)
from .models import (
    AiEstimateRequest,
    DayLogIn,
    FoodItem,
    Nutrients,
    Person,
    PersonIn,
    RecipeGenerateRequest,
    RecipeIn,
    RecipeSuggestionRequest,
)
from .nutrition import (
    bmr_kcal,
    compare_totals,
    condition_notes,
    exercise_kcal,
    person_targets,
    tdee_kcal,
    weight_trend_note,
)
from .ai_foods import estimate_food
from .diet_guidance import build_diet_plan, person_recipe_fit
from .recipe_service import generate_recipe, prepare_recipe, suggest_dishes
from .store import store

app = FastAPI(title="HealthPro", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _person_or_404(person_id: str) -> Person:
    row = store.get_person(person_id)
    if not row:
        raise HTTPException(404, "Person not found")
    return Person(**row)


@app.get("/api/health")
def health():
    from .config import GEMINI_API_KEY, USDA_API_KEY

    return {
        "ok": True,
        "gemini": bool(GEMINI_API_KEY),
        "usda": bool(USDA_API_KEY),
    }


@app.get("/api/foods/search")
def food_search(q: str, quantity: float = 100, unit: str = "g"):
    exact_food = get_exact_local(q)
    local = search_local(q)
    results = []
    for food in local:
        result = scale_food(food, quantity, unit)
        result["match_type"] = (
            "exact"
            if any(
                normalize_food_name(name) == normalize_food_name(q)
                for name in [food.name, *food.names]
            )
            else "suggestion"
        )
        results.append(result)

    # USDA search is cached on disk, including empty responses. Query it whenever
    # local data has no exact identity match instead of treating token matches as exact.
    if not exact_food:
        for row in search_usda(q, limit=5):
            if any(r["id"] == row["id"] for r in results):
                continue
            food = resolve_food(row["id"], None)
            if food:
                result = scale_food(food, quantity, unit)
                result["match_type"] = (
                    "exact"
                    if normalize_food_name(food.name) == normalize_food_name(q)
                    else "suggestion"
                )
                results.append(result)
    exact_match = next((r for r in results if r["match_type"] == "exact"), None)
    results.sort(key=lambda row: 0 if row["match_type"] == "exact" else 1)
    return {
        "query": q,
        "exact_match": bool(exact_match),
        "results": results,
    }


@app.post("/api/foods/ai-estimate")
def food_ai_estimate(body: AiEstimateRequest):
    record, cached = estimate_food(body.query)
    if not record:
        raise HTTPException(503, "Gemini could not estimate this food")
    food = FoodItem(**record["food"])
    result = scale_food(food, body.quantity, body.unit)
    result["match_type"] = "ai_estimate"
    return {
        "food": result,
        "cached": cached,
        "confidence": record.get("confidence", "medium"),
        "assumptions": record.get("assumptions", []),
        "serving_description": record.get("serving_description", ""),
        "serving_grams": record.get("serving_grams", food.default_grams),
    }


@app.get("/api/foods/{food_id}")
def food_detail(food_id: str, quantity: float = 100, unit: str = "g"):
    food = resolve_food(food_id, None)
    if not food:
        raise HTTPException(404, "Food not found")
    return scale_food(food, quantity, unit)


@app.post("/api/recipes/suggest")
def recipe_suggest(body: RecipeSuggestionRequest):
    dishes, reason = suggest_dishes(body.ingredients)
    if dishes is None:
        raise HTTPException(503, reason)
    return {"dishes": dishes, "submitted_ingredients": body.ingredients}


@app.post("/api/recipes/generate")
def recipe_generate(body: RecipeGenerateRequest):
    recipe, reason = generate_recipe(body.dish_name, body.available_ingredients)
    if not recipe:
        raise HTTPException(503, reason)
    # An ingredient with no nutrition match is reported inside the recipe rather
    # than discarding a recipe the user waited for.
    payload = prepare_recipe(recipe)
    # person_fit is for this response only. It is not part of RecipeIn, so a
    # later save cannot persist it.
    if body.person_id.strip():
        row = store.get_person(body.person_id.strip())
        if not row:
            raise HTTPException(404, "Person not found")
        payload["person_fit"] = person_recipe_fit(Person(**row), payload)
    return payload


@app.get("/api/recipes")
def recipe_list():
    return store.list_recipes()


@app.post("/api/recipes")
def recipe_create(body: RecipeIn):
    return store.save_recipe(prepare_recipe(body))


@app.get("/api/recipes/{recipe_id}")
def recipe_get(recipe_id: str):
    recipe = store.get_recipe(recipe_id)
    if not recipe:
        raise HTTPException(404, "Recipe not found")
    return recipe


@app.put("/api/recipes/{recipe_id}")
def recipe_update(recipe_id: str, body: RecipeIn):
    if not store.get_recipe(recipe_id):
        raise HTTPException(404, "Recipe not found")
    return store.save_recipe(prepare_recipe(body, recipe_id))


@app.delete("/api/recipes/{recipe_id}")
def recipe_delete(recipe_id: str):
    if not store.delete_recipe(recipe_id):
        raise HTTPException(404, "Recipe not found")
    return {"ok": True}


@app.get("/api/people")
def list_people():
    return store.list_people()


@app.post("/api/people")
def create_person(body: PersonIn):
    return store.create_person(body)


@app.post("/api/people/{person_id}/diet-plan")
def person_diet_plan(person_id: str):
    row = store.get_person(person_id)
    if not row:
        raise HTTPException(404, "Person not found")
    plan = build_diet_plan(Person(**row))
    saved = store.save_diet_plan(person_id, plan)
    return saved


@app.put("/api/people/{person_id}")
def update_person(person_id: str, body: PersonIn):
    person = store.update_person(person_id, body)
    if not person:
        raise HTTPException(404, "Person not found")
    return person


@app.delete("/api/people/{person_id}")
def delete_person(person_id: str):
    if not store.delete_person(person_id):
        raise HTTPException(404, "Person not found")
    return {"ok": True}


def _build_day(body: DayLogIn) -> dict:
    person = _person_or_404(body.person_id)
    totals = Nutrients()
    foods_out = []
    for item in body.foods:
        food = resolve_food(item.food_id, item.query)
        if not food:
            raise HTTPException(400, f"Could not resolve food: {item.food_id or item.query}")
        scaled = scale_food(food, item.quantity, item.unit)
        totals = totals.add(Nutrients(**scaled["nutrients"]))
        foods_out.append(scaled)
    exercises = []
    burn = 0.0
    for ex in body.exercises:
        kcal = exercise_kcal(ex.activity, ex.minutes, person.weight_kg)
        burn += kcal
        exercises.append({"activity": ex.activity, "minutes": ex.minutes, "kcal": kcal})
    return {
        "person_id": body.person_id,
        "date": body.date,
        "foods": foods_out,
        "exercises": exercises,
        "notes": body.notes,
        "totals": totals.model_dump(),
        "exercise_kcal": round(burn, 1),
    }


def _analyze(person: Person, day: dict) -> dict:
    totals = Nutrients(**day["totals"])
    targets = person_targets(person)
    bmr = bmr_kcal(person)
    tdee = tdee_kcal(person)
    intake = totals.energy_kcal
    burn = day.get("exercise_kcal") or 0
    need = tdee + burn
    balance = round(intake - need, 1)
    rows = compare_totals(totals, targets)
    return {
        "person": person.model_dump(),
        "date": day.get("date"),
        "bmr": bmr,
        "tdee": tdee,
        "intake_kcal": intake,
        "exercise_kcal": burn,
        "estimated_need_kcal": need,
        "calorie_balance": balance,
        "nutrients": rows,
        "notes": condition_notes(person, rows, balance),
        "disclaimer": "Educational personal tracker, not medical advice.",
    }


@app.post("/api/days/preview")
def preview_day(body: DayLogIn):
    day = _build_day(body)
    person = _person_or_404(body.person_id)
    analysis = _analyze(person, day)
    return {"day": day, "analysis": analysis}


@app.post("/api/days")
def save_day(body: DayLogIn):
    day = _build_day(body)
    store.save_day(day)
    person = _person_or_404(body.person_id)
    return {"day": day, "analysis": _analyze(person, day)}


@app.get("/api/days")
def get_day(person_id: str, date: str):
    day = store.get_day(person_id, date)
    if not day:
        raise HTTPException(404, "No log for that person and date")
    person = _person_or_404(person_id)
    return {"day": day, "analysis": _analyze(person, day)}


@app.get("/api/analysis/day")
def analysis_day(person_id: str, date: str):
    day = store.get_day(person_id, date)
    if not day:
        raise HTTPException(404, "No log for that person and date")
    return _analyze(_person_or_404(person_id), day)


@app.get("/api/analysis/trends")
def analysis_trends(person_id: str, limit: int = 30):
    person = _person_or_404(person_id)
    days = store.list_days(person_id)[-limit:]
    if not days:
        return {"person": person.model_dump(), "days": [], "summary": "No saved days yet."}
    analyses = []
    balances = []
    deficit_counts: dict[str, int] = {}
    excess_counts: dict[str, int] = {}
    for day in days:
        a = _analyze(person, day)
        analyses.append(
            {
                "date": day["date"],
                "intake_kcal": a["intake_kcal"],
                "calorie_balance": a["calorie_balance"],
                "nutrients": a["nutrients"],
            }
        )
        balances.append(a["calorie_balance"])
        for row in a["nutrients"]:
            if row["status"] in {"deficit", "low_log"}:
                deficit_counts[row["label"]] = deficit_counts.get(row["label"], 0) + 1
            if row["status"] == "excess":
                excess_counts[row["label"]] = excess_counts.get(row["label"], 0) + 1
    avg_balance = round(sum(balances) / len(balances), 1)
    notes = [
        weight_trend_note(avg_balance),
        f"Average daily calorie balance vs estimated need: {avg_balance} kcal.",
    ]
    n = len(days)
    for label, count in sorted(deficit_counts.items(), key=lambda x: -x[1]):
        if count >= max(2, n // 3):
            notes.append(f"{label} was low on {count} of {n} saved days.")
    for label, count in sorted(excess_counts.items(), key=lambda x: -x[1]):
        if count >= max(2, n // 3):
            notes.append(f"{label} was high on {count} of {n} saved days.")
    if person.conditions:
        notes.append(
            "Targets already include profile conditions: " + ", ".join(person.conditions) + "."
        )
    notes.append("Not medical advice. Incomplete logs look like deficiencies.")
    return {
        "person": person.model_dump(),
        "day_count": n,
        "average_calorie_balance": avg_balance,
        "days": analyses,
        "notes": notes,
    }


@app.post("/api/explain")
def explain(body: dict):
    text = explain_analysis(body)
    if not text:
        raise HTTPException(503, "Gemini is not configured or failed")
    return {"text": text}
