import { useState } from "react";

const MODES = ["Stovetop / gas", "Pressure cooker", "Air fryer", "Microwave"];

function blankIngredient() {
  return { name: "", quantity: 1, unit: "g", grams: 1, is_extra: false, notes: "" };
}

function blankMethods() {
  return MODES.map((mode) => ({ mode, applicable: true, steps: [] }));
}

export function emptyRecipe() {
  return {
    name: "",
    description: "",
    servings: 1,
    ingredients: [blankIngredient()],
    preparation: [],
    cooking_methods: blankMethods(),
    source: "manual",
  };
}

export default function RecipeForm({ initial, onSubmit, submitLabel = "Calculate and save" }) {
  const [form, setForm] = useState(initial || emptyRecipe());
  const [prepText, setPrepText] = useState((initial?.preparation || []).join("\n"));
  const [methodText, setMethodText] = useState(
    Object.fromEntries(
      (initial?.cooking_methods || blankMethods()).map((method) => [
        method.mode,
        (method.steps || []).join("\n"),
      ])
    )
  );

  function updateIngredient(index, key, value) {
    setForm((current) => ({
      ...current,
      ingredients: current.ingredients.map((item, i) =>
        i === index ? { ...item, [key]: value } : item
      ),
    }));
  }

  function updateMethod(index, value) {
    setForm((current) => ({
      ...current,
      cooking_methods: current.cooking_methods.map((method, i) =>
        i === index ? { ...method, ...value } : method
      ),
    }));
  }

  function submit(event) {
    event.preventDefault();
    onSubmit({
      ...form,
      servings: Number(form.servings),
      ingredients: form.ingredients.map((item) => ({
        ...item,
        quantity: Number(item.quantity),
        grams: Number(item.grams),
      })),
      preparation: prepText.split("\n").map((x) => x.trim()).filter(Boolean),
      cooking_methods: form.cooking_methods.map((method) => ({
        ...method,
        steps: (methodText[method.mode] || "")
          .split("\n")
          .map((x) => x.trim())
          .filter(Boolean),
      })),
      source: form.source || "manual",
    });
  }

  return (
    <form className="card stack" onSubmit={submit}>
      <h3>{initial?.id && initial.id !== "new" ? "Edit recipe" : "Add your recipe"}</h3>
      <label>
        Recipe name
        <input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
      </label>
      <label>
        Description
        <textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
      </label>
      <label>
        Number of servings
        <input
          type="number"
          min="1"
          max="100"
          value={form.servings}
          onChange={(e) => setForm({ ...form, servings: e.target.value })}
        />
      </label>

      <fieldset className="stack">
        <legend>Ingredients</legend>
        {form.ingredients.map((item, index) => (
          <div className="ingredient-edit" key={index}>
            <input
              required
              placeholder="Ingredient"
              value={item.name}
              onChange={(e) => updateIngredient(index, "name", e.target.value)}
            />
            <input
              required
              type="number"
              min="0.01"
              step="0.01"
              aria-label="Quantity"
              value={item.quantity}
              onChange={(e) => updateIngredient(index, "quantity", e.target.value)}
            />
            <input
              required
              placeholder="unit"
              value={item.unit}
              onChange={(e) => updateIngredient(index, "unit", e.target.value)}
            />
            <input
              required
              type="number"
              min="0.1"
              step="0.1"
              aria-label="Weight in grams"
              value={item.grams}
              onChange={(e) => updateIngredient(index, "grams", e.target.value)}
            />
            <span>g</span>
            <input
              placeholder="Notes"
              value={item.notes || ""}
              onChange={(e) => updateIngredient(index, "notes", e.target.value)}
            />
            <button
              type="button"
              className="ghost"
              onClick={() => setForm({ ...form, ingredients: form.ingredients.filter((_, i) => i !== index) })}
              disabled={form.ingredients.length === 1}
            >
              Remove
            </button>
          </div>
        ))}
        <button
          type="button"
          className="ghost"
          onClick={() => setForm({ ...form, ingredients: [...form.ingredients, blankIngredient()] })}
        >
          + Add ingredient
        </button>
      </fieldset>

      <label>
        Preparation — one step per line
        <textarea rows="5" value={prepText} onChange={(e) => setPrepText(e.target.value)} />
      </label>

      <fieldset className="stack">
        <legend>Cooking methods</legend>
        {form.cooking_methods.map((method, index) => (
          <div className="method-edit" key={method.mode}>
            <label className="check">
              <input
                type="checkbox"
                checked={method.applicable}
                onChange={(e) => updateMethod(index, { applicable: e.target.checked })}
              />
              {method.mode} applies
            </label>
            <textarea
              rows="4"
              disabled={!method.applicable}
              placeholder="One cooking step per line"
              value={methodText[method.mode] || ""}
              onChange={(e) => setMethodText({ ...methodText, [method.mode]: e.target.value })}
            />
          </div>
        ))}
      </fieldset>

      <button type="submit">{submitLabel}</button>
    </form>
  );
}
