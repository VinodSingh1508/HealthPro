"""Eating guidance from customary cuisine plus the person's nutrient targets.

Nationality and ethnicity pick a food pattern people from that background
commonly cook. They are not treated as a biological requirement. Amounts come
from the same daily targets used elsewhere in the app, so a condition such as
hypertension changes the salt figure instead of a model inventing one.

Person-specific recipe advice is computed for display and is not stored on the
recipe. Condition advice (anyone with hypertension, and so on) is stored,
because it describes the dish rather than one person.
"""

from __future__ import annotations

import json
import math

from .models import Person
from .nutrition import NUTRIENT_LABELS, person_targets

# Table salt is about 38758 mg sodium per 100 g.
SODIUM_MG_PER_SALT_G = 387.58

# One serving already at or over the daily cap is "avoid".
# One serving using a quarter of the day or more is "moderate".
AVOID_SHARE = 1.0
MODERATE_SHARE = 0.25

PREGNANCY_AVOID = (
    "alcohol",
    "beer",
    "wine",
    "rum",
    "whisky",
    "whiskey",
    "vodka",
    "brandy",
    "raw fish",
    "sushi",
    "sashimi",
    "liver",
    "unpasteurized",
    "raw egg",
    "shark",
    "swordfish",
)

CUISINES = [
    {
        "id": "south_indian",
        "label": "South Indian home cooking",
        "keys": (
            "tamil", "telugu", "kannada", "malayali", "malayalee", "kerala",
            "andhra", "telangana", "karnataka", "south indian", "tamilian",
        ),
        "meals": [
            "Breakfast: idli, dosa, or upma with sambar, not a sweet drink.",
            "Lunch: a small portion of rice, a dal or sambar, and a vegetable.",
            "Dinner: millet or less rice, with a vegetable and curd.",
        ],
        "include": [
            ("Cooked dals and sambar", "2 katoris a day", "Main everyday protein and fiber."),
            ("Vegetables, including greens", "2 to 3 servings a day", "Customary and the easiest way to cover potassium and folate."),
            ("Buttermilk or plain curd", "1 cup a day", "Fits the pattern and adds calcium."),
        ],
    },
    {
        "id": "east_indian",
        "label": "East Indian home cooking",
        "keys": ("bengali", "odia", "assamese", "bhojpuri", "bihari", "east indian"),
        "meals": [
            "Breakfast: puffed rice, roti, or a light cooked meal rather than a sweet.",
            "Lunch: rice, a dal, and a vegetable, with fish only if you already eat it.",
            "Dinner: a smaller rice portion and a vegetable.",
        ],
        "include": [
            ("Dal", "2 katoris a day", "Everyday protein."),
            ("Vegetables", "2 to 3 servings a day", "Keeps the plate from being only rice."),
            ("Fish, if you eat it", "2 or 3 times a week, about 100 g cooked", "Common in this pattern; not required."),
        ],
    },
    {
        "id": "north_indian",
        "label": "North Indian home cooking",
        "keys": (
            "punjabi", "haryanvi", "rajasthani", "kashmiri", "pahadi",
            "north indian", "hindi belt",
        ),
        "meals": [
            "Breakfast: roti or poha with a protein such as curd or egg.",
            "Lunch: 2 rotis, a dal, and a dry vegetable.",
            "Dinner: the same pattern with less ghee than a restaurant meal.",
        ],
        "include": [
            ("Whole-wheat roti", "3 to 5 a day, about 40 g each", "The staple grain in this pattern."),
            ("Dal or legumes", "1 to 2 katoris a day", "Protein without relying on fried paneer."),
            ("Sabzi", "2 servings a day", "Bulk and micronutrients."),
        ],
    },
    {
        "id": "indian",
        "label": "Indian home cooking",
        "keys": ("india", "indian", "hindu", "sikh", "gujarati", "marathi", "goan"),
        "meals": [
            "Breakfast: idli, poha, upma, or roti rather than a packaged snack.",
            "Lunch: one grain (rice or roti), one dal, and one vegetable.",
            "Dinner: the same shape, with a smaller grain portion.",
        ],
        "include": [
            ("Dal or another legume", "2 katoris cooked a day", "The usual protein in this pattern."),
            ("Vegetables", "2 to 3 servings a day", "Cover gaps that rice and roti do not."),
            ("Plain curd or buttermilk", "1 cup a day", "Calcium, and easier to keep than sweet lassi."),
        ],
    },
    {
        "id": "jain",
        "label": "Jain vegetarian cooking",
        "keys": ("jain",),
        "meals": [
            "Build meals from grains, dals, milk, and vegetables you already eat.",
            "Skip root vegetables only if that is your own practice; it is not a health requirement.",
        ],
        "include": [
            ("Dal and milk or curd", "dal twice a day and 1 cup of milk or curd", "Protein on a vegetarian pattern."),
            ("Vegetables other than those you personally omit", "2 to 3 servings a day", "Keeps the pattern from being only grain."),
        ],
    },
    {
        "id": "east_asian",
        "label": "East Asian home cooking",
        "keys": (
            "chinese", "han", "japanese", "korean", "cantonese", "taiwanese",
            "vietnamese", "thai", "filipino",
        ),
        "meals": [
            "A bowl of rice or noodles with vegetables and a palm-sized portion of tofu, egg, or fish.",
            "Keep soy sauce and pickles as a condiment, not a side dish.",
        ],
        "include": [
            ("Rice or noodles", "1 to 2 bowls a day", "The staple; the rest of the plate should still have vegetables."),
            ("Tofu, egg, or fish", "one palm-sized portion a day", "Typical protein in this pattern."),
            ("Vegetables", "2 to 3 servings a day", "Balance for a white-rice meal."),
        ],
    },
    {
        "id": "mediterranean",
        "label": "Mediterranean home cooking",
        "keys": (
            "greek", "italian", "spanish", "portuguese", "turkish", "lebanese",
            "mediterranean", "cypriot",
        ),
        "meals": [
            "Vegetables and legumes at both main meals, with olive oil instead of ghee.",
            "Fish a couple of times a week if you eat it; cheese as a garnish.",
        ],
        "include": [
            ("Vegetables and salad", "2 to 3 servings a day", "The centre of this pattern."),
            ("Beans or lentils", "1 cup cooked a day", "Protein and fiber."),
            ("Olive oil", "the oil allowance below, not extra on top", "The usual added fat."),
        ],
    },
    {
        "id": "middle_eastern",
        "label": "Middle Eastern home cooking",
        "keys": ("arab", "egyptian", "syrian", "iraqi", "iranian", "persian", "yemeni", "pakistani"),
        "meals": [
            "Flatbread or rice with a stew of legumes or meat, plus salad and yogurt.",
            "Keep fried pastries and syrup sweets occasional.",
        ],
        "include": [
            ("Lentils, chickpeas, or beans", "1 to 2 cups cooked a day", "A customary protein."),
            ("Salad and cooked vegetables", "2 servings a day", "Bulk beside the rice or bread."),
            ("Plain yogurt", "1 cup a day", "Fits the pattern."),
        ],
    },
    {
        "id": "west_african",
        "label": "West African home cooking",
        "keys": ("nigerian", "yoruba", "igbo", "hausa", "ghanaian", "akan", "senegalese"),
        "meals": [
            "A swallow or rice portion with a stew of beans, vegetables, or fish.",
            "Treat palm oil and fried plantain as part of the oil allowance, not an extra.",
        ],
        "include": [
            ("Beans or a bean stew", "1 cup cooked a day", "Protein and fiber in this pattern."),
            ("Vegetables and leafy stews", "2 servings a day", "Micronutrients beside the staple."),
        ],
    },
    {
        "id": "latin",
        "label": "Latin American home cooking",
        "keys": ("mexican", "brazilian", "colombian", "peruvian", "chilean", "latino", "latina"),
        "meals": [
            "Corn or rice with beans and a vegetable, salsa on the side.",
            "Keep fried dishes and cheese portions inside the fat allowance.",
        ],
        "include": [
            ("Beans", "1 cup cooked a day", "The customary protein and fiber."),
            ("Vegetables or salsa made of vegetables", "2 servings a day", "Adds volume without much oil."),
        ],
    },
]

