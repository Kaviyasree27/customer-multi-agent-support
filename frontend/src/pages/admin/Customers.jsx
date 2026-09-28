import { useEffect, useState } from "react";
import client from "../../api/client";
import StatusBadge from "../../components/StatusBadge";

export default function Customers() {
  const [customers, setCustomers] = useState([]);
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState(null);
  const [detail, setDetail] = useState(null);

  useEffect(() => {
    load();
  }, [search]);

  async function load() {
    const res = await client.get("/admin/customers", { params: search ? { search } : {} });
    setCustomers(res.data.customers);
  }

  async function openCustomer(c) {
    setSelected(c);
    const res = await client.get(`/admin/customers/${c.id}`);
    setDetail(res.data);
  }

  return (
    <div>
      <h1 className="mb-1 text-xl font-semibold">Customers</h1>
      <p className="mb-6 text-sm text-slate">{customers.length} registered customers.</p>

      <input
        className="input mb-4 max-w-sm"
        placeholder="Search by name or email…"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
      />

      <div className="grid grid-cols-5 gap-6">
        <div className="col-span-2 space-y-2">
          {customers.map((c) => (
            <button
              key={c.id}
              onClick={() => openCustomer(c)}
              className={`card block w-full p-3 text-left ${selected?.id === c.id ? "border-teal" : ""}`}
            >
              <p className="text-sm font-medium">{c.name}</p>
              <p className="text-xs text-slate">{c.email}</p>
            </button>
          ))}
          {customers.length === 0 && <p className="card p-4 text-xs text-slate">No customers found.</p>}
        </div>

        <div className="col-span-3">
          {!detail ? (
            <p className="card p-6 text-center text-sm text-slate">Select a customer to view details.</p>
          ) : (
            <div className="space-y-4">
              <div className="card p-4">
                <p className="text-sm font-semibold">{detail.customer.name}</p>
                <p className="text-xs text-slate">{detail.customer.email} · {detail.customer.phone || "no phone"}</p>
              </div>

              <div className="card p-4">
                <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate">
                  Orders ({detail.orders.length})
                </h3>
                <div className="space-y-1.5">
                  {detail.orders.map((o) => (
                    <div key={o.id} className="flex items-center justify-between text-sm">
                      <span className="font-mono text-xs">{o.order_number}</span>
                      <StatusBadge value={o.status} />
                    </div>
                  ))}
                  {detail.orders.length === 0 && <p className="text-xs text-slate">No orders.</p>}
                </div>
              </div>

              <div className="card p-4">
                <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate">
                  Tickets ({detail.tickets.length})
                </h3>
                <div className="space-y-1.5">
                  {detail.tickets.map((t) => (
                    <div key={t.id} className="flex items-center justify-between text-sm">
                      <span className="truncate pr-2">{t.subject}</span>
                      <StatusBadge value={t.status} />
                    </div>
                  ))}
                  {detail.tickets.length === 0 && <p className="text-xs text-slate">No tickets.</p>}
                </div>
              </div>

              <div className="card p-4">
                <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate">
                  Conversations ({detail.conversations.length})
                </h3>
                <div className="space-y-1.5">
                  {detail.conversations.map((c) => (
                    <div key={c.id} className="flex items-center justify-between text-sm">
                      <span className="text-xs text-slate">{c.last_intent || "—"}</span>
                      <StatusBadge value={c.status} />
                    </div>
                  ))}
                  {detail.conversations.length === 0 && <p className="text-xs text-slate">No conversations.</p>}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
