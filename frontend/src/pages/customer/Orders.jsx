import { useEffect, useState } from "react";
import client from "../../api/client";
import StatusBadge from "../../components/StatusBadge";

export default function Orders() {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: "", qty: 1, price: "", address: "" });
  const [busyId, setBusyId] = useState(null);

  useEffect(() => {
    load();
  }, []);

  async function load() {
    setLoading(true);
    const res = await client.get("/orders");
    setOrders(res.data.orders);
    setLoading(false);
  }

  async function placeOrder(e) {
    e.preventDefault();
    setError("");
    try {
      await client.post("/orders", {
        items: [{ name: form.name, qty: Number(form.qty), price: Number(form.price) }],
        shipping_address: form.address,
      });
      setForm({ name: "", qty: 1, price: "", address: "" });
      setShowForm(false);
      load();
    } catch (err) {
      setError(err.response?.data?.error || "Could not place order.");
    }
  }

  async function cancelOrder(id) {
    setBusyId(id);
    setError("");
    try {
      await client.post(`/orders/${id}/cancel`, { reason: "Cancelled from dashboard" });
      load();
    } catch (err) {
      setError(err.response?.data?.error || "Could not cancel this order.");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Your orders</h1>
          <p className="text-sm text-slate">Track status and cancel orders within the eligible window.</p>
        </div>
        <button className="btn-primary" onClick={() => setShowForm((s) => !s)}>
          {showForm ? "Close" : "+ Place demo order"}
        </button>
      </div>

      {showForm && (
        <form onSubmit={placeOrder} className="card mb-6 grid grid-cols-4 gap-3 p-4">
          <input
            className="input"
            placeholder="Item name"
            required
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
          />
          <input
            className="input"
            type="number"
            min="1"
            placeholder="Qty"
            required
            value={form.qty}
            onChange={(e) => setForm({ ...form, qty: e.target.value })}
          />
          <input
            className="input"
            type="number"
            step="0.01"
            placeholder="Price"
            required
            value={form.price}
            onChange={(e) => setForm({ ...form, price: e.target.value })}
          />
          <input
            className="input"
            placeholder="Shipping address"
            value={form.address}
            onChange={(e) => setForm({ ...form, address: e.target.value })}
          />
          <button className="btn-primary col-span-4">Place order</button>
        </form>
      )}

      {error && <p className="mb-4 rounded bg-coral-light px-3 py-2 text-sm text-coral">{error}</p>}

      {loading ? (
        <p className="text-sm text-slate">Loading orders…</p>
      ) : orders.length === 0 ? (
        <p className="card p-6 text-center text-sm text-slate">No orders yet.</p>
      ) : (
        <div className="space-y-3">
          {orders.map((o) => (
            <div key={o.id} className="card flex items-center justify-between p-4">
              <div>
                <p className="font-mono text-sm font-medium">{o.order_number}</p>
                <p className="mt-0.5 text-xs text-slate">
                  {o.items.map((i) => `${i.qty}x ${i.name}`).join(", ")} · ${o.total_amount}
                </p>
                <p className="text-xs text-slate">Placed {new Date(o.created_at).toLocaleString()}</p>
              </div>
              <div className="flex items-center gap-3">
                <StatusBadge value={o.status} />
                {["placed", "processing", "confirmed"].includes(o.status) && (
                  <button
                    className="btn-danger text-xs"
                    onClick={() => cancelOrder(o.id)}
                    disabled={busyId === o.id}
                  >
                    {busyId === o.id ? "Cancelling…" : "Cancel"}
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
