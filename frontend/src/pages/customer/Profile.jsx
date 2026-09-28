import { useState } from "react";
import client from "../../api/client";
import { useAuth } from "../../context/AuthContext";

export default function Profile() {
  const { user, setUser } = useAuth();
  const [form, setForm] = useState({
    name: user?.name || "",
    phone: user?.phone || "",
    address: user?.address || "",
    password: "",
  });
  const [msg, setMsg] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function onSubmit(e) {
    e.preventDefault();
    setMsg("");
    setError("");
    setBusy(true);
    try {
      const payload = { name: form.name, phone: form.phone, address: form.address };
      if (form.password) payload.password = form.password;
      const res = await client.put("/profile", payload);
      setUser(res.data.user);
      localStorage.setItem("user", JSON.stringify(res.data.user));
      setForm((f) => ({ ...f, password: "" }));
      setMsg("Profile updated.");
    } catch (err) {
      setError(err.response?.data?.error || "Could not update profile.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="max-w-lg">
      <h1 className="mb-6 text-xl font-semibold">Your profile</h1>
      <form onSubmit={onSubmit} className="card space-y-4 p-6">
        {msg && <p className="rounded bg-teal-light px-3 py-2 text-sm text-teal-dark">{msg}</p>}
        {error && <p className="rounded bg-coral-light px-3 py-2 text-sm text-coral">{error}</p>}

        <div>
          <label className="mb-1 block text-sm font-medium">Email</label>
          <input className="input bg-paper" value={user?.email} disabled />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium">Full name</label>
          <input className="input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium">Phone</label>
          <input className="input" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium">Address</label>
          <input
            className="input"
            value={form.address}
            onChange={(e) => setForm({ ...form, address: e.target.value })}
          />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium">New password (optional)</label>
          <input
            className="input"
            type="password"
            placeholder="Leave blank to keep current password"
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
          />
        </div>
        <button className="btn-primary" disabled={busy}>
          {busy ? "Saving…" : "Save changes"}
        </button>
      </form>
    </div>
  );
}
