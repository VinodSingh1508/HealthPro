# HealthPro — Software Requirements Specification

| | |
|---|---|
| Product | HealthPro 0.1.0 |
| Date | 30 September 2026 |
| Kind | Personal single-computer application |

## 1. Introduction

### 1.1 Purpose

This specification states what HealthPro must do so that a person can look up foods, log days, review trends, keep recipes, and read a diet plan without sending personal logs to an account service.

### 1.2 Product boundary

HealthPro is the React application served on port 5173 and the FastAPI application served on port 8000. USDA and Gemini are external optional services. The official IFCT PDF is not part of the software; the user may import rows they are allowed to use.

### 1.3 Definitions

| Term | Meaning |
|---|---|
| BMR | Basal metabolic rate, estimated with a Mifflin–St Jeor style formula |
| TDEE | BMR multiplied by the person's activity factor |
| Target | Daily amount used for comparison. Energy comes from TDEE. Other nutrients start from adult reference values and then change for sex, age, and conditions |
| Exact match | A catalog, import, or cached estimate whose name or alias normalizes to the query |
| AI estimate | A nutrient vector produced by Gemini, checked against upper bounds, stored as per 100 g, and labelled as an estimate |
| Condition guidance | A note stored on a recipe for anyone with a tracked condition |
| Person fit | A verdict for one named person, shown while generating a recipe and not saved on the recipe |
| Cuisine pattern | A customary meal style chosen from the words in nationality and ethnicity |

### 1.4 References

- USDA FoodData Central API, `https://api.nal.usda.gov/fdc/v1/`
- Google Gemini API, model named by `GEMINI_MODEL` (default `gemini-2.5-flash`)
- ICMR–NIN Indian Food Composition Tables 2017, user-supplied import only
- Project instructions in `Instructions.md`

## 2. Overall description

### 2.1 Product perspective

The user works in a browser on the same machine as the API. There is no login. The browser calls `/api/...`. Vite proxies those calls in development. Personal data never leaves the project directory except for the food-name queries sent to USDA or Gemini when those features are used.

### 2.2 User characteristics

One operator. They may track several household members. They are not assumed to be a clinician. They must be able to type food names, quantities, and a person profile.

### 2.3 Operating environment

- Windows 10 or later, PowerShell available
- Python 3 with the packages in `backend/requirements.txt`
- Node.js with the packages in `frontend/package.json`
- Browser that can open `http://127.0.0.1:5173`
- Optional outbound HTTPS to USDA and Google

### 2.4 Constraints

- Personal use, no paid tier required.
- Nutrient numbers shown as measurements must come from a table, a validated estimate, or arithmetic on those values.
- Official IFCT content must not be copied into the repository by the application.
- Nationality and ethnicity must not be described as biological requirements.
- The application must say that it is educational and not medical advice.

### 2.5 Assumptions

- Portion units are household approximations: gram, kilogram, millilitre, piece, katori or bowl (150 g), cup (200 g), tablespoon (15 g), teaspoon (5 g).
- One saved file per person per date is enough. Saving again replaces that date.
- Incomplete logs are common. Low sodium in particular should be described as a possibly incomplete diary.
- The operator accepts that recipe yield and cooking losses are estimates.

## 3. Functional requirements

### 3.1 Food lookup

**FR-1.** The user can enter a food name, a quantity, and a unit and receive matching foods with scaled energy and micronutrients.

**FR-2.** The system searches the starter catalog, the IFCT import if present, and cached AI estimates. An exact name or alias is reported as an exact match. Other hits are suggestions.

**FR-3.** If there is no exact local match, the system searches USDA Foundation, SR Legacy, and Survey (FNDDS), using a cached response when one exists.

**FR-4.** Each result shows source (`starter`, `ifct`, `usda`, or `ai_estimate`), form, grams used, nutrients for the portion, and any health note stored with the food.

**FR-5.** When there is no exact match, the user may request an AI estimate. The estimate is for one serving, checked for negative values and absurd per-100 g magnitudes, converted to per 100 g, and written to `ai_food_cache.json`. A later lookup of the same normalized name must not call Gemini again.

**FR-6.** If Gemini cannot estimate the food, the lookup page remains usable and the error is shown.

