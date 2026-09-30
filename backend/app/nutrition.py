from __future__ import annotations

from .models import Nutrients, Person

ACTIVITY_FACTOR = {
    "sedentary": 1.2,
    "light": 1.375,
    "moderate": 1.55,
    "active": 1.725,
    "very_active": 1.9,
}

METS = {
    "walk": 3.5,
    "run": 8.0,
    "cycle": 6.8,
    "gym": 5.0,
    "yoga": 2.5,
    "sports": 7.0,
    "housework": 3.3,
    "other": 4.0,
}

# Approximate adult ICMR/NIN-style daily targets (personal-use estimates).
BASE_RDA = {
    "energy_kcal": None,  # filled from TDEE
    "protein_g": 54,
    "carb_g": 260,
    "fat_g": 60,
    "fiber_g": 30,
    "sodium_mg": 2000,
    "potassium_mg": 3500,
    "calcium_mg": 1000,
    "iron_mg": 19,
    "magnesium_mg": 340,
    "zinc_mg": 13,
    "vitamin_a_ug": 840,
    "vitamin_c_mg": 80,
    "folate_ug": 300,
    "vitamin_b12_ug": 2.2,
    "vitamin_d_ug": 15,
}

NUTRIENT_LABELS = {
    "energy_kcal": "Calories",
    "protein_g": "Protein",
    "carb_g": "Carbohydrate",
    "fat_g": "Fat",
    "fiber_g": "Fiber",
    "sodium_mg": "Sodium",
    "potassium_mg": "Potassium",
    "calcium_mg": "Calcium",
    "iron_mg": "Iron",
    "magnesium_mg": "Magnesium",
    "zinc_mg": "Zinc",
    "vitamin_a_ug": "Vitamin A",
    "vitamin_c_mg": "Vitamin C",
    "folate_ug": "Folate",
    "vitamin_b12_ug": "Vitamin B12",
    "vitamin_d_ug": "Vitamin D",
}


def bmr_kcal(person: Person) -> float:
    w, h, age = person.weight_kg, person.height_cm, person.age
    male = 10 * w + 6.25 * h - 5 * age + 5
    female = 10 * w + 6.25 * h - 5 * age - 161
    sex = person.sex.lower()
    if sex == "male":
        value = male
    elif sex == "female":
        value = female
    else:
        value = (male + female) / 2
    return round(value, 1)


def tdee_kcal(person: Person) -> float:
    factor = ACTIVITY_FACTOR.get(person.activity.lower(), 1.2)
    return round(bmr_kcal(person) * factor, 1)


def exercise_kcal(activity: str, minutes: float, weight_kg: float) -> float:
    met = METS.get(activity.lower(), METS["other"])
    hours = minutes / 60.0
    return round(met * weight_kg * hours, 1)


def person_targets(person: Person) -> dict[str, float]:
    targets = dict(BASE_RDA)
    tdee = tdee_kcal(person)
    targets["energy_kcal"] = tdee
    sex = person.sex.lower()
    if sex == "male":
        targets["iron_mg"] = 19
        targets["protein_g"] = max(54, round(0.83 * person.weight_kg, 1))
    elif sex == "female":
        targets["iron_mg"] = 29
        targets["protein_g"] = max(46, round(0.83 * person.weight_kg, 1))
        targets["calcium_mg"] = 1000
    else:
        targets["iron_mg"] = 24
        targets["protein_g"] = max(50, round(0.83 * person.weight_kg, 1))

    if person.age >= 60:
        targets["calcium_mg"] = 1200
        targets["vitamin_d_ug"] = 20
        targets["protein_g"] = max(targets["protein_g"], round(1.0 * person.weight_kg, 1))

    cond = {c.lower() for c in person.conditions}
    if "hypertension" in cond or "high blood pressure" in cond:
        targets["sodium_mg"] = 1500
    if "diabetes" in cond:
        targets["fiber_g"] = 35
        targets["carb_g"] = round(tdee * 0.45 / 4, 0)
    if "kidney" in cond or "ckd" in cond:
        targets["protein_g"] = round(0.8 * person.weight_kg, 1)
        targets["potassium_mg"] = 2500
        targets["sodium_mg"] = min(targets["sodium_mg"], 1500)
    if "pregnancy" in cond:
        targets["energy_kcal"] = tdee + 300
        targets["iron_mg"] = 40
        targets["folate_ug"] = 600
        targets["calcium_mg"] = 1200
    if "anemia" in cond:
        targets["iron_mg"] = max(targets["iron_mg"], 35)
        targets["vitamin_c_mg"] = 100
    if "thyroid" in cond:
        targets["zinc_mg"] = max(targets["zinc_mg"], 15)
    return {k: float(v) for k, v in targets.items() if v is not None}


