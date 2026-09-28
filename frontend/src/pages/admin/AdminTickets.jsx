import { useEffect, useState } from "react";
import client from "../../api/client";
import StatusBadge from "../../components/StatusBadge";

const STATUSES = ["open", "in_progress", "resolved", "closed", "escalated"];

export default function AdminTickets() {
  const [tickets, setTickets] = useState([]);
  const [filter, setFilter] = useState({ status: "", escalatedOnly: false });
  const [expanded, setExpanded] = useState(null);
  const [resolution, setResolution] = useState("");

  useEffect(() => {
    load();
  }, [filter]);

  async function load() {
    const params = {};
    if (filter.status) params.status = filter.status;
    if (filter.escalatedOnly) params.escalated = "true";
    const res = await client.get("/admin/tickets", { params });
    setTickets(res.data.tickets);
  }

  async function setStatus(id, status) {
    await client.put(`/admin/tickets/${id}/status`, { status });
    load();
  }

  async function resolve(id) {
    if (!resolution.trim()) return;
    await client.put(`/admin/tickets/${id}/resolve`, { resolution });
    setResolution("");
    setExpanded(null);
    load();
  }

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Tickets & escalations</h1>
          <p className="text-sm text-slate">{tickets.length} tickets shown.</p>
        </div>
        <label className="flex items-center gap-2 text-xs text-slate">
          <input
            type="checkbox"
            checked={filter.escalatedOnly}
            onChange={(e) => setFilter((f) => ({ ...f, escalatedOnly: e.target.checked }))}
          />
          Escalated only
        </label>
      </div>

      <div className="mb-4 flex gap-2">
        <button
          onClick={() => setFilter((f) => ({ ...f, status: "" }))}
          className={`btn-outline text-xs ${filter.status === "" ? "border-ink" : ""}`}
        >
          All
        </button>
        {STATUSES.map((s) => (
          <button
            key={s}
            onClick={() => setFilter((f) => ({ ...f, status: s }))}
            className={`btn-outline text-xs capitalize ${filter.status === s ? "border-ink" : ""}`}
          >
            {s.replace("_", " ")}
          </button>
        ))}
      </div>

      <div className="space-y-3">
        {tickets.map((t) => (
          <div key={t.id} className="card p-4">
            <div className="flex items-start justify-between">
              <div className="min-w-0 pr-3">
                <p className="font-mono text-xs text-slate">{t.ticket_number}</p>
                <p className="text-sm font-medium">{t.subject}</p>
                <p className="mt-1 text-xs text-slate">{t.description}</p>
                {t.escalated && (
                  <p className="mt-1 text-xs font-medium text-coral">⚠ Escalated: {t.escalation_reason}</p>
                )}
              </div>
              <div className="flex flex-shrink-0 flex-col items-end gap-1.5">
                <StatusBadge value={t.status} />
                <StatusBadge value={t.priority} />
              </div>
            </div>

            <div className="mt-3 flex items-center gap-2">
              <select
                className="input w-auto text-xs"
                value={t.status}
                onChange={(e) => setStatus(t.id, e.target.value)}
              >
                {STATUSES.map((s) => (
                  <option key={s} value={s}>
                    {s.replace("_", " ")}
                  </option>
                ))}
              </select>
              <button
                className="btn-outline text-xs"
                onClick={() => setExpanded(expanded === t.id ? null : t.id)}
              >
                {expanded === t.id ? "Cancel" : "Resolve with note"}
              </button>
            </div>

            {expanded === t.id && (
              <div className="mt-3 flex gap-2">
                <input
                  className="input"
                  placeholder="Resolution note…"
                  value={resolution}
                  onChange={(e) => setResolution(e.target.value)}
                />
                <button className="btn-primary text-xs" onClick={() => resolve(t.id)}>
                  Save
                </button>
              </div>
            )}
          </div>
        ))}
        {tickets.length === 0 && <p className="card p-6 text-center text-sm text-slate">No tickets found.</p>}
      </div>
    </div>
  );
}
