import { useEffect, useState } from "react";
import {
  API_BASE_URL,
  createAnalysisRun,
  getAnalysisRun,
  listAnalysisRuns
} from "./api";
import "./styles.css";

const terminalStates = new Set(["completed", "failed"]);

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function pollRun(runId, onUpdate) {
  for (let attempt = 0; attempt < 90; attempt += 1) {
    const run = await getAnalysisRun(runId);
    onUpdate(run);
    if (terminalStates.has(run.status)) {
      return run;
    }
    await sleep(2000);
  }
  throw new Error("Timed out waiting for run completion.");
}

function AdvisorCard({ advisorKey, advisorData, verification }) {
  if (!advisorData) return null;
  const verified = verification?.verified_claim_count ?? 0;
  const total = verification?.claim_count ?? 0;

  return (
    <div className="card">
      <h3>{advisorKey.toUpperCase()}</h3>
      <p><strong>Recommendation:</strong> {advisorData.recommendation}</p>
      <p><strong>Confidence:</strong> {advisorData.confidence}</p>
      <p><strong>Thesis:</strong> {advisorData.thesis}</p>
      <p><strong>Claims Verified:</strong> {verified}/{total}</p>
    </div>
  );
}

export default function App() {
  const [ticker, setTicker] = useState("AAPL");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [activeRun, setActiveRun] = useState(null);
  const [recentRuns, setRecentRuns] = useState([]);

  useEffect(() => {
    listAnalysisRuns(12)
      .then(setRecentRuns)
      .catch(() => setRecentRuns([]));
  }, []);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      const created = await createAnalysisRun(ticker.trim().toUpperCase());
      const finalRun = await pollRun(created.run_id, setActiveRun);
      setActiveRun(finalRun);
      const refreshed = await listAnalysisRuns(12);
      setRecentRuns(refreshed);
    } catch (err) {
      setError(err.message || "Could not run analysis.");
    } finally {
      setSubmitting(false);
    }
  }

  const result = activeRun?.result || {};
  const finalPolicy = result.final_policy || {};
  const structured = result.structured_analyses || {};
  const verification = result.claim_verification || {};

  return (
    <main className="container">
      <header className="hero">
        <h1>Financial Agents Dashboard</h1>
        <p>Run multi-agent analysis and inspect reliability signals.</p>
        <small>API: {API_BASE_URL}</small>
      </header>

      <section className="panel">
        <form onSubmit={handleSubmit} className="run-form">
          <input
            value={ticker}
            onChange={(e) => setTicker(e.target.value.toUpperCase())}
            placeholder="Ticker (e.g., NVDA)"
            maxLength={7}
          />
          <button type="submit" disabled={submitting}>
            {submitting ? "Running..." : "Run Analysis"}
          </button>
        </form>
        {error ? <p className="error">{error}</p> : null}
      </section>

      <section className="grid">
        <div className="card">
          <h2>Run Status</h2>
          <p><strong>Run ID:</strong> {activeRun?.run_id || "-"}</p>
          <p><strong>Ticker:</strong> {activeRun?.ticker || "-"}</p>
          <p><strong>Status:</strong> {activeRun?.status || "-"}</p>
          <p><strong>Updated:</strong> {activeRun?.updated_at || "-"}</p>
          {activeRun?.error ? <p className="error">{activeRun.error}</p> : null}
        </div>

        <div className="card">
          <h2>Final Policy</h2>
          <p><strong>Recommendation:</strong> {finalPolicy.final_recommendation || "-"}</p>
          <p><strong>Confidence:</strong> {finalPolicy.confidence ?? "-"}</p>
          <p><strong>Adjusted Score:</strong> {finalPolicy.adjusted_policy_score ?? "-"}</p>
          <p><strong>Coverage Factor:</strong> {finalPolicy.coverage_factor ?? "-"}</p>
          <p><strong>Warnings:</strong> {finalPolicy.warning_count ?? "-"}</p>
        </div>
      </section>

      <section className="advisor-grid">
        {["warren", "bill", "robin"].map((advisor) => (
          <AdvisorCard
            key={advisor}
            advisorKey={advisor}
            advisorData={structured[advisor]}
            verification={verification[advisor]}
          />
        ))}
      </section>

      <section className="panel">
        <h2>Recent Runs</h2>
        <table>
          <thead>
            <tr>
              <th>Run ID</th>
              <th>Ticker</th>
              <th>Status</th>
              <th>Created</th>
            </tr>
          </thead>
          <tbody>
            {recentRuns.map((run) => (
              <tr key={run.run_id}>
                <td>{run.run_id.slice(0, 8)}...</td>
                <td>{run.ticker}</td>
                <td>{run.status}</td>
                <td>{run.created_at}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </main>
  );
}