GENERAL_CHART = {
    "breakfast": [
        "Vegetable oats or porridge, 1 bowl, plus 1 boiled egg or ½ cup curd",
        "2 whole-grain toasts with 1 egg or ½ cup cooked beans",
        "Vegetable poha, 1 bowl, with ½ cup plain curd",
    ],
    "mid_morning": [
        "1 whole fruit",
        "1 cup plain buttermilk or unsweetened yogurt",
        "A small handful (20–25 g) of unsalted nuts",
    ],
    "lunch": [
        "2 small whole-grain rotis, 1 cup dal, and 1 cup vegetables",
        "1 cup cooked rice, 1 palm-sized protein, and 1 cup vegetables",
        "1½ cups bean-and-vegetable bowl with a small whole-grain serving",
    ],
    "evening": [
        "Tea or coffee without sugar, with 25 g roasted chana",
        "1 whole fruit with 10–15 g nuts",
        "1 cup unsweetened yogurt or buttermilk",
    ],
    "dinner": [
        "2 small rotis, 1 cup dal or lean protein, and 1 cup vegetables",
        "¾ cup cooked rice, 1 cup protein curry, and 1 cup vegetables",
        "Vegetable soup plus a palm-sized protein and 1 small roti",
    ],
}

CHART_OPTIONS = {
    "south_indian": {
        "breakfast": [
            "2 idlis with 1 cup sambar",
            "1 medium dosa with 1 cup sambar; chutney up to 1 tablespoon",
            "1 cup vegetable upma with ½ cup plain curd",
        ],
        "lunch": [
            "1 cup cooked rice, 1 cup sambar, 1 cup poriyal, and ½ cup curd",
            "2 small millet rotis, 1 cup dal, and 1 cup vegetables",
            "1 cup lemon rice with little oil, 1 cup dal, and cucumber salad",
        ],
        "dinner": [
            "2 small dosas with 1 cup sambar and vegetables",
            "¾ cup cooked millet, 1 cup dal, and 1 cup vegetables",
            "2 small rotis, 1 cup vegetable kurma, and ½ cup curd",
        ],
    },
    "north_indian": {
        "breakfast": [
            "2 small vegetable rotis with ½ cup plain curd",
            "1 bowl vegetable poha with ½ cup curd",
            "2 besan chillas with mint chutney",
        ],
        "lunch": [
            "2 small rotis, 1 cup dal, 1 cup sabzi, and salad",
            "1 cup cooked rice, 1 cup rajma or chana, and salad",
            "2 small rotis, a palm-sized chicken or paneer portion, and 1 cup sabzi",
        ],
        "dinner": [
            "2 small rotis, 1 cup dal, and 1 cup sabzi",
            "¾ cup cooked rice, a palm-sized protein curry, and salad",
            "1½ cups vegetable khichdi with ½ cup curd",
        ],
    },
    "indian": {
        "breakfast": [
            "2 idlis with 1 cup sambar",
            "1 bowl vegetable poha or upma with ½ cup curd",
            "2 small rotis with 1 egg or ½ cup dal",
        ],
        "lunch": [
            "2 small rotis, 1 cup dal, 1 cup sabzi, and salad",
            "1 cup cooked rice, 1 cup dal or sambar, and 1 cup vegetables",
            "1½ cups vegetable khichdi with ½ cup curd",
        ],
        "dinner": [
            "2 small rotis, 1 cup dal, and 1 cup vegetables",
            "¾ cup cooked rice, a palm-sized protein, and 1 cup vegetables",
            "1 bowl millet khichdi with curd and salad",
        ],
    },
    "jain": {
        "breakfast": [
            "2 besan chillas with plain curd",
            "1 bowl vegetable poha using vegetables allowed in your practice",
            "2 idlis with dal-based sambar prepared to your practice",
        ],
        "lunch": [
            "2 small rotis, 1 cup dal, and 1 cup allowed vegetables",
            "1 cup cooked rice, 1 cup dal, and ½ cup curd",
            "1½ cups moong khichdi with an allowed vegetable",
        ],
        "dinner": [
            "2 small rotis, 1 cup dal, and 1 cup allowed vegetables",
            "1 bowl millet khichdi with ½ cup curd",
            "Paneer or tofu, 100 g, with 2 small rotis and allowed vegetables",
        ],
    },
    "east_indian": {
        "breakfast": [
            "1 bowl vegetable poha or puffed rice with roasted chana",
            "2 small rotis with 1 egg or ½ cup dal",
            "1 bowl vegetable oats with plain curd",
        ],
        "lunch": [
            "1 cup cooked rice, 1 cup dal, and 1 cup vegetables",
            "1 cup cooked rice, 100 g fish, and 1 cup vegetables",
            "2 small rotis, 1 cup chana or dal, and salad",
        ],
        "dinner": [
            "¾ cup cooked rice, 1 cup dal, and vegetables",
            "2 small rotis with a palm-sized fish or paneer portion and vegetables",
            "1½ cups vegetable khichdi with plain curd",
        ],
    },
    "east_asian": {
        "breakfast": [
            "1 bowl rice porridge with egg and vegetables",
            "2 eggs with vegetables and 1 small bowl rice",
            "Unsweetened yogurt with fruit and 20 g nuts",
        ],
        "lunch": [
            "1 bowl rice, tofu or fish, and 2 cups vegetables",
            "1 bowl noodles with a palm-sized protein and vegetables",
            "1½ cups vegetable-and-tofu soup with a small bowl rice",
        ],
        "dinner": [
            "1 small bowl rice, tofu or fish, and 2 cups vegetables",
            "Vegetable soup with a palm-sized protein and a small noodle portion",
            "Stir-fried vegetables and tofu with ¾ cup cooked rice",
        ],
    },
    "mediterranean": {
        "breakfast": [
            "Plain yogurt with fruit and 20 g nuts",
            "2 eggs with tomato and 1 slice whole-grain bread",
            "Oats with fruit and unsweetened milk",
        ],
        "lunch": [
            "1½ cups lentil-and-vegetable salad with whole-grain bread",
            "100 g fish, 1 cup vegetables, and ¾ cup cooked grain",
            "1 cup beans, salad, and 1 small whole-grain pita",
        ],
        "dinner": [
            "Vegetable soup, 1 cup beans, and 1 slice whole-grain bread",
            "100 g fish or chicken with 2 cups vegetables",
            "Whole-grain pasta, 1 cup cooked, with vegetables and beans",
        ],
    },
}


