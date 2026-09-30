# HealthPro — Low-Level Design

| | |
|---|---|
| Version | 0.1.0 |
| Date | 30 September 2026 |

This document is the implementation view of the high-level design. File names are relative to `backend/app` unless stated.

## 1. Frontend

### 1.1 Shell

`frontend/src/App.jsx` renders the title, six `NavLink`s, and a `Routes` table.

| Path | Component |
|---|---|
| `/` | `pages/Lookup.jsx` |
| `/people` | `pages/People.jsx` |
| `/log` | `pages/DailyLog.jsx` |
| `/trends` | `pages/Trends.jsx` |
| `/recipes/generate` | `pages/RecipeGenerator.jsx` |
| `/recipes` | `pages/SavedRecipes.jsx` |

`api.js` sends JSON, reads `detail` from a non-OK body, and throws `Error(detail)`.

### 1.2 People page

Form state includes nationality and ethnicity. Save posts only the profile fields, not `id` or `diet_plan`.

`POST /api/people/{id}/diet-plan` replaces the row in the list and opens the plan. The plan view has two blocks:

1. **Instructions** — `meals`, then include / moderate / avoid lists.
2. **Daily diet chart** — `diet_chart.schedule` as time, meal name, and options. `diet_chart.notes` holds condition adjustments.

### 1.3 Recipe generator

Loads people on mount. The selected id is sent as `person_id` and may be empty. On success the page keeps `person_fit` in its own state. Save posts `recipeInput(recipe)`, which copies name, description, servings, ingredients, preparation, cooking methods, and source. After save, the recipe object is the persisted one (with `condition_guidance`, without `person_fit`) while the on-screen person fit remains.

`RecipeView` shows ingredients, preparation, cooking modes, the nutrient table, person fit when passed, and condition guidance when present.

## 2. API behaviour details

### 2.1 Food search

`GET /api/foods/search?q&quantity&unit`

1. `get_exact_local(q)`.
2. `search_local` scores name and aliases: 100 exact, 80 prefix, 60 substring, else 20 per token hit. Score 0 is dropped.
3. USDA runs only when step 1 found nothing. Each USDA row is fetched and scaled. A USDA name that normalizes equal to the query is `exact`; otherwise `suggestion`.
4. Exact rows sort first.

`scale_food` uses `grams_for`:

| Unit | Grams |
|---|---|
| g | quantity |
| kg | quantity × 1000 |
| ml | quantity |
| piece, roti, idli, egg, and similar | quantity × piece grams, else default grams |
| katori, bowl | quantity × 150 |
| cup | quantity × 200 |
| tbsp | quantity × 15 |
| tsp | quantity × 5 |
| anything else | quantity, treated as grams |

### 2.2 AI estimate

`estimate_food` normalizes the query to lowercase letters and digits. Cache hit returns the stored record and `cached: true`.

The prompt asks for one serving, not per 100 g. `_clean_per_serving` multiplies by `100 / serving_grams`. A value is rejected when negative or when the per-100 g figure exceeds `NUTRIENT_LIMITS` (energy 900 kcal, macros 100 g, sodium 40000 mg, and the other ceilings in `ai_foods.py`). Energy must be positive. Serving grams must be in `(0, 2000]`.

The stored food id is `ai-` plus 12 hex characters of the normalized name. `health_notes` includes confidence, the serving description, assumptions, and a warning when Atwater calories and the stated calories differ by more than 30%.

### 2.3 USDA parsing

Search: `POST https://api.nal.usda.gov/fdc/v1/foods/search` with `dataType: ["Foundation", "SR Legacy", "Survey (FNDDS)"]` in the JSON body. Three attempts, 0.4 s and 0.8 s backoff. Failure returns `[]` and does not write the cache.

Food detail is cached under `food:{fdcId}`. Nutrient numbers use `USDA_NUTRIENT_MAP` (both legacy and current ids). Extra ids: 1085 total fat, 2047 and 2048 Atwater energy. Kilojoules are divided by 4.184. If energy is still 0, it becomes `4·protein + 4·carbohydrate + 9·fat`.

### 2.4 Nutrition

BMR, sex `male`: `10w + 6.25h − 5age + 5`. Sex `female`: same with `− 161`. Sex `other`: the mean of those two. Result rounded to 0.1.

TDEE = BMR × activity factor, rounded to 0.1.

`compare_totals` produces `{key, label, actual, target, percent, status}` as specified in the SRS.

`weight_trend_note`: `kg/week = (average balance × 7) / 7700`. Absolute change under 0.05 kg is described as near maintenance.

### 2.5 Diet plan

`profile_key` is a canonical JSON string of nationality, ethnicity, sorted conditions, sex, age, rounded weight and height, and activity. `update_person` copies the old plan onto the new record only when the keys match.

Cuisine match: if the combined text contains `jain`, use that pattern. Otherwise the longest matching keyword wins, so "south indian" beats "indian", and "ghanaian" beats the short token "han".

`build_diet_plan` always adds oil, salt, fried-snack moderation, and water. Condition blocks append further rows. `_diet_chart` overlays `CHART_OPTIONS[cuisine_id]` on `GENERAL_CHART` for breakfast, lunch, and dinner, then attaches condition notes.

