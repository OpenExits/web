// Typed fetch client for the panel API. Public data comes from the commons
// build artifacts via deliberately dumb routes (swappable for a CDN later).

export interface SiteFeature {
  role: "exit" | "landing" | "parking" | "gearup" | "trailhead";
  name?: string;
  position: {
    lat: number;
    lon: number;
    elevationM?: number;
    precisionM?: number;
    pinConfirmed?: boolean;
  };
  objectType?: "building" | "antenna" | "span" | "earth";
  suitability?: Record<string, boolean>;
  exitDirectionDeg?: number;
  approachTimeMin?: number;
  surface?: string;
  measurements?: Record<string, unknown>;
}

export interface MeasurementValue {
  valueM?: number;
  value?: number;
  reference?: string;
  method?: string;
  measuredAt?: string;
}

export interface SiteDocument {
  schemaVersion: string;
  id: string;
  name: string;
  country: string;
  region?: string;
  city?: string;
  status: string;
  access: string;
  sensitivity: string;
  provenance: { source: string; contributor?: string | null; contributedAt: string }[];
  updatedAt: string;
  features: SiteFeature[];
  guide?: Record<string, Record<string, string>>;
}

export const SITES_GEOJSON_URL = "/api/v1/public/data/sites.geojson";

export async function fetchSite(path: string): Promise<SiteDocument> {
  const resp = await fetch(`/api/v1/public/sites/${path}`);
  if (!resp.ok) throw new Error(`site fetch failed: ${resp.status}`);
  return (await resp.json()) as SiteDocument;
}