def _diet_chart(person: Person, cuisine: dict | None) -> list[dict]:
    """Return a reusable day template. Times are practical anchors, not medical rules."""
    chart = {key: list(value) for key, value in GENERAL_CHART.items()}
    if cuisine:
        for key, options in CHART_OPTIONS.get(cuisine["id"], {}).items():
            chart[key] = list(options)

    cond = _conditions(person)
    suffixes = []
    if "diabetes" in cond:
        suffixes.append("Use no added sugar; choose whole fruit, not juice.")
    if "hypertension" in cond:
        suffixes.append("Cook with little salt and skip pickle, papad, and packaged sauces.")
    if "anemia" in cond:
        suffixes.append("Add lemon or another vitamin C food to lunch or dinner; keep tea/coffee one hour away.")
    if "pregnancy" in cond:
        suffixes.append("Use pasteurized dairy and fully cooked eggs, fish, and meat.")
    if "kidney" in cond:
        suffixes.append("Kidney diets depend on laboratory results; confirm the portions with the treating clinician.")
    if "thyroid" in cond:
        suffixes.append("If taking thyroid medicine, keep breakfast 30–60 minutes after the tablet.")

    schedule = [
        ("On waking", "06:30", [
            "Water; no special detox drink is needed",
            "Warm water or unsweetened herbal drink",
        ]),
        ("Breakfast", "08:00", chart["breakfast"]),
        ("Mid-morning", "11:00", chart["mid_morning"]),
        ("Lunch", "13:30", chart["lunch"]),
        ("Evening snack", "16:30", chart["evening"]),
        ("Dinner", "19:30", chart["dinner"]),
    ]
    rows = [
        {"meal": meal, "time": time, "options": options[:3]}
        for meal, time, options in schedule
    ]
    return {
        "schedule": rows,
        "notes": suffixes,
        "timing_note": (
            "Move all times to fit the person's routine, while keeping meals roughly "
            "3–4 hours apart and dinner about 2–3 hours before sleep."
        ),
    }


