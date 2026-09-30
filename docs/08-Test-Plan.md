# HealthPro — Test Plan

| | |
|---|---|
| Version | 0.1.0 |
| Date | 30 September 2026 |
| Environment | Windows, project venv, Node, servers on 127.0.0.1 ports 8000 and 5173 |

## 1. Approach

Test the six user flows and the boundaries that have already failed once: USDA matching, zero-energy Foundation foods, Gemini quota, and person-specific text leaking into a saved recipe. Prefer the API for nutrient assertions and the browser for navigation, empty states, and the diet-plan layout.

Do not commit `.env` or real personal logs as fixtures. Use a person created for the test and delete that person and any recipe afterwards.

## 2. Smoke

| Step | Expected |
|---|---|
| `.\scripts\start.ps1` | Exit 0. UI and API URLs printed |
| `GET /api/health` | `ok: true`. `gemini` and `usda` match whether those keys are set |
| Open `/`, `/people`, `/log`, `/trends`, `/recipes/generate`, `/recipes` | Each page renders its heading and does not call a missing route |
| `.\scripts\stop.ps1` | Ports 8000 and 5173 are free |

## 3. Food lookup

| Id | Action | Expected |
|---|---|---|
| F1 | Search `roti`, quantity 2, unit `piece` | Exact match. Energy greater than 0. Source `starter` |
| F2 | Search a nonsense string with USDA key absent | No crash. Exact match false. Estimate panel available |
| F3 | Estimate a dish once, search it again | Second time is served from `ai_food_cache.json` and marked cached |
| F4 | Estimate response with energy 0 or sodium far above the ceiling | Rejected. Cache not written for that failure |

## 4. People and diet plan

| Id | Action | Expected |
|---|---|---|
| P1 | Create with age, sex, height, weight | 200. Person appears in `people.json` and the list |
| P2 | Diet plan, nationality India, ethnicity Tamil, condition hypertension | Basis names South Indian home cooking. Salt line uses the 1500 mg sodium target (about 3.9 g salt). Chart has six slots. Main meals have three options. Plan is on the person after restart |
| P3 | Ethnicity Jain | Avoid list includes meat, fish, and eggs, described as custom |
| P4 | Blank nationality and ethnicity | General pattern. Basis says the fields are blank or unmatched |
| P5 | Edit weight, then GET the person | Previous `diet_plan` is gone |
| P6 | Edit the name only, after a plan exists | `diet_plan` remains |
| P7 | Delete the person | Gone from the list. Day files already written are not required to be removed by this version; do not use a real person for this step |

## 5. Daily log and trends

| Id | Action | Expected |
|---|---|---|
| D1 | Preview one starter food and a 30-minute walk | `bmr`, `tdee`, `calorie_balance`, nutrient rows, exercise kcal |
| D2 | Preview with an unknown food id and no query | 400 |
| D3 | Save, then GET the same person and date | Totals match the preview |
| D4 | Save a second time the same date | One file, new contents |
| D5 | Trends for that person | `day_count` at least 1. Average balance present. Disclaimer-style note present |
| D6 | Trends for a person with no days | Empty days and a summary that no days are saved |
| D7 | Hypertension person, sodium over the 1500 mg target | Nutrient status excess and a hypertension note |

## 6. Recipes

| Id | Action | Expected |
|---|---|---|
| R1 | Manual recipe: 200 g cooked rice and 8 g salt, 1 serving | Sodium about 3100 mg. `condition_guidance` includes hypertension `avoid`. No `person_fit` |
| R2 | Same recipe judged with `person_recipe_fit` for a hypertension profile | Verdict `avoid` |
| R3 | Generate with `person_id`, then save using the UI save body | Generate response has `person_fit`. Saved document does not |
| R4 | Generate with Gemini quota exhausted | 503 in a few seconds. Body mentions quota. No partial recipe file |
| R5 | Ingredient `Boneless chicken breast` | Matches chicken breast, not an unrelated chicken dish, and energy per 100 g is in a raw-breast range (not 0) |
| R6 | Ingredient `Cooking oil` | Matches an oil. Energy per 100 g is hundreds of kilocalories, not 0 |
| R7 | Ingredient `Black pepper powder` | Matches pepper, not an unrelated "black" food |
| R8 | Ingredient `Curry leaves` | Does not match curry sauce. Uses the starter curry leaves when present |
| R9 | Edit a saved recipe and save | `updated_at` changes. Nutrition recomputed. `created_at` kept |
| R10 | Add recipe from the saved-recipe form | Title says add, not edit, until it has a real id |

## 7. Browser checks

| Id | Action | Expected |
|---|---|---|
| B1 | People form | Nationality and ethnicity inputs visible. Diet plan button on each saved person |
| B2 | Open a plan | Instructions heading and Daily diet chart heading. Times visible. Options are a numbered list |
| B3 | Narrow window under 800 px | Pages stack. Diet chart time and options stack |
| B4 | Recipe generator person dropdown | Empty option plus each saved person. Generating without a person shows no "For {name}" block |
| B5 | After save on the generator | Condition section remains. Person block remains on that page even though a reload of the saved recipe does not include it |
| B6 | Saved recipes empty state | "No saved recipes yet" or an empty list, no error banner |

## 8. Non-functional checks

| Id | Action | Expected |
|---|---|---|
| N1 | Restart backend | People, the open day's file, recipes, and caches reload |
| N2 | `GET /api/health` | Response has no key material |
| N3 | Frontend `npm run build` | Completes |
| N4 | Start while ports are already taken | Old listeners are stopped and the new servers answer |

## 9. Recorded results for this version

Executed while building 0.1.0:

- P2 chart shape and salt line, via `build_diet_plan`, passed.
- R1 sodium, hypertension avoid, and absence of `person_fit` on `prepare_recipe`, passed.
- R5–R8 class of matches passed against USDA plus the starter catalog during recipe debugging (chicken breast, canola oil around 850 kcal/100 g, black pepper, curry leaves).
- N3 passed after the diet-chart UI change.
- N4 passed when `start.ps1` was run to load the diet-plan and diet-chart changes.

Not re-run as a single scripted suite: F3, D1–D7, R3 in the browser, B1–B6. Those remain manual checks before a future version bump.

## 10. Exit criteria

Ship a personal build when smoke, F1, P1, P2, D1, D3, D5, R1, R3, and B1 pass, and when R4 fails closed if the Gemini quota is already spent.
