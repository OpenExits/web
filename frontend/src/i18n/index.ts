import i18n from "i18next";
import { initReactI18next } from "react-i18next";

import enCommon from "./locales/en/common.json";
import enHome from "./locales/en/home.json";
import enModeration from "./locales/en/moderation.json";
import enSite from "./locales/en/site.json";
import enWizard from "./locales/en/wizard.json";
import frCommon from "./locales/fr/common.json";
import frHome from "./locales/fr/home.json";
import frModeration from "./locales/fr/moderation.json";
import frSite from "./locales/fr/site.json";
import frWizard from "./locales/fr/wizard.json";

export const SUPPORTED_LOCALES = ["en", "fr"] as const;
export type Locale = (typeof SUPPORTED_LOCALES)[number];

function initialLocale(): Locale {
  try {
    const saved = localStorage.getItem("openexits.locale");
    if (saved === "en" || saved === "fr") return saved;
  } catch {
    /* storage unavailable */
  }
  return navigator.language?.toLowerCase().startsWith("fr") ? "fr" : "en";
}

i18n.use(initReactI18next).init({
  resources: {
    en: { common: enCommon, home: enHome, site: enSite, wizard: enWizard, moderation: enModeration },
    fr: { common: frCommon, home: frHome, site: frSite, wizard: frWizard, moderation: frModeration },
  },
  lng: initialLocale(),
  fallbackLng: "en",
  defaultNS: "common",
  interpolation: { escapeValue: false },
});

export function setLocale(locale: Locale) {
  i18n.changeLanguage(locale);
  try {
    localStorage.setItem("openexits.locale", locale);
  } catch {
    /* storage unavailable */
  }
}

export default i18n;
