import { createContext, useContext, useEffect, useState } from "react";
import client from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    const raw = localStorage.getItem("user");
    return raw ? JSON.parse(raw) : null;
  });
  const [role, setRole] = useState(() => localStorage.getItem("role"));
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) {
      setLoading(false);
      return;
    }
    client
      .get("/auth/me")
      .then((res) => {
        setUser(res.data.user);
        setRole(res.data.role);
        localStorage.setItem("user", JSON.stringify(res.data.user));
        localStorage.setItem("role", res.data.role);
      })
      .catch(() => {
        localStorage.clear();
        setUser(null);
        setRole(null);
      })
      .finally(() => setLoading(false));
  }, []);

  async function login(email, password) {
    const res = await client.post("/auth/login", { email, password });
    persist(res.data);
    return res.data;
  }

  async function register(name, email, password, phone) {
    const res = await client.post("/auth/register", { name, email, password, phone });
    persist(res.data);
    return res.data;
  }

  function persist(data) {
    localStorage.setItem("token", data.token);
    localStorage.setItem("user", JSON.stringify(data.user));
    localStorage.setItem("role", data.user.role);
    setUser(data.user);
    setRole(data.user.role);
  }

  function logout() {
    localStorage.clear();
    setUser(null);
    setRole(null);
  }

  return (
    <AuthContext.Provider value={{ user, role, loading, login, register, logout, setUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
