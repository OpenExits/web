import { useTranslation } from "react-i18next";

/**
 * Terms of use, including the liability and no-warranty language.
 *
 * DRAFT — written to be reviewed by a lawyer, not in place of one. The
 * substance it must carry: this data is unverified, review is a conformance
 * check rather than a verification, and nobody acting for the project is
 * telling anyone that a jump is safe.
 */
export default function TermsPage() {
  const { t } = useTranslation("terms");
  const sections = [
    "nature",
    "review",
    "noWarranty",
    "yourResponsibility",
    "contributions",
    "sensitive",
    "licences",
    "people",
    "changes",
  ] as const;

  return (
    <div className="mx-auto w-full max-w-3xl px-6 py-16">
      <h1 className="font-display text-4xl">{t("title")}</h1>
      <p className="mt-2 text-sm text-muted">{t("updated")}</p>

      <div className="mt-8 rounded border-[1.5px] border-signal bg-[#fdf0e9] p-5">
        <p className="text-[15px] font-bold leading-relaxed">{t("headline")}</p>
      </div>

      {sections.map((key) => (
        <section key={key} className="mt-9">
          <h2 className="font-display text-xl">{t(`${key}.title`)}</h2>
          <p className="mt-2 whitespace-pre-line text-[15px] leading-relaxed">
            {t(`${key}.body`)}
          </p>
        </section>
      ))}

      <p className="mt-12 text-sm text-muted">{t("contact")}</p>
    </div>
  );
}
