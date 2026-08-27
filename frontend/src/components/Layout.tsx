import { Link, Outlet } from "react-router";
import { useTranslation } from "react-i18next";
import { setLocale, SUPPORTED_LOCALES, type Locale } from "../i18n";

function Logo({ dark = false }: { dark?: boolean }) {
  const stroke = dark ? "#f2f0ea" : "#1a1c1e";
  return (
    <span className="flex items-center gap-3">
      <svg width="26" height="26" viewBox="0 0 26 26" fill="none" aria-hidden>
        <path
          d="M3 21 L13 4 L18 13 L21 8 L23 21"
          stroke={stroke}
          strokeWidth="2.2"
          strokeLinejoin="round"
          strokeLinecap="round"
        />
        <circle cx="13" cy="4" r="2.6" fill="#e84e10" />
      </svg>
      <span className="font-display text-xl tracking-wider">OPENEXIT</span>
    </span>
  );
}

function LanguageSwitch() {
  const { i18n } = useTranslation();
  return (
    <div className="flex items-center overflow-hidden rounded border border-line text-[13px] font-semibold">
      {SUPPORTED_LOCALES.map((loc) => (
        <button
          key={loc}
          type="button"
          onClick={() => setLocale(loc as Locale)}
          aria-pressed={i18n.language === loc}
          className={
            i18n.language === loc
              ? "bg-ink px-3 py-1.5 text-paper"
              : "px-3 py-1.5 text-muted hover:text-ink"
          }
        >
          {loc.toUpperCase()}
        </button>
      ))}
    </div>
  );
}

export default function Layout() {
  const { t } = useTranslation("common");
  return (
    <div className="flex min-h-screen flex-col">
      <header className="flex h-[76px] items-center justify-between border-b border-line px-6 lg:px-16">
        <Link to="/">
          <Logo />
        </Link>
        <nav className="flex items-center gap-6 lg:gap-9">
          <div className="hidden gap-7 text-[15px] font-medium sm:flex">
            <Link to="/docs">{t("nav.standard")}</Link>
            <Link to="/map">{t("nav.map")}</Link>
            <Link to="/panel">{t("nav.contribute")}</Link>
          </div>
          <LanguageSwitch />
          <Link
            to="/panel"
            className="rounded border-[1.5px] border-ink px-5 py-2 text-sm font-semibold"
          >
            {t("nav.signIn")}
          </Link>
        </nav>
      </header>

      <main className="flex-1">
        <Outlet />
      </main>

      <footer className="bg-granite px-6 py-12 text-[13px] text-ondark-muted lg:px-16">
        <div className="flex flex-col justify-between gap-10 md:flex-row">
          <div className="flex flex-col gap-2.5">
            <span className="font-display text-base tracking-wider text-paper">OPENEXIT</span>
            <span>{t("footer.runBy")}</span>
            <span className="font-mono">{t("footer.licences")}</span>
          </div>
          <div className="flex gap-14">
            <div className="flex flex-col gap-2">
              <span className="font-semibold text-paper">{t("footer.standard")}</span>
              <Link to="/docs">{t("footer.specification")}</Link>
              <Link to="/docs">{t("footer.schema")}</Link>
              <Link to="/docs">{t("footer.validator")}</Link>
            </div>
            <div className="flex flex-col gap-2">
              <span className="font-semibold text-paper">{t("footer.commons")}</span>
              <Link to="/docs">{t("footer.consuming")}</Link>
              <Link to="/docs">{t("footer.terms")}</Link>
              <Link to="/docs">{t("footer.governance")}</Link>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
