import { useTranslation } from "react-i18next";

export default function Placeholder({ title }: { title: string }) {
  const { t } = useTranslation("common");
  return (
    <div className="flex flex-col items-center gap-4 px-6 py-32 text-center">
      <h1 className="font-display text-3xl">{title}</h1>
      <p className="text-muted">{t("comingSoon")}</p>
    </div>
  );
}
