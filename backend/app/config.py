from pathlib import Path
import os

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

BACKEND_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BACKEND_DIR / "data"
PEOPLE_FILE = DATA_DIR / "people.json"
LOGS_DIR = DATA_DIR / "logs"
USDA_CACHE_FILE = DATA_DIR / "usda_cache.json"
AI_FOOD_CACHE_FILE = DATA_DIR / "ai_food_cache.json"
IFCT_IMPORT_FILE = DATA_DIR / "ifct_import.json"
SAVED_RECIPES_FILE = DATA_DIR / "saved_recipes.json"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()
USDA_API_KEY = os.getenv("USDA_API_KEY", "").strip()
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8000"))