Tracked nutrients: energy (kcal), protein, carbohydrate, fat, fiber, sodium, potassium, calcium, iron, magnesium, zinc, vitamin A, vitamin C, folate, vitamin B12, vitamin D.

### 3.2 People

**FR-7.** The user can create, edit, and delete a person.

**FR-8.** A person has name, sex (`male`, `female`, or `other`), age (1–120), height in centimetres, weight in kilograms, activity (`sedentary`, `light`, `moderate`, `active`, `very_active`), and zero or more of: hypertension, diabetes, anemia, pregnancy, thyroid, kidney.

**FR-9.** A person may have nationality and ethnicity as free text. Both may be blank.

**FR-10.** From the people list, the user can request a diet plan. The plan is stored on that person and includes:

- a basis sentence naming the cuisine pattern, or saying that none matched
- standing meal instructions
- foods to eat regularly, each with an amount and a reason
- foods to limit, each with an amount and a reason
- foods to leave out or keep very small, each with an amount and a reason
- a daily chart with times and two or three alternatives for each eating occasion
- a disclaimer

**FR-11.** Chart occasions are: on waking, breakfast, mid-morning, lunch, evening snack, and dinner. Breakfast, lunch, and dinner have three options when a cuisine chart exists. The on-waking slot may have two.

**FR-12.** Amounts that depend on salt, oil, rice, or protein use `person_targets` for that person. Hypertension tightens sodium before the salt sentence is written. Diabetes adds a rice and sweets limit and a no-sugary-drinks line. Kidney, anemia, pregnancy, and thyroid add the adjustments implemented in `diet_guidance.py`.

**FR-13.** Editing a person keeps the stored plan only when nationality, ethnicity, conditions, sex, age, weight, height, and activity are unchanged. Any change to those fields drops the plan until the user generates it again.

**FR-14.** A Jain ethnicity selects the Jain vegetarian chart and lists meat, fish, and eggs as a customary omission, described as custom rather than a medical limit.

**FR-15.** If nationality and ethnicity do not match a known cuisine, the plan uses the general pattern and says so.

### 3.3 Daily log and day analysis

**FR-16.** The user can add foods by search, with quantity and unit, and can add exercise as an activity and a number of minutes.

**FR-17.** The user can preview a day before saving. Preview requires a person.

**FR-18.** Saving a day requires a person and a date. The saved document contains the resolved foods, exercise rows, totals, and exercise kilocalories.

**FR-19.** Saving the same person and date replaces the previous file.

**FR-20.** Analysis reports:

- BMR and TDEE
- intake kilocalories
- exercise kilocalories
- estimated need = TDEE + exercise
- calorie balance = intake − estimated need
- each tracked nutrient against the personal target, with a status
- short notes that mention condition-specific misses
- the disclaimer

**FR-21.** Sodium above the personal target is excess. Sodium under 40% of target is `low_log`, and the note must say the diary may be incomplete. Energy under 90% of target is a deficit. Energy over 110% is excess. Other nutrients under 70% of target are deficits. Fat or carbohydrate over 150% of target is excess.

**FR-22.** The user may request a Gemini explanation of an analysis payload. The explanation is prose about numbers already computed. If Gemini is unavailable, the analysis itself is still shown.

### 3.4 Trends

**FR-23.** The user selects a person and sees up to a requested number of recent saved days (default 30).

**FR-24.** The response includes each day's intake and calorie balance, the average calorie balance, repeated low or high nutrients (at least two days, or at least one third of the days), a weight-direction sentence using about 7700 kcal per kilogram, and a reminder that targets already include listed conditions.

**FR-25.** If the person has no saved days, the response says so and does not invent a trend.

### 3.5 Recipes

**FR-26.** The user can enter an ordered ingredient list and receive up to eight dish suggestions. Suggestions are not cached.

**FR-27.** The user can generate a recipe from a dish name, with or without the available-ingredient list. The recipe includes a name, description, servings, ingredients with gram weights and an extra-ingredient flag, preparation steps, and four cooking modes: stovetop / gas, pressure cooker, air fryer, and microwave. An unsuitable mode is marked not applicable rather than given invented steps.

