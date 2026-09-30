# HealthPro — Project Synopsis

| | |
|---|---|
| Title | HealthPro: a personal food log and nutrition tracker |
| Version | 0.1.0 |
| Date | 30 September 2026 |
| Stack | React, Vite, Python, FastAPI, JSON files |
| External data | USDA FoodData Central (optional), Google Gemini (optional) |

## Abstract

HealthPro tracks what a person eats, prices those foods from composition tables, and compares the day with an energy need and micronutrient targets that change with age, sex, body size, activity, and listed conditions. It also stores a diet plan for each person and can generate recipes whose nutrition is calculated from ingredient weights.

The interface is a single-page React application with six areas: food lookup, people, daily log, trends, recipe generator, and saved recipes. The backend is a FastAPI service on the same computer. People, day logs, saved recipes, and lookup caches are JSON files under `backend/data`. The process keeps those files in memory and writes through on every change.

A food is resolved from the built-in catalog, an optional Indian Food Composition Tables import, a previous estimate, and then USDA. Gemini is asked for a nutrient estimate only when the user requests it and no table matched. Recipe wording and dish suggestions also come from Gemini, but the calorie and micronutrient totals do not. Diet plans are built in code from a cuisine pattern plus the person's existing targets, so they do not spend the model quota.

The product is for personal education. It does not diagnose disease and it does not treat nationality or ethnicity as a biological diet.

## Modules

1. **Food lookup.** Name and quantity in, energy and micronutrients out, with the data source shown.
2. **People.** Profile, conditions, nationality, ethnicity, and a saved diet plan.
3. **Daily log.** Foods, exercise, preview, and save against one person and one date.
4. **Trends.** Saved days, average calorie balance, repeated gaps, and a rough weight note.
5. **Recipes.** Suggest or generate a recipe, price the ingredients, optionally judge it for one person, and save the recipe with condition limits only.
6. **Explanation.** Optional Gemini prose over an analysis the backend has already computed.

## Data kept on disk

| File | Contents |
|---|---|
| `backend/data/people.json` | People, including diet plans |
| `backend/data/logs/<person-id>/<date>.json` | One saved day |
| `backend/data/saved_recipes.json` | Recipes and their condition guidance |
| `backend/data/usda_cache.json` | USDA search and food responses |
| `backend/data/ai_food_cache.json` | Labelled Gemini nutrient estimates |
| `backend/data/ifct_import.json` | Optional user-supplied IFCT rows |

## Result

The application runs locally with `scripts\start.cmd`. Lookup, logging, trends, manual recipes, and diet plans work without a language model. Generation and explanation need a Gemini key and stay inside the free-tier limits.
