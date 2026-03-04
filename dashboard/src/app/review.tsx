import { useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function ReviewPage() {
  const [content, setContent] = useState("");
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const submitReview = async () => {
    if (!content) {
      setError("Please enter content to review.");
      return;
    }

    setLoading(true);
    setError("");
    setResult(null);

    try {
      const res = await fetch(`${API_URL}/review`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content }),
      });

      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.detail || body?.error || `Request failed (${res.status})`);
      }

      const data = await res.json();
      setResult(data);
    } catch (err: any) {
      setError(err?.message || "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: "2rem" }}>
      <h1 style={{ fontSize: "1.5rem", marginBottom: "1rem" }}>AI Review</h1>

      <textarea
        rows={8}
        style={{ width: "100%", padding: "0.5rem", borderRadius: 6 }}
        placeholder="Paste text or code here..."
        value={content}
        onChange={(e) => setContent(e.target.value)}
      />

      <br />
      <br />

      <button onClick={submitReview} disabled={loading} style={{ padding: "0.5rem 1rem" }}>
        {loading ? "Reviewing..." : "Submit Review"}
      </button>

      {error && <p style={{ color: "red" }}>{error}</p>}

      {result && (
        <div style={{ marginTop: "2rem" }}>
          <h3>Summary</h3>
          <p>{result.summary}</p>

          <h3>Strengths</h3>
          <ul>{result.strengths?.map((s: string, i: number) => <li key={i}>{s}</li>)}</ul>

          <h3>Weaknesses</h3>
          <ul>{result.weaknesses?.map((w: string, i: number) => <li key={i}>{w}</li>)}</ul>

          <h3>Suggestions</h3>
          <ul>{result.suggestions?.map((s: string, i: number) => <li key={i}>{s}</li>)}</ul>
        </div>
      )}
    </div>
  );
}


