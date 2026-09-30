# HealthPro — User Manual

| | |
|---|---|
| Version | 0.1.0 |
| Date | 30 September 2026 |

## 1. Install once

From `C:\Work\Personal\HealthPro`:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
cd frontend
npm install
```

Copy `.env.example` to `.env` if `.env` is missing.

- `GEMINI_API_KEY` — Google AI Studio, free tier. Needed for explanations, dish suggestions, recipe text, and the "Estimate with AI" button.
- `USDA_API_KEY` — FoodData Central signup. Needed only for foods that are not in the local catalog.
- `GEMINI_MODEL` — default `gemini-2.5-flash`.

Key steps and the IFCT import shape are also in `Instructions.md` at the project root.

## 2. Start and stop

Double-click `scripts\start.cmd`. When it finishes, open [http://127.0.0.1:5173](http://127.0.0.1:5173).

Double-click `scripts\stop.cmd` to shut both servers down.

From PowerShell, `.\scripts\start.ps1` and `.\scripts\stop.ps1` do the same thing. If a `.cmd` script fails it waits for a key; the `.ps1` scripts are easier to read when you are already in a terminal.

If a server does not come up, the start script prints the last lines of `logs\backend.err.log` or `logs\frontend.err.log`.

## 3. Food lookup

1. Type a name, such as `roti`.
2. Set a quantity and a unit (`piece`, `g`, `katori`, `cup`, `tbsp`, `tsp`).
3. Search.

An exact catalog name is labelled as a match. Other rows are suggestions and are not the same food. If nothing matches exactly, **Estimate with AI** asks Gemini once and saves the result. The card says whether the numbers were just estimated or loaded from the cache. Estimates are not laboratory measurements.

## 4. People

1. Enter name, sex, age, height, and weight. These drive BMR.
2. Choose activity and any conditions. Conditions change targets. They do not diagnose.
3. Enter nationality and ethnicity if you want a cuisine-specific diet plan. Example: nationality `India`, ethnicity `Tamil`.
4. Save. The person appears in the list.
5. Click **Diet plan**.

The plan has two parts, both saved on that person:

- **Instructions** — what to eat, what to limit, and what to leave out, with amounts.
- **Daily diet chart** — times from morning to dinner and two or three choices at each meal.

Click **Diet plan** again after you change nationality, ethnicity, conditions, or body details. Those edits clear the previous plan. Other edits keep it.

## 5. Daily log

1. Choose the person and the date.
2. Search foods, set quantity and unit, and add them.
3. Add exercise as an activity and minutes.
4. Preview the analysis. Read calorie balance and the nutrient table.
5. Save. The same person and date replaces the earlier file.

A very low sodium total usually means salt was not logged, not that the person needs a sodium supplement. The note on the page says this.

**Explain** asks Gemini to describe the analysis that is already on screen. It does not recalculate the numbers.

## 6. Trends

Choose a person. The page lists saved days, the average calorie balance, nutrients that were repeatedly low or high, and a rough weight-direction sentence. It needs saved days. An empty log is not a health finding.

## 7. Recipe generator

1. Optionally choose a person. Leave the box empty if you only want a recipe.
2. Either list ingredients and ask for dish ideas, or type a dish name and ask for the recipe.
3. Read ingredients, preparation, the four cooking modes, and nutrition per serving.
4. If a person was selected, read the block that says whether a normal serving fits, should be limited, or should be skipped, and how much of the dish fits the day. That block is not saved.
5. Read **People with these conditions** for the reusable warning. That part is saved with the recipe.
6. Click **Save recipe** if you want it in the library.

Generation calls Gemini and is not cached. If the key is over the free daily quota, the page returns in a few seconds with that reason. Wait for the daily reset or set `GEMINI_MODEL` to another free model and restart the backend.

## 8. Saved recipes

Open a recipe from the list. **Edit** changes ingredients, steps, and servings. **Calculate nutrition and save** reprices the recipe. **Add my recipe** does the same for a recipe you type yourself. **Delete** removes it.

Typed recipes do not need Gemini. Nutrition and condition notes are calculated locally. Some ingredient names may still use USDA or a cached estimate.

## 9. Where your data is

| Path | What it is |
|---|---|
| `backend/data/people.json` | People and diet plans |
| `backend/data/logs/` | One file per person per day |
| `backend/data/saved_recipes.json` | Recipes |
| `backend/data/usda_cache.json` | USDA responses |
| `backend/data/ai_food_cache.json` | AI food estimates |
| `backend/data/ifct_import.json` | Optional. You create this |

Copy `backend/data` to back up. Do not publish `.env`.

To force a new AI estimate, delete that dish's entry from `ai_food_cache.json` and restart, or restart after the edit so the cache reloads.

## 10. What this is not

HealthPro does not diagnose, prescribe, or replace a clinician. Pregnancy, kidney disease, and thyroid treatment in particular need the person's own clinician. The diet chart is a customary pattern with personal targets applied on top, not a medical diet order.