def profile_key(person: Person) -> str:
    payload = {
        "nationality": person.nationality.strip().lower(),
        "ethnicity": person.ethnicity.strip().lower(),
        "conditions": sorted(c.lower() for c in person.conditions),
        "sex": person.sex.lower(),
        "age": person.age,
        "weight_kg": round(person.weight_kg, 1),
        "height_cm": round(person.height_cm, 1),
        "activity": person.activity.lower(),
    }
    return json.dumps(payload, sort_keys=True)


def _conditions(person: Person) -> set[str]:
    return {c.lower() for c in person.conditions}


def _salt_amount(sodium_mg: float) -> str:
    grams = sodium_mg / SODIUM_MG_PER_SALT_G
    teaspoons = grams / 5
    return (
        f"up to {grams:.1f} g of salt a day (about {teaspoons:.1f} teaspoons), "
        "including salt already in the food"
    )


def _oil_grams(fat_g: float) -> int:
    return int(round(min(30, max(10, fat_g * 0.35))))


def _match_cuisine(person: Person) -> dict | None:
    text = f"{person.nationality} {person.ethnicity}".lower()
    if not text.strip():
        return None
    # A Jain pattern is a stricter customary diet than the regional one.
    if "jain" in text:
        return next(cuisine for cuisine in CUISINES if cuisine["id"] == "jain")
    best = None
    best_len = 0
    for cuisine in CUISINES:
        for key in cuisine["keys"]:
            if key in text and len(key) > best_len:
                best = cuisine
                best_len = len(key)
    return best


