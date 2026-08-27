import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { useAuth } from "../../lib/auth";

const label = "text-sm font-semibold";
const input =
  "rounded border border-line bg-white px-3.5 py-2.5 text-[15px] outline-none focus:border-ink";

export default function AuthPage() {
  const { login, register } = useAuth();
  const { i18n } = useTranslation();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [handle, setHandle] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const err =
      mode === "login"
        ? await login(email, password)
        : await register(handle, email, password, i18n.language);
    setBusy(false);
    if (err) setError(err);
  }

  const fr = i18n.language === "fr";
  return (
    <div className="mx-auto flex max-w-md flex-col gap-6 px-6 py-16">
      <div className="flex overflow-hidden rounded border border-line text-sm font-semibold">
        <button
          type="button"
          onClick={() => setMode("login")}
          className={mode === "login" ? "flex-1 bg-ink py-2.5 text-paper" : "flex-1 py-2.5 text-muted"}
        >
          {fr ? "Connexion" : "Sign in"}
        </button>
        <button
          type="button"
          onClick={() => setMode("register")}
          className={mode === "register" ? "flex-1 bg-ink py-2.5 text-paper" : "flex-1 py-2.5 text-muted"}
        >
          {fr ? "Créer un compte" : "Create account"}
        </button>
      </div>
      <form onSubmit={submit} className="flex flex-col gap-4">
        {mode === "register" && (
          <label className="flex flex-col gap-1.5">
            <span className={label}>{fr ? "Pseudo public" : "Public handle"}</span>
            <input
              className={input}
              value={handle}
              onChange={(e) => setHandle(e.target.value)}
              autoComplete="username"
              required
            />
            <span className="text-xs text-faint">
              {fr
                ? "Visible publiquement sur vos contributions, pour toujours — choisissez un pseudonyme."
                : "Publicly visible on your contributions, forever — pick a pseudonym."}
            </span>
          </label>
        )}
        <label className="flex flex-col gap-1.5">
          <span className={label}>Email</span>
          <input
            className={input}
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="email"
            required
          />
          {mode === "register" && (
            <span className="text-xs text-faint">
              {fr ? "Privé — jamais publié." : "Private — never published."}
            </span>
          )}
        </label>
        <label className="flex flex-col gap-1.5">
          <span className={label}>{fr ? "Mot de passe" : "Password"}</span>
          <input
            className={input}
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete={mode === "login" ? "current-password" : "new-password"}
            minLength={10}
            required
          />
        </label>
        {error && <p className="text-sm font-semibold text-[#8f231d]">{error}</p>}
        <button
          type="submit"
          disabled={busy}
          className="mt-1 rounded bg-signal py-3 font-bold text-white disabled:opacity-60"
        >
          {mode === "login" ? (fr ? "Connexion" : "Sign in") : fr ? "Créer le compte" : "Create account"}
        </button>
      </form>
    </div>
  );
}
