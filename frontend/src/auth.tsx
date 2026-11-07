import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { api, tokenStore } from "./api";
import type { User } from "./types";

interface Ctx { user: User | null; loading: boolean; login: (e: string, p: string) => Promise<void>; register: (n: string, e: string, p: string) => Promise<void>; logout: () => void }
const AuthCtx = createContext<Ctx>(null as unknown as Ctx);
export const useAuth = () => useContext(AuthCtx);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(!!tokenStore.get());

  const logout = useCallback(() => { tokenStore.clear(); setUser(null); }, []);

  useEffect(() => {
    if (tokenStore.get()) api.get<User>("/api/auth/me").then(setUser).catch(logout).finally(() => setLoading(false));
    window.addEventListener("mm-logout", logout);
    return () => window.removeEventListener("mm-logout", logout);
  }, [logout]);

  const done = (r: { access_token: string; user: User }) => { tokenStore.set(r.access_token); setUser(r.user); };
  const login = async (email: string, password: string) => done(await api.post("/api/auth/login", { email, password }));
  const register = async (name: string, email: string, password: string) => done(await api.post("/api/auth/register", { name, email, password }));

  return <AuthCtx.Provider value={{ user, loading, login, register, logout }}>{children}</AuthCtx.Provider>;
}
