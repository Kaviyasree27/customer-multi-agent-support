import { useEffect, useState } from "react";
import client from "../../api/client";

export default function AdminFaqs() {
  const [faqs, setFaqs] = useState([]);
  const [form, setForm] = useState({ question: "", answer: "", category: "general" });
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    load();
  }, []);

  async function load() {
    const res = await client.get("/admin/faqs");
    setFaqs(res.data.faqs);
  }

  async function add(e) {
    e.preventDefault();
    setBusy(true);
    try {
      await client.post("/admin/faqs", form);
      setForm({ question: "", answer: "", category: "general" });
      load();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <h1 className="mb-1 text-xl font-semibold">Knowledge base</h1>
      <p className="mb-6 text-sm text-slate">
        Articles here are retrieved live by the Query Agent's RAG pipeline to answer customer questions.
      </p>

      <form onSubmit={add} className="card mb-6 space-y-3 p-4">
        <input
          className="input"
          placeholder="Question"
          required
          value={form.question}
          onChange={(e) => setForm({ ...form, question: e.target.value })}
        />
        <textarea
          className="input"
          rows={3}
          placeholder="Answer"
          required
          value={form.answer}
          onChange={(e) => setForm({ ...form, answer: e.target.value })}
        />
        <input
          className="input"
          placeholder="Category"
          value={form.category}
          onChange={(e) => setForm({ ...form, category: e.target.value })}
        />
        <button className="btn-primary text-sm" disabled={busy}>
          {busy ? "Adding…" : "Add FAQ"}
        </button>
      </form>

      <div className="space-y-2">
        {faqs.map((f) => (
          <div key={f.id} className="card p-4">
            <p className="text-sm font-medium">{f.question}</p>
            <p className="mt-1 text-xs text-slate">{f.answer}</p>
            <span className="badge mt-2 bg-slate/10 text-slate">{f.category}</span>
          </div>
        ))}
        {faqs.length === 0 && <p className="card p-6 text-center text-sm text-slate">No FAQ articles yet.</p>}
      </div>
    </div>
  );
}
