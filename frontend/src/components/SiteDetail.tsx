import { Link } from "react-router";
import { useTranslation } from "react-i18next";
import type { MeasurementValue, SiteDocument } from "../lib/api";
import CommunitySection from "./CommunitySection";

const SUITABILITY_ORDER = ["slick", "sliderOff", "sliderUp", "wingsuit", "tracksuit", "staticLine"];
const MEASUREMENT_ORDER = ["rockdrop", "heightAgl", "totalHeight", "distanceToTalus", "flyableAltitude", "minGlideRatio"];

function statusBadgeClass(status: string): string {
  if (status === "open") return "bg-[#e5efe0] text-pass";
  if (status === "seasonal") return "bg-warnbg text-warntext";
  return "bg-[#fbe4e2] text-[#8f231d]";
}

export default function SiteDetail({ site, sitePath }: { site: SiteDocument; sitePath?: string }) {
  const { t } = useTranslation(["site", "common"]);
  const mainExit = site.features.find((f) => f.role === "exit");
  const pos = mainExit?.position;
  const measurements = (mainExit?.measurements ?? {}) as Record<string, MeasurementValue>;
  const suitability = mainExit?.suitability ?? {};
  const firstProv = site.provenance[0];

  return (
    <div className="flex h-full flex-col gap-4 overflow-y-auto bg-[#f7f5ef] p-6">
      {/* Identity */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex flex-col gap-1">
          <h2 className="font-display text-2xl">{site.name}</h2>
          <span className="text-[13px] text-muted">
            {site.country}
            {site.region ? ` · ${site.region}` : ""}
            {site.city ? ` · ${site.city}` : ""}
          </span>
          {pos && (
            <span className="font-mono text-xs text-muted">
              {pos.lat.toFixed(5)}, {pos.lon.toFixed(5)}
              {pos.elevationM != null ? ` · ${pos.elevationM} m MSL` : ""}
            </span>
          )}
        </div>
        <div className="flex flex-col items-end gap-1.5">
          <span className={`rounded px-2.5 py-1 text-xs font-bold ${statusBadgeClass(site.status)}`}>
            {t(`site:status.${site.status}`)}
          </span>
          <span className="rounded bg-[#eee9db] px-2.5 py-1 text-xs font-bold text-warntext">
            {t(`site:access.${site.access}`)}
          </span>
        </div>
      </div>

      {/* Features */}
      <div className="flex flex-wrap gap-2">
        {site.features.map((f, i) => (
          <span
            key={i}
            className={
              f.role === "landing"
                ? "rounded border border-pass px-3 py-1.5 text-[13px] font-medium text-pass"
                : i === 0
                  ? "rounded bg-ink px-3 py-1.5 text-[13px] font-semibold text-paper"
                  : "rounded border border-line bg-white px-3 py-1.5 text-[13px] font-medium"
            }
          >
            {f.name || t(`site:roles.${f.role}`)}
          </span>
        ))}
      </div>

      {/* Suitability */}
      {mainExit && (
        <div className="flex flex-wrap gap-1.5">
          {SUITABILITY_ORDER.filter((k) => k in suitability).map((k) => (
            <span
              key={k}
              className={
                suitability[k]
                  ? "rounded bg-[#efece2] px-2.5 py-1 text-xs font-semibold"
                  : "rounded bg-[#f4f2ec] px-2.5 py-1 text-xs font-semibold text-[#b0aca0] line-through"
              }
            >
              {t(`site:suitability.${k}`)}
            </span>
          ))}
        </div>
      )}

      {/* Measurements */}
      {mainExit && (
        <div className="flex flex-col gap-2.5 rounded-md border border-line bg-white px-4 py-3.5 text-[13px]">
          {MEASUREMENT_ORDER.filter((k) => measurements[k]).map((k) => {
            const m = measurements[k];
            const label =
              k === "heightAgl"
                ? t("site:measurements.heightAgl", { reference: m.reference })
                : t(`site:measurements.${k}`);
            const value = k === "minGlideRatio" ? `${m.value}` : `${m.valueM} m`;
            return (
              <div key={k} className="flex items-baseline justify-between gap-3">
                <span className="text-[#4a4c46]">{label}</span>
                <span className="font-mono font-medium">
                  {value}{" "}
                  {m.method && (
                    <span className="text-[11px] text-faint">
                      {m.method} · {m.measuredAt}
                    </span>
                  )}
                </span>
              </div>
            );
          })}
          {mainExit.exitDirectionDeg != null && (
            <div className="flex items-baseline justify-between gap-3">
              <span className="text-[#4a4c46]">{t("site:measurements.exitDirection")}</span>
              <span className="font-mono font-medium">
                {mainExit.exitDirectionDeg}° {t("site:measurements.trueSuffix")}
              </span>
            </div>
          )}
          {mainExit.approachTimeMin != null && (
            <div className="flex items-baseline justify-between gap-3">
              <span className="text-[#4a4c46]">{t("site:measurements.approach")}</span>
              <span className="font-mono font-medium">
                {mainExit.approachTimeMin} {t("site:measurements.minSuffix")}
              </span>
            </div>
          )}
        </div>
      )}

      {/* Safety notice — rule OE-R09, always visible */}
      <div className="flex gap-2.5 rounded-md border border-warnline bg-warnbg px-3.5 py-3">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" className="mt-0.5 shrink-0" aria-hidden>
          <path d="M12 3 L22 20 H2 Z" stroke="#8a5a0a" strokeWidth="2" strokeLinejoin="round" />
          <path d="M12 10 V14.5" stroke="#8a5a0a" strokeWidth="2" strokeLinecap="round" />
          <circle cx="12" cy="17.2" r="1.2" fill="#8a5a0a" />
        </svg>
        <p className="text-xs leading-relaxed text-warntext">
          <strong>{t("common:safety.title")}</strong> {t("common:safety.body")}
        </p>
      </div>

      {/* Community layer (ADR-7) */}
      {sitePath && <CommunitySection sitePath={sitePath} />}

      <div className="flex gap-2.5">
        {sitePath ? (
          <Link
            to={`/panel/wizard?correct=${sitePath}`}
            className="flex-1 rounded border-[1.5px] border-ink py-3 text-center text-sm font-bold"
          >
            {t("site:panel.suggestChange")}
          </Link>
        ) : (
          <span className="flex-1 rounded border-[1.5px] border-line py-3 text-center text-sm font-bold text-faint">
            {t("site:panel.suggestChange")}
          </span>
        )}
        <button
          type="button"
          disabled
          className="flex-1 cursor-not-allowed rounded bg-ink py-3 text-sm font-bold text-paper opacity-50"
        >
          {t("site:panel.fullGuide")}
        </button>
      </div>

      {firstProv && (
        <span className="text-xs text-faint">
          {t("site:panel.contributedBy")}{" "}
          <span className="font-semibold text-muted">@{firstProv.contributor ?? "?"}</span>
          {" · "}
          {firstProv.contributedAt}
        </span>
      )}
    </div>
  );
}
