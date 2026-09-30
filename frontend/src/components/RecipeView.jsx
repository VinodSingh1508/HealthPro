const nutrientLabel = (key) => key.replaceAll("_", " ");

export function recipeInput(recipe) {
  return {
    name: recipe.name,
    description: recipe.description || "",
    servings: Number(recipe.servings) || 1,
    ingredients: recipe.ingredients || [],
    preparation: recipe.preparation || [],
    cooking_methods: recipe.cooking_methods || [],
    source: recipe.source || "manual",
  };
}

export default function RecipeView({ recipe, actions, personFit }) {
  if (!recipe) return null;
  const perServing = recipe.nutrition?.per_serving || {};

  return (
    <article className="recipe card">
      <div className="recipe-title">
        <div>
          <h2>{recipe.name}</h2>
          <p>{recipe.description}</p>
          <p className="muted">
            {recipe.servings} serving(s) · {recipe.source || "manual"}
          </p>
        </div>
        {actions && <div className="row">{actions}</div>}
      </div>

      <section>
        <h3>Ingredients</h3>
        <ul className="ingredient-list">
          {recipe.ingredients.map((item, index) => (
            <li key={`${item.name}-${index}`} className={item.is_extra ? "extra" : ""}>
              <strong>{item.quantity} {item.unit}</strong> {item.name}
              <span className="muted"> · {item.grams} g</span>
              {item.notes && <span> · {item.notes}</span>}
              {item.is_extra && <span className="badge-extra">extra required</span>}
            </li>
          ))}
        </ul>
      </section>

      <section>
        <h3>Preparation</h3>
        {recipe.preparation.length ? (
          <ol>
            {recipe.preparation.map((step, index) => <li key={index}>{step}</li>)}
          </ol>
        ) : <p className="muted">No separate preparation.</p>}
      </section>

      <section>
        <h3>Cooking</h3>
        <div className="method-grid">
          {recipe.cooking_methods.map((method) => (
            <div className="method" key={method.mode}>
              <h4>{method.mode}</h4>
              {!method.applicable ? (
                <p className="muted">Not suitable for this recipe.</p>
              ) : (
                <ol>
                  {method.steps.map((step, index) => <li key={index}>{step}</li>)}
                </ol>
              )}
            </div>
          ))}
        </div>
      </section>

      <section>
        <h3>Nutrition per serving</h3>
        {recipe.nutrition?.unmatched_ingredients?.length > 0 && (
          <p className="error">
            Missing from these totals: {recipe.nutrition.unmatched_ingredients.join(", ")}.
          </p>
        )}
        <p className="muted">{recipe.nutrition?.note}</p>
        <table>
          <tbody>
            {Object.entries(perServing).map(([key, value]) => (
              <tr key={key}>
                <td>{nutrientLabel(key)}</td>
                <td>{value}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {recipe.nutrition?.ingredient_matches?.length > 0 && (
          <details>
            <summary>Nutrition sources</summary>
            <ul>
              {recipe.nutrition.ingredient_matches.map((match, index) => (
                <li key={index}>
                  {match.ingredient} ({match.grams} g) → {match.matched_food} [{match.source}]
                </li>
              ))}
            </ul>
          </details>
        )}
      </section>

      {personFit && (
          <section className={`advice verdict-${personFit.verdict}`}>
            <h3>For {personFit.person_name}</h3>
            <p><strong>{personFit.headline}</strong></p>
            <p>{personFit.max_amount}</p>
            <ul>
              {personFit.reasons.map((reason) => <li key={reason}>{reason}</li>)}
            </ul>
            <p className="muted">This is for the selected person only and is not stored with the recipe.</p>
          </section>
        )}
        {recipe.condition_guidance?.length > 0 && (
          <section>
            <h3>People with these conditions</h3>
            <ul className="advice-list">
              {recipe.condition_guidance.map((row) => (
                <li key={row.condition} className={`advice verdict-${row.verdict}`}>
                  <strong>{row.condition}: {row.verdict === "avoid" ? "avoid" : "in moderation"}</strong>
                  <span>{row.limit}</span>
                  <span className="muted">{row.reason}</span>
                </li>
              ))}
            </ul>
          </section>
        )}
    </article>
  );
}
