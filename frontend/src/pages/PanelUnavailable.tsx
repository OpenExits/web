import { useTranslation } from "react-i18next";

/**
 * Shown in place of the panel when this build ships without a backend.
 *
 * The alternative — rendering the real sign-in form against an API that is not
 * there — would let someone fill in a registration that silently fails. Saying
 * plainly that contribution is not open yet is both truthful and more useful:
 * it points at the routes that do work today.
 */
export default function PanelUnavailable() {
  const { t } = useTranslation("common");
  return (
    <div className="mx-auto flex w-full max-w-xl flex-col gap-5 px-6 py-20">
      <h1 className="font-display text-3xl">{t("panelUnavailable.title")}</h1>
      <p className="text-[15px] leading-relaxed">{t("panelUnavailable.body")}</p>
      <p className="text-[15px] leading-relaxed text-muted">
        {t("panelUnavailable.meanwhile")}
      </p>
      <div className="flex flex-wrap gap-3 pt-2">
        <a
          href="https://github.com/OpenExits/commons/blob/main/CONTRIBUTING.md"
          className="rounded bg-signal px-5 py-3 font-bold text-white"
        >
          {t("panelUnavailable.contributing")}
        </a>
        <a
          href="https://github.com/OpenExits"
          className="rounded border-[1.5px] border-ink px-5 py-3 font-semibold"
        >
          {t("panelUnavailable.github")}
        </a>
      </div>
    </div>
  );
}
