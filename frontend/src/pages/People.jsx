import { useEffect, useState } from "react";
import { api } from "../api";

const empty = {
  name: "",
  sex: "female",
  age: 30,
  height_cm: 160,
  weight_kg: 60,
  activity: "light",
  conditions: [],
  nationality: "",
  ethnicity: "",
};

const CONDITION_OPTIONS = ["hypertension", "diabetes", "anemia", "pregnancy", "thyroid", "kidney"];

export default function People() {
  const [people, setPeople] = useState([]);
  const [form, setForm] = useState(empty);
  const [editing, setEditing] = useState(null);
  const [error, setError] = useState("");
  const [planFor, setPlanFor] = useState(null);
  const [planLoading, setPlanLoading] = useState(false);

  async function refresh() {
    setPeople(await api("/api/people"));
  }

  useEffect(() => {
    refresh().catch((e) => setError(e.message));
  }, []);

  function toggleCondition(c) {
    setForm((f) => {
      const has = f.conditions.includes(c);
      return { ...f, conditions: has ? f.conditions.filter((x) => x !== c) : [...f.conditions, c] };
    });
  }

  async function showDietPlan(person) {
    setPlanLoading(true);
    setError("");
    setPlanFor(person);
    try {
      const saved = await api(`/api/people/${person.id}/diet-plan`, { method: "POST" });
      setPlanFor(saved);
      setPeople((rows) => rows.map((row) => (row.id === saved.id ? saved : row)));
    } catch (err) {
      setError(err.message);
    } finally {
      setPlanLoading(false);
    }
  }

  async function save(e) {
    e.preventDefault();
    setError("");
    const body = {
      name: form.name,
      sex: form.sex,
      age: Number(form.age),
      height_cm: Number(form.height_cm),
      weight_kg: Number(form.weight_kg),
      activity: form.activity,
      conditions: form.conditions,
      nationality: form.nationality || "",
      ethnicity: form.ethnicity || "",
    };
    try {
      if (editing) {
        await api(`/api/people/${editing}`, { method: "PUT", body });
      } else {
        await api("/api/people", { method: "POST", body });
      }
      setForm(empty);
      setEditing(null);
      await refresh();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <section>
      <h2>People</h2>
      <p className="muted">
        Age and sex are required for BMR. Nationality and ethnicity pick a customary cuisine, not a biological requirement. Conditions only change nutrient targets.
      </p>
      {error && <p className="error">{error}</p>}
      <div className="split">
        <form className="card stack" onSubmit={save}>
          <label>
            Name
            <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
          </label>
          <label>
            Sex
            <select value={form.sex} onChange={(e) => setForm({ ...form, sex: e.target.value })}>
              <option value="female">Female</option>
              <option value="male">Male</option>
              <option value="other">Other / skip binary</option>
            </select>
          </label>
          <div className="row">
            <label>
              Age
              <input type="number" min="1" value={form.age} onChange={(e) => setForm({ ...form, age: e.target.value })} required />
            </label>
            <label>
              Height (cm)
              <input type="number" min="1" step="0.1" value={form.height_cm} onChange={(e) => setForm({ ...form, height_cm: e.target.value })} required />
            </label>
            <label>
              Weight (kg)
              <input type="number" min="1" step="0.1" value={form.weight_kg} onChange={(e) => setForm({ ...form, weight_kg: e.target.value })} required />
            </label>
          </div>
          <div className="row">
            <label className="grow">
              Nationality
              <input
                value={form.nationality}
                onChange={(e) => setForm({ ...form, nationality: e.target.value })}
                placeholder="India"
              />
            </label>
            <label className="grow">
              Ethnicity
              <input
                value={form.ethnicity}
                onChange={(e) => setForm({ ...form, ethnicity: e.target.value })}
                placeholder="Tamil"
              />
            </label>
          </div>
          <label>
            Activity
            <select value={form.activity} onChange={(e) => setForm({ ...form, activity: e.target.value })}>
              <option value="sedentary">Sedentary</option>
              <option value="light">Light</option>
              <option value="moderate">Moderate</option>
              <option value="active">Active</option>
              <option value="very_active">Very active</option>
            </select>
          </label>
          <fieldset>
            <legend>Conditions</legend>
            {CONDITION_OPTIONS.map((c) => (
              <label key={c} className="check">
                <input type="checkbox" checked={form.conditions.includes(c)} onChange={() => toggleCondition(c)} />
                {c}
              </label>
            ))}
          </fieldset>
          <button type="submit">{editing ? "Update person" : "Save person"}</button>
        </form>
        <div className="card">
          <h3>Saved people</h3>
          <ul className="list">
            {people.map((p) => (
              <li key={p.id} className="person">
                <div>
                  <strong>{p.name}</strong>
                  <p className="muted">
                    {p.sex}, {p.age} y · {p.height_cm} cm · {p.weight_kg} kg
                    {(p.nationality || p.ethnicity) && ` · ${[p.nationality, p.ethnicity].filter(Boolean).join(", ")}`}
                    {p.conditions?.length ? ` · ${p.conditions.join(", ")}` : ""}
                  </p>
                </div>
                <div className="person-actions">
                  <button
                    type="button"
                    className="ghost"
                    onClick={() => showDietPlan(p)}
                    disabled={planLoading}
                  >
                    Diet plan
                  </button>
                  <button
                    type="button"
                    className="ghost"
                    onClick={() => {
                      setEditing(p.id);
                      setForm({ ...empty, ...p, nationality: p.nationality || "", ethnicity: p.ethnicity || "" });
                    }}
                  >
                    Edit
                  </button>
                </div>
              </li>
            ))}
          </ul>
        </div>
      </div>
      {planFor?.diet_plan && (
        <DietPlan person={planFor} loading={planLoading} />
      )}
    </section>
  );
}

function AdviceList({ title, rows, tone }) {
  if (!rows?.length) return null;
  return (
    <div>
      <h4>{title}</h4>
      <ul className="advice-list">
        {rows.map((row) => (
          <li key={row.item} className={`advice verdict-${tone}`}>
            <strong>{row.item}</strong>
            <span>{row.amount}</span>
            <span className="muted">{row.reason}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function DietPlan({ person, loading }) {
  const plan = person.diet_plan;
  return (
    <article className="card stack">
      <h3>Diet plan for {person.name}</h3>
      {loading && <p className="muted">Updating…</p>}
      <p>{plan.basis}</p>
      <section>
        <h4>Instructions</h4>
        <ul>
          {plan.meals.map((meal) => <li key={meal}>{meal}</li>)}
        </ul>
        <AdviceList title="Eat regularly" rows={plan.include} tone="good" />
        <AdviceList title="Keep limited" rows={plan.moderate} tone="moderate" />
        <AdviceList title="Leave out or keep very small" rows={plan.avoid} tone="avoid" />
      </section>
      {plan.diet_chart && <DietChart chart={plan.diet_chart} />}
      <p className="muted">{plan.disclaimer}</p>
    </article>
  );
}

function DietChart({ chart }) {
  return (
    <section>
      <h4>Daily diet chart</h4>
      <p className="muted">{chart.timing_note}</p>
      <div className="diet-chart">
        {chart.schedule.map((slot) => (
          <div className="diet-slot" key={`${slot.time}-${slot.meal}`}>
            <div className="diet-time">
              <strong>{slot.time}</strong>
              <span>{slot.meal}</span>
            </div>
            <ol>
              {slot.options.map((option) => <li key={option}>{option}</li>)}
            </ol>
          </div>
        ))}
      </div>
      {chart.notes?.length > 0 && (
        <div className="advice verdict-moderate">
          <strong>Adjustments for this profile</strong>
          <ul>
            {chart.notes.map((note) => <li key={note}>{note}</li>)}
          </ul>
        </div>
      )}
    </section>
  );
}
