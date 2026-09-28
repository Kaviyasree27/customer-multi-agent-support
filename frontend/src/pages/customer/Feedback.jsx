import { useEffect, useState } from "react";
import client from "../../api/client";

export default function Feedback() {
  const [rating, setRating] = useState(5);
  const [comment, setComment] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const [history, setHistory] = useState([]);

  useEffect(() => {
    load();
  }, []);

  async function load() {
    const res = await client.get("/feedback");
    setHistory(res.data.feedback);
  }

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setMsg("");
    try {
      await client.post("/feedback", { rating, comment });
      setComment("");
      setMsg("Thanks — your feedback was submitted.");
      load();
    } catch (err) {
      setMsg(err.response?.data?.error || "Could not submit feedback.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="max-w-lg">
      <h1 className="mb-6 text-xl font-semibold">Feedback</h1>

      <form onSubmit={submit} className="card mb-8 space-y-4 p-6">
        {msg && <p className="rounded bg-teal-light px-3 py-2 text-sm text-teal-dark">{msg}</p>}
        <div>
          <label className="mb-2 block text-sm font-medium">How was your experience?</label>
          <div className="flex gap-2">
            {[1, 2, 3, 4, 5].map((n) => (
              <button
                type="button"
                key={n}
                onClick={() => setRating(n)}
                className={`h-10 w-10 rounded border text-sm font-medium ${
                  rating === n ? "border-teal bg-teal-light text-teal-dark" : "border-line text-slate"
                }`}
              >
                {n}
              </button>
            ))}
          </div>
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium">Comment (optional)</label>
          <textarea className="input" rows={3} value={comment} onChange={(e) => setComment(e.target.value)} />
        </div>
        <button className="btn-primary" disabled={busy}>
          {busy ? "Submitting…" : "Submit feedback"}
        </button>
      </form>

      <h2 className="mb-2 text-sm font-semibold">Your past feedback</h2>
      <div className="space-y-2">
        {history.map((f) => (
          <div key={f.id} className="card p-3 text-sm">
            <p className="font-medium">{"★".repeat(f.rating)}{"☆".repeat(5 - f.rating)}</p>
            {f.comment && <p className="mt-1 text-xs text-slate">{f.comment}</p>}
          </div>
        ))}
        {history.length === 0 && <p className="card p-4 text-xs text-slate">No feedback submitted yet.</p>}
      </div>
    </div>
  );
}
