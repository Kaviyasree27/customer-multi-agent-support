import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import client from "../../api/client";
import StatusBadge from "../../components/StatusBadge";
import { useAuth } from "../../context/AuthContext";

export default function Home() {
  const { user } = useAuth();
  const [orders, setOrders] = useState([]);
  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([client.get("/orders"), client.get("/tickets")]).then(([o, t]) => {
      setOrders(o.data.orders);
      setTickets(t.data.tickets);
      setLoading(false);
    });
  }, []);

  const openTickets = tickets.filter((t) => !["resolved", "closed"].includes(t.status));
  const activeOrders = orders.filter((o) => !["delivered", "cancelled"].includes(o.status));

  return (
    <div>
      <h1 className="text-xl font-semibold">Welcome back, {user?.name?.split(" ")[0]}</h1>
      <p className="mb-6 text-sm text-slate">Here's what's happening with your account.</p>

      <div className="mb-8 grid grid-cols-3 gap-4">
        <div className="card p-5">
          <p className="text-xs text-slate">Total orders</p>
          <p className="mt-1 text-2xl font-semibold">{loading ? "…" : orders.length}</p>
          <p className="mt-1 text-xs text-slate">{activeOrders.length} active</p>
        </div>
        <div className="card p-5">
          <p className="text-xs text-slate">Open tickets</p>
          <p className="mt-1 text-2xl font-semibold">{loading ? "…" : openTickets.length}</p>
          <p className="mt-1 text-xs text-slate">{tickets.length} total</p>
        </div>
        <div className="card p-5">
          <p className="text-xs text-slate">Need help?</p>
          <Link to="/chat" className="btn-primary mt-2 inline-flex text-xs">
            Open AI chat
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-6">
        <div>
          <div className="mb-2 flex items-center justify-between">
            <h2 className="text-sm font-semibold">Recent orders</h2>
            <Link to="/orders" className="text-xs text-teal-dark">
              View all
            </Link>
          </div>
          <div className="space-y-2">
            {orders.slice(0, 4).map((o) => (
              <div key={o.id} className="card flex items-center justify-between p-3">
                <div>
                  <p className="font-mono text-xs font-medium">{o.order_number}</p>
                  <p className="text-xs text-slate">${o.total_amount}</p>
                </div>
                <StatusBadge value={o.status} />
              </div>
            ))}
            {!loading && orders.length === 0 && <p className="card p-4 text-xs text-slate">No orders yet.</p>}
          </div>
        </div>

        <div>
          <div className="mb-2 flex items-center justify-between">
            <h2 className="text-sm font-semibold">Recent tickets</h2>
            <Link to="/tickets" className="text-xs text-teal-dark">
              View all
            </Link>
          </div>
          <div className="space-y-2">
            {tickets.slice(0, 4).map((t) => (
              <div key={t.id} className="card flex items-center justify-between p-3">
                <div className="truncate pr-2">
                  <p className="truncate text-xs font-medium">{t.subject}</p>
                  <p className="font-mono text-xs text-slate">{t.ticket_number}</p>
                </div>
                <StatusBadge value={t.status} />
              </div>
            ))}
            {!loading && tickets.length === 0 && <p className="card p-4 text-xs text-slate">No tickets yet.</p>}
          </div>
        </div>
      </div>
    </div>
  );
}
