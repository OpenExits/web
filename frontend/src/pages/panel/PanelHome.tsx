import { Link } from "react-router";
import { useTranslation } from "react-i18next";
import { useAuth } from "../../lib/auth";
import AuthPage from "./Auth";

export default function PanelHome() {
  const { t } = useTranslation(["common", "moderation"]);
  const { user, ready, logout } = useAuth();

  if (!ready) return <div className="p-16 text-center text-muted">…</div>;
  if (!user) return <AuthPage />;

  return (
    <div className="mx-auto flex w-full max-w-md flex-col gap-4 px-6 py-16">
      <h1 className="font-display text-3xl">{t("panelHome.title")}</h1>
      <p className="font-mono text-sm text-muted">@{user.handle}</p>
      <Link to="/panel/wizard" className="rounded bg-signal py-3.5 text-center font-bold text-white">
        {t("panelHome.addExit")}
      </Link>
      <Link
        to="/panel/submissions"
        className="rounded border-[1.5px] border-ink py-3.5 text-center font-semibold"
      >
        {t("panelHome.mySubmissions")}
      </Link>
      {user.role !== "user" && (
        <Link
          to="/panel/moderation"
          className="rounded border-[1.5px] border-ink py-3.5 text-center font-semibold"
        >
          {t("moderation:title")}
        </Link>
      )}
      <button type="button" onClick={logout} className="mt-4 self-start text-sm font-semibold text-muted">
        {t("panelHome.signOut")}
      </button>
    </div>
  );
}
