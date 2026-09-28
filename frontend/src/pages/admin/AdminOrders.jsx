import { useEffect, useState } from "react";
import client from "../../api/client";
import StatusBadge from "../../components/StatusBadge";

const STATUSES = ["placed", "processing", "confirmed", "shipped", "delivered", "cancelled"];

export default function AdminOrders() {
  const [orders, setOrders] = useState([]);
  const [filter, setFilter] = useState("");

  useEffect(() => {
    load();
  }, [filter]);

  async function load() {
    const res = await client.get("/admin/orders", { params: filter ? { status: filter } : {} });
    setOrders(res.data.orders);
  }

  async function setStatus(id, status) {
    await client.put(`/admin/orders/${id}/status`, { status });
    load();
  }

  return (
    <div>
      <h1 className="mb-1 text-xl font-semibold">Orders</h1>
      <p className="mb-6 text-sm text-slate">{orders.length} orders shown.</p>

      <div className="mb-4 flex gap-2">
        <button
          onClick={() => setFilter("")}
          className={`btn-outline text-xs ${filter === "" ? "border-ink" : ""}`}
        >
          All
        </button>
        {STATUSES.map((s) => (
          <button
            key={s}
            onClick={() => setFilter(s)}
            className={`btn-outline text-xs capitalize ${filter === s ? "border-ink" : ""}`}
          >
            {s}
          </button>
        ))}
      </div>

      <div className="space-y-2">
        {orders.map((o) => (
          <div key={o.id} className="card flex items-center justify-between p-4">
            <div>
              <p className="font-mono text-sm font-medium">{o.order_number}</p>
              <p className="text-xs text-slate">
                {o.items.map((i) => `${i.qty}x ${i.name}`).join(", ")} · ${o.total_amount}
              </p>
            </div>
            <div className="flex items-center gap-3">
              <StatusBadge value={o.status} />
              <select
                className="input w-auto text-xs"
                value={o.status}
                onChange={(e) => setStatus(o.id, e.target.value)}
              >
                {STATUSES.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </div>
          </div>
        ))}
        {orders.length === 0 && <p className="card p-6 text-center text-sm text-slate">No orders found.</p>}
      </div>
    </div>
  );
}
