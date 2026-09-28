import { useEffect, useState } from "react";
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import client from "../../api/client";

const COLORS = ["#0E8A82", "#DE9B34", "#D5563F", "#5B6472", "#14171F", "#8FBFBB"];

export default function AdminHome() {
  const [data, setData] = useState(null);

  useEffect(() => {
    load();
    const id = setInterval(load, 15000);
    return () => clearInterval(id);
  }, []);

  async function load() {
    const res = await client.get("/admin/analytics");
    setData(res.data);
  }

  if (!data) return <p className="text-sm text-slate">Loading analytics…</p>;

  const t = data.totals;
  const toChart = (obj) => Object.entries(obj || {}).map(([name, count]) => ({ name, count }));

  return (
    <div>
      <h1 className="mb-1 text-xl font-semibold">Overview</h1>
      <p className="mb-6 text-sm text-slate">Live metrics computed from MongoDB. Refreshes every 15s.</p>

      <div className="mb-8 grid grid-cols-4 gap-4">
        <Stat label="Customers" value={t.customers} />
        <Stat label="Orders" value={t.orders} />
        <Stat label="Open tickets" value={t.open_tickets} accent="amber" />
        <Stat label="Escalated" value={t.escalated_tickets} accent="coral" />
        <Stat label="Conversations" value={t.conversations} />
        <Stat label="Revenue" value={`$${t.revenue}`} />
        <Stat label="Avg rating" value={t.avg_rating || "—"} />
        <Stat label="Feedback count" value={t.feedback_count} />
      </div>

      <div className="grid grid-cols-2 gap-6">
        <div className="card p-5">
          <h2 className="mb-3 text-sm font-semibold">Orders by status</h2>
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie data={toChart(data.orders_by_status)} dataKey="count" nameKey="name" outerRadius={80}>
                {toChart(data.orders_by_status).map((_, i) => (
                  <Cell key={i} fill={COLORS[i % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div className="card p-5">
          <h2 className="mb-3 text-sm font-semibold">Tickets by priority</h2>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={toChart(data.tickets_by_priority)}>
              <XAxis dataKey="name" fontSize={12} />
              <YAxis fontSize={12} allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="count" fill="#0E8A82" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="card p-5">
          <h2 className="mb-3 text-sm font-semibold">Tickets by category</h2>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={toChart(data.tickets_by_category)} layout="vertical">
              <XAxis type="number" fontSize={12} allowDecimals={false} />
              <YAxis type="category" dataKey="name" fontSize={11} width={110} />
              <Tooltip />
              <Bar dataKey="count" fill="#DE9B34" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="card p-5">
          <h2 className="mb-3 text-sm font-semibold">AI agent activity</h2>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={toChart(data.agent_activity)}>
              <XAxis dataKey="name" fontSize={11} />
              <YAxis fontSize={12} allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="count" fill="#14171F" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}

function Stat({ label, value, accent }) {
  const color = accent === "coral" ? "text-coral" : accent === "amber" ? "text-amber" : "text-ink";
  return (
    <div className="card p-4">
      <p className="text-xs text-slate">{label}</p>
      <p className={`mt-1 text-xl font-semibold ${color}`}>{value}</p>
    </div>
  );
}
