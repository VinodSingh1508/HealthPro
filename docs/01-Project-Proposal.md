# HealthPro — Project Proposal

| | |
|---|---|
| Product | HealthPro |
| Version | 0.1.0 |
| Date | 30 September 2026 |
| Audience | Personal use |
| Status | Implemented as a local application |

## 1. Summary

HealthPro is a personal nutrition tracker. A person looks up a food, logs a day of eating and exercise, and sees calorie balance and micronutrient gaps against targets that already include age, sex, body size, activity, and listed health conditions. The same profile can produce a diet plan and can be used to judge whether a generated recipe is a reasonable amount for that person.

The application is a React frontend and a Python FastAPI backend. All personal data stays in JSON files inside the project. External services are optional and free for personal use: USDA FoodData Central for foods missing from the local catalog, and Google Gemini for wording, dish suggestions, recipes, and estimates of foods that no table contains.

## 2. Problem

General calorie apps are a poor fit for this use.

- Indian home foods are often missing or oddly named in international databases.
- A single lookup does not answer whether the day was short of iron, sodium, or calories relative to a particular person.
- Health conditions change the target, not just the commentary. Hypertension should tighten sodium. Diabetes should tighten carbohydrate and raise the fiber target. Pregnancy should raise folate, iron, and energy.
- Asking a chatbot for the calorie count of a meal produces numbers that cannot be traced, repeated, or corrected.
- Recipe ideas and a personal diet plan are useful only when they stay tied to the foods and limits the tracker already uses.

## 3. Goals

1. Look up a food by name and quantity and show energy and micronutrients.
2. Store people with age, sex, height, weight, activity, conditions, nationality, and ethnicity.
3. Log foods and exercise for a day, compare the day with BMR, TDEE, and personal targets, and save that day against a person.
4. Show trends across saved days: calorie balance, repeated nutrient gaps, and a rough weight-direction estimate.
5. Suggest dishes and generate recipes, then calculate nutrition from ingredient weights.
6. Give each person a saved diet plan: standing instructions plus a timed daily chart with two or three options per meal.
7. When a recipe is generated for a selected person, say whether they should eat a normal serving, limit it, or skip it, and how much fits their day. Save only the condition-level warning with the recipe, not the named person's verdict.
8. Keep the project free for personal use and runnable on one Windows computer.

## 4. Approach

Numbers and judgements that can be computed are computed.

| Question | Source |
|---|---|
| Calories and micronutrients of a known food | Local starter catalog, optional IFCT import, USDA FoodData Central |
| Unknown home dish, after the user asks | Gemini estimate, validated, converted to per-100 g, cached, and labelled `ai_estimate` |
| BMR, TDEE, exercise burn, nutrient targets | Mifflin–St Jeor style BMR, activity factors, and condition adjustments in code |
| Diet plan and daily chart | Cuisine patterns selected from nationality and ethnicity, with amounts taken from that person's targets |
| Recipe text and dish suggestions | Gemini, not cached, because the ingredient list and order are part of the request |
| Recipe nutrition | Sum of resolved ingredient weights. Salt and water are built in. Other names are simplified and matched to tables before any model estimate |
| "Should this person eat this recipe?" | Computed at display time from the serving and that person's targets. Not stored on the recipe |
| "Who should limit this recipe?" | Computed from the serving and fixed condition caps, then stored with the recipe |

Gemini is a language layer. If the key is missing or the free-tier quota is spent, lookup, logging, trends, manual recipes, and diet plans still work. Only generation and prose explanation stop.

## 5. Scope

### In scope

- One user on one machine, several people in one household file.
- Six pages: Food lookup, People, Daily log, Trends, Recipe generator, Saved recipes.
- File persistence with an in-memory cache.
- Windows start and stop scripts.
- A written path for importing official IFCT 2017 rows that the user obtains themselves.

### Out of scope

- Accounts, cloud sync, mobile apps, and multi-user login.
- Diagnosis, prescribing, or replacing a clinician.
- Copying or redistributing the official IFCT book.
- Billing, paid APIs, or a hosted deployment.
- Treating nationality or ethnicity as a biological nutrient requirement. Those fields only select a customary cuisine.

## 6. Users

The user is the person running the tracker for themselves or their household. They can record more than one person. They are expected to understand that an incomplete food log looks like a deficiency.

## 7. Success criteria

- A known food such as roti returns energy and micronutrients for the entered quantity without calling a model.
- A saved day shows intake against estimated need and flags nutrients that miss the personal target.
- Trends read the saved day files for one person.
- A diet plan for a person with nationality and ethnicity is stored on that person and includes both instructions and a timed chart.
- A generated or typed recipe stores nutrition and condition guidance. It does not store which person was selected on the generator page.
- Restarting the backend does not lose people, day logs, saved recipes, or cached lookups.

## 8. Risks and responses

| Risk | Response |
|---|---|
| USDA search is flaky when filters are put in the query string | Search is sent as a JSON body, retried, and failed responses are not cached as "no such food" |
| Gemini free tier is small and often returns 503 | Transient failures are retried. Quota failures return immediately with a clear message. Nutrition does not depend on the model |
| A fuzzy food search matches the wrong row | Ingredient names are simplified, then candidates are scored. A hit that drops a word is rejected |
| Some USDA Foundation foods omit energy | Energy is derived from protein, carbohydrate, and fat when the record has no kilocalorie field |
| Model estimates can be wrong | They are range-checked, labelled, and used only after tables miss |
| Users may read the diet plan as medical advice | Every plan and analysis carries an educational disclaimer |

## 9. Cost

No application fee. USDA and Gemini keys are the personal free tiers. The IFCT dataset, if wanted as an official file, is obtained by the user from ICMR–NIN and is not bundled.
