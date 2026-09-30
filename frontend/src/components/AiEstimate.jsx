import { useState } from "react";
import { api } from "../api";

export default function AiEstimate({ query, quantity, unit, onEstimated }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);

  async function estimate() {
    if (!query.trim()) return;
    setLoading(true);
    setError("");
    try {
      const data = await api("/api/foods/ai-estimate", {
        method: "POST",
        body: { query: query.trim(), quantity: Number(quantity) || 100, unit },
      });
      setResult(data);
      onEstimated?.(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="card stack">
      <h3>No exact match</h3>
      <p className="muted">
        Gemini can estimate nutrition for this dish. Values are model estimates,
        not measured data, and are saved so the same dish is never asked twice.
      </p>
      <div className="row">
        <button type="button" onClick={estimate} disabled={loading || !query.trim()}>
          {loading ? "Estimating…" : `Estimate “${query}” with AI`}
        </button>
        {result && (
          <span className="muted">
            {result.cached ? "loaded from cache" : "new estimate, now cached"} ·{" "}
            {result.confidence} confidence
          </span>
        )}
      </div>
      {error && <p className="error">{error}</p>}
      {result && (
        <p className="muted">
          {result.serving_description
            ? `One serving = ${result.serving_description} (${result.serving_grams} g). `
            : `One serving = ${result.serving_grams} g. `}
          Showing {result.food.quantity} {result.food.unit} = {result.food.grams} g.
        </p>
      )}
      {result?.assumptions?.length > 0 && (
        <p className="muted">Assumed: {result.assumptions.join(" ")}</p>
      )}
    </div>
  );
}
