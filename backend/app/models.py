from typing import Any, Optional

from pydantic import BaseModel, Field


NUTRIENT_KEYS = [
    "energy_kcal",
    "protein_g",
    "carb_g",
    "fat_g",
    "fiber_g",
    "sodium_mg",
    "potassium_mg",
    "calcium_mg",
    "iron_mg",
    "magnesium_mg",
    "zinc_mg",
    "vitamin_a_ug",
    "vitamin_c_mg",
    "folate_ug",
    "vitamin_b12_ug",
    "vitamin_d_ug",
]


class Nutrients(BaseModel):
    energy_kcal: float = 0
    protein_g: float = 0
    carb_g: float = 0
    fat_g: float = 0
    fiber_g: float = 0
    sodium_mg: float = 0
    potassium_mg: float = 0
    calcium_mg: float = 0
    iron_mg: float = 0
    magnesium_mg: float = 0
    zinc_mg: float = 0
    vitamin_a_ug: float = 0
    vitamin_c_mg: float = 0
    folate_ug: float = 0
    vitamin_b12_ug: float = 0
    vitamin_d_ug: float = 0

    def scaled(self, factor: float) -> "Nutrients":
        data = {k: round(getattr(self, k) * factor, 3) for k in NUTRIENT_KEYS}
        return Nutrients(**data)

    def add(self, other: "Nutrients") -> "Nutrients":
        data = {k: round(getattr(self, k) + getattr(other, k), 3) for k in NUTRIENT_KEYS}
        return Nutrients(**data)


class FoodItem(BaseModel):
    id: str
    name: str
    names: list[str] = Field(default_factory=list)
    form: str = "cooked"
    source: str = "starter"
    default_grams: float = 100
    piece_grams: Optional[float] = None
    health_notes: str = ""
    nutrients_per_100g: Nutrients


class PersonIn(BaseModel):
    name: str
    sex: str  # male | female | other
    age: int = Field(ge=1, le=120)
    height_cm: float = Field(gt=0)
    weight_kg: float = Field(gt=0)
    activity: str = "sedentary"
    conditions: list[str] = Field(default_factory=list)
    nationality: str = ""
    ethnicity: str = ""


class Person(PersonIn):
    id: str


class LogFoodIn(BaseModel):
    food_id: Optional[str] = None
    query: Optional[str] = None
    quantity: float = 100
    unit: str = "g"


class ExerciseIn(BaseModel):
    activity: str
    minutes: float = Field(gt=0)


class DayLogIn(BaseModel):
    person_id: str
    date: str
    foods: list[LogFoodIn]
    exercises: list[ExerciseIn] = Field(default_factory=list)
    notes: str = ""


class DayLog(BaseModel):
    person_id: str
    date: str
    foods: list[dict[str, Any]]
    exercises: list[dict[str, Any]]
    notes: str = ""
    totals: Nutrients
    exercise_kcal: float = 0


class AiEstimateRequest(BaseModel):
    query: str = Field(min_length=2)
    quantity: float = Field(default=100, gt=0)
    unit: str = "g"


class RecipeSuggestionRequest(BaseModel):
    ingredients: list[str] = Field(min_length=1)


class RecipeGenerateRequest(BaseModel):
    dish_name: str = Field(min_length=2)
    available_ingredients: list[str] = Field(default_factory=list)
    person_id: str = ""


class RecipeIngredient(BaseModel):
    name: str = Field(min_length=1)
    quantity: float = Field(default=1, gt=0)
    unit: str = "g"
    grams: float = Field(gt=0)
    is_extra: bool = False
    notes: str = ""


class CookingMethod(BaseModel):
    mode: str = Field(min_length=2)
    applicable: bool = True
    steps: list[str] = Field(default_factory=list)


class RecipeIn(BaseModel):
    name: str = Field(min_length=2)
    description: str = ""
    servings: int = Field(default=1, ge=1, le=100)
    ingredients: list[RecipeIngredient] = Field(min_length=1)
    preparation: list[str] = Field(default_factory=list)
    cooking_methods: list[CookingMethod] = Field(default_factory=list)
    source: str = "manual"
