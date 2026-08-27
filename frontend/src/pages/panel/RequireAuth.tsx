import type { ReactNode } from "react";
import { useAuth } from "../../lib/auth";
import AuthPage from "./Auth";

export default function RequireAuth({ children }: { children: ReactNode }) {
  const { user, ready } = useAuth();
  if (!ready) return <div className="p-16 text-center text-muted">…</div>;
  if (!user) return <AuthPage />;
  return <>{children}</>;
}