**FR-28.** Nutrition is calculated by resolving every ingredient to a food and scaling per-100 g values by edible grams, then dividing by servings. Unresolved ingredients are listed and omitted from the totals. The recipe is still returned.

**FR-29.** Resolution order for an ingredient is: built-in water, built-in salt, local exact match excluding AI estimates, USDA with a scored match, then a Gemini estimate. Qualifiers such as "chopped" and "roasted" are removed when the full phrase misses. A USDA hit that does not contain every query word is rejected.

**FR-30.** The generator can optionally send a person id. The response then includes a person fit: verdict `good`, `moderate`, or `avoid`; a headline; a maximum amount; and reasons. This object is not part of the recipe save body.

**FR-31.** Every saved recipe, whether generated or typed, stores `condition_guidance` for tracked conditions when a serving crosses a generic cap or contains a flagged ingredient. Hypertension and kidney use sodium. Diabetes uses carbohydrate and sweet ingredients. Pregnancy uses a list of items to leave out, including alcohol and raw fish. Anemia flags tea or coffee. Thyroid flags soy.

**FR-32.** The user can list, open, edit, and delete saved recipes. Edit and manual create recalculate nutrition and condition guidance on save.

**FR-33.** Manual recipes accept ingredients (name, quantity, unit, grams, notes), preparation lines, cooking-method steps, and a serving count from 1 to 100.

### 3.6 Operations

**FR-34.** `GET /api/health` reports whether the Gemini key and the USDA key are present. It does not reveal the keys.

**FR-35.** `scripts\start.cmd` starts the backend and frontend in hidden windows, frees ports 8000 and 5173 first, waits until both answer, and prints the URLs. `scripts\stop.cmd` stops those processes.

**FR-36.** Keys and host settings are read from the project-root `.env`. `.env` is gitignored.

## 4. External interface requirements

### 4.1 User interface

- Pages: `/`, `/people`, `/log`, `/trends`, `/recipes/generate`, `/recipes`.
- Navigation is visible on every page.
- Errors from the API are shown as text. Loading states disable the button that started the action.
- Diet-plan lists use three visual states: regular, limited, and leave-out.
- Person fit and condition guidance are visible on the recipe view. Person fit includes the sentence that it is not stored.
- Layout remains usable below 800 px width. Ingredient editing and the diet chart stack on narrow screens.

### 4.2 Software interfaces

REST JSON over HTTP on `127.0.0.1:8000`. CORS allows the Vite origins `http://127.0.0.1:5173` and `http://localhost:5173`.

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | Process and key presence |
| GET | `/api/foods/search` | Search and scale |
| GET | `/api/foods/{food_id}` | One scaled food |
| POST | `/api/foods/ai-estimate` | Estimate and cache |
| GET, POST | `/api/people` | List, create |
| PUT, DELETE | `/api/people/{id}` | Update, delete |
| POST | `/api/people/{id}/diet-plan` | Build and store the plan |
| POST | `/api/days/preview` | Analyse without saving |
| POST | `/api/days` | Save and analyse |
| GET | `/api/days` | Load one saved day |
| GET | `/api/analysis/day` | Analyse a saved day |
| GET | `/api/analysis/trends` | Trend summary |
| POST | `/api/explain` | Prose for a computed analysis |
| POST | `/api/recipes/suggest` | Dish ideas |
| POST | `/api/recipes/generate` | Recipe, nutrition, optional person fit |
| GET, POST | `/api/recipes` | List, create |
| GET, PUT, DELETE | `/api/recipes/{id}` | Read, update, delete |

USDA is called only from the backend. Gemini is called only from the backend. The browser never sees API keys.

### 4.3 Data files

See section 5. Files are UTF-8 JSON. Writes replace the file. Readers tolerate a missing file by using an empty collection.

## 5. Logical data requirements

### 5.1 Person

`id`, `name`, `sex`, `age`, `height_cm`, `weight_kg`, `activity`, `conditions[]`, `nationality`, `ethnicity`, optional `diet_plan`.

`diet_plan` contains `profile_key`, `basis`, `meals[]`, `include[]`, `moderate[]`, `avoid[]`, `diet_chart`, `disclaimer`. Each advice row has `item`, `amount`, `reason`. Each chart slot has `meal`, `time`, `options[]`.

### 5.2 Day log

