# HealthPro — High-Level Design

| | |
|---|---|
| Version | 0.1.0 |
| Date | 30 September 2026 |

## 1. Design goals

- Keep personal data on disk in the project.
- Compute nutrient numbers from tables and arithmetic.
- Use Gemini only where the task is language: wording, dish ideas, recipe steps, or a last-resort food estimate.
- Make a missing API key degrade a feature rather than the whole application.
- Let a restart rebuild the working set from files.

## 2. Context

```text
Browser (React, port 5173)
        |  HTTP /api
        v
FastAPI (port 8000)
        |-- JSON files in backend/data
        |-- USDA FoodData Central   (optional)
        |-- Gemini generateContent  (optional)
```

The browser does not hold keys and does not call USDA or Gemini. CORS allows only the local Vite origins.

## 3. Containers

| Container | Responsibility |
|---|---|
| `frontend/` | Pages, forms, recipe display, fetch wrapper |
| `backend/app` | HTTP, food resolution, nutrition math, recipes, diet plans, file cache |
| `backend/data` | System of record |
| `scripts/` | Start, stop, port cleanup |
| `.env` | Keys, host, port, Gemini model name |

There is one backend process and one Vite process. No queue, no database server, no separate cache server.

## 4. Backend modules

| Module | Role |
|---|---|
| `main.py` | Routes, day analysis assembly, HTTP errors |
| `models.py` | Request and stored shapes |
| `store.py` | People, days, USDA cache, AI-food cache, recipes. In-memory, write-through |
| `catalog.py` | Starter foods, including common Indian dishes and raw staples |
| `foods.py` | Local search, unit conversion, USDA search and nutrient parsing |
| `nutrition.py` | BMR, TDEE, targets, day comparison, trend note |
| `diet_guidance.py` | Diet plan, daily chart, recipe condition guidance, person fit |
| `recipe_service.py` | Gemini recipe text, ingredient resolution, nutrition totals |
| `ai_foods.py` | One-shot nutrient estimate and cache record |
| `gemini.py` | Shared JSON call, retry, quota message |
| `explain.py` | Prose over an already computed analysis |
| `config.py` | Paths and environment |

## 5. Main flows

### 5.1 Food search

```text
query
  -> exact local name (catalog + IFCT + cached estimates)
  -> ranked local suggestions
  -> if no exact local identity: USDA search (disk cache, then network)
  -> scale each hit to the requested quantity and unit
```

AI estimate is a separate user action. It writes a food into the AI cache, after which search treats it as local.

### 5.2 Day analysis

```text
person + food rows + exercises
  -> resolve each food id or query
  -> scale and sum nutrients
  -> MET × weight × hours for exercise
  -> targets(person), BMR, TDEE
  -> balance = intake - (TDEE + exercise)
  -> status per nutrient
  -> condition notes
```

Preview and save share this path. Save writes `backend/data/logs/<person-id>/<date>.json`.

### 5.3 Recipe

```text
Gemini (recipe JSON, not cached)
  -> schema check, fill any missing cooking mode
  -> resolve ingredients in parallel
  -> sum nutrients, divide by servings
  -> condition_guidance from the serving
  -> if a person was selected: person_fit for the response only
```

Save accepts the recipe fields only. The backend recalculates nutrition and condition guidance. `person_fit` is not a field on the save model, so it cannot be persisted by the normal save path.

### 5.4 Diet plan

```text
person
  -> match cuisine by the longest keyword in nationality + ethnicity
  -> Jain wins over a regional Indian pattern when the text says jain
  -> copy chart slots for that cuisine, else the general chart
  -> append salt, oil, and condition lines from person_targets
  -> store the plan on the person
```

No network call.

## 6. Persistence

`Store` holds a lock, a dict of people, an LRU of day documents, and dicts for USDA cache, AI foods, and recipes. Mutations write the corresponding JSON file before returning. Day files are one document each so the log set can grow without rewriting every day. People and recipes are small enough to live in one file each.

Empty or failed upstream searches are not written as "this food does not exist". A later retry can succeed.

## 7. Deployment view

Local only.

| Port | Process |
|---|---|
| 8000 | `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000` |
| 5173 | Vite on `127.0.0.1` |

`scripts/start.ps1` stops anything already bound to those ports, starts both processes hidden, records PIDs, and waits for `/api/health` and the Vite root. Logs go to `logs/backend.*.log` and `logs/frontend.*.log`.

## 8. Major decisions

| Decision | Why |
|---|---|
| JSON files instead of a database | Personal scale, easy backup, no server to install |
| Write-through cache | Restarts stay correct without a cache warmer beyond loading the files |
| Tables before the model | A calorie figure needs a source the user can see |
| Diet plan in code | It must be stable, free of quota, and tied to the same targets as the log |
| Person fit not stored on recipes | The same recipe is reused across people. Condition guidance is the reusable part |
| USDA `dataType` in a POST body | Repeating that parameter in the query string produced random HTTP 400 responses |
| Score USDA hits | The search answered "black pepper" with unrelated foods and "cooking oil" with dishes cooked in oil |
| Atwater fallback for energy | Some Foundation records have fat but no kilocalorie field, which made oil look like 0 kcal |

## 9. Trust boundaries

- The browser is trusted as the only UI. There is no authentication because the server is bound to localhost.
- USDA and Gemini see the food or dish text that the feature sends. They do not receive the day log or the person profile, except that recipe generation receives the dish name and ingredient list. Person fit is computed locally after the recipe returns.
- `.env` is the only secret store. It is not a document and must not be copied into `docs/`.

## 10. Failure behaviour

| Failure | User-visible result |
|---|---|
| USDA down | Local hits still return. New USDA foods are skipped for that call |
| Gemini quota or outage | Lookup, log, trends, manual recipe, and diet plan still work. Generate, suggest, estimate, and explain return 503 with a reason |
| Ingredient has no table | Recipe still renders. The name is listed as missing from the totals |
| No saved days | Trends returns an empty summary |
| Unknown person id | 404 |

## 11. Extension points

- Drop IFCT rows into `backend/data/ifct_import.json` using the shape in `Instructions.md`. They are searched before USDA.
- Change `GEMINI_MODEL` when a free-tier model has quota left.
- Add a cuisine by extending the tables in `diet_guidance.py`. The rest of the plan (salt, oil, conditions, chart shell) stays the same.