Chart times are fixed anchors: 06:30, 08:00, 11:00, 13:30, 16:30, 19:30. The timing note tells the user to shift the whole day.

### 2.6 Recipe nutrition

`_query_variants` builds, in order, the original name, the name without parenthetical glosses, the words that are not in `QUALIFIERS`, the first two core words, and the last two core words. A single core word is also tried alone. Multi-word names are not split down to one word, so "curry leaves" is not searched as "curry".

`_match_score` returns 0 unless every query token has a counterpart in the description. Tokens match with a one- or two-character plural suffix when the shorter token is at least four letters (`onion` / `onions`). Matching descriptions lose 8 points per extra word and gain 25 when the description starts with the query. A strong match (60 or more) returns immediately. Otherwise the best weaker match across variants is kept, with later variants penalized by 3 points per step.

`calculate_recipe_nutrition` sums scaled nutrients. `prepare_recipe` then sets `condition_guidance`.

Generic caps used for stored guidance:

| Condition | Cap that can flag a serving |
|---|---|
| Hypertension | 1500 mg sodium / day |
| Diabetes | 180 g carbohydrate / day, plus sweet-name words |
| Kidney | 1500 mg sodium, 55 g protein, 2500 mg potassium |
| Pregnancy | ingredient words in `PREGNANCY_AVOID` |
| Anemia | tea or coffee in the ingredient list |
| Thyroid | soy, soya, or tofu |

A serving at or above 25% of a cap is `moderate`. A serving at or above 100% is `avoid`. The amount text floors the allowed servings to the nearest 0.5. Three or more allowed servings is described as a normal serving. Under 0.5 is "skip it".

`person_recipe_fit` uses the person's own targets for energy, sodium, carbohydrate, and fat. Kidney also caps protein and potassium. Hard ingredient rules apply only for conditions that person has. The verdict is the worst of the triggered limits.

### 2.7 Gemini client

`generate_json_with_reason` posts to `v1beta/models/{model}:generateContent` with `responseMimeType: application/json`. Status 500, 502, 503, and 504 retry up to three attempts with 1.5 s × attempt. Status 429 returns the quota message immediately. Missing key returns a configuration message.

Recipe calls use temperature 0.25 and a 60 s timeout. Nutrient estimates use temperature 0.1.

## 3. Store

Thread lock: `threading.RLock`.

| Method group | File |
|---|---|
| `list/get/create/update/delete_person`, `save_diet_plan` | `people.json` |
| `get_day`, `save_day`, `list_days` | `logs/<person-id>/<YYYY-MM-DD>.json` |
| `usda_get`, `usda_set` | `usda_cache.json` |
| `ai_food_get`, `ai_food_set`, `ai_food_values` | `ai_food_cache.json` |
| `list/get/save/delete_recipe` | `saved_recipes.json` |

Day cache size defaults to 400 keys. People, USDA, AI foods, and recipes are fully loaded at startup. Recent day files are preloaded.

Ids for new people and recipes are UUID4 strings. AI food ids are content hashes of the normalized query, so the same dish keeps one id.

## 4. Catalog

`FOODS` is a list of `FoodItem` built from `_RAW` tuples: id, name, aliases, form, default grams, piece grams, note, nutrient dict. Source is `starter`. The list includes cooked Indian dishes and raw staples used by recipes (green chilli, curry leaves, ginger-garlic paste, raw rice, atta, besan, spices, chicken breast, mayonnaise, and others). Salt and water are not catalog rows; `recipe_service` supplies them so salt can have sodium with zero energy, which the AI estimator would reject.

IFCT import rows use the same `FoodItem` fields. Source is `ifct`. They are loaded once at import time.

## 5. Error mapping

| Situation | Status | Detail |
|---|---|---|
| Unknown person, recipe, food, or day | 404 | Short message |
| Food on a day cannot be resolved | 400 | `Could not resolve food: ...` |
| Gemini feature failed | 503 | Reason from `gemini.py` or a feature-specific sentence |
| Validation (empty name, bad age, no ingredients) | 422 | FastAPI / Pydantic |

Recipe generation no longer fails the whole recipe because one ingredient could not be priced.

## 6. Frontend state that must stay consistent

- People list after create, update, delete, and diet-plan generation.
- Daily log food search: `exact_match === false` shows suggestions and the estimate panel. `null` means the user has not searched this text yet.
- Saved recipes: editing id `new` is a create. Any other id is a PUT.
- Recipe generator: changing the ingredient search clears the current recipe and person fit. Saving does not clear person fit.

## 7. Logging

Uvicorn writes to the redirected backend logs. Gemini and USDA failures are `logger.warning` with status and a truncated body. Application logs are not a data store; the JSON files are.

## 8. What is deliberately not designed

- No user accounts or encryption at rest. The machine user is the trust boundary.
- No background scheduler. Diet plans do not refresh until the user clicks again.
- No collaborative recipe editing.
- No automatic medical threshold beyond the coded targets.
