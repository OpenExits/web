import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

export interface PanelUser {
  id: number;
  handle: string;
  role: "user" | "moderator" | "admin";
  locale: string;
  terms_accepted: boolean;
  current_terms_version: string;
}

interface AuthState {
  user: PanelUser | null;
  ready: boolean;
  csrf: string | null;
  login: (email: string, password: string) => Promise<string | null>;
  register: (handle: string, email: string, password: string, locale: string) => Promise<string | null>;
  logout: () => Promise<void>;
  acceptTerms: () => Promise<boolean>;
  api: (path: string, init?: RequestInit) => Promise<Response>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<PanelUser | null>(null);
  const [csrf, setCsrf] = useState<string | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    fetch("/api/v1/auth/me")
      .then((r) => r.json())
      .then((body) => {
        setUser(body.user);
        setCsrf(body.csrf ?? null);
      })
      .catch(() => undefined)
      .finally(() => setReady(true));
  }, []);

  const api = useCallback(
    (path: string, init: RequestInit = {}) => {
      const headers = new Headers(init.headers);
      if (csrf) headers.set("X-CSRF-Token", csrf);
      if (init.body && typeof init.body === "string") {
        headers.set("Content-Type", "application/json");
      }
      return fetch(path, { ...init, headers });
    },
    [csrf],
  );

  const login = useCallback(async (email: string, password: string) => {
    const r = await fetch("/api/v1/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    const body = await r.json();
    if (!r.ok) return (body.error as string) ?? "auth.failed";
    setUser(body.user);
    setCsrf(body.csrf);
    return null;
  }, []);

  const register = useCallback(
    async (handle: string, email: string, password: string, locale: string) => {
      const r = await fetch("/api/v1/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ handle, email, password, locale }),
      });
      const body = await r.json();
      if (!r.ok) {
        const fields = body.fields as Record<string, string> | undefined;
        return fields ? Object.values(fields)[0] : ((body.error as string) ?? "auth.failed");
      }
      setUser(body.user);
      setCsrf(body.csrf);
      return null;
    },
    [],
  );

  const logout = useCallback(async () => {
    await api("/api/v1/auth/logout", { method: "POST" });
    setUser(null);
    setCsrf(null);
  }, [api]);

  const acceptTerms = useCallback(async () => {
    if (!user) return false;
    const r = await api("/api/v1/terms/accept", {
      method: "POST",
      body: JSON.stringify({ terms_version: user.current_terms_version }),
    });
    if (r.ok) setUser({ ...user, terms_accepted: true });
    return r.ok;
  }, [api, user]);

  const value = useMemo(
    () => ({ user, ready, csrf, login, register, logout, acceptTerms, api }),
    [user, ready, csrf, login, register, logout, acceptTerms, api],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth outside AuthProvider");
  return ctx;
}
