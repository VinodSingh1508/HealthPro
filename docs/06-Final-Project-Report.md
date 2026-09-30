# HealthPro — Final Project Report

| | |
|---|---|
| Product | HealthPro 0.1.0 |
| Date | 30 September 2026 |
| Form | Local web application |

## 1. Purpose

The project set out to build a personal nutrition tracker that can price Indian home foods, judge a day against a person's energy need and micronutrient targets, and keep that history on the same computer. Recipe generation and a diet plan were added on that base, with the same rule: measured or table-based numbers stay in code, and the language model writes language.

## 2. What was built

A React 18 interface and a FastAPI backend.

**Food lookup** searches a starter catalog of common Indian foods, an optional IFCT import, cached estimates, and USDA. Quantities scale to grams. Unknown dishes can be estimated once and reused.

**People** stores age, sex, height, weight, activity, conditions, nationality, and ethnicity. Targets change for older adults and for hypertension, diabetes, kidney disease, pregnancy, anemia, and thyroid disease.

**Daily log** sums foods and exercise, compares the day with BMR and TDEE, and saves one file per person per date.

**Trends** reads those files and reports average energy balance, repeated gaps, and a rough kilogram-per-week note.

**Recipes** suggest dishes or generate a four-mode recipe, price ingredients from tables, and store condition limits. A selected person gets an on-screen verdict that is not written onto the recipe.

**Diet plan** stores standing instructions and a six-slot daily chart with two or three options per meal. Cuisine follows nationality and ethnicity. Salt, oil, and condition lines follow the person's targets. Generating the plan does not call Gemini.

Start and stop scripts launch both servers without a visible console window and write logs under `logs/`.

## 3. Architecture outcome

The design in the HLD held. One process serves the API. One process serves the UI. JSON files are the system of record. The in-memory cache is write-through. External calls are isolated in `foods.py`, `gemini.py`, `ai_foods.py`, and `recipe_service.py`.

The important boundary is in `prepare_recipe` and the save model. Condition guidance is attached whenever a recipe is prepared. Person fit is attached only on the generate response, after preparation, and the save body cannot carry it.

## 4. Problems found and corrected

These were discovered by using the application, not by speculation.

| Observation | Cause | Correction |
|---|---|---|
| Recipe generation for "Chicken salad" appeared stuck and then failed | USDA rejected a large share of searches that put `Survey (FNDDS)` in the query string. Each miss then called Gemini, one ingredient at a time, and a single miss discarded the recipe | USDA search uses a JSON body and retries. Ingredients resolve in parallel. A miss is listed on the recipe instead of aborting it |
| Oil and some chicken cuts showed 0 kcal | Foundation records omit the energy field | Energy falls back to Atwater factors from protein, carbohydrate, and fat |
| "Black pepper" matched an unrelated food and "cooking oil" matched a dish cooked in oil | The first USDA hit was accepted | Hits must contain every query word and are scored. Weak one-word splits of multi-word names were removed |
| "Salt" could not be priced | The estimator rejects zero-energy foods | Salt is a built-in food with its sodium value |
| Gemini 503s looked like a hang | Timeouts were sequential and not retried usefully | Shared client retries overload, and quota (429) fails fast with an explanation |
| New recipe form said "Edit recipe" | The draft id `"new"` was treated as an existing id | Create is distinguished from update |

## 5. Verification

Checks performed against the implementation:

- Python modules compile.
- A Tamil / India profile with hypertension and diabetes builds a South Indian chart with six slots, three options on the main meals, a tightened salt line, and condition notes. This path does not call Gemini.
- A one-serving recipe with 8 g of salt resolves to about 3100 mg sodium, stores hypertension guidance as avoid, and does not contain `person_fit`. Person fit for a hypertension profile is also avoid.
- The frontend production build completes.
- `scripts/start.ps1` reports the UI on port 5173 and the API on port 8000.

Browser click-through of every page was not repeated for the documentation pass. The user manual lists the clicks that cover each requirement.

## 6. How the requirements landed

The SRS acceptance items for catalog lookup, diet-plan persistence shape, cuisine selection, salty-recipe guidance, and the absence of person fit on save are implemented and covered by the checks above. Day preview, trends, and the empty-Gemini-key path follow the same code paths and were exercised during construction. Official IFCT data is supported as an import and is intentionally absent until the user supplies a file.

## 7. Limits

- The starter catalog is representative, not the NIN tables.
- Household units are fixed gram guesses.
- Cooking loss is not modelled. Recipe totals are raw edible weights.
- The diet chart is a template for a customary pattern, not a prescribed menu and not adjusted meal-by-meal to the exact kilocalorie target.
- Gemini free tier for `gemini-2.5-flash` is about 20 requests a day on the key used during development. Generation stops until reset or until `GEMINI_MODEL` is changed.
- There is no login. Anyone who can open the local ports can call the API.
- Ethnicity matching is keyword based. Unrecognised text gets the general pattern on purpose.

## 8. Operation

See `Instructions.md` and `docs/07-User-Manual.md`. Data to back up is `backend/data`. Secrets to keep out of copies are in `.env`.

## 9. Possible later work

- Import a personal IFCT subset for the foods actually cooked.
- Let the user edit chart times and pin chosen options.
- Split oil across the day's chart so the gram allowance is visible on each meal.
- Add a localhost token if the machine is shared.
- Record the source id of each USDA match inside the recipe so a later cache clear cannot change a saved total silently. Saved recipes already store the nutrient snapshot, so history does not change until the user saves again.

## 10. Conclusion

HealthPro meets the personal-tracker goal: foods can be priced, days can be compared with a person-specific target, and the history stays in the project. Recipes and diet plans sit on that calculation instead of replacing it. The application is ready for personal use with the disclaimer that it teaches and tracks; it does not practise medicine.
