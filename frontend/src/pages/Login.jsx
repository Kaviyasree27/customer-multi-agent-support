import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function onSubmit(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const data = await login(email, password);
      navigate(data.user.role === "admin" ? "/admin" : "/", { replace: true });
    } catch (err) {
      setError(err.response?.data?.error || "Login failed. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-paper px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <div className="mx-auto mb-3 flex h-10 w-10 items-center justify-center rounded bg-ink font-mono text-paper">
            A
          </div>
          <h1 className="text-xl font-semibold">Sign in to Aria Support</h1>
          <p className="mt-1 text-sm text-slate">Customer and admin accounts both sign in here.</p>
        </div>

        <form onSubmit={onSubmit} className="card space-y-4 p-6">
          {error && <p className="rounded bg-coral-light px-3 py-2 text-sm text-coral">{error}</p>}
          <div>
            <label className="mb-1 block text-sm font-medium">Email</label>
            <input className="input" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">Password</label>
            <input
              className="input"
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
          <button className="btn-primary w-full" disabled={busy}>
            {busy ? "Signing in…" : "Sign in"}
          </button>
        </form>

        <p className="mt-5 text-center text-sm text-slate">
          New here?{" "}
          <Link to="/register" className="font-medium text-teal-dark">
            Create an account
          </Link>
        </p>
      </div>
    </div>
  );
}
