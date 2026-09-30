"""JSON file persistence with a write-through in-memory cache.

People live in one file. Each day log is its own file so the set can grow
without rewriting a giant document. The cache avoids repeated disk reads.
"""

from __future__ import annotations

import json
import threading
from collections import OrderedDict
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

from .config import (
    AI_FOOD_CACHE_FILE,
    DATA_DIR,
    LOGS_DIR,
    PEOPLE_FILE,
    SAVED_RECIPES_FILE,
    USDA_CACHE_FILE,
)
from .diet_guidance import profile_key
from .models import Person, PersonIn


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    tmp.replace(path)


class Store:
    def __init__(self, day_cache_size: int = 400) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._people: dict[str, dict] = {}
        self._days: OrderedDict[str, dict] = OrderedDict()
        self._day_cache_size = day_cache_size
        self._usda_cache: dict[str, Any] = {}
        self._ai_food_cache: dict[str, Any] = {}
        self._recipes: dict[str, dict] = {}
        self._load_people()
        self._load_usda_cache()
        self._load_ai_food_cache()
        self._load_recipes()
        self._preload_recent_days()

    def _day_key(self, person_id: str, date: str) -> str:
        return f"{person_id}:{date}"

    def _day_path(self, person_id: str, date: str) -> Path:
        return LOGS_DIR / person_id / f"{date}.json"

    def _load_people(self) -> None:
        rows = _read_json(PEOPLE_FILE, [])
        self._people = {p["id"]: p for p in rows}

    def _persist_people(self) -> None:
        _write_json(PEOPLE_FILE, list(self._people.values()))

    def _load_usda_cache(self) -> None:
        self._usda_cache = _read_json(USDA_CACHE_FILE, {})

    def persist_usda_cache(self) -> None:
        with self._lock:
            _write_json(USDA_CACHE_FILE, self._usda_cache)

    def usda_get(self, key: str) -> Optional[Any]:
        with self._lock:
            return self._usda_cache.get(key)

    def usda_set(self, key: str, value: Any) -> None:
        with self._lock:
            self._usda_cache[key] = value
        self.persist_usda_cache()

    def _load_ai_food_cache(self) -> None:
        self._ai_food_cache = _read_json(AI_FOOD_CACHE_FILE, {})

    def ai_food_values(self) -> list[dict]:
        with self._lock:
            return list(self._ai_food_cache.values())

    def ai_food_get(self, normalized_name: str) -> Optional[dict]:
        with self._lock:
            return self._ai_food_cache.get(normalized_name)

    def ai_food_set(self, normalized_name: str, value: dict) -> None:
        with self._lock:
            self._ai_food_cache[normalized_name] = value
            _write_json(AI_FOOD_CACHE_FILE, self._ai_food_cache)

    def _load_recipes(self) -> None:
        rows = _read_json(SAVED_RECIPES_FILE, [])
        self._recipes = {row["id"]: row for row in rows if row.get("id")}

    def _persist_recipes(self) -> None:
        _write_json(SAVED_RECIPES_FILE, list(self._recipes.values()))

    def list_recipes(self) -> list[dict]:
        with self._lock:
            return sorted(
                self._recipes.values(),
                key=lambda row: row.get("updated_at", ""),
                reverse=True,
            )

    def get_recipe(self, recipe_id: str) -> Optional[dict]:
        with self._lock:
            return self._recipes.get(recipe_id)

    def save_recipe(self, payload: dict) -> dict:
        with self._lock:
            self._recipes[payload["id"]] = payload
            self._persist_recipes()
        return payload

    def delete_recipe(self, recipe_id: str) -> bool:
        with self._lock:
            if recipe_id not in self._recipes:
                return False
            del self._recipes[recipe_id]
            self._persist_recipes()
            return True

    def _touch_day(self, key: str, payload: dict) -> None:
        if key in self._days:
            self._days.move_to_end(key)
        self._days[key] = payload
        while len(self._days) > self._day_cache_size:
            self._days.popitem(last=False)

    def _preload_recent_days(self) -> None:
        files = sorted(LOGS_DIR.glob("*/*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        for path in files[: self._day_cache_size]:
            try:
                payload = _read_json(path, None)
            except json.JSONDecodeError:
                continue
            if not payload:
                continue
            key = self._day_key(payload["person_id"], payload["date"])
            self._days[key] = payload

    def list_people(self) -> list[dict]:
        with self._lock:
            return sorted(self._people.values(), key=lambda p: p["name"].lower())

    def get_person(self, person_id: str) -> Optional[dict]:
        with self._lock:
            return self._people.get(person_id)

    def create_person(self, data: PersonIn) -> dict:
        person = Person(id=str(uuid4()), **data.model_dump()).model_dump()
        with self._lock:
            self._people[person["id"]] = person
            self._persist_people()
        return person

    def update_person(self, person_id: str, data: PersonIn) -> Optional[dict]:
        with self._lock:
            old = self._people.get(person_id)
            if not old:
                return None
            person = Person(id=person_id, **data.model_dump()).model_dump()
            # Keep a saved diet plan only while the fields it was built from are unchanged.
            previous = old.get("diet_plan")
            if previous and previous.get("profile_key") == profile_key(Person(**person)):
                person["diet_plan"] = previous
            self._people[person_id] = person
            self._persist_people()
            return person

    def save_diet_plan(self, person_id: str, plan: dict) -> Optional[dict]:
        with self._lock:
            person = self._people.get(person_id)
            if not person:
                return None
            person["diet_plan"] = plan
            self._persist_people()
            return person

    def delete_person(self, person_id: str) -> bool:
        with self._lock:
            if person_id not in self._people:
                return False
            del self._people[person_id]
            self._persist_people()
            return True

    def get_day(self, person_id: str, date: str) -> Optional[dict]:
        key = self._day_key(person_id, date)
        with self._lock:
            if key in self._days:
                self._days.move_to_end(key)
                return self._days[key]
        path = self._day_path(person_id, date)
        payload = _read_json(path, None)
        if payload is None:
            return None
        with self._lock:
            self._touch_day(key, payload)
        return payload

    def save_day(self, payload: dict) -> dict:
        key = self._day_key(payload["person_id"], payload["date"])
        path = self._day_path(payload["person_id"], payload["date"])
        _write_json(path, payload)
        with self._lock:
            self._touch_day(key, payload)
        return payload

    def list_days(self, person_id: str) -> list[dict]:
        folder = LOGS_DIR / person_id
        if not folder.exists():
            return []
        out: list[dict] = []
        for path in sorted(folder.glob("*.json")):
            date = path.stem
            day = self.get_day(person_id, date)
            if day:
                out.append(day)
        return out


store = Store()
