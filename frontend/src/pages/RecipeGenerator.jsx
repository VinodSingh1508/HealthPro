import { useEffect, useState } from "react";
import { api } from "../api";
import RecipeView, { recipeInput } from "../components/RecipeView";

function parseIngredients(text) {
  return text
    .split(/[\n,]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

export default function RecipeGenerator() {
  const [mode, setMode] = useState("ingredients");
  const [ingredientText, setIngredientText] = useState("");
  const [dishName, setDishName] = useState("");
  const [suggestions, setSuggestions] = useState([]);
  const [recipe, setRecipe] = useState(null);
  const [loading, setLoading] = useState("");
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);
  const [people, setPeople] = useState([]);
  const [personId, setPersonId] = useState("");
  const [personFit, setPersonFit] = useState(null);

  useEffect(() => {
    api("/api/people").then(setPeople).catch(() => setPeople([]));
  }, []);

  async function suggest() {
    const ingredients = parseIngredients(ingredientText);
    if (!ingredients.length) return;
    setLoading("suggest");
    setError("");
    setRecipe(null);
    setPersonFit(null);
    setSaved(false);
    try {
      const data = await api("/api/recipes/suggest", {
        method: "POST",
        body: { ingredients },
      });
      setSuggestions(data.dishes || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading("");
    }
  }

  async function generate(name) {
    setLoading("generate");
    setError("");
    setSaved(false);
    try {
      const data = await api("/api/recipes/generate", {
        method: "POST",
        body: {
          dish_name: name,
          available_ingredients: mode === "ingredients" ? parseIngredients(ingredientText) : [],
          person_id: personId,
        },
      });
      setRecipe(data);
      setPersonFit(data.person_fit || null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading("");
    }
  }

  async function save() {
    setLoading("save");
    setError("");
    try {
      const data = await api("/api/recipes", {
        method: "POST",
        body: recipeInput(recipe),
      });
      setRecipe(data);
      setSaved(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading("");
    }
  }

  return (
    <section>
      <h2>Recipe generator</h2>
      <p className="muted">
        Generate from ingredients you have, or enter a dish directly. Generation is not cached.
      </p>
      <label className="card">
        Check against a person (optional)
        <select value={personId} onChange={(e) => setPersonId(e.target.value)}>
          <option value="">No person — show only general condition limits</option>
          {people.map((person) => (
            <option key={person.id} value={person.id}>
              {person.name}
              {person.conditions?.length ? ` (${person.conditions.join(", ")})` : ""}
            </option>
          ))}
        </select>
      </label>
      <div className="tabs">
        <button className={mode === "ingredients" ? "" : "ghost"} onClick={() => setMode("ingredients")}>
          From ingredients
        </button>
        <button className={mode === "dish" ? "" : "ghost"} onClick={() => setMode("dish")}>
          From dish name
        </button>
      </div>

      {mode === "ingredients" ? (
        <div className="card stack">
          <label>
            Available ingredients — comma-separated or one per line
            <textarea
              rows="6"
              value={ingredientText}
              onChange={(e) => setIngredientText(e.target.value)}
              placeholder={"ragi flour\nonion\ncurd\noil"}
            />
          </label>
          <button onClick={suggest} disabled={loading || !parseIngredients(ingredientText).length}>
            {loading === "suggest" ? "Finding dishes…" : "Suggest dishes"}
          </button>
          <div className="suggestion-grid">
            {suggestions.map((item) => (
              <button
                type="button"
                className="dish-suggestion"
                key={item.name}
                onClick={() => generate(item.name)}
                disabled={loading}
              >
                <strong>{item.name}</strong>
                <span>{item.reason}</span>
                {item.extra_ingredients?.length > 0 && (
                  <span className="extra-text">Needs: {item.extra_ingredients.join(", ")}</span>
                )}
              </button>
            ))}
          </div>
        </div>
      ) : (
        <div className="card row">
          <label className="grow">
            Dish name
            <input value={dishName} onChange={(e) => setDishName(e.target.value)} placeholder="Ragi roti" />
          </label>
          <button onClick={() => generate(dishName)} disabled={loading || !dishName.trim()}>
            {loading === "generate" ? "Generating…" : "Get recipe"}
          </button>
        </div>
      )}

      {loading === "generate" && <p>Generating recipe and calculating nutrition…</p>}
      {error && <p className="error">{error}</p>}
      {recipe && (
        <RecipeView
          recipe={recipe}
          personFit={personFit}
          actions={
            <button onClick={save} disabled={loading === "save" || saved}>
              {saved ? "Saved" : loading === "save" ? "Saving…" : "Save recipe"}
            </button>
          }
        />
      )}
    </section>
  );
}
