import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import AiEstimate from "../components/AiEstimate";

function today() {
  return new Date().toISOString().slice(0, 10);
}

function Analysis({ analysis, geminiText }) {
  if (!analysis) return null;
  return (
    <div className="card">
      <h3>Day analysis</h3>
      <p>
        Intake <strong>{analysis.intake_kcal}</strong> kcal · BMR {analysis.bmr} · TDEE {analysis.tdee} ·
        exercise {analysis.exercise_kcal} · estimated need {analysis.estimated_need_kcal} · balance{" "}
        <strong>{analysis.calorie_balance}</strong> kcal
      </p>
      <table>
        <thead>
          <tr>
            <th>Nutrient</th>
            <th>Actual</th>
            <th>Target</th>
            <th>%</th>
            <th>Flag</th>
          </tr>
        </thead>
        <tbody>
          {analysis.nutrients.map((n) => (
            <tr key={n.key} className={n.status}>
              <td>{n.label}</td>
              <td>{n.actual}</td>
              <td>{n.target}</td>
              <td>{n.percent}</td>
              <td>{n.status}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <ul>
        {analysis.notes.map((n) => (
          <li key={n}>{n}</li>
        ))}
      </ul>
      {geminiText && <p className="explain">{geminiText}</p>}
    </div>
  );
}

export default function DailyLog() {
  const [people, setPeople] = useState([]);
  const [personId, setPersonId] = useState("");
  const [date, setDate] = useState(today());
  const [foodQuery, setFoodQuery] = useState("");
  const [qty, setQty] = useState(1);
  const [unit, setUnit] = useState("katori");
  const [hits, setHits] = useState([]);
  const [exactMatch, setExactMatch] = useState(null);
  const [items, setItems] = useState([]);
  const [activity, setActivity] = useState("walk");
  const [minutes, setMinutes] = useState(30);
  const [exercises, setExercises] = useState([]);
  const [analysis, setAnalysis] = useState(null);
  const [geminiText, setGeminiText] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    api("/api/people")
      .then((rows) => {
        setPeople(rows);
        if (rows[0]) setPersonId(rows[0].id);
      })
      .catch((e) => setError(e.message));
  }, []);

  const body = useMemo(
    () => ({
      person_id: personId,
      date,
      foods: items.map((i) => ({ food_id: i.id, quantity: i.quantity, unit: i.unit })),
      exercises,
    }),
    [personId, date, items, exercises]
  );

  async function findFoods() {
    setError("");
    const data = await api(
      `/api/foods/search?q=${encodeURIComponent(foodQuery)}&quantity=${qty}&unit=${encodeURIComponent(unit)}`
    );
    setHits(data.results || []);
    setExactMatch(data.exact_match);
  }

  async function preview() {
    setError("");
    setGeminiText("");
    if (!personId) {
      setError("Create a person on the People page first, then select them here.");
      return;
    }
    try {
      const data = await api("/api/days/preview", { method: "POST", body });
      setAnalysis(data.analysis);
    } catch (err) {
      setError(err.message);
    }
  }

  async function save() {
    setError("");
    if (!personId) {
      setError("Select the person this day belongs to.");
      return;
    }
    try {
      const data = await api("/api/days", { method: "POST", body });
      setAnalysis(data.analysis);
      try {
        const explained = await api("/api/explain", { method: "POST", body: data.analysis });
        setGeminiText(explained.text);
      } catch {
        setGeminiText("");
      }
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <section>
      <h2>Daily log</h2>
      <p className="muted">Add foods and exercise, preview totals, then save for a selected person.</p>
      {error && <p className="error">{error}</p>}
      <div className="row">
        <label>
          Person
          <select value={personId} onChange={(e) => setPersonId(e.target.value)}>
            <option value="">Select…</option>
            {people.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Date
          <input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
        </label>
      </div>
      <div className="card stack">
        <h3>Foods</h3>
        <div className="row">
          <input
            value={foodQuery}
            onChange={(e) => {
              setFoodQuery(e.target.value);
              setExactMatch(null);
            }}
            placeholder="dal, roti, rice…"
          />
          <input type="number" min="0.1" step="0.1" value={qty} onChange={(e) => setQty(e.target.value)} style={{ maxWidth: 100 }} />
          <select value={unit} onChange={(e) => setUnit(e.target.value)}>
            <option value="g">g</option>
            <option value="piece">piece</option>
            <option value="katori">katori</option>
            <option value="cup">cup</option>
          </select>
          <button type="button" onClick={() => findFoods().catch((e) => setError(e.message))}>
            Find
          </button>
        </div>
        {exactMatch === false && (
          <>
            <p className="error">
              No exact match. The items below are suggestions.
            </p>
            <AiEstimate
              query={foodQuery}
              quantity={qty}
              unit={unit}
              onEstimated={(data) => {
                setHits((prev) => [data.food, ...prev.filter((h) => h.id !== data.food.id)]);
                setExactMatch(true);
              }}
            />
          </>
        )}
        <ul className="list">
          {hits.map((h) => (
            <li key={h.id}>
              <button
                type="button"
                className="pick"
                onClick={() => {
                  setItems((prev) => [...prev, { ...h, quantity: Number(qty), unit }]);
                  setHits([]);
                  setFoodQuery("");
                  setExactMatch(null);
                }}
              >
                Add {h.name} ({h.nutrients.energy_kcal} kcal)
              </button>
            </li>
          ))}
        </ul>
        <ul className="chips">
          {items.map((item, idx) => (
            <li key={`${item.id}-${idx}`}>
              {item.name} · {item.quantity} {item.unit}
              <button type="button" className="ghost" onClick={() => setItems(items.filter((_, i) => i !== idx))}>
                ×
              </button>
            </li>
          ))}
        </ul>
      </div>
      <div className="card row">
        <label>
          Exercise
          <select value={activity} onChange={(e) => setActivity(e.target.value)}>
            <option value="walk">Walk</option>
            <option value="run">Run</option>
            <option value="cycle">Cycle</option>
            <option value="gym">Gym</option>
            <option value="yoga">Yoga</option>
            <option value="sports">Sports</option>
            <option value="housework">Housework</option>
          </select>
        </label>
        <label>
          Minutes
          <input type="number" min="1" value={minutes} onChange={(e) => setMinutes(e.target.value)} />
        </label>
        <button type="button" onClick={() => setExercises([...exercises, { activity, minutes: Number(minutes) }])}>
          Add exercise
        </button>
        <span className="muted">{exercises.map((e) => `${e.activity} ${e.minutes}m`).join(" · ")}</span>
      </div>
      <div className="row">
        <button type="button" onClick={preview} disabled={!items.length}>
          Analyze without saving
        </button>
        <button type="button" onClick={save} disabled={!items.length || !personId}>
          Save this day
        </button>
      </div>
      <Analysis analysis={analysis} geminiText={geminiText} />
    </section>
  );
}