def compare_totals(totals: Nutrients, targets: dict[str, float]) -> list[dict]:
    rows = []
    data = totals.model_dump()
    for key, target in targets.items():
        actual = data.get(key, 0) or 0
        pct = round(100 * actual / target, 1) if target else 0
        if key == "sodium_mg":
            status = "excess" if actual > target else ("ok" if actual >= 0.4 * target else "low_log")
        elif key == "energy_kcal":
            if actual < target * 0.9:
                status = "deficit"
            elif actual > target * 1.1:
                status = "excess"
            else:
                status = "ok"
        else:
            if actual < target * 0.7:
                status = "deficit"
            elif actual > target * 1.5 and key in {"fat_g", "carb_g"}:
                status = "excess"
            else:
                status = "ok"
        rows.append(
            {
                "key": key,
                "label": NUTRIENT_LABELS.get(key, key),
                "actual": round(actual, 2),
                "target": target,
                "percent": pct,
                "status": status,
            }
        )
    return rows


def condition_notes(person: Person, rows: list[dict], calorie_balance: float) -> list[str]:
    notes: list[str] = []
    by_key = {r["key"]: r for r in rows}
    cond = {c.lower() for c in person.conditions}

    if calorie_balance < -200:
        notes.append(
            f"Calorie intake is about {abs(int(calorie_balance))} kcal below estimated need (TDEE minus exercise). "
            "Useful for weight loss only if the log is complete."
        )
    elif calorie_balance > 200:
        notes.append(
            f"Calorie intake is about {int(calorie_balance)} kcal above estimated need. "
            "Sustained surplus usually increases body weight."
        )
    else:
        notes.append("Calories are near estimated maintenance for this body size and activity.")

    sodium = by_key.get("sodium_mg")
    if sodium and sodium["status"] == "low_log":
        notes.append(
            "Logged sodium is very low. Indian cooked food usually contains salt — the diary may be incomplete, "
            "not a medical sodium deficiency."
        )
    if sodium and sodium["status"] == "excess" and ("hypertension" in cond or "high blood pressure" in cond):
        notes.append("Sodium is above the tighter target used because hypertension is on the profile.")

    iron = by_key.get("iron_mg")
    if iron and iron["status"] == "deficit":
        extra = " This matters more because anemia is listed." if "anemia" in cond else ""
        notes.append(f"Iron is below 70% of the personal target.{extra}")

    if "diabetes" in cond:
        fiber = by_key.get("fiber_g")
        if fiber and fiber["status"] == "deficit":
            notes.append("Fiber is low relative to the diabetes-adjusted target; vegetables, dals, and millets help.")

    if "pregnancy" in cond:
        folate = by_key.get("folate_ug")
        if folate and folate["status"] == "deficit":
            notes.append("Folate is below the pregnancy target. This is educational only — follow clinician advice.")

    b12 = by_key.get("vitamin_b12_ug")
    if b12 and b12["status"] == "deficit":
        notes.append("Vitamin B12 is low in this log (common if the day is mostly plant foods).")

    notes.append("Not medical advice. Numbers depend on logged foods, portion guesses, and reference tables.")
    return notes


def weight_trend_note(avg_balance: float) -> str:
    # ~7700 kcal ~ 1 kg body fat (rough).
    kg_per_week = round((avg_balance * 7) / 7700, 2)
    if abs(kg_per_week) < 0.05:
        return "Average energy balance is near maintenance; little weight change expected from these logs."
    direction = "gain" if kg_per_week > 0 else "loss"
    return (
        f"If these logs are complete and typical, the average energy balance implies roughly "
        f"{abs(kg_per_week)} kg/week {direction}. That is a crude estimate, not a prediction."
    )
