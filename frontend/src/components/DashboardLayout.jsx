import { NavLink } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function DashboardLayout({ title, links, children }) {
  const { user, logout } = useAuth();

  return (
    <div className="flex h-screen overflow-hidden">
      <aside className="flex w-60 flex-shrink-0 flex-col border-r border-line bg-white">
        <div className="flex items-center gap-2 border-b border-line px-5 py-5">
          <div className="flex h-8 w-8 items-center justify-center rounded bg-ink font-mono text-sm text-paper">
            A
          </div>
          <div>
            <p className="text-sm font-semibold leading-none">Aria Support</p>
            <p className="mt-0.5 text-xs text-slate">{title}</p>
          </div>
        </div>

        <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4">
          {links.map((l) => (
            <NavLink
              key={l.to}
              to={l.to}
              end={l.end}
              className={({ isActive }) =>
                `flex items-center gap-2.5 rounded px-3 py-2 text-sm font-medium transition-colors ${
                  isActive ? "bg-teal-light text-teal-dark" : "text-slate hover:bg-paper hover:text-ink"
                }`
              }
            >
              <span className="text-base leading-none">{l.icon}</span>
              {l.label}
            </NavLink>
          ))}
        </nav>

        <div className="border-t border-line px-4 py-4">
          <p className="truncate text-sm font-medium">{user?.name}</p>
          <p className="truncate text-xs text-slate">{user?.email}</p>
          <button onClick={logout} className="btn-outline mt-3 w-full text-xs">
            Log out
          </button>
        </div>
      </aside>

      <main className="flex-1 overflow-y-auto bg-paper">
        <div className="mx-auto max-w-6xl px-6 py-8">{children}</div>
      </main>
    </div>
  );
}