def _row(item: str, amount: str, reason: str) -> dict:
    return {"item": item, "amount": amount, "reason": reason}


def build_diet_plan(person: Person) -> dict:
    targets = person_targets(person)
    cond = _conditions(person)
    cuisine = _match_cuisine(person)
    oil_g = _oil_grams(targets["fat_g"])

    include = []
    moderate = []
    avoid = []

    if cuisine:
        basis = (
            f"Eating pattern: {cuisine['label']}, chosen from the nationality and ethnicity "
            "as a customary cuisine, not as a biological category."
        )
        meals = list(cuisine["meals"])
        include.extend(_row(*item) for item in cuisine["include"])
    else:
        named = ", ".join(
            part for part in (person.nationality.strip(), person.ethnicity.strip()) if part
        )
        if named:
            basis = (
                f"No specific cuisine is tied to “{named}”, so this is a general pattern. "
                "Nationality and ethnicity are used only as a clue to customary food."
            )
        else:
            basis = (
                "Nationality and ethnicity are blank, so this is a general pattern. "
                "Add them on the person to match a customary cuisine."
            )
        meals = [
            "Each main meal: one grain, one protein food, and one vegetable.",
            "Fruit once a day, and water rather than a sweet drink.",
        ]
        include.extend(
            [
                _row("Vegetables", "2 to 3 servings a day", "The most reliable way to cover micronutrients."),
                _row("Legumes, eggs, dairy, or a palm of meat or fish", "a protein food at two meals", "Covers protein without a large fried portion."),
                _row("Whole grains or millet", "the grain portion of two meals", "More fiber than a plate of only polished rice."),
            ]
        )

    if "jain" in f"{person.nationality} {person.ethnicity}".lower():
        avoid.append(
            _row(
                "Meat, fish, and eggs",
                "none, if you follow a Jain pattern",
                "This is the customary pattern, not a medical limit.",
            )
        )

    moderate.append(
        _row(
            "Added oil or ghee",
            f"up to {oil_g} g a day (about {max(1, round(oil_g / 5))} teaspoons)",
            "Leaves room for the fat already in dals, nuts, dairy, and meat.",
        )
    )
    moderate.append(
        _row(
            "Salt",
            _salt_amount(targets["sodium_mg"]),
            "Set from this person's sodium target"
            + (" (tightened because hypertension is listed)." if "hypertension" in cond else "."),
        )
    )
    moderate.append(
        _row(
            "Fried snacks and sweets",
            "a few times a week, not every day",
            "Restaurant and festive portions sit outside the oil and sugar room above.",
        )
    )

    if "hypertension" in cond:
        avoid.append(
            _row(
                "Papad, pickle, and salted snacks as a regular side",
                "pickle at most 1 teaspoon a day",
                "These use up the sodium target before the meal does.",
            )
        )
    if "diabetes" in cond:
        rice_g = int(round(targets["carb_g"] * 0.35 / 0.28))
        moderate.append(
            _row(
                "Cooked rice, sweets, and fruit juice",
                f"cooked rice up to about {rice_g} g a day, sweets at most 15 g",
                "Carbohydrate target is tightened because diabetes is listed.",
            )
        )
        avoid.append(
            _row(
                "Sugary drinks",
                "none as a daily habit",
                "They spend the carbohydrate target without any fiber.",
            )
        )
    if "kidney" in cond:
        moderate.append(
            _row(
                "Protein foods and fruit juice",
                f"protein foods up to about {targets['protein_g']:.0f} g of protein a day; juice at most 150 ml",
                "Protein and potassium targets are tightened because kidney disease is listed.",
            )
        )
    if "anemia" in cond:
        include.append(
            _row(
                "Dal, greens, sprouts, or meat, with a vitamin C food",
                "an iron-containing food at two meals",
                "Iron target is higher because anemia is listed.",
            )
        )
        moderate.append(
            _row(
                "Tea and coffee",
                "not with the iron-rich meal; leave an hour either side",
                "They reduce how much iron that meal provides.",
            )
        )
    if "pregnancy" in cond:
        avoid.append(
            _row(
                "Alcohol, and liver in large amounts",
                "alcohol: none",
                "Listed because pregnancy is on the profile. Follow the clinician for the rest.",
            )
        )
        include.append(
            _row(
                "Folate-rich foods such as dal and greens",
                "every day, alongside whatever folate was prescribed",
                "The folate target is higher in pregnancy. This does not replace a prescribed supplement.",
            )
        )
    if "thyroid" in cond:
        moderate.append(
            _row(
                "Soy foods",
                "up to 1 serving a day",
                "Large soy intakes can matter for some thyroid treatment. Do not drop iodized salt.",
            )
        )

    include.append(
        _row(
            "Water",
            "through the day, to thirst",
            "Replaces sugary drinks without adding a nutrient target.",
        )
    )

    return {
        "profile_key": profile_key(person),
        "basis": basis,
        "meals": meals,
        "diet_chart": _diet_chart(person, cuisine),
        "include": include,
        "moderate": moderate,
        "avoid": avoid,
        "disclaimer": (
            "Educational pattern for personal tracking, not a prescription. "
            "Ethnicity here only points at customary food."
        ),
    }


