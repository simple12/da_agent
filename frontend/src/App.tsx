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

type ApiErrorDetail = {
  error: string;
  message: string;
  options?: string[];
};

function parseApiError(data: unknown, fallback: string): ApiErrorDetail {
  if (data && typeof data === "object" && "detail" in data) {
    const detail = (data as { detail: unknown }).detail;
    if (detail && typeof detail === "object" && "error" in detail && "message" in detail) {
      return detail as ApiErrorDetail;
    }
    if (typeof detail === "string") {
      return { error: "ERROR", message: detail };
    }
  }
  return { error: "ERROR", message: fallback };
}

function formatErrorCode(code: string): string {
  return code.replace(/_/g, " ").toLowerCase();
}

function applyDimensionOption(question: string, option: string): string {
  const label = option.replace(/_/g, " ");
  if (/\bby\s+group\b/i.test(question)) {
    return question.replace(/\bby\s+group\b/i, `by ${label}`);
  }
  if (/\bby\s+\w+/i.test(question)) {
    return question.replace(/\bby\s+[\w\s]+/i, `by ${label}`);
  }
  return `${question.replace(/[?.!\s]+$/, "")} by ${label}?`;
}

export default function App() {
  const [question, setQuestion] = useState(EXAMPLES[0]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<ApiErrorDetail | null>(null);
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
        setError(parseApiError(data, res.statusText));
        return;
      }
      setResponse(data);
    } catch {
      setError({ error: "NETWORK_ERROR", message: "Request failed. Is the API running?" });
    } finally {
      setLoading(false);
    }
  }

  function chooseDimension(option: string) {
    setQuestion(applyDimensionOption(question, option));
    setError(null);
  }

  const columns =
    response?.results?.length &&
    Object.keys(response.results[0] as Record<string, unknown>);

  return (
    <>
      <h1>Healthcare Data Analyst Agent</h1>
      <p className="subtitle">Phase 2 — metadata-driven natural language to SQL to results</p>

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

      {error && (
        <div className="error-panel" role="alert">
          <div className="error-header">
            <span className="error-code">{formatErrorCode(error.error)}</span>
            <span className="error-message">{error.message}</span>
          </div>
          {error.options && error.options.length > 0 && (
            <div className="error-options">
              <p className="error-options-label">Choose a dimension:</p>
              <div className="error-option-buttons">
                {error.options.map((option) => (
                  <button
                    key={option}
                    type="button"
                    className="ghost"
                    onClick={() => chooseDimension(option)}
                  >
                    {option.replace(/_/g, " ")}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {response && (
        <>
          <div className="card">
            <label>Generated SQL</label>
            <pre>{response.sql}</pre>
          </div>
          <div className="card">
            <label>Results ({response.results.length} rows)</label>
            {response.results.length === 0 ? (
              <p className="muted">No rows returned.</p>
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