`person_id`, `date`, `foods[]` (scaled snapshots), `exercises[]`, `notes`, `totals`, `exercise_kcal`.

### 5.3 Recipe

`id`, `name`, `description`, `servings`, `ingredients[]`, `preparation[]`, `cooking_methods[]`, `source`, `nutrition`, `condition_guidance[]`, `created_at`, `updated_at`.

`nutrition` contains `total_recipe`, `per_serving`, `servings`, `ingredient_matches[]`, `unmatched_ingredients[]`, `note`.

A generate response may also contain `person_fit`. That field is absent after save.

## 6. Non-functional requirements

**NFR-1 Performance.** People and recent day logs are cached in memory. USDA and AI estimates are cached on disk. Ingredient resolution for one recipe runs in a pool of at most four workers.

**NFR-2 Reliability.** A failed USDA call is retried and is not stored as an empty result. A Gemini 503 or network error is retried a small number of times. HTTP 429 is not retried as if it were a brief overload; the user is told the quota is spent.

**NFR-3 Privacy.** Profiles, logs, and recipes remain in the project tree. Keys remain in `.env`. Logs of upstream errors must not be required to contain the key.

**NFR-4 Integrity.** Nutrient estimates with negative values, a non-positive serving weight, or per-100 g values above the coded ceilings are rejected. Recipe servings are limited to 1–100. Age and body measurements are bounded by the API models.

**NFR-5 Portability of data.** A user can back up the project by copying `backend/data`. No database server is required.

**NFR-6 Operability.** Start and stop scripts are in `scripts\`. Process output goes to `logs\`. Running start twice replaces the previous servers.

**NFR-7 Honesty of provenance.** Every scaled food carries a source. AI estimates carry confidence, assumptions, and a serving description. Recipe nutrition says it is calculated from weights and that cooking losses are estimates.

## 7. Target rules

These are requirements on the calculation, not clinical orders.

| Input | Effect |
|---|---|
| Activity | Multiplies BMR by 1.2, 1.375, 1.55, 1.725, or 1.9 |
| Male / female / other | Iron and protein baselines differ. `other` uses the midpoint of the male and female BMR |
| Age 60 or older | Calcium 1200 mg, vitamin D 20 µg, protein at least 1.0 g/kg |
| Hypertension | Sodium target 1500 mg |
| Diabetes | Fiber 35 g, carbohydrate about 45% of energy |
| Kidney | Protein 0.8 g/kg, potassium 2500 mg, sodium at most 1500 mg |
| Pregnancy | Energy TDEE + 300 kcal, iron 40 mg, folate 600 µg, calcium 1200 mg |
| Anemia | Iron at least 35 mg, vitamin C 100 mg |
| Thyroid | Zinc at least 15 mg |

Exercise kilocalories use a MET table (walk, run, cycle, gym, yoga, sports, housework, other) × weight × hours.

## 8. Acceptance criteria

1. Searching `roti` with a piece quantity returns the starter roti and a positive energy value.
2. Creating a person and posting `/diet-plan` persists a plan that survives a process restart.
3. A Tamil / India profile names South Indian home cooking. A blank nationality uses the general pattern. A Jain ethnicity omits meat, fish, and eggs as custom.
4. Previewing a day with a known food returns BMR, TDEE, balance, and nutrient rows.
5. Saving that day and opening trends shows a day count of at least one.
6. Posting a manual recipe that contains several grams of salt stores hypertension guidance with verdict avoid or moderate, and the saved document has no `person_fit`.
7. Generating a recipe with a person id returns `person_fit` in that response. Saving through the recipe input body does not send that object.
8. With `GEMINI_API_KEY` empty, health reports `gemini: false`, and food search of a catalog item still returns 200.
9. Start script reports the UI and API URLs. Stop script releases ports 8000 and 5173.

## 9. Traceability

| Goal in the proposal | Requirements |
|---|---|
| Food lookup | FR-1–FR-6 |
| People and conditions | FR-7–FR-15, section 7 |
| Daily log | FR-16–FR-22 |
| Trends | FR-23–FR-25 |
| Recipes and person check | FR-26–FR-33 |
| Local, free, restart-safe | FR-34–FR-36, NFR-2–NFR-6 |
