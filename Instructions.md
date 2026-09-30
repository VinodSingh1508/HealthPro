# HealthPro

Project documents and the presentation are in [`docs/`](docs/README.md).

Personal nutrition tracker: React frontend, Python FastAPI backend. Completely free for personal use. Nutrient **numbers** come from a local food catalog (and optional USDA). Gemini is used only to **explain** computed results.

## Start the application

All start/stop scripts live in `scripts\`.

Double-click **`scripts\start.cmd`**. It starts backend and frontend in hidden windows, waits until both answer, and prints the URLs. Then open [http://127.0.0.1:5173](http://127.0.0.1:5173).

Double-click **`scripts\stop.cmd`** to shut both down.

From a terminal the equivalents are `.\scripts\start.ps1` and `.\scripts\stop.ps1`. Shared helpers live in `scripts\common.ps1`; process output goes to `logs\`.

`start.cmd` frees ports 8000 and 5173 before launching, so it is safe to run twice. If a server fails to come up, the window stays open and shows the tail of the matching log.

First-time setup (once):

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
cd frontend
npm install
```

Copy `.env.example` to `.env` if `.env` is missing. API keys are read from the project-root `.env`.

## Where data is stored

All personal data stays **inside this project** (JSON files):

| Path | Contents |
|---|---|
| `backend/data/people.json` | People (name, age, sex, height, weight, conditions) |
| `backend/data/logs/<person-id>/<YYYY-MM-DD>.json` | One saved day per file |
| `backend/data/usda_cache.json` | Cached USDA lookups |
| `backend/data/ai_food_cache.json` | Gemini nutrient estimates, one entry per dish |
| `backend/data/saved_recipes.json` | Recipes explicitly saved by the user |
| `backend/data/ifct_import.json` | Optional official IFCT foods you add |

The backend keeps an **in-memory cache**: all people, an LRU of day logs, USDA responses, and AI estimates. Writes go to disk immediately (write-through) so a restart does not lose data.

Lookup order is local catalog / IFCT / previous AI estimate → cached USDA response → live USDA. Gemini is called only when you press **Estimate with AI** on a dish with no exact match, and the result is cached to `ai_food_cache.json`, so each dish costs at most one call ever. Those foods carry `source: ai_estimate` and are labelled in the UI; delete an entry from that file to force a fresh estimate.

Recipe suggestions and generated recipes are intentionally **not cached**. The exact ingredient list and order are sent to Gemini each time. A recipe is persisted only when you press **Save recipe**, or when you add your own recipe on the Saved Recipes page. Nutrition is calculated from ingredient gram weights and recalculated on every save.

Generating a recipe costs **one** Gemini call. The ingredients it returns are priced from the local catalog and USDA, which need no key and are looked up in parallel. A name like "Boneless chicken breast" or "Roasted cumin powder" is progressively simplified ("chicken breast", "cumin") until a food table matches it, and candidate matches are scored so USDA's fuzzy search cannot answer "black pepper" with "Black Russian". Only an ingredient that survives all of that reaches Gemini.

If an ingredient still cannot be priced, the recipe is shown anyway. The missing names are listed above the nutrition table and excluded from the totals, rather than throwing away a recipe you waited for.

## Gemini API key (free)

To create or rotate a key:

1. Open [Google AI Studio](https://aistudio.google.com/).
2. Sign in with a Google account.
3. Open **Get API key** / [API keys](https://aistudio.google.com/app/apikey).
4. Create a key in a Google Cloud project. Stay on the **free tier** (no billing required). The caps below are per project, not per key.
5. Put it in `.env` as `GEMINI_API_KEY=...`
6. Optional: `GEMINI_MODEL=gemini-2.5-flash` or `gemini-2.5-flash-lite`.

HealthPro never asks Gemini for calorie counts. If the key is missing, lookup/log/trends still work; only the prose explanation is skipped.

### Free-tier quota for the two models

Each limit is enforced on its own. Crossing requests per minute, input tokens per minute, or requests per day returns HTTP 429. The daily count resets at midnight Pacific.

| Model | Requests per minute | Input tokens per minute | Requests per day |
|---|---:|---:|---:|
| `gemini-2.5-flash` | 5 | 250,000 | 20 |
| `gemini-2.5-flash-lite` | 15 | 250,000 | 1,000 |

The Flash daily cap of **20** is the figure this project's key received from Google (`generate_content_free_tier_requests`, limit 20). It did not clear after a minute, so that 20 is the day, not the minute. The 5 requests per minute and 250,000 input tokens per minute are the other two Flash dimensions published with that cut.

Flash-Lite keeps the larger published free allowance: **15** requests per minute, **250,000** input tokens per minute, and **1,000** requests per day.

One recipe generation, one dish suggestion, one new food estimate, and one written explanation each cost one request. A cached food estimate does not. Diet plans, logs, and manual recipes do not call Gemini at all.

Google's [rate limits](https://ai.google.dev/gemini-api/docs/rate-limits) page says the live numbers for a project are shown in [AI Studio](https://ai.google.dev/gemini-api/docs/rate-limits). If those differ from this table, the AI Studio figures are the ones that apply.

### When Gemini says "over quota"

Recipe generation and AI estimates fail immediately and say the quota is spent. Lookup, logs, trends, manual recipes, and diet plans keep working. Wait for midnight Pacific, or switch the model and restart the backend:

```
GEMINI_MODEL=gemini-2.5-flash-lite
```

Transient `503 overloaded` responses are retried automatically. A 429 is not retried, because the cap will not clear by waiting a few seconds.

## USDA FoodData Central / data.gov API key (free)

Needed only when a food is **not** in the starter catalog (or your IFCT import).

1. Open the USDA signup page: [https://fdc.nal.usda.gov/api-key-signup/](https://fdc.nal.usda.gov/api-key-signup/)  
   or the generic data.gov form: [https://api.data.gov/signup/](https://api.data.gov/signup/).
2. Enter name and email. No payment.
3. Confirm the email and copy the key.
4. Put it in `.env` as `USDA_API_KEY=...`
5. Restart the backend.

Rate limits: a personal key is typically about **1,000 requests/hour**. Do not use `DEMO_KEY` for regular use (it is throttled). Keep the key out of git (`.env` is gitignored). USDA data is public domain (CC0).

## Official IFCT 2017 file

The **Indian Food Composition Tables 2017** are published by ICMR–National Institute of Nutrition (Hyderabad). They are **not** a public REST API.

**Official PDF (free to read):**  
[https://www.nin.res.in/ebooks/IFCT2017.pdf](https://www.nin.res.in/ebooks/IFCT2017.pdf)

**How to obtain machine-readable data for personal use:**

1. Download the official PDF from NIN (link above).
2. NIN also ships **Nutrify India Now** (Android) which uses the same tables: search the Play Store for “Nutrify India Now”.
3. For a file you can import, you generally need to **request or purchase the dataset from NIN/ICMR** (email via [https://www.nin.res.in](https://www.nin.res.in)) or transcribe foods you care about. Do not assume a random GitHub CSV is licensed for redistribution.
4. Convert rows to JSON with this shape and save as `backend/data/ifct_import.json` (array). Restart the backend; those foods are searched **before** USDA:

```json
[
  {
    "id": "ifct-a001",
    "name": "Rice, raw, milled",
    "names": ["chawal"],
    "form": "raw",
    "default_grams": 100,
    "health_notes": "IFCT 2017",
    "nutrients_per_100g": {
      "energy_kcal": 356,
      "protein_g": 6.8,
      "carb_g": 78,
      "fat_g": 0.5,
      "fiber_g": 2.8,
      "sodium_mg": 2,
      "potassium_mg": 100,
      "calcium_mg": 10,
      "iron_mg": 0.7,
      "magnesium_mg": 20,
      "zinc_mg": 1.2,
      "vitamin_a_ug": 0,
      "vitamin_c_mg": 0,
      "folate_ug": 10,
      "vitamin_b12_ug": 0,
      "vitamin_d_ug": 0
    }
  }
]
```

Until that file exists, HealthPro uses a **starter catalog** of common Indian foods with representative (USDA-style) per-100 g values — not a copy of the NIN book.

## What the four pages do

1. **Food lookup** — name + optional quantity → calories, micros, short food notes.
2. **People** — name, **age**, **sex**, height, weight, activity, conditions, nationality, and ethnicity. Saved to `people.json`. **Diet plan** builds a customary eating pattern from nationality and ethnicity, then lists what to eat, what to limit, and what to leave out, with amounts taken from that person's targets. It also includes a daily diet chart with six suggested times and 2–3 alternatives per meal. The plan and chart are saved on the person.
3. **Daily log** — foods + quantities + exercise; analysis vs BMR/TDEE and personal RDAs; save asks you to select a person.
4. **Trends** — saved days per person: calorie surplus/deficit, repeated nutrient gaps, weight-management estimate, condition-aware targets.
5. **Recipe generator** — suggest dishes from an ordered ingredient list, or generate directly from a dish name. Optionally pick a person: the page then says whether a serving is a reasonable choice, something to limit, or something to skip, and how much of it fits their targets. That person-specific line is not saved. What is saved is a separate note for anyone with a tracked condition (hypertension, diabetes, kidney disease, pregnancy, anemia, thyroid).
6. **Saved recipes** — read generated recipes or add/edit your own; saving recalculates nutrition and the condition notes.

This is educational, not medical advice.
