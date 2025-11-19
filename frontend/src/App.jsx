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
          {result.meta && (
            <details>
              <summary>Debug</summary>
              <pre>{JSON.stringify(result.meta, null, 2)}</pre>
            </details>
          )}
        </div>
      );
    }

    const sections = result.sections || [];
    const intent = result.meta?.intent;

    // Fallback / browse_subjects display
    if (intent === "browse_subjects") {
      return (
        <div className="card">
          <h2>Subjects (fallback)</h2>
          <ul>
            {result.subjects?.map((s) => (
              <li key={s.subject_code}>
                <strong>{s.subject_code}</strong> — {s.name || "(no name)"}
              </li>
            ))}
          </ul>
          <details>
            <summary>Debug meta</summary>
            <pre>{JSON.stringify(result.meta, null, 2)}</pre>
          </details>
        </div>
      );
    }

    // No sections found for a course_lookup
    if (intent === "course_lookup" && sections.length === 0) {
      return (
        <div className="card">
          <h2>No matching sections</h2>
          <p>Did not find that course / section in the sample data.</p>
          <details>
            <summary>Debug meta</summary>
            <pre>{JSON.stringify(result.meta, null, 2)}</pre>
          </details>
        </div>
      );
    }

    return (
      <div className="card">
        <h2>Sections ({sections.length})</h2>

        {sections.map((s) => {
          const grades = s.grades || {};
          const gpa =
            grades.gpa != null && !Number.isNaN(grades.gpa)
              ? Number(grades.gpa).toFixed(2)
              : "N/A";

          return (
            <div key={s.section_id} className="section-card">
              <h3>
                {s.course.subject_code} {s.course.course_number} —{" "}
                {s.course.title || "(no title)"}
              </h3>
              <p>
                <strong>Section ID:</strong> {s.section_id} |{" "}
                <strong>Course ID:</strong> {s.course_id}
              </p>
              <p>
                <strong>Term:</strong> {s.term.label} ({s.term.academic_year})
              </p>
              <p>
                <strong>Instructor:</strong> {s.instructor.name_display}
              </p>
              <p>
                <strong>Level:</strong> {s.course.level || "N/A"} |{" "}
                <strong>Credits:</strong> {s.course.credits ?? "N/A"}
              </p>
              <p>
                <strong>GPA:</strong> {gpa} |{" "}
                <strong>Graded enrollment:</strong>{" "}
                {grades.graded_enrollment ?? "N/A"} |{" "}
                <strong>Withdraws:</strong> {grades.withdraws ?? "N/A"}
              </p>
              <details>
                <summary>Grade breakdown</summary>
                <pre>{JSON.stringify(grades.breakdown || {}, null, 2)}</pre>
              </details>
            </div>
          );
        })}

        <details>
          <summary>Aggregates</summary>
          <pre>{JSON.stringify(result.aggregates, null, 2)}</pre>
        </details>

        <details>
          <summary>Meta / debug</summary>
          <pre>{JSON.stringify(result.meta, null, 2)}</pre>
        </details>
      </div>
    );
  };

  return (
    <div className="page">
      <header>
        <h1>VT Data Commons NLP Demo</h1>
        <p>
          Try: <code>CS 2104</code> or any random text.
        </p>
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