def _blob(names: list[str]) -> str:
    return " ".join(names).lower()


def _has_any(blob: str, words: tuple[str, ...]) -> str:
    return next((word for word in words if word in blob), "")


def _serving_grams(recipe: dict) -> float:
    servings = max(1, int(recipe.get("servings") or 1))
    total = sum(float(item.get("grams") or 0) for item in recipe.get("ingredients") or [])
    return total / servings


def _amount_text(servings_allowed: float, serving_grams: float) -> str:
    stepped = math.floor(servings_allowed * 2) / 2
    if stepped >= 3:
        return f"A normal serving (about {round(serving_grams)} g) fits in a day."
    if stepped < 0.5:
        return "One serving already passes the daily limit, so skip it."
    grams = round(stepped * serving_grams)
    label = "1 serving" if stepped == 1 else f"{stepped:g} servings"
    return f"Up to {label} a day (about {grams} g of this dish)."


def _nutrient_limits(
    per_serving: dict,
    caps: dict[str, float],
) -> list[dict]:
    """How many servings fit under each daily cap. Empty caps are skipped."""
    found = []
    for key, daily in caps.items():
        amount = float(per_serving.get(key) or 0)
        if daily <= 0 or amount <= 0:
            continue
        share = amount / daily
        if share < MODERATE_SHARE:
            continue
        verdict = "avoid" if share >= AVOID_SHARE else "moderate"
        label = NUTRIENT_LABELS.get(key, key)
        found.append(
            {
                "verdict": verdict,
                "servings": daily / amount,
                "reason": (
                    f"One serving has {round(amount)} {label.lower()}, "
                    f"against a daily cap of {round(daily)}."
                ),
            }
        )
    return found


