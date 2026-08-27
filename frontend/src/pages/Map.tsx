import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import MapView from "../components/map/MapView";
import SiteDetail from "../components/SiteDetail";
import { fetchSite, type SiteDocument } from "../lib/api";

type PanelState =
  | { kind: "closed" }
  | { kind: "loading"; path: string }
  | { kind: "loaded"; path: string; site: SiteDocument }
  | { kind: "error"; path: string };

export default function MapPage() {
  const { t } = useTranslation("site");
  const [panel, setPanel] = useState<PanelState>({ kind: "closed" });

  const openSite = useCallback((path: string) => {
    setPanel({ kind: "loading", path });
  }, []);

  useEffect(() => {
    if (panel.kind !== "loading") return;
    let cancelled = false;
    fetchSite(panel.path)
      .then((site) => {
        if (!cancelled) setPanel({ kind: "loaded", path: panel.path, site });
      })
      .catch(() => {
        if (!cancelled) setPanel({ kind: "error", path: panel.path });
      });
    return () => {
      cancelled = true;
    };
  }, [panel]);

  return (
    <div className="relative h-[calc(100vh-76px)] w-full">
      <MapView onSiteClick={openSite} />
      {panel.kind !== "closed" && (
        <aside className="absolute bottom-0 right-0 top-0 w-full max-w-[424px] border-l border-line bg-[#f7f5ef] shadow-xl">
          <button
            type="button"
            aria-label="close"
            onClick={() => setPanel({ kind: "closed" })}
            className="absolute right-3 top-3 z-10 flex h-9 w-9 items-center justify-center rounded-full bg-white shadow"
          >
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden>
              <path d="M2 2 L12 12 M12 2 L2 12" stroke="#1a1c1e" strokeWidth="2" strokeLinecap="round" />
            </svg>
          </button>
          {panel.kind === "loading" && (
            <p className="p-6 text-sm text-muted">{t("panel.loading")}</p>
          )}
          {panel.kind === "error" && (
            <p className="p-6 text-sm text-warntext">{t("panel.error")}</p>
          )}
          {panel.kind === "loaded" && <SiteDetail site={panel.site} />}
        </aside>
      )}
    </div>
  );
}
