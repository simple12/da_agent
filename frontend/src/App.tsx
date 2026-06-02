import { FormEvent, useState } from "react";

const API_BASE = import.meta.env.VITE_API_URL ?? "";

const EXAMPLES = [
  "What is PMPM for Alameda County?",
  "Show PMPM by county.",
  "Show PMPM by age group.",
  "What are outstanding claims by provider?",
  "How many claims are pending payment?",
  "What is PMPM for Alameda County and stratify by age group?",
];

type AskResponse = {
  question: string;
  sql: string;
  results: Record<string, unknown>[];
};

export default function App() {
  const [question, setQuestion] = useState(EXAMPLES[0]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState<AskResponse | null>(null);

  async function submit(e?: FormEvent) {
    e?.preventDefault();
    setLoading(true);
    setError(null);
    setResponse(null);
    try {
      const res = await fetch(`${API_BASE}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: question.trim() }),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail ?? res.statusText);
      }
      setResponse(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setLoading(false);
    }
  }

  const columns =
    response?.results?.length &&
    Object.keys(response.results[0] as Record<string, unknown>);

  return (
    <>
      <h1>Healthcare Data Analyst Agent</h1>
      <p className="subtitle">Phase 1 MVP — natural language to SQL to results</p>

      <form className="card" onSubmit={submit}>
        <label htmlFor="question">Your question</label>
        <textarea
          id="question"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="e.g. What is PMPM for Alameda County?"
        />
        <div className="examples">
          {EXAMPLES.map((ex) => (
            <button
              key={ex}
              type="button"
              className="ghost"
              onClick={() => setQuestion(ex)}
            >
              {ex.length > 42 ? ex.slice(0, 40) + "…" : ex}
            </button>
          ))}
        </div>
        <div className="actions">
          <button type="submit" className="primary" disabled={loading || !question.trim()}>
            {loading ? "Running…" : "Ask"}
          </button>
        </div>
      </form>

      {error && <div className="error">{error}</div>}

      {response && (
        <>
          <div className="card">
            <label>Generated SQL</label>
            <pre>{response.sql}</pre>
          </div>
          <div className="card">
            <label>Results ({response.results.length} rows)</label>
            {response.results.length === 0 ? (
              <p style={{ margin: 0, color: "#64748b" }}>No rows returned.</p>
            ) : (
              <table>
                <thead>
                  <tr>
                    {columns?.map((col) => (
                      <th key={col}>{col}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {response.results.map((row, i) => (
                    <tr key={i}>
                      {columns?.map((col) => (
                        <td key={col}>{String(row[col] ?? "")}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </>
      )}
    </>
  );
}