def _hard_limits(blob: str, conditions: set[str]) -> list[dict]:
    found = []
    if "pregnancy" in conditions:
        hit = _has_any(blob, PREGNANCY_AVOID)
        if hit:
            found.append(
                {
                    "verdict": "avoid",
                    "servings": 0,
                    "reason": f"Contains “{hit}”, which is left out when pregnancy is listed.",
                }
            )
    if "diabetes" in conditions and _has_any(blob, ("sugar", "jaggery", "syrup", "dessert", "sweet")):
        found.append(
            {
                "verdict": "moderate",
                "servings": 0.5,
                "reason": "A sweet ingredient spends the carbohydrate room quickly when diabetes is listed.",
            }
        )
    if "anemia" in conditions and _has_any(blob, ("tea", "coffee")):
        found.append(
            {
                "verdict": "moderate",
                "servings": 1,
                "reason": "Tea or coffee with the meal reduces iron absorption.",
            }
        )
    if "thyroid" in conditions and _has_any(blob, ("soy", "soya", "tofu")):
        found.append(
            {
                "verdict": "moderate",
                "servings": 1,
                "reason": "Soy more than once a day is the amount to stay under when thyroid disease is listed.",
            }
        )
    return found


def _combine(limits: list[dict], serving_grams: float) -> dict | None:
    if not limits:
        return None
    rank = {"good": 0, "moderate": 1, "avoid": 2}
    verdict = max(limits, key=lambda row: rank[row["verdict"]])["verdict"]
    tightest = min(row["servings"] for row in limits)
    return {
        "verdict": verdict,
        "max_amount": _amount_text(tightest, serving_grams),
        "reasons": [row["reason"] for row in limits],
    }


def condition_guidance(recipe: dict) -> list[dict]:
    """Limits for anyone with a tracked condition. Stored on the recipe."""
    per_serving = (recipe.get("nutrition") or {}).get("per_serving") or {}
    names = [item.get("name", "") for item in recipe.get("ingredients") or []]
    blob = _blob(names)
    grams = _serving_grams(recipe)
    rows = []

    checks = {
        "hypertension": {"sodium_mg": 1500},
        "diabetes": {"carb_g": 180},
        "kidney": {"sodium_mg": 1500, "protein_g": 55, "potassium_mg": 2500},
    }
    for condition, caps in checks.items():
        combined = _combine(_nutrient_limits(per_serving, caps), grams)
        if not combined:
            continue
        rows.append(
            {
                "condition": condition,
                "verdict": combined["verdict"],
                "limit": combined["max_amount"],
                "reason": " ".join(combined["reasons"]),
            }
        )

    for condition in ("pregnancy", "anemia", "thyroid"):
        combined = _combine(_hard_limits(blob, {condition}), grams)
        if not combined:
            continue
        rows.append(
            {
                "condition": condition,
                "verdict": combined["verdict"],
                "limit": combined["max_amount"],
                "reason": " ".join(combined["reasons"]),
            }
        )
    return rows


def person_recipe_fit(person: Person, recipe: dict) -> dict:
    """Shown while generating. Not written onto the saved recipe."""
    per_serving = (recipe.get("nutrition") or {}).get("per_serving") or {}
    names = [item.get("name", "") for item in recipe.get("ingredients") or []]
    grams = _serving_grams(recipe)
    targets = person_targets(person)
    cond = _conditions(person)

    caps = {
        "energy_kcal": targets["energy_kcal"],
        "sodium_mg": targets["sodium_mg"],
        "carb_g": targets["carb_g"],
        "fat_g": targets["fat_g"],
    }
    if "kidney" in cond:
        caps["protein_g"] = targets["protein_g"]
        caps["potassium_mg"] = targets["potassium_mg"]

    limits = _nutrient_limits(per_serving, caps) + _hard_limits(_blob(names), cond)
    combined = _combine(limits, grams)
    unmatched = (recipe.get("nutrition") or {}).get("unmatched_ingredients") or []

    if combined is None:
        verdict = "good"
        max_amount = f"A normal serving (about {round(grams)} g) fits this person's daily targets."
        reasons = ["One serving stays under a quarter of the daily targets used for this profile."]
    else:
        verdict = combined["verdict"]
        max_amount = combined["max_amount"]
        reasons = combined["reasons"]

    headlines = {
        "good": f"A normal serving is a reasonable choice for {person.name}.",
        "moderate": f"{person.name} can eat this in a limited amount.",
        "avoid": f"{person.name} should skip this, or keep it far below one serving.",
    }
    if unmatched:
        reasons.append(
            "No nutrition data for " + ", ".join(unmatched) + ", so this check is incomplete."
        )

    return {
        "person_id": person.id,
        "person_name": person.name,
        "verdict": verdict,
        "headline": headlines[verdict],
        "max_amount": max_amount,
        "reasons": reasons,
    }
