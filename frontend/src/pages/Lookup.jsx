import { useState } from "react";
import { api } from "../api";
import AiEstimate from "../components/AiEstimate";

function NutrientTable({ nutrients, title }) {
  if (!nutrients) return null;
  const entries = Object.entries(nutrients);
  return (
    <div className="card">
      <h3>{title}</h3>
      <table>
        <tbody>
          {entries.map(([k, v]) => (
            <tr key={k}>
              <td>{k.replaceAll("_", " ")}</td>
              <td>{v}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function Lookup() {
  const [q, setQ] = useState("roti");
  const [quantity, setQuantity] = useState(2);
  const [unit, setUnit] = useState("piece");
  const [results, setResults] = useState([]);
  const [selected, setSelected] = useState(null);
  const [exactMatch, setExactMatch] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function loadResults() {
    setError("");
    setLoading(true);
    try {
      const data = await api(
        `/api/foods/search?q=${encodeURIComponent(q)}&quantity=${quantity}&unit=${encodeURIComponent(unit)}`
      );
      setResults(data.results || []);
      setExactMatch(data.exact_match);
      setSelected(
        data.exact_match
          ? data.results?.find((item) => item.match_type === "exact") || null
          : null
      );
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function search(e) {
    e.preventDefault();
    await loadResults();
  }

  return (
    <section>
      <h2>Food lookup</h2>
      <p className="muted">
        Search by English or common Indian names. Quantity is optional (default 100 g). Pick a match if several appear.
      </p>
      <form className="row" onSubmit={search}>
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Food name" />
        <input
          type="number"
          min="0"
          step="0.1"
          value={quantity}
          onChange={(e) => setQuantity(e.target.value)}
          style={{ maxWidth: 120 }}
        />
        <select value={unit} onChange={(e) => setUnit(e.target.value)}>
          <option value="g">grams</option>
          <option value="piece">piece</option>
          <option value="katori">katori</option>
          <option value="cup">cup</option>
          <option value="tbsp">tbsp</option>
        </select>
        <button type="submit" disabled={loading}>
          {loading ? "Searching…" : "Search"}
        </button>
      </form>
      {error && <p className="error">{error}</p>}
      {results.length > 0 && !exactMatch && (
        <p className="error">
          No exact match for “{q}”. These are suggestions, not the same food.
        </p>
      )}
      {exactMatch === false && (
        <AiEstimate
          query={q}
          quantity={quantity}
          unit={unit}
          onEstimated={(data) => {
            setResults((prev) => [data.food, ...prev.filter((r) => r.id !== data.food.id)]);
            setSelected(data.food);
            setExactMatch(true);
          }}
        />
      )}
      <div className="split">
        <div className="card">
          <h3>{exactMatch === false ? "Suggestions" : "Matches"}</h3>
          <ul className="list">
            {results.map((r) => (
              <li key={r.id}>
                <button type="button" className={selected?.id === r.id ? "pick on" : "pick"} onClick={() => setSelected(r)}>
                  <strong>{r.name}</strong>
                  <span>
                    {r.grams} g · {r.nutrients.energy_kcal} kcal · {r.source}
                    {r.match_type === "exact" ? " · exact" : ""}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </div>
        {selected && (
          <div>
            <div className="card">
              <h3>{selected.name}</h3>
              <p>{selected.health_notes}</p>
              <p className="muted">
                Source: {selected.source} · form: {selected.form} · {selected.quantity} {selected.unit} = {selected.grams} g
              </p>
            </div>
            <NutrientTable nutrients={selected.nutrients} title="For this quantity" />
          </div>
        )}
      </div>
    </section>
  );
}
