import { useState } from "react";

function App() {
  const [input, setInput] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;

    setLoading(true);
    setResult(null);

    try {
      const res = await fetch("http://localhost:8000/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: input }),
      });
      const data = await res.json();
      setResult(data);
    } catch (err) {
      setResult({ ok: false, error: String(err) });
    } finally {
      setLoading(false);
    }
  };

  const renderBody = () => {
    if (!result) return null;

    if (!result.ok) {
      return (
        <div className="card error">
          <h2>Error</h2>
          <p>{result.error}</p>
        </div>
      );
    }

    if (result.mode === "course_lookup") {
      const matches = result.course_matches || [];
      if (matches.length === 0) {
        return (
          <div className="card">
            <h2>No matches</h2>
            <p>Did not find that course / section in the sample data.</p>
          </div>
        );
      }

      const m = matches[0];
      const gpa = (m.gpa / 10).toFixed(2);

      return (
        <div className="card">
          <h2>
            {m.subject_code} {m.course_number} — {m.title}
          </h2>
          <p>
            Term: <strong>{m.term_label}</strong>
          </p>
          <p>
            Instructor: <strong>{m.instructor}</strong>
          </p>
          <p>
            GPA: <strong>{gpa}</strong> (graded enrollment {m.graded_enrollment})
          </p>

          <details>
            <summary>Full grade distribution</summary>
            <pre>{JSON.stringify(m, null, 2)}</pre>
          </details>

          <details>
            <summary>Debug tokens</summary>
            <pre>{JSON.stringify(result.debug, null, 2)}</pre>
          </details>
        </div>
      );
    }

    if (result.mode === "subjects") {
      return (
        <div className="card">
          <h2>Subjects (fallback demo)</h2>
          <ul>
            {result.subjects?.map((s) => (
              <li key={s.subject_code}>
                <strong>{s.subject_code}</strong> — {s.name || "(no name)"}
              </li>
            ))}
          </ul>
          <details>
            <summary>Debug tokens</summary>
            <pre>{JSON.stringify(result.tokens, null, 2)}</pre>
          </details>
        </div>
      );
    }

    return (
      <div className="card">
        <h2>Raw response</h2>
        <pre>{JSON.stringify(result, null, 2)}</pre>
      </div>
    );
  };

  return (
    <div className="page">
      <header>
        <h1>VT Data Commons NLP Demo</h1>
        <p>Try: <code>CS 2104</code> or any random text.</p>
      </header>

      <form onSubmit={handleSubmit} className="form">
        <input
          className="text-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about a course, e.g. 'Show me CS 2104'"
        />
        <button type="submit" disabled={loading}>
          {loading ? "Querying..." : "Run query"}
        </button>
      </form>

      {renderBody()}
    </div>
  );
}

export default App;
