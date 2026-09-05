// Typed fetch client for the panel API. Public data comes from the commons
// build artifacts via deliberately dumb routes (swappable for a CDN later).

export interface ObjectFeature {
  role: "exit" | "landing" | "parking" | "gearup" | "trailhead";
  name?: string;
  position: {
    lat: number;
    lon: number;
    elevationM?: number;
    precisionM?: number;
    pinConfirmed?: boolean;
  };
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

export interface ObjectDocument {
  schemaVersion: string;
  id: string;
  name: string;
  country: string;
  region?: string;
  city?: string;
  status: string;
  access: string;
  sensitivity: string;
  objectType?: "building" | "antenna" | "span" | "earth";
  provenance: { source: string; contributor?: string | null; contributedAt: string }[];
  updatedAt: string;
  features: ObjectFeature[];
  guide?: Record<string, Record<string, string>>;
}

// Where public object data comes from.
//
// With the panel deployed, its routes serve the local commons clone, which can
// be fresher than what has reached GitHub. Without it -- a static build of this
// site on its own -- the same artifacts are read straight from the CDN, which is
// the pattern docs/consuming.md prescribes to every other consumer. Reading our
// own published data the way we tell everyone else to is a useful check on
// whether that advice actually works.
//
// VITE_DATA_BASE selects: unset means the panel API, otherwise a base URL such
// as https://cdn.jsdelivr.net/gh/OpenExits/commons@main
const DATA_BASE = (import.meta.env.VITE_DATA_BASE ?? "").replace(/\/$/, "");

/** False when this build ships without a panel behind it. */
export const PANEL_ENABLED = import.meta.env.VITE_PANEL_ENABLED !== "false";

export const OBJECTS_GEOJSON_URL = DATA_BASE
  ? `${DATA_BASE}/build/objects.geojson`
  : "/api/v1/public/data/objects.geojson";

export async function fetchObject(path: string): Promise<ObjectDocument> {
  const url = DATA_BASE
    ? `${DATA_BASE}/objects/${path}`
    : `/api/v1/public/objects/${path}`;
  const resp = await fetch(url);
  if (!resp.ok) throw new Error(`object fetch failed: ${resp.status}`);
  return (await resp.json()) as ObjectDocument;
}
