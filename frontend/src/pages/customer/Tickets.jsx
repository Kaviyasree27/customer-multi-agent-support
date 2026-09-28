import { useEffect, useState } from "react";
import client from "../../api/client";
import StatusBadge from "../../components/StatusBadge";

export default function Tickets() {
  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ subject: "", description: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    load();
  }, []);

  async function load() {
    setLoading(true);
    const res = await client.get("/tickets");
    setTickets(res.data.tickets);
    setLoading(false);
  }

  async function submitTicket(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await client.post("/tickets", form);
      setForm({ subject: "", description: "" });
      setShowForm(false);
      load();
    } catch (err) {
      setError(err.response?.data?.error || "Could not create ticket.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Complaints & tickets</h1>
          <p className="text-sm text-slate">
            The AI Complaint Agent categorizes and prioritizes every ticket automatically.
          </p>
        </div>
        <button className="btn-primary" onClick={() => setShowForm((s) => !s)}>
          {showForm ? "Close" : "+ Raise a complaint"}
        </button>
      </div>

      {showForm && (
        <form onSubmit={submitTicket} className="card mb-6 space-y-3 p-4">
          {error && <p className="rounded bg-coral-light px-3 py-2 text-sm text-coral">{error}</p>}
          <input
            className="input"
            placeholder="Subject"
            required
            value={form.subject}
            onChange={(e) => setForm({ ...form, subject: e.target.value })}
          />
          <textarea
            className="input"
            rows={4}
            placeholder="Describe the issue…"
            required
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
          />
          <button className="btn-primary" disabled={busy}>
            {busy ? "Submitting…" : "Submit complaint"}
          </button>
        </form>
      )}

      {loading ? (
        <p className="text-sm text-slate">Loading tickets…</p>
      ) : tickets.length === 0 ? (
        <p className="card p-6 text-center text-sm text-slate">No tickets yet.</p>
      ) : (
        <div className="space-y-3">
          {tickets.map((t) => (
            <div key={t.id} className="card p-4">
              <div className="flex items-start justify-between">
                <div>
                  <p className="font-mono text-sm font-medium">{t.ticket_number}</p>
                  <p className="mt-0.5 text-sm font-medium">{t.subject}</p>
                  <p className="mt-1 text-xs text-slate">{t.description}</p>
                </div>
                <div className="flex flex-shrink-0 flex-col items-end gap-1.5">
                  <StatusBadge value={t.status} />
                  <StatusBadge value={t.priority} />
                </div>
              </div>
              {t.resolution && (
                <p className="mt-3 rounded bg-teal-light px-3 py-2 text-xs text-teal-dark">
                  Resolution: {t.resolution}
                </p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
