import { useState } from "react";
import "./App.css";

function App() {
  const [file, setFile] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleUpload(event) {
    event.preventDefault();

    if (!file) return;

    setLoading(true);
    setError("");
    setResult(null);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch(
        "http://localhost:8000/api/documents/upload",
        {
          method: "POST",
          body: formData,
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Upload failed");
      }

      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="container">
      <h1>Living Study Guide</h1>
      <p>Upload your lecture notes to begin studying.</p>

      <form onSubmit={handleUpload}>
        <input
          type="file"
          accept=".pdf,application/pdf"
          onChange={(event) => {
            setFile(event.target.files[0] || null);
            setResult(null);
            setError("");
          }}
        />

        <button disabled={!file || loading}>
          {loading ? "Processing..." : "Upload PDF"}
        </button>
      </form>

      {error && <p role="alert">{error}</p>}

      {result && (
        <section>
          <h2>{result.filename}</h2>
          <p>Total pages: {result.total_pages}</p>

          {result.pages.map((page) => (
            <article key={page.page_number}>
              <h3>Page {page.page_number}</h3>
              <pre>{page.text || "No extractable text"}</pre>
            </article>
          ))}
        </section>
      )}
    </main>
  );
}

export default App;