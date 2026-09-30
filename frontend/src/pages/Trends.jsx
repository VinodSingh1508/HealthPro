import { useEffect, useState } from "react";
import { api } from "../api";

export default function Trends() {
  const [people, setPeople] = useState([]);
  const [personId, setPersonId] = useState("");
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api("/api/people")
      .then((rows) => {
        setPeople(rows);
        if (rows[0]) setPersonId(rows[0].id);
      })
      .catch((e) => setError(e.message));
  }, []);

  async function load() {
    setError("");
    if (!personId) return;
    try {
      setData(await api(`/api/analysis/trends?person_id=${personId}`));
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    if (personId) load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [personId]);

  return (
    <section>
      <h2>Trends</h2>
      <p className="muted">Uses only days you saved. Conditions on the person change targets before these flags are computed.</p>
      {error && <p className="error">{error}</p>}
      <label>
        Person
        <select value={personId} onChange={(e) => setPersonId(e.target.value)}>
          {people.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </select>
      </label>
      {data && (
        <div className="card">
          <p>
            {data.day_count} saved day(s). Average calorie balance: <strong>{data.average_calorie_balance}</strong> kcal.
          </p>
          <ul>
            {(data.notes || []).map((n) => (
              <li key={n}>{n}</li>
            ))}
          </ul>
          <table>
            <thead>
              <tr>
                <th>Date</th>
                <th>Intake kcal</th>
                <th>Balance</th>
              </tr>
            </thead>
            <tbody>
              {(data.days || []).map((d) => (
                <tr key={d.date}>
                  <td>{d.date}</td>
                  <td>{d.intake_kcal}</td>
                  <td>{d.calorie_balance}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
